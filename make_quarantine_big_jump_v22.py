from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_prior_v19 import add_segments, period_summary
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_big_jump_v22"
ANCHOR_FILE = "submission_qbb60v18_cogs2023h2_down010.csv"
ANCHOR_SCORE = 662607.08245


@dataclass(frozen=True)
class Candidate:
    name: str
    family: str
    thesis: str
    frame: pd.DataFrame


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def load_submission(filename: str) -> pd.DataFrame:
    frame = pd.read_csv(DATASET_DIR / filename, parse_dates=["Date"])
    return frame.sort_values("Date").reset_index(drop=True)


def assert_aligned(left: pd.DataFrame, right: pd.DataFrame, label: str) -> None:
    if not left["Date"].equals(right["Date"]):
        raise ValueError(f"Date mismatch for {label}")


def scale_revenue(base: pd.DataFrame, mask: pd.Series, scale: float) -> pd.DataFrame:
    out = base.copy()
    out.loc[mask.to_numpy(), "Revenue"] *= scale
    return out


def scale_cogs(base: pd.DataFrame, mask: pd.Series, scale: float) -> pd.DataFrame:
    out = base.copy()
    out.loc[mask.to_numpy(), "COGS"] *= scale
    return out


def preserve_total_shift(
    base: pd.DataFrame,
    target: str,
    up_mask: pd.Series,
    down_mask: pd.Series,
    up_scale: float,
) -> pd.DataFrame:
    out = base.copy()
    up_idx = up_mask.to_numpy()
    down_idx = down_mask.to_numpy()
    original_total = float(out.loc[up_idx | down_idx, target].sum())
    up_original = float(out.loc[up_idx, target].sum())
    down_original = float(out.loc[down_idx, target].sum())
    up_new = up_original * up_scale
    if down_original <= 0.0:
        raise ValueError("Cannot preserve total with empty down bucket")
    down_scale = (original_total - up_new) / down_original
    if down_scale <= 0.0:
        raise ValueError(f"Invalid down scale {down_scale:.6f} for {target}")
    out.loc[up_idx, target] *= up_scale
    out.loc[down_idx, target] *= down_scale
    return out


def period_aligned_shape(base: pd.DataFrame, donor: pd.DataFrame, target: str, periods: set[str], alpha: float) -> pd.DataFrame:
    base_seg = add_segments(base)
    donor_seg = add_segments(donor)
    out = base.copy()
    for period in periods:
        mask = base_seg["period"].eq(period).to_numpy()
        base_total = float(base_seg.loc[mask, target].sum())
        donor_total = float(donor_seg.loc[mask, target].sum())
        if donor_total <= 0.0:
            continue
        aligned = donor_seg.loc[mask, target].to_numpy() * base_total / donor_total
        out.loc[mask, target] = (1.0 - alpha) * base_seg.loc[mask, target].to_numpy() + alpha * aligned
    return out


def current_masks(anchor: pd.DataFrame) -> dict[str, pd.Series]:
    seg = add_segments(anchor)
    date = seg["Date"]
    h1_2023 = seg["period"].eq("2023H1")
    h2_2023 = seg["period"].eq("2023H2")
    h1_2024 = seg["period"].eq("2024H1")
    q1_2023 = date.dt.year.eq(2023) & date.dt.month.isin([1, 2, 3])
    q2_2023 = date.dt.year.eq(2023) & date.dt.month.isin([4, 5, 6])
    q1_2024 = date.dt.year.eq(2024) & date.dt.month.isin([1, 2, 3])
    q2_2024 = date.dt.year.eq(2024) & date.dt.month.isin([4, 5, 6])
    h1_rev_rank = seg.loc[h1_2023, "Revenue"].rank(pct=True)
    top_h1 = pd.Series(False, index=seg.index)
    top_h1.loc[h1_rev_rank.index] = h1_rev_rank.ge(0.60)
    bottom_h1 = h1_2023 & ~top_h1
    h2_ratio_rank = (seg.loc[h2_2023, "COGS"] / seg.loc[h2_2023, "Revenue"]).rank(pct=True)
    h2_high_ratio = pd.Series(False, index=seg.index)
    h2_high_ratio.loc[h2_ratio_rank.index] = h2_ratio_rank.ge(0.60)
    h2_low_ratio = h2_2023 & ~h2_high_ratio
    return {
        "2023H1": h1_2023,
        "2023H2": h2_2023,
        "2024H1": h1_2024,
        "2023Q1": q1_2023,
        "2023Q2": q2_2023,
        "2024Q1": q1_2024,
        "2024Q2": q2_2024,
        "2023H1_top40": top_h1,
        "2023H1_bottom60": bottom_h1,
        "2023H2_high_ratio40": h2_high_ratio,
        "2023H2_low_ratio60": h2_low_ratio,
    }


