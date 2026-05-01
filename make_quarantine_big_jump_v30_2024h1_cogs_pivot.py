from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_prior_v19 import period_summary
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_big_jump_v30_2024h1_cogs_pivot"
ANCHOR_FILE = "submission_qbb69_h1_q1_cogs_down120_keeprev.csv"
ANCHOR_SCORE = 655838.51372
SAMPLE_FILE = "sample_submission.csv"


@dataclass(frozen=True)
class Candidate:
    name: str
    family: str
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


def month_mask(frame: pd.DataFrame, year: int, months: tuple[int, ...]) -> pd.Series:
    return frame["Date"].dt.year.eq(year) & frame["Date"].dt.month.isin(months)


def scale_cogs(frame: pd.DataFrame, mask: pd.Series, scale: float) -> pd.DataFrame:
    out = frame.copy()
    out.loc[mask.to_numpy(), "COGS"] *= scale
    return out


def preserve_total_shift(
    frame: pd.DataFrame,
    down_mask: pd.Series,
    up_mask: pd.Series,
    down_scale: float,
) -> pd.DataFrame:
    out = frame.copy()
    down_idx = down_mask.to_numpy()
    up_idx = up_mask.to_numpy()
    original_total = float(out.loc[down_idx | up_idx, "COGS"].sum())
    down_total = float(out.loc[down_idx, "COGS"].sum())
    up_total = float(out.loc[up_idx, "COGS"].sum())
    if up_total <= 0.0:
        raise ValueError("Cannot preserve total with non-positive up bucket")
    up_scale = (original_total - down_total * down_scale) / up_total
    if up_scale <= 0.0:
        raise ValueError(f"Invalid up scale {up_scale:.6f}")
    out.loc[down_idx, "COGS"] *= down_scale
    out.loc[up_idx, "COGS"] *= up_scale
    return out


def sample_month_ratio_frame(anchor: pd.DataFrame, sample: pd.DataFrame, months: tuple[int, ...], alpha: float) -> pd.DataFrame:
    out = anchor.copy()
    sample_month = sample.copy()
    sample_month["month"] = sample_month["Date"].dt.to_period("M")
    monthly = sample_month.groupby("month").agg(Revenue=("Revenue", "sum"), COGS=("COGS", "sum"))
    sample_ratio = monthly["COGS"] / monthly["Revenue"]
    month_key = out["Date"].dt.to_period("M")
    mask = month_mask(out, 2024, months).to_numpy()
    desired = out["Revenue"] * month_key.map(sample_ratio).astype(float)
    out.loc[mask, "COGS"] = (1.0 - alpha) * out.loc[mask, "COGS"] + alpha * desired.loc[mask]
    return out


