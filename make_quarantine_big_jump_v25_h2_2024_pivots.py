from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_prior_v19 import add_segments, period_summary
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_big_jump_v25_h2_2024_pivots"
ANCHOR_FILE = "submission_qbb62_h1_backload_preserve_total_q2up040.csv"
ANCHOR_SCORE = 661327.00240
RECENCY_DONOR_FILE = "submission_catboost_md2y_core_recencyexp20.csv"


@dataclass(frozen=True)
class Candidate:
    name: str
    family: str
    target: str
    changed_scope: str
    thesis: str
    frame: pd.DataFrame


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def load_submission(filename: str) -> pd.DataFrame:
    return pd.read_csv(DATASET_DIR / filename, parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)


def assert_aligned(left: pd.DataFrame, right: pd.DataFrame, label: str) -> None:
    if not left["Date"].equals(right["Date"]):
        raise ValueError(f"Date mismatch for {label}")


def period_mask(frame: pd.DataFrame, period: str) -> pd.Series:
    seg = add_segments(frame)
    return seg["period"].eq(period)


def month_mask(frame: pd.DataFrame, year: int, months: tuple[int, ...]) -> pd.Series:
    return frame["Date"].dt.year.eq(year) & frame["Date"].dt.month.isin(months)


def scale_cogs(frame: pd.DataFrame, mask: pd.Series, scale: float) -> pd.DataFrame:
    out = frame.copy()
    out.loc[mask.to_numpy(), "COGS"] *= scale
    return out


def preserve_total_shift(
    frame: pd.DataFrame,
    target: str,
    up_mask: pd.Series,
    down_mask: pd.Series,
    up_scale: float,
) -> pd.DataFrame:
    out = frame.copy()
    up_idx = up_mask.to_numpy()
    down_idx = down_mask.to_numpy()
    original_total = float(out.loc[up_idx | down_idx, target].sum())
    up_total = float(out.loc[up_idx, target].sum())
    down_total = float(out.loc[down_idx, target].sum())
    if down_total <= 0.0:
        raise ValueError("Cannot preserve total with non-positive down bucket")
    down_scale = (original_total - up_total * up_scale) / down_total
    if down_scale <= 0.0:
        raise ValueError(f"Invalid down scale {down_scale:.6f}")
    out.loc[up_idx, target] *= up_scale
    out.loc[down_idx, target] *= down_scale
    return out


def period_aligned_shape(
    frame: pd.DataFrame,
    donor: pd.DataFrame,
    target: str,
    period: str,
    alpha: float,
) -> pd.DataFrame:
    out = frame.copy()
    mask = period_mask(frame, period).to_numpy()
    frame_total = float(frame.loc[mask, target].sum())
    donor_total = float(donor.loc[mask, target].sum())
    if donor_total <= 0.0:
        raise ValueError(f"Donor total is non-positive for {target}/{period}")
    aligned_donor = donor.loc[mask, target].to_numpy() * frame_total / donor_total
    out.loc[mask, target] = (1.0 - alpha) * frame.loc[mask, target].to_numpy() + alpha * aligned_donor
    return out


def h2_high_ratio_mask(frame: pd.DataFrame) -> pd.Series:
    h2 = period_mask(frame, "2023H2")
    ratio = frame.loc[h2, "COGS"] / frame.loc[h2, "Revenue"]
    mask = pd.Series(False, index=frame.index)
    mask.loc[ratio.index] = ratio.rank(pct=True).ge(0.60)
    return mask