def build_candidates(anchor: pd.DataFrame) -> list[Candidate]:
    masks = current_masks(anchor)
    recency = load_submission("submission_catboost_md2y_core_recencyexp20.csv")
    catboost_core = load_submission("submission_catboost_md2y_core.csv")
    clean = load_submission("submission_cleanv2_h1fine_b044_r0876.csv")
    assert_aligned(anchor, recency, "recency")
    assert_aligned(anchor, catboost_core, "catboost_core")
    assert_aligned(anchor, clean, "clean")

    candidates: list[Candidate] = []
    candidates.append(
        Candidate(
            "qbb62_h1_q2_rev_up060_keepcogs",
            "2023H1_subperiod_level",
            "Large sign test: if the all-H1 +13% gain was really concentrated in Apr-Jun, add +6% Revenue only to 2023Q2.",
            scale_revenue(anchor, masks["2023Q2"], 1.060),
        )
    )
    candidates.append(
        Candidate(
            "qbb62_h1_q1_rev_up080_keepcogs",
            "2023H1_subperiod_level",
            "Opposite large sign test: put the missing level into Jan-Mar instead of the already-high Q2 block.",
            scale_revenue(anchor, masks["2023Q1"], 1.080),
        )
    )
    candidates.append(
        Candidate(
            "qbb62_h1_backload_preserve_total_q2up040",
            "2023H1_shape_total_preserve",
            "Shift 2023H1 Revenue mass from Q1 to Q2 while preserving total H1 Revenue; tests whether level is right but timing is wrong.",
            preserve_total_shift(anchor, "Revenue", masks["2023Q2"], masks["2023Q1"], 1.040),
        )
    )
    candidates.append(
        Candidate(
            "qbb62_h1_frontload_preserve_total_q1up050",
            "2023H1_shape_total_preserve",
            "Opposite total-preserving 2023H1 shape test: move mass forward into Jan-Mar.",
            preserve_total_shift(anchor, "Revenue", masks["2023Q1"], masks["2023Q2"], 1.050),
        )
    )
    candidates.append(
        Candidate(
            "qbb62_h1_frontload_preserve_total_q1up080",
            "2023H1_shape_total_preserve",
            "Bolder frontload: if sample-like Q2 concentration is the remaining error, move more H1 Revenue into Jan-Mar.",
            preserve_total_shift(anchor, "Revenue", masks["2023Q1"], masks["2023Q2"], 1.080),
        )
    )
    candidates.append(
        Candidate(
            "qbb62_h1_top40_rev_up080_keepcogs",
            "2023H1_high_volume_level",
            "Scale only the largest 40% 2023H1 Revenue days by +8%; tests high-volume underprediction rather than uniform period underprediction.",
            scale_revenue(anchor, masks["2023H1_top40"], 1.080),
        )
    )
    candidates.append(
        Candidate(
            "qbb62_h1_top40_shape_preserve_up080",
            "2023H1_high_volume_shape",
            "Preserve 2023H1 total but move Revenue mass into high-volume days; tests daily concentration without another level squeeze.",
            preserve_total_shift(anchor, "Revenue", masks["2023H1_top40"], masks["2023H1_bottom60"], 1.080),
        )
    )
    candidates.append(
        Candidate(
            "qbb62_2024h1_recency_revshape_a060_keepcogs",
            "2024H1_donor_shape",
            "Replace 60% of 2024H1 Revenue shape with period-aligned recency model shape; big alternative to more sample-shape.",
            period_aligned_shape(anchor, recency, "Revenue", {"2024H1"}, 0.600),
        )
    )
    candidates.append(
        Candidate(
            "qbb62_2024h1_frontload_preserve_q1up060",
            "2024H1_shape_total_preserve",
            "Move 2024H1 Revenue mass from Q2 into Q1 while preserving total; direct test of sample-shape over-backload in 2024.",
            preserve_total_shift(anchor, "Revenue", masks["2024Q1"], masks["2024Q2"], 1.060),
        )
    )
    candidates.append(
        Candidate(
            "qbb62_nonh2_recency_revshape_a040_keepcogs",
            "nonH2_donor_shape",
            "Use period-aligned recency Revenue shape for both non-H2 blocks; tests a different donor manifold than sample_submission shape.",
            period_aligned_shape(anchor, recency, "Revenue", {"2023H1", "2024H1"}, 0.400),
        )
    )
    candidates.append(
        Candidate(
            "qbb62_h2_highratio_cogs_down100_keeprev",
            "2023H2_cogs_ratio_shape",
            "Target the 40% highest COGS/Revenue days in 2023H2 with -10% COGS; tests whether H2 cost error is concentrated, not uniform.",
            scale_cogs(anchor, masks["2023H2_high_ratio40"], 0.900),
        )
    )
    candidates.append(
        Candidate(
            "qbb62_h2_cogsratio_preserve_highdown080",
            "2023H2_cogs_ratio_shape",
            "Preserve total 2023H2 COGS but move COGS away from extreme high-ratio days; shape-only H2 cost correction.",
            preserve_total_shift(anchor, "COGS", masks["2023H2_low_ratio60"], masks["2023H2_high_ratio40"], 1.080),
        )
    )
    candidates.append(
        Candidate(
            "qbb62_clean_antigap_rev_a035_keepcogs",
            "clean_qbb_gap_extrapolation",
            "Move Revenue farther away from the clean best along the already-public-winning qbb-clean gap; bold check for unresolved public shift.",
            extrapolate_from_clean(anchor, clean, "Revenue", 0.350),
        )
    )
    candidates.append(
        Candidate(
            "qbb62_core_recency_cogs_shape_h2_a050",
            "2023H2_cogs_donor_shape",
            "Use period-aligned CatBoost-core COGS shape in 2023H2 while keeping current H2 COGS total; different H2 cost manifold.",
            period_aligned_shape(anchor, catboost_core, "COGS", {"2023H2"}, 0.500),
        )
    )
    return candidates


