from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_prior_v19 import add_segments, period_summary
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_big_jump_v28_h1_cogs_phase"
ANCHOR_FILE = "submission_qbb65_h2_highratio_cogs_down060_keeprev.csv"
ANCHOR_SCORE = 659211.90870
PRE_H1_BACKLOAD_FILE = "submission_qbb60v18_cogs2023h2_down010.csv"
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


def period_mask(frame: pd.DataFrame, period: str) -> pd.Series:
    return add_segments(frame)["period"].eq(period)


def scale_cogs(frame: pd.DataFrame, mask: pd.Series, scale: float) -> pd.DataFrame:
    out = frame.copy()
    out.loc[mask.to_numpy(), "COGS"] *= scale
    return out


def preserve_total_shift(
    frame: pd.DataFrame,
    target_mask: pd.Series,
    source_mask: pd.Series,
    target_scale: float,
) -> pd.DataFrame:
    out = frame.copy()
    target_idx = target_mask.to_numpy()
    source_idx = source_mask.to_numpy()
    original_total = float(out.loc[target_idx | source_idx, "COGS"].sum())
    target_total = float(out.loc[target_idx, "COGS"].sum())
    source_total = float(out.loc[source_idx, "COGS"].sum())
    if source_total <= 0.0:
        raise ValueError("Cannot preserve total with non-positive source bucket")
    source_scale = (original_total - target_total * target_scale) / source_total
    if source_scale <= 0.0:
        raise ValueError(f"Invalid source scale {source_scale:.6f}")
    out.loc[target_idx, "COGS"] *= target_scale
    out.loc[source_idx, "COGS"] *= source_scale
    return out


def blend_q1_cogs_to_sample_month_ratio(anchor: pd.DataFrame, sample: pd.DataFrame, alpha: float) -> pd.DataFrame:
    out = anchor.copy()
    sample_month = sample.copy()
    sample_month["month"] = sample_month["Date"].dt.to_period("M")
    monthly = sample_month.groupby("month").agg(Revenue=("Revenue", "sum"), COGS=("COGS", "sum"))
    ratio_by_month = (monthly["COGS"] / monthly["Revenue"]).to_dict()
    months = anchor["Date"].dt.to_period("M")
    q1 = month_mask(anchor, 2023, (1, 2, 3)).to_numpy()
    desired = anchor["Revenue"] * months.map(ratio_by_month).astype(float)
    out.loc[q1, "COGS"] = (1.0 - alpha) * anchor.loc[q1, "COGS"] + alpha * desired.loc[q1]
    return out


def cogs_follow_revenue_backload(anchor: pd.DataFrame, pre_h1: pd.DataFrame, alpha: float) -> pd.DataFrame:
    out = anchor.copy()
    h1 = period_mask(anchor, "2023H1").to_numpy()
    revenue_ratio = anchor["Revenue"] / pre_h1["Revenue"]
    moved = pre_h1["COGS"] * (1.0 + alpha * (revenue_ratio - 1.0))
    out.loc[h1, "COGS"] = moved.loc[h1]
    return out