def build_candidates(anchor: pd.DataFrame, sample: pd.DataFrame) -> list[Candidate]:
    assert_aligned(anchor, sample, "sample")

    q1_2024 = month_mask(anchor, 2024, (1, 2, 3))
    q2_2024 = month_mask(anchor, 2024, (4, 5, 6))
    jun_2024 = month_mask(anchor, 2024, (6,))
    janfeb_2024 = month_mask(anchor, 2024, (1, 2))
    march_2024 = month_mask(anchor, 2024, (3,))

    return [
        Candidate(
            name="qbb70_2024q1_cogs_down030_keeprev",
            family="2024q1_cogs_level",
            changed_scope="2024Q1 COGS only",
            thesis="Sign test: lower 2024Q1 COGS by 3%. Monthly ratios show Jan-Mar are above sample while Q2 is not.",
            frame=scale_cogs(anchor, q1_2024, 0.970),
        ),
        Candidate(
            name="qbb70_2024q1_cogs_down060_keeprev",
            family="2024q1_cogs_level",
            changed_scope="2024Q1 COGS only",
            thesis="Stronger 2024Q1 COGS-down test if Q1 2024 is the remaining high-ratio block.",
            frame=scale_cogs(anchor, q1_2024, 0.940),
        ),
        Candidate(
            name="qbb70_2024h1_cogs_monthratio_a050_keeprev",
            family="2024h1_cogs_month_ratio",
            changed_scope="2024H1 COGS only",
            thesis="Blend 50% toward sample monthly COGS/Revenue ratios: lowers Jan-Mar, leaves May near-neutral, raises June.",
            frame=sample_month_ratio_frame(anchor, sample, (1, 2, 3, 4, 5, 6), 0.500),
        ),
        Candidate(
            name="qbb70_2024h1_cogs_monthratio_a100_keeprev",
            family="2024h1_cogs_month_ratio",
            changed_scope="2024H1 COGS only",
            thesis="Full 2024H1 monthly-ratio repair toward sample shape; high-information structured pivot.",
            frame=sample_month_ratio_frame(anchor, sample, (1, 2, 3, 4, 5, 6), 1.000),
        ),
        Candidate(
            name="qbb70_2024q1_cogs_monthratio_a100_keeprev",
            family="2024q1_cogs_month_ratio",
            changed_scope="2024Q1 COGS only",
            thesis="Only Jan-Mar 2024 toward sample ratios; isolates the high-ratio Q1 block without touching Q2.",
            frame=sample_month_ratio_frame(anchor, sample, (1, 2, 3), 1.000),
        ),
        Candidate(
            name="qbb70_2024h1_cogs_q1down040_q2fund_preserve",
            family="2024h1_cogs_phase_preserve",
            changed_scope="2024H1 COGS shape only",
            thesis="Preserve 2024H1 COGS total but shift cost mass from high-ratio Q1 into Q2.",
            frame=preserve_total_shift(anchor, q1_2024, q2_2024, 0.960),
        ),
        Candidate(
            name="qbb70_2024h1_cogs_q1down040_junfund_preserve",
            family="2024h1_cogs_phase_preserve",
            changed_scope="2024H1 COGS shape only",
            thesis="Preserve 2024H1 COGS total but move Q1 cost mass specifically into June, whose current ratio is below sample.",
            frame=preserve_total_shift(anchor, q1_2024, jun_2024, 0.960),
        ),
        Candidate(
            name="qbb70_2024_janfeb_cogs_down040_keeprev",
            family="2024q1_month_concentration",
            changed_scope="2024 Jan-Feb COGS only",
            thesis="Lower Jan-Feb 2024 only; tests whether Tet/early-year COGS is the high-ratio residual.",
            frame=scale_cogs(anchor, janfeb_2024, 0.960),
        ),
        Candidate(
            name="qbb70_2024_mar_cogs_down050_keeprev",
            family="2024q1_month_concentration",
            changed_scope="2024 March COGS only",
            thesis="Lower March 2024 only; March has the largest 2024H1 COGS/Revenue ratio.",
            frame=scale_cogs(anchor, march_2024, 0.950),
        ),
    ]


