from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_clean_regime_recovery_scenarios import load_sales, period_summary
from run_clean_v2_eda_guided_candidates import base_totals
from run_clean_v3_funnel_regime_head import build_period_table, funnel_revenue, same_half_history
from run_cleaninput_rawmdshape_pubguided import apply_period_totals, build_shape_base
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v3_ratio_axis"
BASE_CONV_RECOVERY = 0.110


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    h1_cogs_ratio: float = 0.876
    h2_cogs_ratio: float | None = None
    h1_2024_cogs_ratio: float | None = None
    note: str = ""


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def add_period_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out["year"] = out["Date"].dt.year
    out["month"] = out["Date"].dt.month
    out["half"] = np.where(out["month"].le(6), "H1", "H2")
    out["period"] = out["year"].astype(str) + out["half"]
    out.loc[out["Date"].eq(pd.Timestamp("2024-07-01")), "period"] = "2024-07-01"
    return out


def ratio_reference(sales: pd.DataFrame) -> dict[str, float]:
    hist = add_period_columns(sales)
    periods = (
        hist.loc[hist["year"].between(2013, 2022)]
        .groupby(["year", "half"], as_index=False)
        .agg(revenue=("Revenue", "sum"), cogs=("COGS", "sum"))
    )
    periods["ratio"] = periods["cogs"] / periods["revenue"]
    out: dict[str, float] = {}
    for half in ["H1", "H2"]:
        values = periods.loc[periods["half"].eq(half), "ratio"]
        for q in [0.50, 0.75, 0.90, 0.95, 0.975, 0.98, 0.99, 1.0]:
            out[f"{half.lower()}_q{str(q).replace('.', '')}"] = float(values.quantile(q))
    return out


def build_specs(ref: dict[str, float]) -> list[CandidateSpec]:
    return [
        CandidateSpec(
            name="cleanv3_ratio_c110_h1r0870",
            h1_cogs_ratio=0.870,
            note="Same c110 funnel H1 level; lower H1 COGS ratio.",
        ),
        CandidateSpec(
            name="cleanv3_ratio_c110_h1r0882",
            h1_cogs_ratio=0.882,
            note="Same c110 funnel H1 level; higher H1 COGS ratio.",
        ),
        CandidateSpec(
            name="cleanv3_ratio_c110_h1r0866",
            h1_cogs_ratio=0.866,
            note="Lower H1 COGS ratio stress, still above train H1 max.",
        ),
        CandidateSpec(
            name="cleanv3_ratio_c110_h2q98",
            h2_cogs_ratio=ref["h2_q098"],
            note="Normalize 2023H2 COGS ratio from train max to train H2 q98.",
        ),
        CandidateSpec(
            name="cleanv3_ratio_c110_h2q975",
            h2_cogs_ratio=ref["h2_q0975"],
            note="Normalize 2023H2 COGS ratio from train max to train H2 q97.5.",
        ),
        CandidateSpec(
            name="cleanv3_ratio_c110_h1r0870_h2q98",
            h1_cogs_ratio=0.870,
            h2_cogs_ratio=ref["h2_q098"],
            note="Combine lower H1 ratio with mild H2 ratio normalization.",
        ),
        CandidateSpec(
            name="cleanv3_ratio_c110_2024h1q95",
            h1_2024_cogs_ratio=ref["h1_q095"],
            note="Small 2024H1 COGS ratio lift to train H1 q95.",
        ),
        CandidateSpec(
            name="cleanv3_ratio_c110_2024h1q98",
            h1_2024_cogs_ratio=ref["h1_q098"],
            note="Stronger 2024H1 COGS ratio lift to train H1 q98.",
        ),
        CandidateSpec(
            name="cleanv3_ratio_c110_h1r0870_2024h1q95",
            h1_cogs_ratio=0.870,
            h1_2024_cogs_ratio=ref["h1_q095"],
            note="Lower 2023H1 ratio plus small 2024H1 ratio lift.",
        ),
    ]


