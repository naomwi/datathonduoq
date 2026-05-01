from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json
from train_recursive_forecast import (
    ensure_inputs,
    get_candidate_feature_sets,
    recursive_forecast,
    zero_unknown_promo_signals,
)


RUN_PREFIX = "analyze_2020_regime"
YEAR = 2020
REFERENCE_YEARS = [2018, 2019]
VARIANTS = {
    "recursive_control_revenue_promo": {
        "revenue_experiment": "baseline_plus_promo",
        "cogs_experiment": "curated_promo_cogs",
    },
    "recursive_challenger_revenue_promo_cogs": {
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
    },
}
REGIME_COLUMNS = [
    "Revenue",
    "COGS",
    "gross_margin",
    "total_discount",
    "avg_discount_rate",
    "promo_line_share",
    "active_promo_count",
    "active_stackable_promo_count",
]


def add_regime_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["cogs_ratio"] = np.where(out["Revenue"] > 0, out["COGS"] / out["Revenue"], np.nan)
    out["gross_margin_rate"] = np.where(out["Revenue"] > 0, out["gross_margin"] / out["Revenue"], np.nan)
    return out


def build_predictions(
    feature_store: pd.DataFrame,
    base: pd.DataFrame,
    feature_sets: dict[str, list[str]],
    variant_name: str,
) -> pd.DataFrame:
    config = VARIANTS[variant_name]
    start_ts = pd.Timestamp(f"{YEAR}-01-01")
    end_ts = pd.Timestamp(f"{YEAR}-12-31")
    cutoff = start_ts - pd.Timedelta(days=1)
    adjusted_base = zero_unknown_promo_signals(base, cutoff)
    preds = recursive_forecast(
        feature_store=feature_store,
        full_base=adjusted_base,
        train_end_date=cutoff,
        forecast_start=start_ts,
        forecast_end=end_ts,
        revenue_features=feature_sets[config["revenue_experiment"]],
        cogs_features=feature_sets[config["cogs_experiment"]],
    )
    preds = preds.rename(
        columns={
            "Revenue_pred": f"{variant_name}_Revenue_pred",
            "COGS_pred": f"{variant_name}_COGS_pred",
        }
    )
    return preds


def make_monthly_error_table(merged: pd.DataFrame) -> pd.DataFrame:
    table = merged.copy()
    table["month"] = table["Date"].dt.month

    for variant_name in VARIANTS:
        table[f"{variant_name}_revenue_abs_err"] = (
            table["Revenue"] - table[f"{variant_name}_Revenue_pred"]
        ).abs()
        table[f"{variant_name}_cogs_abs_err"] = (
            table["COGS"] - table[f"{variant_name}_COGS_pred"]
        ).abs()

    monthly = (
        table.groupby("month")
        .agg(
            revenue_actual_mean=("Revenue", "mean"),
            cogs_actual_mean=("COGS", "mean"),
            cogs_ratio_actual_mean=("cogs_ratio", "mean"),
            gross_margin_rate_actual_mean=("gross_margin_rate", "mean"),
            total_discount_mean=("total_discount", "mean"),
            avg_discount_rate_mean=("avg_discount_rate", "mean"),
            promo_line_share_mean=("promo_line_share", "mean"),
            active_promo_count_mean=("active_promo_count", "mean"),
            control_revenue_mae=("recursive_control_revenue_promo_revenue_abs_err", "mean"),
            challenger_revenue_mae=("recursive_challenger_revenue_promo_cogs_revenue_abs_err", "mean"),
            control_cogs_mae=("recursive_control_revenue_promo_cogs_abs_err", "mean"),
            challenger_cogs_mae=("recursive_challenger_revenue_promo_cogs_cogs_abs_err", "mean"),
        )
        .reset_index()
    )
    monthly["delta_revenue_mae_challenger_minus_control"] = (
        monthly["challenger_revenue_mae"] - monthly["control_revenue_mae"]
    )
    monthly["delta_cogs_mae_challenger_minus_control"] = (
        monthly["challenger_cogs_mae"] - monthly["control_cogs_mae"]
    )
    return monthly