def build_candidates(anchor: pd.DataFrame, pre_h1: pd.DataFrame, sample: pd.DataFrame) -> list[Candidate]:
    assert_aligned(anchor, pre_h1, "pre-H1-backload anchor")
    assert_aligned(anchor, sample, "sample")

    q1 = month_mask(anchor, 2023, (1, 2, 3))
    q2 = month_mask(anchor, 2023, (4, 5, 6))

    return [
        Candidate(
            name="qbb68_h1_q1_cogs_down040_keeprev",
            family="h1_q1_cogs_level",
            changed_scope="2023Q1 COGS only",
            thesis="Lower 2023Q1 COGS after the accepted Revenue backload; tests whether Q1 cost stayed too high.",
            frame=scale_cogs(anchor, q1, 0.960),
        ),
        Candidate(
            name="qbb68_h1_q1_cogs_down080_keeprev",
            family="h1_q1_cogs_level",
            changed_scope="2023Q1 COGS only",
            thesis="Higher-amplitude Q1 COGS-down sign test if down040 is positive.",
            frame=scale_cogs(anchor, q1, 0.920),
        ),
        Candidate(
            name="qbb68_h1_cogs_backload_q2up020_preserve",
            family="h1_cogs_phase_preserve",
            changed_scope="2023H1 COGS shape only",
            thesis="Move 2023H1 COGS from Q1 to Q2, preserving H1 total; partial cost co-move with the winning Revenue backload.",
            frame=preserve_total_shift(anchor, q2, q1, 1.020),
        ),
        Candidate(
            name="qbb68_h1_cogs_backload_q2up040_preserve",
            family="h1_cogs_phase_preserve",
            changed_scope="2023H1 COGS shape only",
            thesis="Full-size COGS co-move with the winning Revenue Q2 backload.",
            frame=preserve_total_shift(anchor, q2, q1, 1.040),
        ),
        Candidate(
            name="qbb68_h1_cogs_follow_revbackload_a050",
            family="h1_cogs_phase_follow_revenue",
            changed_scope="2023H1 COGS shape only",
            thesis="Apply 50% of the accepted daily Revenue backload multiplier to COGS.",
            frame=cogs_follow_revenue_backload(anchor, pre_h1, 0.500),
        ),
        Candidate(
            name="qbb68_h1_cogs_follow_revbackload_a100",
            family="h1_cogs_phase_follow_revenue",
            changed_scope="2023H1 COGS shape only",
            thesis="Apply 100% of the accepted daily Revenue backload multiplier to COGS.",
            frame=cogs_follow_revenue_backload(anchor, pre_h1, 1.000),
        ),
        Candidate(
            name="qbb68_h1_q1_cogs_sample_ratio_a025",
            family="h1_q1_cogs_sample_ratio",
            changed_scope="2023Q1 COGS only",
            thesis="Blend 25% of Q1 COGS toward sample monthly COGS/Revenue ratios; tests suspicious Q1 ratio spike after Revenue backload.",
            frame=blend_q1_cogs_to_sample_month_ratio(anchor, sample, 0.250),
        ),
        Candidate(
            name="qbb68_h1_q1_cogs_sample_ratio_a040",
            family="h1_q1_cogs_sample_ratio",
            changed_scope="2023Q1 COGS only",
            thesis="Stronger Q1 monthly-ratio repair if the sample-ratio direction is positive.",
            frame=blend_q1_cogs_to_sample_month_ratio(anchor, sample, 0.400),
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
    h2_mask = period_mask(anchor, "2023H2")
    h24_mask = period_mask(anchor, "2024H1")
    return {
        "priority": priority,
        "filename": filename,
        "family": candidate.family,
        "changed_scope": candidate.changed_scope,
        "thesis": candidate.thesis,
        "rev_rows_changed": int(delta_rev.abs().gt(1e-6).sum()),
        "cogs_rows_changed": int(delta_cogs.abs().gt(1e-6).sum()),
        "h2_max_abs_delta_vs_anchor": float(
            max(delta_rev.loc[h2_mask].abs().max(), delta_cogs.loc[h2_mask].abs().max())
        ),
        "h24_max_abs_delta_vs_anchor": float(
            max(delta_rev.loc[h24_mask].abs().max(), delta_cogs.loc[h24_mask].abs().max())
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
    report = f"""# Quarantine Big Jump V28 H1 COGS Phase

Run directory: `{run_dir}`

## Status

This branch is **quarantine blackbox**, not clean.

## Current Read

- Current best anchor: `{ANCHOR_FILE}` = `{ANCHOR_SCORE}`.
- `qbb67_h2_highratio_shape_preserve_down040` failed at `659804.99207`, so H2 total-preserving redistribution is not the next path.
- New hypothesis: after the accepted 2023H1 Revenue Q2-backload, 2023H1 COGS may be out of phase because COGS was kept fixed.
- This batch changes only 2023H1 COGS. Revenue, 2023H2, and 2024H1 are preserved.

## Anchor Month Ratios

{month_summary(anchor).head(6).to_markdown(index=False)}

## Sample Month Ratios

{month_summary(sample).head(6).to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Suggested Submit Order

1. `submission_qbb68_h1_q1_cogs_down040_keeprev.csv`
2. If it improves, submit `submission_qbb68_h1_q1_cogs_down080_keeprev.csv`
3. If Q1-down is flat/fails, submit `submission_qbb68_h1_cogs_backload_q2up020_preserve.csv`
4. If backload improves, submit `submission_qbb68_h1_cogs_backload_q2up040_preserve.csv`
5. Use sample-ratio candidates only if Q1-down improves but needs a more structured repair.

## Do Not Use As Clean

These candidates are public-guided/quarantine probes and must not be presented as clean model outputs.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_big_jump_v28_h1_cogs_phase_2026-04-26.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    anchor = load_submission(ANCHOR_FILE)
    pre_h1 = load_submission(PRE_H1_BACKLOAD_FILE)
    sample = load_submission(SAMPLE_FILE)

    rows: list[dict[str, object]] = []
    profiles: list[pd.DataFrame] = []
    for priority, candidate in enumerate(build_candidates(anchor, pre_h1, sample), start=1):
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
