from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from logging_utils import create_run_dir, setup_logger, write_json
from run_ablation import evaluate_experiment, load_training_frame
from train_recursive_forecast import (
    BACKTEST_FOLDS,
    ensure_inputs,
    get_candidate_feature_sets,
    recursive_forecast,
    zero_unknown_promo_signals,
)


RUN_PREFIX = "cogs_history_conflict_analysis"
ONE_STEP_CONTROL = "baseline_plus_promo"
ONE_STEP_CHALLENGER = "curated_promo_cogs"
RECURSIVE_VARIANTS = {
    "recursive_control_revenue_promo": {
        "revenue_experiment": "baseline_plus_promo",
        "cogs_experiment": "curated_promo_cogs",
    },
    "recursive_challenger_revenue_promo_cogs": {
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
    },
}
HORIZON_BUCKETS = [
    ("days_1_30", 1, 30),
    ("days_31_90", 31, 90),
    ("days_91_plus", 91, 10_000),
]


def _rmse(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def summarize_one_step(feature_sets: dict[str, list[str]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = load_training_frame()
    one_step_rows: list[dict[str, object]] = []

    for experiment_name in [ONE_STEP_CONTROL, ONE_STEP_CHALLENGER]:
        features = feature_sets[experiment_name]
        one_step_rows.extend(evaluate_experiment(df, experiment_name, features))

    fold_df = pd.DataFrame(one_step_rows)
    summary_df = (
        fold_df.groupby("experiment")
        .agg(
            n_features=("n_features", "mean"),
            mae_mean=("mae", "mean"),
            mae_std=("mae", "std"),
            rmse_mean=("rmse", "mean"),
            r2_mean=("r2", "mean"),
        )
        .reset_index()
        .sort_values("mae_mean")
        .reset_index(drop=True)
    )
    control_mae = float(summary_df.loc[summary_df["experiment"] == ONE_STEP_CONTROL, "mae_mean"].iloc[0])
    summary_df["delta_mae_vs_one_step_control"] = summary_df["mae_mean"] - control_mae
    return fold_df, summary_df


def evaluate_recursive_variants(
    feature_store: pd.DataFrame,
    base: pd.DataFrame,
    feature_sets: dict[str, list[str]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    fold_rows: list[dict[str, object]] = []
    horizon_rows: list[dict[str, object]] = []

    for variant_name, config in RECURSIVE_VARIANTS.items():
        revenue_features = feature_sets[config["revenue_experiment"]]
        cogs_features = feature_sets[config["cogs_experiment"]]

        for fold_id, (start_date, end_date) in enumerate(BACKTEST_FOLDS, start=1):
            start_ts = pd.Timestamp(start_date)
            end_ts = pd.Timestamp(end_date)
            cutoff = start_ts - pd.Timedelta(days=1)

            adjusted_base = zero_unknown_promo_signals(base, cutoff)
            preds = recursive_forecast(
                feature_store=feature_store,
                full_base=adjusted_base,
                train_end_date=cutoff,
                forecast_start=start_ts,
                forecast_end=end_ts,
                revenue_features=revenue_features,
                cogs_features=cogs_features,
            )

            truth = feature_store.loc[
                (feature_store["Date"] >= start_ts) & (feature_store["Date"] <= end_ts),
                ["Date", "Revenue", "COGS"],
            ].copy()
            merged = truth.merge(preds, on="Date", how="left").sort_values("Date").reset_index(drop=True)
            merged["horizon_day"] = np.arange(1, len(merged) + 1)

            fold_rows.append(
                {
                    "variant": variant_name,
                    "fold": fold_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "revenue_experiment": config["revenue_experiment"],
                    "cogs_experiment": config["cogs_experiment"],
                    "revenue_mae": mean_absolute_error(merged["Revenue"], merged["Revenue_pred"]),
                    "revenue_rmse": _rmse(merged["Revenue"], merged["Revenue_pred"]),
                    "revenue_r2": r2_score(merged["Revenue"], merged["Revenue_pred"]),
                    "cogs_mae": mean_absolute_error(merged["COGS"], merged["COGS_pred"]),
                    "cogs_rmse": _rmse(merged["COGS"], merged["COGS_pred"]),
                    "cogs_r2": r2_score(merged["COGS"], merged["COGS_pred"]),
                }
            )

            for bucket_name, start_h, end_h in HORIZON_BUCKETS:
                bucket = merged[(merged["horizon_day"] >= start_h) & (merged["horizon_day"] <= end_h)].copy()
                if bucket.empty:
                    continue
                horizon_rows.append(
                    {
                        "variant": variant_name,
                        "fold": fold_id,
                        "bucket": bucket_name,
                        "bucket_start_day": start_h,
                        "bucket_end_day": min(end_h, int(bucket["horizon_day"].max())),
                        "n_days": len(bucket),
                        "revenue_mae": mean_absolute_error(bucket["Revenue"], bucket["Revenue_pred"]),
                        "revenue_rmse": _rmse(bucket["Revenue"], bucket["Revenue_pred"]),
                        "cogs_mae": mean_absolute_error(bucket["COGS"], bucket["COGS_pred"]),
                        "cogs_rmse": _rmse(bucket["COGS"], bucket["COGS_pred"]),
                    }
                )

    fold_df = pd.DataFrame(fold_rows)
    horizon_df = pd.DataFrame(horizon_rows)
    return fold_df, horizon_df


def write_report(
    run_dir: Path,
    one_step_summary: pd.DataFrame,
    one_step_folds: pd.DataFrame,
    recursive_summary: pd.DataFrame,
    recursive_folds: pd.DataFrame,
    recursive_horizon_summary: pd.DataFrame,
) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# COGS History Conflict Analysis\n\n")
        f.write("## Question\n")
        f.write(
            "- Why does `cogs_history` lose in one-step ablation but appear to help in recursive backtesting?\n\n"
        )
        f.write("## Design Notes\n")
        f.write(f"- One-step control: `{ONE_STEP_CONTROL}`\n")
        f.write(f"- One-step challenger: `{ONE_STEP_CHALLENGER}`\n")
        f.write("- Recursive control changes only the revenue branch to `baseline_plus_promo`\n")
        f.write("- Recursive challenger changes only the revenue branch to `curated_promo_cogs`\n")
        f.write("- The COGS branch feature set stays `curated_promo_cogs`, but its predictions can still change because it consumes recursive revenue history.\n\n")

        f.write("## One-Step Summary\n")
        f.write(one_step_summary.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Recursive Fold Summary\n")
        f.write(recursive_summary.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Recursive Horizon Summary\n")
        f.write(recursive_horizon_summary.to_markdown(index=False))
        f.write("\n\n")

        f.write("## One-Step Fold Details\n")
        f.write(one_step_folds.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Recursive Fold Details\n")
        f.write(recursive_folds.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting cogs_history conflict analysis in %s", run_dir)

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))

    write_json(
        run_dir / "config.json",
        {
            "one_step_control": ONE_STEP_CONTROL,
            "one_step_challenger": ONE_STEP_CHALLENGER,
            "recursive_variants": RECURSIVE_VARIANTS,
            "horizon_buckets": HORIZON_BUCKETS,
        },
    )

    logger.info("Running one-step evidence...")
    one_step_folds, one_step_summary = summarize_one_step(feature_sets)
    one_step_folds.to_csv(run_dir / "one_step_fold_results.csv", index=False)
    one_step_summary.to_csv(run_dir / "one_step_summary.csv", index=False)

    logger.info("Running recursive evidence...")
    recursive_folds, recursive_horizons = evaluate_recursive_variants(feature_store, base, feature_sets)
    recursive_folds.to_csv(run_dir / "recursive_fold_results.csv", index=False)
    recursive_horizons.to_csv(run_dir / "recursive_horizon_results.csv", index=False)

    recursive_summary = (
        recursive_folds.groupby("variant")
        .agg(
            revenue_mae_mean=("revenue_mae", "mean"),
            revenue_rmse_mean=("revenue_rmse", "mean"),
            revenue_r2_mean=("revenue_r2", "mean"),
            cogs_mae_mean=("cogs_mae", "mean"),
            cogs_rmse_mean=("cogs_rmse", "mean"),
            cogs_r2_mean=("cogs_r2", "mean"),
        )
        .reset_index()
        .sort_values("revenue_mae_mean")
        .reset_index(drop=True)
    )
    recursive_summary.to_csv(run_dir / "recursive_summary.csv", index=False)

    recursive_horizon_summary = (
        recursive_horizons.groupby(["variant", "bucket"])
        .agg(
            n_days_total=("n_days", "sum"),
            revenue_mae_mean=("revenue_mae", "mean"),
            revenue_rmse_mean=("revenue_rmse", "mean"),
            cogs_mae_mean=("cogs_mae", "mean"),
            cogs_rmse_mean=("cogs_rmse", "mean"),
        )
        .reset_index()
    )
    recursive_horizon_summary.to_csv(run_dir / "recursive_horizon_summary.csv", index=False)

    write_report(
        run_dir=run_dir,
        one_step_summary=one_step_summary,
        one_step_folds=one_step_folds,
        recursive_summary=recursive_summary,
        recursive_folds=recursive_folds,
        recursive_horizon_summary=recursive_horizon_summary,
    )
    logger.info("Finished cogs_history conflict analysis. Artifacts written to %s", run_dir)


if __name__ == "__main__":
    main()
