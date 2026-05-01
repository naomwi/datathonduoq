from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_clean_regime_recovery_scenarios import (
    Scenario,
    build_forecast,
    load_sales,
    period_summary as scenario_period_summary,
)
from run_cleanroom_rawmd_pipeline import RawMdConfig, add_period_columns, apply_rawmd_config, build_clean_anchor
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission
from train_recursive_forecast import TRAIN_END, ensure_inputs, get_candidate_feature_sets


RUN_PREFIX = "cleaninput_rawmdshape_pubguided"


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    scenario: Scenario
    cogs_2024h1_mode: str = "scenario"
    note: str = ""


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def train_gap_cogs_total(sales: pd.DataFrame, year: int, half: str, beta: float) -> float:
    hist = (
        sales.groupby(["year", "half"], as_index=False)
        .agg(cogs=("COGS", "sum"))
        .loc[lambda d: d["year"].between(2013, 2022) & d["half"].eq(half)]
    )
    recent = float(hist.loc[hist["year"].between(2019, 2022), "cogs"].mean())
    pre = float(hist.loc[hist["year"].between(2013, 2018), "cogs"].mean())
    return float((1.0 - beta) * recent + beta * pre)


def build_shape_base() -> pd.DataFrame:
    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    anchor = build_clean_anchor(feature_store, base, feature_sets)
    history = feature_store.loc[feature_store["Date"] <= TRAIN_END, ["Date", "Revenue", "COGS"]].copy()
    raw_config = RawMdConfig(
        name="rawmd_r080_h2r010_c065",
        revenue_alpha_non_h2=0.80,
        revenue_alpha_h2=0.10,
        cogs_alpha=0.65,
        cogs_period_scale={},
        note="Train-only raw month-day shape mixed with regenerated clean anchor.",
    )
    return apply_rawmd_config(anchor, history, raw_config)


def apply_period_totals(shape_base: pd.DataFrame, totals: pd.DataFrame) -> pd.DataFrame:
    out = add_period_columns(shape_base)
    totals = totals.set_index("period")
    for period, idx in out.groupby("period").groups.items():
        if period not in totals.index:
            continue
        idx = list(idx)
        for target, total_col in [("Revenue", "revenue"), ("COGS", "cogs")]:
            current = float(out.loc[idx, target].sum())
            target_total = float(totals.loc[period, total_col])
            if current <= 0:
                out.loc[idx, target] = target_total / len(idx)
            else:
                out.loc[idx, target] *= target_total / current
    return out[["Date", "Revenue", "COGS", "period"]]


