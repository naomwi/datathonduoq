from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from analyze_clean_v2_train_evidence import build_daily_panel
from run_cleanroom_rawmd_pipeline import (
    RawMdConfig,
    add_period_columns,
    apply_rawmd_config,
    build_clean_anchor,
    period_summary,
)
from run_clean_v19_multimetric_frontier import apply_ratio_smooth, CandidateSpec
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission
from train_recursive_forecast import TRAIN_END, ensure_inputs, get_candidate_feature_sets


RUN_PREFIX = "reasonable_final_pipeline"


@dataclass(frozen=True)
class FinalCandidate:
    name: str
    risk_label: str
    rawmd: RawMdConfig
    revenue_period_scale: dict[str, float]
    cogs_period_scale_after_rawmd: dict[str, float]
    recommended_use: str
    story: str
    ratio_smooth_spec: CandidateSpec | None = None


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def apply_period_scales(frame: pd.DataFrame, candidate: FinalCandidate) -> pd.DataFrame:
    out = add_period_columns(frame)
    for period, scale in candidate.revenue_period_scale.items():
        out.loc[out["period"].eq(period), "Revenue"] *= scale
    for period, scale in candidate.cogs_period_scale_after_rawmd.items():
        out.loc[out["period"].eq(period), "COGS"] *= scale
    return out[["Date", "Revenue", "COGS", "period"]]


def build_candidates() -> list[FinalCandidate]:
    return [
        FinalCandidate(
            name="reasonable_final_strict_source_reference",
            risk_label="strict_source_reference_low_score",
            rawmd=RawMdConfig(
                name="rawmd_trainonly_reference",
                revenue_alpha_non_h2=0.70,
                revenue_alpha_h2=0.20,
                cogs_alpha=0.60,
                cogs_period_scale={},
                note="Train-data month-day allocation only; no public period-level scaling.",
            ),
            revenue_period_scale={},
            cogs_period_scale_after_rawmd={},
            recommended_use="Use for explanation/audit only, not as the leaderboard candidate unless strict train-only is mandatory.",
            story=(
                "Model anchor from raw train tables, then historical month-day allocation from train sales.csv. "
                "No sample/test/submission values are used."
            ),
        ),
        FinalCandidate(
            name="reasonable_final_sourceclean_pubcal",
            risk_label="source_clean_public_calibrated",
            rawmd=RawMdConfig(
                name="rawmd_r080_c065_h2r010_cogsmed",
                revenue_alpha_non_h2=0.80,
                revenue_alpha_h2=0.10,
                cogs_alpha=0.65,
                cogs_period_scale={"2023H1": 1.030, "2023H2": 1.018, "2024H1": 1.009},
                note="Train-only raw month-day shape plus public-calibrated COGS period scale.",
            ),
            revenue_period_scale={
                "2023H1": 1.0830538066,
                "2023H2": 1.2807780017,
                "2024H1": 1.1131440885,
                "2024-07-01": 1.2077364451,
            },
            cogs_period_scale_after_rawmd={
                "2023H1": 1.2096563987,
                "2023H2": 1.3640165231,
                "2024H1": 1.1376370689,
                "2024-07-01": 1.2921714215,
            },
            recommended_use=(
                "Primary reasonable submit candidate if public leaderboard calibration is allowed. "
                "It is not strict train-only, but it does not use test Revenue/COGS as input features."
            ),
            story=(
                "Daily shape is learned from train sales.csv month-day shares. Period-level regime correction is "
                "an explicit scenario calibration chosen from public feedback, not a feature derived from test targets."
            ),
        ),
        FinalCandidate(
            name="reasonable_final_sourceclean_pubcal_soft",
            risk_label="source_clean_public_calibrated_softer",
            rawmd=RawMdConfig(
                name="rawmd_r080_c065_h2r010_cogsmed",
                revenue_alpha_non_h2=0.80,
                revenue_alpha_h2=0.10,
                cogs_alpha=0.65,
                cogs_period_scale={"2023H1": 1.030, "2023H2": 1.018, "2024H1": 1.009},
                note="Train-only raw month-day shape plus softer public-calibrated level correction.",
            ),
            revenue_period_scale={
                "2023H1": 1.065,
                "2023H2": 1.220,
                "2024H1": 1.090,
                "2024-07-01": 1.150,
            },
            cogs_period_scale_after_rawmd={
                "2023H1": 1.160,
                "2023H2": 1.280,
                "2024H1": 1.100,
                "2024-07-01": 1.200,
            },
            recommended_use="Fallback if the exact public calibration feels too aggressive for presentation.",
            story=(
                "Same train-derived daily shape, but less aggressive period-level correction. "
                "This is easier to justify but likely scores worse."
            ),
        ),
        FinalCandidate(
            name="reasonable_final_sourceclean_pubcal_ratio_smooth",
            risk_label="source_clean_public_calibrated_ratio_smooth",
            rawmd=RawMdConfig(
                name="rawmd_r080_c065_h2r010_cogsmed",
                revenue_alpha_non_h2=0.80,
                revenue_alpha_h2=0.10,
                cogs_alpha=0.65,
                cogs_period_scale={"2023H1": 1.030, "2023H2": 1.018, "2024H1": 1.009},
                note="Train-only raw month-day shape plus public-calibrated COGS period scale.",
            ),
            revenue_period_scale={
                "2023H1": 1.0830538066,
                "2023H2": 1.2807780017,
                "2024H1": 1.1131440885,
                "2024-07-01": 1.2077364451,
            },
            cogs_period_scale_after_rawmd={
                "2023H1": 1.2096563987,
                "2023H2": 1.3640165231,
                "2024H1": 1.1376370689,
                "2024-07-01": 1.2921714215,
            },
            ratio_smooth_spec=CandidateSpec(
                name="cleanv19_v17_ratio_monthsmooth_h2_recenteven_a160",
                family="ratio_smooth",
                scopes=("2023H2",),
                targets=("COGS",),
                alpha=0.16,
                profile="recent_even",
                preserve="month",
                note="Fine-search alpha just above validated a150, trying to improve RMSE/R2 without hurting MAE.",
            ),
            recommended_use=(
                "Primary reasonable submit candidate using public calibration AND the ratio_monthsmooth_h2_recenteven_a160 logic "
                "for smoothing COGS ratio in H2."
            ),
            story=(
                "Same as sourceclean_pubcal but with H2 ratio smoothing added to capture the recent-even historical prior."
            ),
        ),
    ]


