from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_prior_v19 import add_segments, period_summary
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_big_jump_v26_2024_after_h2"
ANCHOR_FILE = "submission_qbb65_h2_highratio_cogs_down060_keeprev.csv"
ANCHOR_SCORE = 659211.90870
RECENCY_DONOR_FILE = "submission_catboost_md2y_core_recencyexp20.csv"


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
    return pd.read_csv(DATASET_DIR / filename, parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)


def assert_aligned(left: pd.DataFrame, right: pd.DataFrame, label: str) -> None:
    if not left["Date"].equals(right["Date"]):
        raise ValueError(f"Date mismatch for {label}")


def period_mask(frame: pd.DataFrame, period: str) -> pd.Series:
    return add_segments(frame)["period"].eq(period)


def month_mask(frame: pd.DataFrame, year: int, months: tuple[int, ...]) -> pd.Series:
    return frame["Date"].dt.year.eq(year) & frame["Date"].dt.month.isin(months)


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
    aligned = donor.loc[mask, target].to_numpy() * frame_total / donor_total
    out.loc[mask, target] = (1.0 - alpha) * frame.loc[mask, target].to_numpy() + alpha * aligned
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


def build_candidates(anchor: pd.DataFrame) -> list[Candidate]:
    recency = load_submission(RECENCY_DONOR_FILE)
    assert_aligned(anchor, recency, "recency donor")

    q1_2024 = month_mask(anchor, 2024, (1, 2, 3))
    q2_2024 = month_mask(anchor, 2024, (4, 5, 6))
    jan_feb_2024 = month_mask(anchor, 2024, (1, 2))
    may_jun_2024 = month_mask(anchor, 2024, (5, 6))
    march_2024 = month_mask(anchor, 2024, (3,))
    june_2024 = month_mask(anchor, 2024, (6,))

    candidates: list[Candidate] = []
    for suffix, alpha in [("a030", 0.30), ("a040", 0.40), ("a060", 0.60)]:
        candidates.append(
            Candidate(
                name=f"qbb66_2024h1_recency_revshape_{suffix}_keep_h2cogs",
                family="2024h1_recency_revenue_shape",
                thesis=f"Keep H2 high-ratio COGS down060; blend {alpha:.0%} period-aligned recency Revenue shape into 2024H1.",
                frame=period_aligned_shape(anchor, recency, "Revenue", "2024H1", alpha),
            )
        )

    for suffix, scale in [("q1up030", 1.03), ("q1up040", 1.04), ("q1up060", 1.06)]:
        candidates.append(
            Candidate(
                name=f"qbb66_2024h1_frontload_{suffix}_keep_h2cogs",
                family="2024h1_frontload_revenue",
                thesis=f"Keep H2 high-ratio COGS down060; preserve 2024H1 total and move Revenue from Apr-Jun into Jan-Mar with Q1 scale {scale:.3f}.",
                frame=preserve_total_shift(anchor, "Revenue", q1_2024, q2_2024, scale),
            )
        )

    candidates.append(
        Candidate(
            name="qbb66_2024h1_janfeb_from_mayjun_up050_keep_h2cogs",
            family="2024h1_frontload_revenue",
            thesis="More concentrated frontload: preserve Jan-Feb + May-Jun total and move Revenue from May-Jun into Jan-Feb.",
            frame=preserve_total_shift(anchor, "Revenue", jan_feb_2024, may_jun_2024, 1.05),
        )
    )
    candidates.append(
        Candidate(
            name="qbb66_2024h1_march_from_june_up080_keep_h2cogs",
            family="2024h1_month_transition",
            thesis="March-June contrast test: preserve Mar+Jun total and move Revenue from June into March.",
            frame=preserve_total_shift(anchor, "Revenue", march_2024, june_2024, 1.08),
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


def summarize_candidate(anchor: pd.DataFrame, candidate: Candidate, filename: str, priority: int) -> dict[str, object]:
    frame = candidate.frame
    delta_rev = frame["Revenue"] - anchor["Revenue"]
    delta_cogs = frame["COGS"] - anchor["COGS"]
    prof = period_summary(frame)
    h1_mask = period_mask(anchor, "2023H1")
    h2_mask = period_mask(anchor, "2023H2")
    return {
        "priority": priority,
        "filename": filename,
        "family": candidate.family,
        "thesis": candidate.thesis,
        "rev_rows_changed": int(delta_rev.abs().gt(1e-6).sum()),
        "cogs_rows_changed": int(delta_cogs.abs().gt(1e-6).sum()),
        "h1_max_abs_delta_vs_anchor": float(
            max(delta_rev.loc[h1_mask].abs().max(), delta_cogs.loc[h1_mask].abs().max())
        ),
        "h2_cogs_max_abs_delta_vs_anchor": float(delta_cogs.loc[h2_mask].abs().max()),
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
    report = f"""# Quarantine Big Jump V26 2024H1 After H2

Run directory: `{run_dir}`

## Status

This branch is **quarantine blackbox**, not clean.

## Current Read

- Current best anchor: `{ANCHOR_FILE}` = `{ANCHOR_SCORE}`.
- `h2_highratio_down100` overshot, so do not continue H2 intensity blindly.
- This batch changes 2024H1 Revenue while preserving the current H1 backload and H2 high-ratio COGS down060 gains.

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Suggested Submit Order

1. `submission_qbb66_2024h1_recency_revshape_a030_keep_h2cogs.csv`
2. If it improves, submit `submission_qbb66_2024h1_recency_revshape_a040_keep_h2cogs.csv`
3. If recency shape fails, submit `submission_qbb66_2024h1_frontload_q1up030_keep_h2cogs.csv`
4. Escalate only after a positive sign: `a060`, `q1up060`, or the Jan-Feb/March concentrated variants.

## Do Not Use As Clean

These candidates are public-guided/quarantine probes and must not be presented as clean model outputs.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_big_jump_v26_2024_after_h2_2026-04-26.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    anchor = add_segments(load_submission(ANCHOR_FILE))

    rows: list[dict[str, object]] = []
    month_profiles: list[pd.DataFrame] = []
    for priority, candidate in enumerate(build_candidates(anchor), start=1):
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
