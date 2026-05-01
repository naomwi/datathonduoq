from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_clean_regime_recovery_scenarios import load_sales, period_summary
from run_clean_v2_eda_guided_candidates import base_totals
from run_clean_v7_period_funnel_council import build_source_period_table, source_quality_revenue
from run_cleaninput_rawmdshape_pubguided import apply_period_totals, build_shape_base
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v9_bigjump_all_paths"
FORECAST_START = pd.Timestamp("2023-01-01")
FORECAST_END = pd.Timestamp("2024-07-01")


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    thesis: str
    h1_source_recovery: float | None = 0.20
    h1_ratio: float | None = 0.870
    h2_source_recovery: float | None = None
    h2_ratio: float | None = None
    h2_keep_revenue: bool = True
    h1_2024_source_recovery: float | None = None
    h1_2024_ratio: float | None = None
    h1_2024_keep_revenue: bool = True
    final_day_scale: float = 1.0


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def build_current_clean_totals(source_periods: pd.DataFrame) -> pd.DataFrame:
    sales = load_sales()
    totals = base_totals(sales)
    h1_revenue = source_quality_revenue(source_periods, 2023, "H1", 0.20)
    mask = totals["period"].eq("2023H1")
    totals.loc[mask, "revenue"] = h1_revenue
    totals.loc[mask, "cogs"] = h1_revenue * 0.870
    totals["cogs_ratio"] = totals["cogs"] / totals["revenue"]
    return totals