def apply_ratio_axis(periods: pd.DataFrame, base: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    out = base.copy()
    h1_history = same_half_history(periods, 2023, "H1")
    h1_revenue = funnel_revenue(h1_history, 2023, BASE_CONV_RECOVERY, sessions_mode="last")
    h1_mask = out["period"].eq("2023H1")
    out.loc[h1_mask, "revenue"] = h1_revenue
    out.loc[h1_mask, "cogs"] = h1_revenue * spec.h1_cogs_ratio

    if spec.h2_cogs_ratio is not None:
        h2_mask = out["period"].eq("2023H2")
        out.loc[h2_mask, "cogs"] = out.loc[h2_mask, "revenue"] * spec.h2_cogs_ratio

    if spec.h1_2024_cogs_ratio is not None:
        h1_2024_mask = out["period"].eq("2024H1")
        out.loc[h1_2024_mask, "cogs"] = out.loc[h1_2024_mask, "revenue"] * spec.h1_2024_cogs_ratio

    out["cogs_ratio"] = out["cogs"] / out["revenue"]
    return out


def write_report(run_dir: Path, manifest: pd.DataFrame, ref: dict[str, float]) -> None:
    report = f"""# Clean V3 Ratio Axis

Run directory: `{run_dir}`

## Boundary

This is a clean-input public-guided follow-up. It freezes the H1 level at the submitted `c110` funnel head:

`2023H1 Revenue = 2022 sessions * recovered_conversion(0.110) * 2022 AOV`

Then it changes only COGS ratio assumptions. It does not read `sample_submission.csv`, previous submissions, or test targets as inputs.

Known score:

- `submission_cleanv3_funnel_c110_h1r0876.csv = 673759.96838`

## Train Ratio Reference

{pd.DataFrame([ref]).to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Order

1. `submission_cleanv3_ratio_c110_h1r0870.csv`
2. `submission_cleanv3_ratio_c110_h1r0882.csv`
3. `submission_cleanv3_ratio_c110_h2q98.csv`
4. `submission_cleanv3_ratio_c110_h1r0866.csv`
5. `submission_cleanv3_ratio_c110_h1r0870_h2q98.csv`
6. `submission_cleanv3_ratio_c110_2024h1q95.csv`
7. `submission_cleanv3_ratio_c110_h2q975.csv`
8. `submission_cleanv3_ratio_c110_2024h1q98.csv`
9. `submission_cleanv3_ratio_c110_h1r0870_2024h1q95.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v3_ratio_axis_2026-04-24.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    sales = load_sales()
    periods = build_period_table()
    base = base_totals(sales)
    shape_base = build_shape_base()
    ref = ratio_reference(sales)

    rows = []
    for priority, spec in enumerate(build_specs(ref), start=1):
        totals = apply_ratio_axis(periods, base, spec)
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
                "h1_cogs_ratio": spec.h1_cogs_ratio,
                "h2_cogs_ratio": spec.h2_cogs_ratio,
                "h1_2024_cogs_ratio": spec.h1_2024_cogs_ratio,
                "revenue_total": frame["Revenue"].sum(),
                "cogs_total": frame["COGS"].sum(),
                "ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
                "rev_2023H1": prof.loc[prof["period"].eq("2023H1"), "revenue"].iloc[0],
                "cogs_2023H1": prof.loc[prof["period"].eq("2023H1"), "cogs"].iloc[0],
                "ratio_2023H1": prof.loc[prof["period"].eq("2023H1"), "cogs_ratio"].iloc[0],
                "rev_2023H2": prof.loc[prof["period"].eq("2023H2"), "revenue"].iloc[0],
                "cogs_2023H2": prof.loc[prof["period"].eq("2023H2"), "cogs"].iloc[0],
                "ratio_2023H2": prof.loc[prof["period"].eq("2023H2"), "cogs_ratio"].iloc[0],
                "rev_2024H1": prof.loc[prof["period"].eq("2024H1"), "revenue"].iloc[0],
                "cogs_2024H1": prof.loc[prof["period"].eq("2024H1"), "cogs"].iloc[0],
                "ratio_2024H1": prof.loc[prof["period"].eq("2024H1"), "cogs_ratio"].iloc[0],
                "note": spec.note,
            }
        )

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    write_report(run_dir, manifest, ref)
    print(run_dir)


if __name__ == "__main__":
    main()