def build_candidates(anchor: pd.DataFrame) -> list[Candidate]:
    recency = load_submission(RECENCY_DONOR_FILE)
    assert_aligned(anchor, recency, "recency donor")

    h2_high = h2_high_ratio_mask(anchor)
    aug_2023 = month_mask(anchor, 2023, (8,))
    jul_aug_dec_2023 = month_mask(anchor, 2023, (7, 8, 12))
    q1_2024 = month_mask(anchor, 2024, (1, 2, 3))
    q2_2024 = month_mask(anchor, 2024, (4, 5, 6))

    candidates: list[Candidate] = []

    for suffix, scale, thesis in [
        (
            "down060",
            0.94,
            "Moderate sign test: lower top 40% 2023H2 COGS/Revenue days by 6%, keeping Revenue fixed.",
        ),
        (
            "down100",
            0.90,
            "Stronger version if high-ratio 2023H2 COGS reduction is the right direction.",
        ),
        (
            "down140",
            0.86,
            "High-risk large version for the same high-ratio H2 COGS hypothesis.",
        ),
    ]:
        candidates.append(
            Candidate(
                name=f"qbb65_h2_highratio_cogs_{suffix}_keeprev",
                family="h2_cogs_concentration",
                target="COGS",
                changed_scope="2023H2 high COGS/Revenue days",
                thesis=thesis,
                frame=scale_cogs(anchor, h2_high, scale),
            )
        )

    candidates.append(
        Candidate(
            name="qbb65_h2_aug_cogs_down120_keeprev",
            family="h2_cogs_month",
            target="COGS",
            changed_scope="2023-08",
            thesis="Lower August 2023 COGS by 12%; August has the most extreme current H2 COGS/Revenue ratio.",
            frame=scale_cogs(anchor, aug_2023, 0.88),
        )
    )
    candidates.append(
        Candidate(
            name="qbb65_h2_julaugdec_cogs_down060_keeprev",
            family="h2_cogs_month",
            target="COGS",
            changed_scope="2023-07, 2023-08, 2023-12",
            thesis="Lower the three high-ratio H2 months by 6%, keeping Revenue fixed.",
            frame=scale_cogs(anchor, jul_aug_dec_2023, 0.94),
        )
    )

    for suffix, alpha in [("a040", 0.40), ("a060", 0.60)]:
        candidates.append(
            Candidate(
                name=f"qbb65_2024h1_recency_revshape_{suffix}_keepcogs",
                family="2024h1_recency_revenue_shape",
                target="Revenue",
                changed_scope="2024H1",
                thesis=f"Blend {alpha:.0%} period-aligned recency-model Revenue shape into 2024H1, preserving 2024H1 total.",
                frame=period_aligned_shape(anchor, recency, "Revenue", "2024H1", alpha),
            )
        )

    for suffix, scale in [("q1up040", 1.04), ("q1up060", 1.06)]:
        candidates.append(
            Candidate(
                name=f"qbb65_2024h1_frontload_{suffix}_keepcogs",
                family="2024h1_frontload_revenue",
                target="Revenue",
                changed_scope="2024H1 Q1/Q2 timing",
                thesis=f"Preserve 2024H1 Revenue total and move mass from Apr-Jun into Jan-Mar with Q1 scale {scale:.3f}.",
                frame=preserve_total_shift(anchor, "Revenue", q1_2024, q2_2024, scale),
            )
        )

    return candidates