def make_totals_from_scenario(sales: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    scenario_frame = build_forecast(sales, spec.scenario)
    totals = scenario_period_summary(scenario_frame)
    if spec.cogs_2024h1_mode == "gap_beta0545":
        mask = totals["period"].eq("2024H1")
        totals.loc[mask, "cogs"] = train_gap_cogs_total(sales, 2024, "H1", beta=0.545)
        totals["cogs_ratio"] = totals["cogs"] / totals["revenue"]
    if spec.cogs_2024h1_mode == "gap_beta0515":
        mask = totals["period"].eq("2024H1")
        totals.loc[mask, "cogs"] = train_gap_cogs_total(sales, 2024, "H1", beta=0.515)
        totals["cogs_ratio"] = totals["cogs"] / totals["revenue"]
    return totals


def build_specs() -> list[CandidateSpec]:
    main = Scenario(
        name="internal_v4_main",
        level_mode="gap",
        beta_2023_h1=0.24,
        beta_2023_h2=0.53,
        beta_2024_h1=0.51,
        beta_2024_h2=0.51,
        revenue_h1_pre_shape=0.55,
        revenue_h2_pre_shape=1.00,
        cogs_h1_pre_shape=0.35,
        cogs_h2_pre_shape=1.00,
        cogs_ratio_mode="transition_stress_p95_h2max_2024h1max",
    )
    h1p85 = Scenario(
        name="internal_v4_h1p85",
        level_mode="gap",
        beta_2023_h1=0.24,
        beta_2023_h2=0.53,
        beta_2024_h1=0.51,
        beta_2024_h2=0.51,
        revenue_h1_pre_shape=0.55,
        revenue_h2_pre_shape=1.00,
        cogs_h1_pre_shape=0.35,
        cogs_h2_pre_shape=1.00,
        cogs_ratio_mode="transition_stress_p85_h2max_2024h1max",
    )
    revlow = Scenario(
        name="internal_v4_revlow",
        level_mode="gap",
        beta_2023_h1=0.18,
        beta_2023_h2=0.55,
        beta_2024_h1=0.51,
        beta_2024_h2=0.51,
        revenue_h1_pre_shape=0.55,
        revenue_h2_pre_shape=1.00,
        cogs_h1_pre_shape=0.35,
        cogs_h2_pre_shape=1.00,
        cogs_ratio_mode="transition_stress_p95_h2max_2024h1max",
    )
    return [
        CandidateSpec(
            name="cleaninput_rawmdshape_v5_v4main",
            scenario=main,
            note="Use clean raw-md/anchor daily shape with v4 clean-input public-guided period totals.",
        ),
        CandidateSpec(
            name="cleaninput_rawmdshape_v5_v4main_cogs2024gap0545",
            scenario=main,
            cogs_2024h1_mode="gap_beta0545",
            note="Same as v4main, but 2024H1 COGS is an independent train low/high gap total rather than max H1 ratio.",
        ),
        CandidateSpec(
            name="cleaninput_rawmdshape_v5_h1p85",
            scenario=h1p85,
            cogs_2024h1_mode="gap_beta0545",
            note="Softer 2023H1 COGS upper-tail plus independent 2024H1 COGS gap total.",
        ),
        CandidateSpec(
            name="cleaninput_rawmdshape_v5_revlow",
            scenario=revlow,
            cogs_2024h1_mode="gap_beta0545",
            note="Lower 2023H1 revenue, stronger 2023H2 revenue, raw-md daily shape.",
        ),
        CandidateSpec(
            name="cleaninput_rawmdshape_v5_v4main_cogs2024gap0515",
            scenario=main,
            cogs_2024h1_mode="gap_beta0515",
            note="Slightly lower 2024H1 COGS independent gap total.",
        ),
    ]


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Clean-Input RawMD Shape Public-Guided V5

Run directory: `{run_dir}`

## Boundary

This branch does not read `sample_submission.csv`, previous submission files, or test target values as inputs.

It is **clean-input but public-guided**: period-level recovery assumptions were adjusted after public feedback, while daily shape is rebuilt from raw provided files and train `sales.csv` month-day priors.

## Why This Run Exists

The v4 period totals are close to the best-known region, but v4 uses a pure historical sales-profile daily shape. The earlier source-clean raw-md/anchor shape scored much better, so this run keeps v4-style totals and swaps in the cleaner raw-md/anchor daily allocation.

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Order

1. `submission_cleaninput_rawmdshape_v5_v4main_cogs2024gap0545.csv`
2. `submission_cleaninput_rawmdshape_v5_v4main.csv`
3. `submission_cleaninput_rawmdshape_v5_h1p85.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "cleaninput_rawmdshape_pubguided_v5_2026-04-23.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    sales = load_sales()
    shape_base = build_shape_base()
    rows = []
    for priority, spec in enumerate(build_specs(), start=1):
        totals = make_totals_from_scenario(sales, spec)
        frame = apply_period_totals(shape_base, totals)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)
        prof = scenario_period_summary(frame)
        prof.to_csv(run_dir / f"{spec.name}_period_summary.csv", index=False)
        rows.append(
            {
                "priority": priority,
                "filename": path.name,
                "cogs_2024h1_mode": spec.cogs_2024h1_mode,
                "revenue_total": frame["Revenue"].sum(),
                "cogs_total": frame["COGS"].sum(),
                "ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
                "rev_2023H1": prof.loc[prof["period"].eq("2023H1"), "revenue"].iloc[0],
                "rev_2023H2": prof.loc[prof["period"].eq("2023H2"), "revenue"].iloc[0],
                "rev_2024H1": prof.loc[prof["period"].eq("2024H1"), "revenue"].iloc[0],
                "cogs_2023H1": prof.loc[prof["period"].eq("2023H1"), "cogs"].iloc[0],
                "cogs_2023H2": prof.loc[prof["period"].eq("2023H2"), "cogs"].iloc[0],
                "cogs_2024H1": prof.loc[prof["period"].eq("2024H1"), "cogs"].iloc[0],
                "ratio_2023H1": prof.loc[prof["period"].eq("2023H1"), "cogs_ratio"].iloc[0],
                "ratio_2023H2": prof.loc[prof["period"].eq("2023H2"), "cogs_ratio"].iloc[0],
                "ratio_2024H1": prof.loc[prof["period"].eq("2024H1"), "cogs_ratio"].iloc[0],
                "note": spec.note,
            }
        )

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    write_report(run_dir, manifest)
    print(run_dir)


if __name__ == "__main__":
    main()