def apply_spec(base_totals_frame: pd.DataFrame, source_periods: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    out = base_totals_frame.copy()

    h1_mask = out["period"].eq("2023H1")
    if spec.h1_source_recovery is not None:
        revenue = source_quality_revenue(source_periods, 2023, "H1", spec.h1_source_recovery)
        out.loc[h1_mask, "revenue"] = revenue
    if spec.h1_ratio is not None:
        out.loc[h1_mask, "cogs"] = out.loc[h1_mask, "revenue"] * spec.h1_ratio

    h2_mask = out["period"].eq("2023H2")
    if spec.h2_source_recovery is not None:
        revenue = source_quality_revenue(source_periods, 2023, "H2", spec.h2_source_recovery)
        out.loc[h2_mask, "revenue"] = revenue
        if spec.h2_keep_revenue:
            raise ValueError(f"{spec.name}: h2_keep_revenue=True conflicts with h2_source_recovery")
    if spec.h2_ratio is not None:
        out.loc[h2_mask, "cogs"] = out.loc[h2_mask, "revenue"] * spec.h2_ratio

    h1_2024_mask = out["period"].eq("2024H1")
    if spec.h1_2024_source_recovery is not None:
        revenue = source_quality_revenue(source_periods, 2024, "H1", spec.h1_2024_source_recovery)
        out.loc[h1_2024_mask, "revenue"] = revenue
        if spec.h1_2024_keep_revenue:
            raise ValueError(f"{spec.name}: h1_2024_keep_revenue=True conflicts with h1_2024_source_recovery")
    if spec.h1_2024_ratio is not None:
        out.loc[h1_2024_mask, "cogs"] = out.loc[h1_2024_mask, "revenue"] * spec.h1_2024_ratio

    final_mask = out["period"].eq("2024-07-01")
    if spec.final_day_scale != 1.0:
        out.loc[final_mask, "revenue"] *= spec.final_day_scale
        out.loc[final_mask, "cogs"] *= spec.final_day_scale

    out["cogs_ratio"] = out["cogs"] / out["revenue"]
    return out


def build_specs() -> list[CandidateSpec]:
    return [
        CandidateSpec(
            name="cleanv9_big_h1_source_s023_r0868",
            h1_source_recovery=0.23,
            h1_ratio=0.868,
            thesis="s0190 failed; test the opposite direction: materially higher 2023H1 source-quality Revenue with lower COGS ratio.",
        ),
        CandidateSpec(
            name="cleanv9_big_h1_source_s026_r0868",
            h1_source_recovery=0.26,
            h1_ratio=0.868,
            thesis="Escalation of H1 level-up direction; large enough to detect if public wants more H1 Revenue.",
        ),
        CandidateSpec(
            name="cleanv9_big_h1_source_s030_r0868",
            h1_source_recovery=0.30,
            h1_ratio=0.868,
            thesis="High-risk H1 level-up stress; not a local tweak.",
        ),
        CandidateSpec(
            name="cleanv9_big_h1_keeprev_cogs_r0840",
            h1_source_recovery=0.20,
            h1_ratio=0.840,
            thesis="Large 2023H1 COGS-ratio down test while keeping current best H1 Revenue.",
        ),
        CandidateSpec(
            name="cleanv9_big_h1_keeprev_cogs_r0820",
            h1_source_recovery=0.20,
            h1_ratio=0.820,
            thesis="High-risk 2023H1 COGS-ratio down stress; tests whether MAE gap is mostly COGS.",
        ),
        CandidateSpec(
            name="cleanv9_big_h2_keeprev_cogs_r0950",
            h1_source_recovery=0.20,
            h1_ratio=0.870,
            h2_ratio=0.950,
            thesis="2023H2 COGS ratio is very high in current clean; lower it to a plausible train regime.",
        ),
        CandidateSpec(
            name="cleanv9_big_h2_keeprev_cogs_r0900",
            h1_source_recovery=0.20,
            h1_ratio=0.870,
            h2_ratio=0.900,
            thesis="Large 2023H2 COGS-ratio down stress, orthogonal to H1 source head.",
        ),
        CandidateSpec(
            name="cleanv9_big_h2_source_s045_cogs_r0950",
            h1_source_recovery=0.20,
            h1_ratio=0.870,
            h2_source_recovery=0.45,
            h2_ratio=0.950,
            h2_keep_revenue=False,
            thesis="H2 source-quality level-up with lower ratio; tests if current H2 Revenue is undercalled but COGS ratio overcalled.",
        ),
        CandidateSpec(
            name="cleanv9_big_2024h1_keeprev_cogs_r0800",
            h1_source_recovery=0.20,
            h1_ratio=0.870,
            h1_2024_ratio=0.800,
            thesis="Large 2024H1 COGS-ratio down test; clean analog of public COGS-down signal.",
        ),
        CandidateSpec(
            name="cleanv9_big_2024h1_keeprev_cogs_r0780",
            h1_source_recovery=0.20,
            h1_ratio=0.870,
            h1_2024_ratio=0.780,
            thesis="High-risk 2024H1 COGS-ratio down stress.",
        ),
        CandidateSpec(
            name="cleanv9_big_2024h1_source_s020_r0820",
            h1_source_recovery=0.20,
            h1_ratio=0.870,
            h1_2024_source_recovery=0.20,
            h1_2024_ratio=0.820,
            h1_2024_keep_revenue=False,
            thesis="Reset 2024H1 to source-quality period head and lower COGS ratio; tests a full 2024H1 regime break.",
        ),
        CandidateSpec(
            name="cleanv9_big_finalday_scale070",
            h1_source_recovery=0.20,
            h1_ratio=0.870,
            final_day_scale=0.70,
            thesis="Single final-day boundary stress; checks if 2024-07-01 is overcalled.",
        ),
    ]


def sanity_check(frame: pd.DataFrame, name: str) -> None:
    if len(frame) != 548:
        raise ValueError(f"{name}: expected 548 rows, got {len(frame)}")
    dates = pd.to_datetime(frame["Date"])
    if dates.min() != FORECAST_START or dates.max() != FORECAST_END:
        raise ValueError(f"{name}: bad date range {dates.min()} - {dates.max()}")
    if frame[["Revenue", "COGS"]].isna().any().any():
        raise ValueError(f"{name}: contains NaN")
    if frame[["Revenue", "COGS"]].lt(0).any().any():
        raise ValueError(f"{name}: contains negative target values")


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Clean V9 Big-Jump All Paths

Run directory: `{run_dir}`

## Boundary

This is **clean-input public-guided**. It uses raw/train-derived source-quality period heads and current clean model components; it does not read `sample_submission.csv`, prior submissions, quarantine files, or test targets as inputs.

## Why This Run Exists

Instruction: stop local micro-optimization and test large public-informative axes.

Known public:

- `submission_cleanv7_source_h1_s020_r0870.csv = 673720.88479`
- `submission_cleanv7_sourcefine_s0190_r0870.csv = 674415.02000`, so lower H1 source level is rejected.

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Order

1. `submission_cleanv9_big_h1_keeprev_cogs_r0820.csv`
2. If improves: `submission_cleanv9_big_h1_source_s023_r0868.csv`
3. If H1 COGS-down fails: `submission_cleanv9_big_2024h1_keeprev_cogs_r0800.csv`
4. If 2024H1 COGS-down improves: `submission_cleanv9_big_2024h1_keeprev_cogs_r0780.csv`
5. If both H1 and 2024H1 fail: `submission_cleanv9_big_h2_keeprev_cogs_r0900.csv`
6. Use H1 source escalation only after a positive H1 sign: `submission_cleanv9_big_h1_source_s026_r0868.csv`, then `submission_cleanv9_big_h1_source_s030_r0868.csv`.

Do not use local gate as selector for this batch; each candidate is a public sign test for a large axis.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v9_bigjump_all_paths_2026-04-28.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    source_periods = build_source_period_table(run_dir)
    base_totals_frame = build_current_clean_totals(source_periods)
    shape_base = build_shape_base()

    rows: list[dict[str, object]] = []
    for priority, spec in enumerate(build_specs(), start=1):
        totals = apply_spec(base_totals_frame, source_periods, spec)
        frame = apply_period_totals(shape_base, totals).reset_index(drop=True)
        sanity_check(frame, spec.name)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)
        prof = period_summary(frame)
        prof.to_csv(run_dir / f"{spec.name}_period_summary.csv", index=False)
        totals.to_csv(run_dir / f"{spec.name}_target_totals.csv", index=False)
        row = {
            "priority": priority,
            "filename": path.name,
            "thesis": spec.thesis,
            "h1_source_recovery": spec.h1_source_recovery,
            "h1_ratio": spec.h1_ratio,
            "h2_source_recovery": spec.h2_source_recovery,
            "h2_ratio": spec.h2_ratio,
            "h1_2024_source_recovery": spec.h1_2024_source_recovery,
            "h1_2024_ratio": spec.h1_2024_ratio,
            "final_day_scale": spec.final_day_scale,
            "revenue_total": float(frame["Revenue"].sum()),
            "cogs_total": float(frame["COGS"].sum()),
            "ratio_total": float(frame["COGS"].sum() / frame["Revenue"].sum()),
            "max_revenue": float(frame["Revenue"].max()),
            "max_cogs": float(frame["COGS"].max()),
        }
        for _, period_row in prof.iterrows():
            period = str(period_row["period"])
            row[f"rev_{period}"] = float(period_row["revenue"])
            row[f"cogs_{period}"] = float(period_row["cogs"])
            row[f"ratio_{period}"] = float(period_row["cogs_ratio"])
        rows.append(row)

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    base_totals_frame.to_csv(run_dir / "base_current_clean_totals.csv", index=False)
    write_report(run_dir, manifest)
    print(run_dir)
    print(manifest[["priority", "filename", "h1_source_recovery", "h1_ratio", "h2_ratio", "h1_2024_ratio", "revenue_total", "cogs_total"]].to_string(index=False))


if __name__ == "__main__":
    main()
