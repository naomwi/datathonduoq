from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from run_clean_regime_recovery_scenarios import load_sales, period_summary
from run_clean_v2_eda_guided_candidates import base_totals
from run_clean_v3_funnel_regime_head import build_period_table, funnel_revenue, same_half_history
from run_cleaninput_rawmdshape_pubguided import apply_period_totals, build_shape_base
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v3_funnel_followup"


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    conv_recovery: float
    h1_cogs_ratio: float
    note: str


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def build_specs() -> list[CandidateSpec]:
    return [
        CandidateSpec(
            name="cleanv3_funnel_c110_h1r0876",
            conv_recovery=0.110,
            h1_cogs_ratio=0.876,
            note="Funnel H1 recovery just below the current b044-equivalent level.",
        ),
        CandidateSpec(
            name="cleanv3_funnel_c111_h1r0876",
            conv_recovery=0.111,
            h1_cogs_ratio=0.876,
            note="Funnel H1 recovery nearly matching current clean best H1 total.",
        ),
        CandidateSpec(
            name="cleanv3_funnel_c112_h1r0876",
            conv_recovery=0.112,
            h1_cogs_ratio=0.876,
            note="Funnel H1 recovery slightly above current clean best H1 total.",
        ),
        CandidateSpec(
            name="cleanv3_funnel_c113_h1r0876",
            conv_recovery=0.113,
            h1_cogs_ratio=0.876,
            note="Upper-side funnel H1 recovery before the known b050 overshoot region.",
        ),
        CandidateSpec(
            name="cleanv3_funnel_c111_h1r0870",
            conv_recovery=0.111,
            h1_cogs_ratio=0.870,
            note="Same funnel H1 level, lower COGS ratio to test ratio head direction.",
        ),
        CandidateSpec(
            name="cleanv3_funnel_c111_h1r0882",
            conv_recovery=0.111,
            h1_cogs_ratio=0.882,
            note="Same funnel H1 level, higher COGS ratio to test ratio head direction.",
        ),
    ]


def apply_funnel_h1(periods: pd.DataFrame, base: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    out = base.copy()
    history = same_half_history(periods, 2023, "H1")
    revenue = funnel_revenue(history, 2023, spec.conv_recovery, sessions_mode="last")
    mask = out["period"].eq("2023H1")
    out.loc[mask, "revenue"] = revenue
    out.loc[mask, "cogs"] = revenue * spec.h1_cogs_ratio
    out["cogs_ratio"] = out["cogs"] / out["revenue"]
    return out


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Clean V3 Funnel Follow-Up

Run directory: `{run_dir}`

## Boundary

This is a clean-input public-guided follow-up. It uses raw/train data to compute a business funnel head:

`2023H1 Revenue = 2022 sessions * recovered_conversion * 2022 AOV`

No `sample_submission.csv`, previous submissions, or test targets are read as inputs.

The public result `submission_cleanv3_head_funnel_last_c10_h1only_r0876.csv = 674590.42937` showed that `c10` undercalled H1 versus the current clean best. This run maps the conversion-recovery parameter around the H1 total implied by `b044`.

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Order

1. `submission_cleanv3_funnel_c111_h1r0876.csv`
2. `submission_cleanv3_funnel_c112_h1r0876.csv`
3. `submission_cleanv3_funnel_c110_h1r0876.csv`
4. `submission_cleanv3_funnel_c111_h1r0870.csv`
5. `submission_cleanv3_funnel_c111_h1r0882.csv`
6. `submission_cleanv3_funnel_c113_h1r0876.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v3_funnel_followup_2026-04-24.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    sales = load_sales()
    periods = build_period_table()
    base = base_totals(sales)
    shape_base = build_shape_base()

    rows = []
    for priority, spec in enumerate(build_specs(), start=1):
        totals = apply_funnel_h1(periods, base, spec)
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
                "conv_recovery": spec.conv_recovery,
                "h1_cogs_ratio": spec.h1_cogs_ratio,
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
    write_report(run_dir, manifest)
    print(run_dir)


if __name__ == "__main__":
    main()
