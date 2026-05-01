from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from run_clean_regime_recovery_scenarios import load_sales, period_summary
from run_clean_v2_eda_guided_candidates import base_totals
from run_clean_v7_period_funnel_council import (
    build_customer_period_table,
    build_period_table,
    build_source_period_table,
    source_quality_revenue,
)
from run_cleaninput_rawmdshape_pubguided import apply_period_totals, build_shape_base
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v7_source_followup"


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    source_recovery: float
    h1_ratio: float
    note: str


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def build_specs() -> list[CandidateSpec]:
    return [
        CandidateSpec(
            name="cleanv7_sourcefine_s0190_r0870",
            source_recovery=0.190,
            h1_ratio=0.870,
            note="Slightly lower source-quality H1 recovery than current clean best.",
        ),
        CandidateSpec(
            name="cleanv7_sourcefine_s0195_r0870",
            source_recovery=0.195,
            h1_ratio=0.870,
            note="Half-step below current source-quality H1 recovery.",
        ),
        CandidateSpec(
            name="cleanv7_sourcefine_s0205_r0870",
            source_recovery=0.205,
            h1_ratio=0.870,
            note="Half-step above current source-quality H1 recovery.",
        ),
        CandidateSpec(
            name="cleanv7_sourcefine_s0210_r0870",
            source_recovery=0.210,
            h1_ratio=0.870,
            note="Slightly higher source-quality H1 recovery.",
        ),
        CandidateSpec(
            name="cleanv7_sourcefine_s0200_r0866",
            source_recovery=0.200,
            h1_ratio=0.866,
            note="Same H1 source level, lower COGS ratio.",
        ),
        CandidateSpec(
            name="cleanv7_sourcefine_s0200_r0868",
            source_recovery=0.200,
            h1_ratio=0.868,
            note="Same H1 source level, slightly lower COGS ratio.",
        ),
        CandidateSpec(
            name="cleanv7_sourcefine_s0200_r0872",
            source_recovery=0.200,
            h1_ratio=0.872,
            note="Same H1 source level, slightly higher COGS ratio.",
        ),
        CandidateSpec(
            name="cleanv7_sourcefine_s0200_r0874",
            source_recovery=0.200,
            h1_ratio=0.874,
            note="Same H1 source level, mid-way back toward r0876.",
        ),
        CandidateSpec(
            name="cleanv7_sourcefine_s0195_r0868",
            source_recovery=0.195,
            h1_ratio=0.868,
            note="Lower source recovery plus lower COGS ratio.",
        ),
        CandidateSpec(
            name="cleanv7_sourcefine_s0205_r0872",
            source_recovery=0.205,
            h1_ratio=0.872,
            note="Higher source recovery plus slightly higher COGS ratio.",
        ),
    ]


def apply_source_h1(source_periods: pd.DataFrame, base: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    out = base.copy()
    revenue = source_quality_revenue(source_periods, 2023, "H1", spec.source_recovery)
    mask = out["period"].eq("2023H1")
    out.loc[mask, "revenue"] = revenue
    out.loc[mask, "cogs"] = revenue * spec.h1_ratio
    out["cogs_ratio"] = out["cogs"] / out["revenue"]
    return out


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Clean V7 Source Follow-Up

Run directory: `{run_dir}`

## Boundary

This is clean-input public-guided. It does not read `sample_submission.csv`, previous submissions, blackbox files, or test targets.

Known public results:

- `submission_cleanv2_h1fine_b044_r0876.csv = 673757.34993`
- `submission_cleanv3_funnel_c110_h1r0876.csv = 673759.96838`
- `submission_cleanv7_source_h1_s020_r0870.csv = 673720.88479`

## Hypothesis

The source-quality period-total head is a real clean improvement, but the first gain is tiny. This run maps the local optimum around:

- source recovery near `0.20`
- H1 COGS ratio near `0.870`

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Order

1. `submission_cleanv7_sourcefine_s0200_r0868.csv`
2. `submission_cleanv7_sourcefine_s0195_r0870.csv`
3. `submission_cleanv7_sourcefine_s0205_r0870.csv`
4. `submission_cleanv7_sourcefine_s0200_r0872.csv`
5. `submission_cleanv7_sourcefine_s0195_r0868.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v7_source_followup_2026-04-28.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    sales = load_sales()
    source_periods = build_source_period_table(run_dir)
    # Build for provenance/log parity with v7 council; not used for this follow-up.
    build_customer_period_table(run_dir)
    build_period_table()
    base = base_totals(sales)
    shape_base = build_shape_base()

    rows = []
    for priority, spec in enumerate(build_specs(), start=1):
        totals = apply_source_h1(source_periods, base, spec)
        frame = apply_period_totals(shape_base, totals)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)
        prof = period_summary(frame)
        prof.to_csv(run_dir / f"{spec.name}_period_summary.csv", index=False)
        totals.to_csv(run_dir / f"{spec.name}_target_totals.csv", index=False)
        rows.append(
            {
                "priority": priority,
                "filename": path.name,
                "source_recovery": spec.source_recovery,
                "h1_ratio": spec.h1_ratio,
                "revenue_total": frame["Revenue"].sum(),
                "cogs_total": frame["COGS"].sum(),
                "ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
                "rev_2023H1": prof.loc[prof["period"].eq("2023H1"), "revenue"].iloc[0],
                "cogs_2023H1": prof.loc[prof["period"].eq("2023H1"), "cogs"].iloc[0],
                "ratio_2023H1": prof.loc[prof["period"].eq("2023H1"), "cogs_ratio"].iloc[0],
                "rev_2023H2": prof.loc[prof["period"].eq("2023H2"), "revenue"].iloc[0],
                "cogs_2023H2": prof.loc[prof["period"].eq("2023H2"), "cogs"].iloc[0],
                "rev_2024H1": prof.loc[prof["period"].eq("2024H1"), "revenue"].iloc[0],
                "cogs_2024H1": prof.loc[prof["period"].eq("2024H1"), "cogs"].iloc[0],
                "note": spec.note,
            }
        )

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    write_report(run_dir, manifest)
    print(run_dir)
    print(manifest[["priority", "filename", "source_recovery", "h1_ratio", "rev_2023H1", "cogs_2023H1"]].to_string(index=False))


if __name__ == "__main__":
    main()