def make_reference_comparison(base_2020: pd.DataFrame, historical_df: pd.DataFrame) -> pd.DataFrame:
    ref = (
        historical_df[historical_df["year"].isin(REFERENCE_YEARS)]
        .groupby("month")[REGIME_COLUMNS + ["cogs_ratio", "gross_margin_rate"]]
        .mean()
        .reset_index()
        .rename(
            columns={
                "Revenue": "ref_revenue_mean",
                "COGS": "ref_cogs_mean",
                "gross_margin": "ref_gross_margin_mean",
                "total_discount": "ref_total_discount_mean",
                "avg_discount_rate": "ref_avg_discount_rate_mean",
                "promo_line_share": "ref_promo_line_share_mean",
                "active_promo_count": "ref_active_promo_count_mean",
                "active_stackable_promo_count": "ref_active_stackable_promo_count_mean",
                "cogs_ratio": "ref_cogs_ratio_mean",
                "gross_margin_rate": "ref_gross_margin_rate_mean",
            }
        )
    )
    compare = base_2020.merge(ref, on="month", how="left")
    compare["delta_revenue_vs_ref"] = compare["Revenue"] - compare["ref_revenue_mean"]
    compare["delta_cogs_ratio_vs_ref"] = compare["cogs_ratio"] - compare["ref_cogs_ratio_mean"]
    compare["delta_gross_margin_rate_vs_ref"] = compare["gross_margin_rate"] - compare["ref_gross_margin_rate_mean"]
    compare["delta_discount_vs_ref"] = compare["total_discount"] - compare["ref_total_discount_mean"]
    compare["delta_promo_count_vs_ref"] = compare["active_promo_count"] - compare["ref_active_promo_count_mean"]
    return compare


def make_year_summary(base_df: pd.DataFrame) -> pd.DataFrame:
    return (
        base_df.groupby("year")[REGIME_COLUMNS + ["cogs_ratio", "gross_margin_rate"]]
        .mean()
        .reset_index()
        .sort_values("year")
    )


def write_report(
    run_dir: Path,
    year_summary: pd.DataFrame,
    monthly_errors: pd.DataFrame,
    monthly_reference: pd.DataFrame,
) -> None:
    report_path = run_dir / "report.md"
    worst_months = monthly_errors.sort_values("delta_revenue_mae_challenger_minus_control").tail(4)
    best_months = monthly_errors.sort_values("delta_revenue_mae_challenger_minus_control").head(4)

    with report_path.open("w", encoding="utf-8") as f:
        f.write("# 2020 Regime Analysis\n\n")
        f.write("## Goal\n")
        f.write("- Explain why the recursive challenger with `cogs_history` loses in 2020 but wins in 2021-2022.\n\n")

        f.write("## Year Summary\n")
        f.write(year_summary.to_markdown(index=False))
        f.write("\n\n")

        f.write("## 2020 Monthly Error Comparison\n")
        f.write(monthly_errors.to_markdown(index=False))
        f.write("\n\n")

        f.write("## 2020 vs 2018-2019 Reference\n")
        f.write(monthly_reference.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Months Where Challenger Was Most Worse\n")
        f.write(worst_months.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Months Where Challenger Was Best\n")
        f.write(best_months.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting 2020 regime analysis in %s", run_dir)

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    feature_store = add_regime_columns(feature_store)
    base = add_regime_columns(base)
    base["year"] = base["Date"].dt.year
    base["month"] = base["Date"].dt.month

    write_json(
        run_dir / "config.json",
        {
            "year": YEAR,
            "reference_years": REFERENCE_YEARS,
            "variants": VARIANTS,
        },
    )

    logger.info("Generating recursive predictions for 2020...")
    pred_frames = [build_predictions(feature_store, base, feature_sets, variant_name) for variant_name in VARIANTS]

    truth_2020 = feature_store.loc[
        (feature_store["Date"] >= pd.Timestamp(f"{YEAR}-01-01")) & (feature_store["Date"] <= pd.Timestamp(f"{YEAR}-12-31")),
        ["Date", "Revenue", "COGS", "gross_margin", "cogs_ratio", "gross_margin_rate", "total_discount", "avg_discount_rate", "promo_line_share", "active_promo_count"],
    ].copy()
    merged = truth_2020.copy()
    for pred_df in pred_frames:
        merged = merged.merge(pred_df, on="Date", how="left")

    monthly_errors = make_monthly_error_table(merged)
    monthly_errors.to_csv(run_dir / "monthly_error_2020.csv", index=False)

    base_2020 = (
        base[base["year"] == YEAR]
        .groupby("month")[REGIME_COLUMNS + ["cogs_ratio", "gross_margin_rate"]]
        .mean()
        .reset_index()
    )
    monthly_reference = make_reference_comparison(base_2020, base)
    monthly_reference.to_csv(run_dir / "monthly_reference_comparison.csv", index=False)

    year_summary = make_year_summary(base[base["year"].between(2018, 2022)])
    year_summary.to_csv(run_dir / "year_summary_2018_2022.csv", index=False)

    write_report(run_dir, year_summary, monthly_errors, monthly_reference)
    logger.info("Finished 2020 regime analysis. Artifacts written to %s", run_dir)


if __name__ == "__main__":
    main()
