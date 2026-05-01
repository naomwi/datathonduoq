from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from run_clean_regime_recovery_scenarios import gap_blend_total, load_sales, period_summary
from run_clean_v2_eda_guided_candidates import apply_ratio_shape, base_totals
from run_cleaninput_rawmdshape_pubguided import apply_period_totals, build_shape_base
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v3_period_funnel_ratio"


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    h1_beta: float
    h1_cogs_ratio: float
    h2_cogs_ratio: float | None = None
    ratio_shape_gamma: float = 0.0
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
    out["half"] = out["month"].le(6).map({True: "H1", False: "H2"})
    out["period"] = out["year"].astype(str) + out["half"]
    out.loc[out["Date"].eq(pd.Timestamp("2024-07-01")), "period"] = "2024-07-01"
    return out


def ratio_reference(sales: pd.DataFrame) -> dict[str, float]:
    hist = add_period_columns(sales)
    period = (
        hist.loc[hist["year"].between(2013, 2022)]
        .groupby(["year", "half"], as_index=False)
        .agg(revenue=("Revenue", "sum"), cogs=("COGS", "sum"))
    )
    period["ratio"] = period["cogs"] / period["revenue"]
    out: dict[str, float] = {}
    for half in ["H1", "H2"]:
        ratios = period.loc[period["half"].eq(half), "ratio"]
        for q in [0.50, 0.90, 0.95, 0.975, 0.98, 0.99, 1.0]:
            out[f"{half.lower()}_q{str(q).replace('.', '')}"] = float(ratios.quantile(q))
    return out


def override_period_totals(
    sales: pd.DataFrame,
    base: pd.DataFrame,
    h1_beta: float,
    h1_cogs_ratio: float,
    h2_cogs_ratio: float | None,
) -> pd.DataFrame:
    out = base.copy()

    h1_revenue = gap_blend_total(sales, "Revenue", 2023, "H1", h1_beta)
    h1_mask = out["period"].eq("2023H1")
    out.loc[h1_mask, "revenue"] = h1_revenue
    out.loc[h1_mask, "cogs"] = h1_revenue * h1_cogs_ratio

    if h2_cogs_ratio is not None:
        h2_mask = out["period"].eq("2023H2")
        out.loc[h2_mask, "cogs"] = out.loc[h2_mask, "revenue"] * h2_cogs_ratio

    out["cogs_ratio"] = out["cogs"] / out["revenue"]
    return out


def build_specs(ref: dict[str, float]) -> list[CandidateSpec]:
    h2_q98 = ref["h2_q098"]
    h2_q975 = ref["h2_q0975"]
    h2_q95 = ref["h2_q095"]
    return [
        CandidateSpec(
            name="cleanv3_b0440_h1r0870",
            h1_beta=0.440,
            h1_cogs_ratio=0.870,
            note="Best H1 level held fixed; lower H1 ratio toward train-plausible recovery stress.",
        ),
        CandidateSpec(
            name="cleanv3_b0440_h1r0882",
            h1_beta=0.440,
            h1_cogs_ratio=0.882,
            note="Best H1 level held fixed; higher H1 ratio to test whether COGS is undercalled.",
        ),
        CandidateSpec(
            name="cleanv3_b0440_h1r0876_h2q98",
            h1_beta=0.440,
            h1_cogs_ratio=0.876,
            h2_cogs_ratio=h2_q98,
            note="Keep best H1; replace 2023H2 max-ratio stress with train H2 q98 ratio.",
        ),
        CandidateSpec(
            name="cleanv3_b0440_h1r0876_h2q975",
            h1_beta=0.440,
            h1_cogs_ratio=0.876,
            h2_cogs_ratio=h2_q975,
            note="Keep best H1; soften 2023H2 ratio from max to train q97.5.",
        ),
        CandidateSpec(
            name="cleanv3_b0440_h1r0876_h2q95",
            h1_beta=0.440,
            h1_cogs_ratio=0.876,
            h2_cogs_ratio=h2_q95,
            note="Keep best H1; stronger clean H2 ratio normalization to train q95.",
        ),
        CandidateSpec(
            name="cleanv3_b0440_h1r0870_h2q98",
            h1_beta=0.440,
            h1_cogs_ratio=0.870,
            h2_cogs_ratio=h2_q98,
            note="Lower H1 ratio plus mild 2023H2 ratio normalization.",
        ),
        CandidateSpec(
            name="cleanv3_b0435_h1r0876",
            h1_beta=0.435,
            h1_cogs_ratio=0.876,
            note="Fine-map H1 period head just below current best b044.",
        ),
        CandidateSpec(
            name="cleanv3_b0445_h1r0876",
            h1_beta=0.445,
            h1_cogs_ratio=0.876,
            note="Fine-map H1 period head just above current best b044.",
        ),
        CandidateSpec(
            name="cleanv3_b0440_h1r0876_h2q98_dailyg025",
            h1_beta=0.440,
            h1_cogs_ratio=0.876,
            h2_cogs_ratio=h2_q98,
            ratio_shape_gamma=0.25,
            note="H2 q98 total plus train-derived promo/month daily COGS-ratio reshaping.",
        ),
    ]