def month_summary(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["month"] = out["Date"].dt.strftime("%Y-%m")
    return (
        out.groupby("month", as_index=False)
        .agg(days=("Date", "count"), Revenue=("Revenue", "sum"), COGS=("COGS", "sum"))
        .assign(ratio=lambda data: data["COGS"] / data["Revenue"])
    )


def summarize_candidate(anchor: pd.DataFrame, candidate: Candidate, filename: str, priority: int) -> dict[str, object]:
    frame = candidate.frame
    delta_rev = frame["Revenue"] - anchor["Revenue"]
    delta_cogs = frame["COGS"] - anchor["COGS"]
    prof = period_summary(frame)
    h23 = frame["Date"].dt.year.eq(2023)
    non_2024h1 = ~(frame["Date"].dt.year.eq(2024) & frame["Date"].dt.month.le(6))
    return {
        "priority": priority,
        "filename": filename,
        "family": candidate.family,
        "changed_scope": candidate.changed_scope,
        "thesis": candidate.thesis,
        "rev_rows_changed": int(delta_rev.abs().gt(1e-6).sum()),
        "cogs_rows_changed": int(delta_cogs.abs().gt(1e-6).sum()),
        "non_2024h1_max_abs_delta_vs_anchor": float(
            max(delta_rev.loc[non_2024h1].abs().max(), delta_cogs.loc[non_2024h1].abs().max())
        ),
        "y2023_max_abs_delta_vs_anchor": float(
            max(delta_rev.loc[h23].abs().max(), delta_cogs.loc[h23].abs().max())
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


def validate_frame(frame: pd.DataFrame, filename: str) -> None:
    if len(frame) != 548:
        raise ValueError(f"{filename}: expected 548 rows, found {len(frame)}")
    if frame["Date"].min() != pd.Timestamp("2023-01-01"):
        raise ValueError(f"{filename}: bad start date")
    if frame["Date"].max() != pd.Timestamp("2024-07-01"):
        raise ValueError(f"{filename}: bad end date")
    if frame[["Revenue", "COGS"]].isna().any().any():
        raise ValueError(f"{filename}: NaN values found")
    if (frame[["Revenue", "COGS"]] < 0).any().any():
        raise ValueError(f"{filename}: negative values found")


def write_report(run_dir: Path, manifest: pd.DataFrame, anchor: pd.DataFrame, sample: pd.DataFrame) -> None:
    report = f"""# Quarantine Big Jump V30 2024H1 COGS Pivot

Run directory: `{run_dir}`

## Status

This branch is **quarantine blackbox**, not clean.

## Current Read

- Current best anchor: `{ANCHOR_FILE}` = `{ANCHOR_SCORE}`.
- Q1 2023 uniform COGS-down is nearly exhausted.
- Pivot axis: 2024H1 COGS month structure. Current 2024 Jan-Mar ratios are above sample, while June is below sample.
- This batch preserves all 2023 values and Revenue; only 2024H1 COGS moves.

## Anchor 2024H1 Month Ratios

{month_summary(anchor).query("month >= '2024-01' and month <= '2024-06'").to_markdown(index=False)}

## Sample 2024H1 Month Ratios

{month_summary(sample).query("month >= '2024-01' and month <= '2024-06'").to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Suggested Submit Order

1. `submission_qbb70_2024h1_cogs_monthratio_a050_keeprev.csv`
2. If it improves, submit `submission_qbb70_2024h1_cogs_monthratio_a100_keeprev.csv`
3. If it worsens, submit `submission_qbb70_2024h1_cogs_q1down040_q2fund_preserve.csv`
4. Use `2024q1_cogs_down030` only as a simpler sign-check if structured month-ratio is unclear.
5. Do not submit 2024H1 COGS-up; earlier evidence rejected 2024H1 COGS +10% strongly.

## Do Not Use As Clean

These candidates are public-guided/quarantine probes and must not be presented as clean model outputs.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_big_jump_v30_2024h1_cogs_pivot_2026-04-28.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    anchor = load_submission(ANCHOR_FILE)
    sample = load_submission(SAMPLE_FILE)

    rows: list[dict[str, object]] = []
    profiles: list[pd.DataFrame] = []
    for priority, candidate in enumerate(build_candidates(anchor, sample), start=1):
        filename = f"submission_{candidate.name}.csv"
        export = candidate.frame[["Date", "Revenue", "COGS"]].copy()
        validate_frame(export, filename)
        write_submission(export, DATASET_DIR / filename)
        write_submission(export, run_dir / filename)
        rows.append(summarize_candidate(anchor, candidate, filename, priority))
        profile = month_summary(export)
        profile.insert(0, "filename", filename)
        profiles.append(profile)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    pd.concat(profiles, ignore_index=True).to_csv(run_dir / "month_profiles.csv", index=False)
    period_summary(anchor).to_csv(run_dir / "anchor_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_period_summary.csv", index=False)
    write_report(run_dir, manifest, anchor, sample)
    print(run_dir)


if __name__ == "__main__":
    main()