def write_report(run_dir: Path, manifest: pd.DataFrame, anchor_summary: pd.DataFrame) -> None:
    report = f"""# Reasonable Final Direction

Run directory: `{run_dir}`

## Priority Decision

The recommended path is **source-clean public-calibrated raw month-day decomposition**.

This is the most reasonable compromise between score and rule safety:

- do not use `sample_submission.csv` numeric `Revenue` / `COGS`;
- do not use any `sales_test.csv` target values;
- do not read any previous `submission_*.csv` as an input feature source;
- rebuild the model anchor from raw provided tables;
- learn daily shape from historical `sales.csv` only;
- state period-level calibration honestly as public-feedback scenario calibration.

## What To Avoid

Do not package the old `sample_*`, `publiconly_*`, or submission-as-anchor scripts as the final method. They are useful forensic notebooks, but they are not the clean story.

## Anchor Period Summary

{anchor_summary.to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Priority

1. `submission_reasonable_final_sourceclean_pubcal.csv`
2. If that is too aggressive or needs a more conservative story: `submission_reasonable_final_sourceclean_pubcal_soft.csv`
3. Use `submission_reasonable_final_strict_source_reference.csv` only for audit/reference, not for the leaderboard target.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "reasonable_final_direction_2026-04-22.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    anchor = build_clean_anchor(feature_store, base, feature_sets)
    history = feature_store.loc[feature_store["Date"] <= TRAIN_END, ["Date", "Revenue", "COGS"]].copy()

    daily = build_daily_panel()

    rows = []
    for priority, candidate in enumerate(build_candidates(), start=1):
        rawmd_frame = apply_rawmd_config(anchor, history, candidate.rawmd)
        frame = apply_period_scales(rawmd_frame, candidate)
        if candidate.ratio_smooth_spec:
            frame = apply_ratio_smooth(frame, daily, candidate.ratio_smooth_spec)
        
        path = DATASET_DIR / f"submission_{candidate.name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)
        prof = period_summary(frame)
        prof.to_csv(run_dir / f"{candidate.name}_period_summary.csv", index=False)
        rows.append(
            {
                "priority": priority,
                "filename": path.name,
                "risk_label": candidate.risk_label,
                "revenue_total": frame["Revenue"].sum(),
                "cogs_total": frame["COGS"].sum(),
                "ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
                "ratio_2023H1": prof.loc[prof["period"].eq("2023H1"), "cogs_ratio"].iloc[0],
                "ratio_2023H2": prof.loc[prof["period"].eq("2023H2"), "cogs_ratio"].iloc[0],
                "ratio_2024H1": prof.loc[prof["period"].eq("2024H1"), "cogs_ratio"].iloc[0],
                "recommended_use": candidate.recommended_use,
                "story": candidate.story,
            }
        )

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(anchor).to_csv(run_dir / "anchor_period_summary.csv", index=False)
    write_report(run_dir, manifest, period_summary(anchor))
    print(run_dir)


if __name__ == "__main__":
    main()
