from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from logging_utils import create_run_dir, setup_logger, write_json
from train_recursive_forecast import (
    SYSTEMS,
    apply_future_promo_policy,
    ensure_inputs,
    get_candidate_feature_sets,
    recursive_forecast,
)


RUN_PREFIX = "long_horizon_selection"
LONG_HORIZON_FOLDS = [
    ("2018-01-01", "2019-07-02"),
    ("2019-01-01", "2020-07-01"),
    ("2020-01-01", "2021-07-01"),
    ("2021-01-01", "2022-07-02"),
]
HORIZON_BUCKETS = [
    ("days_1_30", 1, 30),
    ("days_31_180", 31, 180),
    ("days_181_365", 181, 365),
    ("days_366_plus", 366, 10_000),
]


def _rmse(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def evaluate_long_horizon_systems(
    feature_store: pd.DataFrame,
    base: pd.DataFrame,
    feature_sets: dict[str, list[str]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    fold_rows: list[dict[str, object]] = []
    horizon_rows: list[dict[str, object]] = []

    for system_name, config in SYSTEMS.items():
        revenue_features = feature_sets[config["revenue_experiment"]]
        secondary_revenue_features = (
            feature_sets[config["secondary_revenue_experiment"]]
            if config.get("secondary_revenue_experiment")
            else None
        )
        revenue_regime_variant = config.get("revenue_regime_variant", "none")
        promo_future_policy = config.get("promo_future_policy", "zero")
        cogs_features = feature_sets[config["cogs_experiment"]]
        cogs_postprocess_variant = config["cogs_postprocess_variant"]

        for fold_id, (start_date, end_date) in enumerate(LONG_HORIZON_FOLDS, start=1):
            start_ts = pd.Timestamp(start_date)
            end_ts = pd.Timestamp(end_date)
            cutoff = start_ts - pd.Timedelta(days=1)

            adjusted_base = apply_future_promo_policy(base, cutoff, promo_future_policy)
            preds = recursive_forecast(
                feature_store=feature_store,
                full_base=adjusted_base,
                train_end_date=cutoff,
                forecast_start=start_ts,
                forecast_end=end_ts,
                revenue_features=revenue_features,
                cogs_features=cogs_features,
                cogs_postprocess_variant=cogs_postprocess_variant,
                secondary_revenue_features=secondary_revenue_features,
                revenue_regime_variant=revenue_regime_variant,
            )

            truth = feature_store.loc[
                (feature_store["Date"] >= start_ts) & (feature_store["Date"] <= end_ts),
                ["Date", "Revenue", "COGS"],
            ].copy()
            merged = truth.merge(preds, on="Date", how="left").sort_values("Date").reset_index(drop=True)
            merged["horizon_day"] = np.arange(1, len(merged) + 1)

            fold_rows.append(
                {
                    "system": system_name,
                    "fold": fold_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "n_days": len(merged),
                    "revenue_experiment": config["revenue_experiment"],
                    "secondary_revenue_experiment": config.get("secondary_revenue_experiment"),
                    "revenue_regime_variant": revenue_regime_variant,
                    "promo_future_policy": promo_future_policy,
                    "cogs_experiment": config["cogs_experiment"],
                    "cogs_postprocess_variant": cogs_postprocess_variant,
                    "revenue_mae": mean_absolute_error(merged["Revenue"], merged["Revenue_pred"]),
                    "revenue_rmse": _rmse(merged["Revenue"], merged["Revenue_pred"]),
                    "revenue_r2": r2_score(merged["Revenue"], merged["Revenue_pred"]),
                    "cogs_mae": mean_absolute_error(merged["COGS"], merged["COGS_pred"]),
                    "cogs_rmse": _rmse(merged["COGS"], merged["COGS_pred"]),
                    "cogs_r2": r2_score(merged["COGS"], merged["COGS_pred"]),
                    "combined_mae": mean_absolute_error(merged["Revenue"], merged["Revenue_pred"])
                    + mean_absolute_error(merged["COGS"], merged["COGS_pred"]),
                }
            )

            for bucket_name, start_h, end_h in HORIZON_BUCKETS:
                bucket = merged[(merged["horizon_day"] >= start_h) & (merged["horizon_day"] <= end_h)].copy()
                if bucket.empty:
                    continue
                horizon_rows.append(
                    {
                        "system": system_name,
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

    return pd.DataFrame(fold_rows), pd.DataFrame(horizon_rows)


def build_summary(fold_df: pd.DataFrame) -> pd.DataFrame:
    summary_df = (
        fold_df.groupby("system")
        .agg(
            revenue_mae_mean=("revenue_mae", "mean"),
            revenue_mae_std=("revenue_mae", "std"),
            revenue_mae_worst=("revenue_mae", "max"),
            revenue_rmse_mean=("revenue_rmse", "mean"),
            revenue_r2_mean=("revenue_r2", "mean"),
            cogs_mae_mean=("cogs_mae", "mean"),
            cogs_rmse_mean=("cogs_rmse", "mean"),
            cogs_r2_mean=("cogs_r2", "mean"),
            combined_mae_mean=("combined_mae", "mean"),
        )
        .reset_index()
        .sort_values(["revenue_mae_mean", "revenue_mae_worst"])
        .reset_index(drop=True)
    )
    summary_df["selector_rank"] = np.arange(1, len(summary_df) + 1)
    return summary_df


def build_horizon_summary(horizon_df: pd.DataFrame) -> pd.DataFrame:
    return (
        horizon_df.groupby(["system", "bucket"])
        .agg(
            n_days_total=("n_days", "sum"),
            revenue_mae_mean=("revenue_mae", "mean"),
            revenue_rmse_mean=("revenue_rmse", "mean"),
            cogs_mae_mean=("cogs_mae", "mean"),
            cogs_rmse_mean=("cogs_rmse", "mean"),
        )
        .reset_index()
        .sort_values(["bucket", "revenue_mae_mean", "cogs_mae_mean"])
        .reset_index(drop=True)
    )


def write_report(
    run_dir: Path,
    summary_df: pd.DataFrame,
    fold_df: pd.DataFrame,
    horizon_summary_df: pd.DataFrame,
    winner: str,
) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Long Horizon Selection Check\n\n")
        f.write("## Question\n")
        f.write(
            "- Does a longer recursive proxy closer to the real test horizon change the selected winner?\n\n"
        )
        f.write("## Design Notes\n")
        f.write("- Forecast horizon in the real submission: `548` days (`2023-01-01` to `2024-07-01`)\n")
        f.write("- Pseudo-test folds: four `548`-day windows that start on January 1 and end in July of the next year\n")
        f.write("- Ranking metric: `Revenue MAE mean`, then `Revenue MAE worst-fold` as tie-breaker\n")
        f.write(f"- Long-horizon winner: `{winner}`\n\n")

        f.write("## Long-Horizon Summary\n")
        f.write(summary_df.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Horizon Bucket Summary\n")
        f.write(horizon_summary_df.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Fold Details\n")
        f.write(fold_df.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting long-horizon selection check in %s", run_dir)

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))

    write_json(
        run_dir / "config.json",
        {
            "long_horizon_folds": LONG_HORIZON_FOLDS,
            "horizon_buckets": HORIZON_BUCKETS,
            "systems": SYSTEMS,
        },
    )

    fold_df, horizon_df = evaluate_long_horizon_systems(feature_store, base, feature_sets)
    fold_df.to_csv(run_dir / "long_horizon_fold_results.csv", index=False)
    horizon_df.to_csv(run_dir / "long_horizon_horizon_results.csv", index=False)

    summary_df = build_summary(fold_df)
    horizon_summary_df = build_horizon_summary(horizon_df)
    summary_df.to_csv(run_dir / "long_horizon_summary.csv", index=False)
    horizon_summary_df.to_csv(run_dir / "long_horizon_horizon_summary.csv", index=False)

    winner = str(summary_df.iloc[0]["system"])
    write_report(run_dir, summary_df, fold_df, horizon_summary_df, winner)

    logger.info("Long-horizon winner: %s", winner)
    logger.info("Saved summary to %s", run_dir / "long_horizon_summary.csv")
    logger.info("Saved report to %s", run_dir / "report.md")


if __name__ == "__main__":
    main()