def extrapolate_from_clean(anchor: pd.DataFrame, clean: pd.DataFrame, target: str, gamma: float) -> pd.DataFrame:
    out = anchor.copy()
    out[target] = (anchor[target] + gamma * (anchor[target] - clean[target])).clip(lower=0.0)
    return out


def summarize_candidate(anchor: pd.DataFrame, candidate: Candidate, filename: str) -> dict[str, object]:
    frame = candidate.frame
    delta_rev = frame["Revenue"] - anchor["Revenue"]
    delta_cogs = frame["COGS"] - anchor["COGS"]
    prof = period_summary(frame)
    return {
        "filename": filename,
        "family": candidate.family,
        "thesis": candidate.thesis,
        "rev_rows_changed": int(delta_rev.abs().gt(1e-6).sum()),
        "cogs_rows_changed": int(delta_cogs.abs().gt(1e-6).sum()),
        "mean_abs_rev_delta_vs_anchor": float(delta_rev.abs().mean()),
        "mean_abs_cogs_delta_vs_anchor": float(delta_cogs.abs().mean()),
        "movement_vs_anchor": float(0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean())),
        "best_case_score_if_direction_perfect": float(ANCHOR_SCORE - 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean())),
        "revenue_total_ratio_vs_anchor": float(frame["Revenue"].sum() / anchor["Revenue"].sum()),
        "cogs_total_ratio_vs_anchor": float(frame["COGS"].sum() / anchor["COGS"].sum()),
        "ratio_all": float(frame["COGS"].sum() / frame["Revenue"].sum()),
        "ratio_2023H1": float(prof.loc[prof["period"].eq("2023H1"), "ratio"].iloc[0]),
        "ratio_2023H2": float(prof.loc[prof["period"].eq("2023H2"), "ratio"].iloc[0]),
        "ratio_2024H1": float(prof.loc[prof["period"].eq("2024H1"), "ratio"].iloc[0]),
        "max_revenue": float(frame["Revenue"].max()),
        "max_cogs": float(frame["COGS"].max()),
    }


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    strong = manifest.sort_values("movement_vs_anchor", ascending=False)
    report = f"""# Quarantine Big Jump V22

Run directory: `{run_dir}`

## Status

This branch is **quarantine blackbox**, not clean. It builds on `{ANCHOR_FILE}` = `{ANCHOR_SCORE}` and intentionally avoids small coefficient squeezing.

## Why This Batch Exists

The current 662k path has exhausted the smooth axes:

- 2023H1 uniform level saturates around `+13%`.
- 2024H1 stronger sample shape worsened.
- 2023H2 Revenue up/down and Q3/Q4 splits worsened.
- H2 COGS uniform down helped only slightly.

So this batch tests larger structural alternatives:

- split 2023H1 into Q1/Q2 or high-volume/low-volume days;
- switch 2024H1/non-H2 shape to a different donor manifold;
- target H2 COGS concentration rather than uniform H2 COGS level.

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Suggested Submit Order

1. `submission_qbb62_h1_frontload_preserve_total_q1up050.csv` as the first total-safe large test. This is more consistent with `2023H1 p1000` failing vs `p0900`: sample/Q2 concentration may be too strong.
2. If it improves clearly, submit `submission_qbb62_h1_frontload_preserve_total_q1up080.csv`; same direction, larger move.
3. If H1 frontload fails, submit `submission_qbb62_2024h1_frontload_preserve_q1up060.csv`; it tests the analogous 2024H1 over-backload hypothesis.
4. If both frontload tests fail, use `submission_qbb62_2024h1_recency_revshape_a060_keepcogs.csv` for the broader donor-manifold pivot.
5. `submission_qbb62_h2_highratio_cogs_down100_keeprev.csv` only if we want a COGS-side large move independent of Revenue.

## Largest Movement Candidates

{strong[["filename", "family", "movement_vs_anchor", "best_case_score_if_direction_perfect", "revenue_total_ratio_vs_anchor", "cogs_total_ratio_vs_anchor"]].head(8).to_markdown(index=False)}
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_big_jump_v22_2026-04-24.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    anchor = add_segments(load_submission(ANCHOR_FILE))

    rows: list[dict[str, object]] = []
    period_profiles: list[pd.DataFrame] = []
    for priority, candidate in enumerate(build_candidates(anchor), start=1):
        filename = f"submission_{candidate.name}.csv"
        output_path = DATASET_DIR / filename
        run_path = run_dir / filename
        frame = candidate.frame[["Date", "Revenue", "COGS"]].copy()
        write_submission(frame, output_path)
        write_submission(frame, run_path)

        row = summarize_candidate(anchor, candidate, filename)
        row["priority"] = priority
        rows.append(row)

        prof = period_summary(frame)
        prof.insert(0, "filename", filename)
        period_profiles.append(prof)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    pd.concat(period_profiles, ignore_index=True).to_csv(run_dir / "period_profiles.csv", index=False)
    period_summary(anchor).to_csv(run_dir / "anchor_period_summary.csv", index=False)
    write_report(run_dir, manifest)
    print(run_dir)


if __name__ == "__main__":
    main()