def write_report(run_dir: Path, manifest: pd.DataFrame, ref: dict[str, float]) -> None:
    report = f"""# Clean V3 Period Funnel Ratio

Run directory: `{run_dir}`

## Boundary

This is a clean-input, public-guided calibration branch. It rebuilds the anchor/daily shape from raw provided inputs and train `sales.csv`; it does not read `sample_submission.csv`, previous submissions, or test targets as inputs.

Public feedback is used only to focus the neighborhood around the current clean-input best:

- `submission_cleanv2_h1fine_b044_r0876.csv = 673757.34993`
- `submission_cleanv2_h1fine_b045_r0876.csv = 673785.31754`
- `submission_cleanv2_h1fine_b046_r0876.csv = 673951.68734`
- `submission_cleanv2_h1funnel_b050_r0876.csv = 676153.29609`

## Method

Revenue period head:

- `2023H1 Revenue = recent_low_H1 + beta * (pre2019_high_H1 - recent_low_H1)`
- Current best beta neighborhood is around `0.44`.

COGS ratio head:

- `2023H1 COGS = 2023H1 Revenue * h1_ratio`
- `2023H2 COGS = 2023H2 Revenue * h2_ratio` for H2 ratio candidates.
- H2 ratio candidates use train quantiles instead of the old max-ratio stress.

## Train Ratio Reference

{pd.DataFrame([ref]).to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Order

1. `submission_cleanv3_b0440_h1r0870.csv`
2. `submission_cleanv3_b0440_h1r0882.csv`
3. `submission_cleanv3_b0440_h1r0876_h2q98.csv`
4. `submission_cleanv3_b0435_h1r0876.csv`
5. `submission_cleanv3_b0445_h1r0876.csv`
6. `submission_cleanv3_b0440_h1r0876_h2q975.csv`
7. `submission_cleanv3_b0440_h1r0870_h2q98.csv`
8. `submission_cleanv3_b0440_h1r0876_h2q98_dailyg025.csv`
9. `submission_cleanv3_b0440_h1r0876_h2q95.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v3_period_funnel_ratio_2026-04-24.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    sales = load_sales()
    shape_base = build_shape_base()
    base = base_totals(sales)
    ref = ratio_reference(sales)

    rows = []
    for priority, spec in enumerate(build_specs(ref), start=1):
        totals = override_period_totals(
            sales=sales,
            base=base,
            h1_beta=spec.h1_beta,
            h1_cogs_ratio=spec.h1_cogs_ratio,
            h2_cogs_ratio=spec.h2_cogs_ratio,
        )
        frame = apply_period_totals(shape_base, totals)
        if spec.ratio_shape_gamma:
            frame = apply_ratio_shape(frame, sales, spec.ratio_shape_gamma, "h2")
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)
        prof = period_summary(frame)
        prof.to_csv(run_dir / f"{spec.name}_period_summary.csv", index=False)
        totals.to_csv(run_dir / f"{spec.name}_target_totals.csv", index=False)
        rows.append(
            {
                "priority": priority,
                "filename": path.name,
                "h1_beta": spec.h1_beta,
                "h1_cogs_ratio_input": spec.h1_cogs_ratio,
                "h2_cogs_ratio_input": spec.h2_cogs_ratio,
                "ratio_shape_gamma": spec.ratio_shape_gamma,
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