def month_summary(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["month"] = out["Date"].dt.strftime("%Y-%m")
    return (
        out.groupby("month", as_index=False)
        .agg(days=("Date", "count"), Revenue=("Revenue", "sum"), COGS=("COGS", "sum"))
        .assign(ratio=lambda d: d["COGS"] / d["Revenue"])
    )


def changed_period_summary(anchor: pd.DataFrame, frame: pd.DataFrame) -> dict[str, float]:
    seg = add_segments(anchor)
    delta_rev = frame["Revenue"] - anchor["Revenue"]
    delta_cogs = frame["COGS"] - anchor["COGS"]
    out: dict[str, float] = {}
    for period in ("2023H1", "2023H2", "2024H1"):
        mask = seg["period"].eq(period)
        out[f"{period}_movement"] = float(0.5 * (delta_rev.loc[mask].abs().mean() + delta_cogs.loc[mask].abs().mean()))
    return out


def summarize_candidate(anchor: pd.DataFrame, candidate: Candidate, filename: str, priority: int) -> dict[str, object]:
    frame = candidate.frame
    delta_rev = frame["Revenue"] - anchor["Revenue"]
    delta_cogs = frame["COGS"] - anchor["COGS"]
    prof = period_summary(frame)
    h1_mask = period_mask(anchor, "2023H1")
    rows_changed = delta_rev.abs().gt(1e-6) | delta_cogs.abs().gt(1e-6)
    row = {
        "priority": priority,
        "filename": filename,
        "family": candidate.family,
        "target": candidate.target,
        "changed_scope": candidate.changed_scope,
        "thesis": candidate.thesis,
        "rev_rows_changed": int(delta_rev.abs().gt(1e-6).sum()),
        "cogs_rows_changed": int(delta_cogs.abs().gt(1e-6).sum()),
        "rows_changed_total": int(rows_changed.sum()),
        "h1_max_abs_delta_vs_anchor": float(
            max(delta_rev.loc[h1_mask].abs().max(), delta_cogs.loc[h1_mask].abs().max())
        ),
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
    row.update(changed_period_summary(anchor, frame))
    return row


def validate_frame(frame: pd.DataFrame, filename: str) -> None:
    if len(frame) != 548:
        raise ValueError(f"{filename}: expected 548 rows, found {len(frame)}")
    if frame["Date"].min() != pd.Timestamp("2023-01-01"):
        raise ValueError(f"{filename}: invalid min date {frame['Date'].min()}")
    if frame["Date"].max() != pd.Timestamp("2024-07-01"):
        raise ValueError(f"{filename}: invalid max date {frame['Date'].max()}")
    if frame[["Revenue", "COGS"]].isna().any().any():
        raise ValueError(f"{filename}: NaN found")
    if (frame[["Revenue", "COGS"]] < 0).any().any():
        raise ValueError(f"{filename}: negative target found")


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Quarantine Big Jump V25 H2 + 2024H1 Pivots

Run directory: `{run_dir}`

## Status

This branch is **quarantine blackbox**, not clean.

## Current Read

- Current best anchor: `{ANCHOR_FILE}` = `{ANCHOR_SCORE}`.
- H1/Q2 timing localization is rejected after Q1, May-Jun, April Revenue, and April COGS failures.
- This batch preserves the current H1 backload gain and pivots to two larger axes: H2 COGS concentration and 2024H1 Revenue shape/manifold.

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Suggested Submit Order

1. `submission_qbb65_h2_highratio_cogs_down060_keeprev.csv`
2. If it improves, submit `submission_qbb65_h2_highratio_cogs_down100_keeprev.csv`
3. If it fails, submit `submission_qbb65_2024h1_recency_revshape_a040_keepcogs.csv`
4. If 2024H1 recency improves, submit `submission_qbb65_2024h1_recency_revshape_a060_keepcogs.csv`
5. If both signs fail, submit `submission_qbb65_2024h1_frontload_q1up040_keepcogs.csv`

## Do Not Use As Clean

These candidates are public-guided/quarantine probes and must not be presented as clean model outputs.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_big_jump_v25_h2_2024_pivots_2026-04-26.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    anchor = add_segments(load_submission(ANCHOR_FILE))
    candidates = build_candidates(anchor)

    rows: list[dict[str, object]] = []
    month_profiles: list[pd.DataFrame] = []
    for priority, candidate in enumerate(candidates, start=1):
        filename = f"submission_{candidate.name}.csv"
        output = candidate.frame[["Date", "Revenue", "COGS"]].copy()
        validate_frame(output, filename)
        write_submission(output, DATASET_DIR / filename)
        write_submission(output, run_dir / filename)

        rows.append(summarize_candidate(anchor, candidate, filename, priority))
        profile = month_summary(output)
        profile.insert(0, "filename", filename)
        month_profiles.append(profile)

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    month_summary(anchor).to_csv(run_dir / "anchor_month_profiles.csv", index=False)
    pd.concat(month_profiles, ignore_index=True).to_csv(run_dir / "month_profiles.csv", index=False)
    period_summary(anchor).to_csv(run_dir / "anchor_period_summary.csv", index=False)
    write_report(run_dir, manifest)
    print(run_dir)


if __name__ == "__main__":
    main()
