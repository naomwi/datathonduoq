from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from build_feature_store import OUT_PATH as FEATURE_STORE_PATH, build_feature_store
from feature_pipeline import (
    PROMO_TARGET_ENCODING_COLUMNS,
    TRAIN_END,
    get_ablation_feature_groups,
    get_feature_group_policies,
)


OUT_DIR = Path("outputs/ablation")
OUT_DIR.mkdir(parents=True, exist_ok=True)

FOLDS = [
    ("2020-01-01", "2020-12-31"),
    ("2021-01-01", "2021-12-31"),
    ("2022-01-01", "2022-12-31"),
]

MODEL_PARAMS = {
    "objective": "reg:squarederror",
    "n_estimators": 700,
    "learning_rate": 0.03,
    "max_depth": 5,
    "min_child_weight": 3,
    "subsample": 0.8,
    "colsample_bytree": 0.7,
    "reg_alpha": 0.0,
    "reg_lambda": 1.0,
    "random_state": 42,
    "tree_method": "hist",
    "n_jobs": 0,
    "early_stopping_rounds": 40,
}


def ensure_feature_store() -> Path:
    if not FEATURE_STORE_PATH.exists():
        return build_feature_store()
    return FEATURE_STORE_PATH


def load_training_frame() -> pd.DataFrame:
    feature_store_path = ensure_feature_store()
    df = pd.read_csv(feature_store_path, parse_dates=["Date"], low_memory=False)
    return df[df["Date"] <= pd.Timestamp(TRAIN_END)].copy()


def build_experiments(df: pd.DataFrame) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    groups = get_ablation_feature_groups(df)
    policies = get_feature_group_policies()
    baseline_groups = ["calendar", "revenue_history"]
    additive_groups = [
        name
        for name in [
            "cogs_history",
            "order_flow",
            "traffic",
            "promo",
            "returns_reviews",
            "inventory",
            "mix",
            "geo_logistics",
        ]
        if groups.get(name)
    ]

    baseline_features = sorted(set().union(*(groups[name] for name in baseline_groups)))
    full_features = sorted(set(baseline_features).union(*(groups[name] for name in additive_groups)))

    experiments: dict[str, list[str]] = {
        "baseline_calendar_revenue_history": baseline_features,
    }

    for group_name in additive_groups:
        experiments[f"baseline_plus_{group_name}"] = sorted(set(baseline_features).union(groups[group_name]))

    experiments["curated_promo_cogs"] = sorted(
        set(baseline_features).union(groups.get("promo", [])).union(groups.get("cogs_history", []))
    )
    experiments["curated_promo_cogs_hierarchy_lite"] = sorted(
        set(experiments["curated_promo_cogs"]).union(groups.get("hierarchy_lite", []))
    )
    experiments["curated_promo_cogs_target_seasonal"] = sorted(
        set(experiments["curated_promo_cogs"]).union(groups.get("target_seasonal_priors", []))
    )
    experiments["curated_promo_cogs_promo_research"] = sorted(
        set(experiments["curated_promo_cogs"]).union(groups.get("promo_research", []))
    )
    experiments["curated_promo_cogs_target_history_plus"] = sorted(
        set(experiments["curated_promo_cogs"]).union(groups.get("target_history_plus", []))
    )
    experiments["curated_promo_cogs_price_history"] = sorted(
        set(experiments["curated_promo_cogs"]).union(groups.get("price_history", []))
    )
    experiments["curated_promo_cogs_research_blocks"] = sorted(
        set(experiments["curated_promo_cogs"])
        .union(groups.get("promo_research", []))
        .union(groups.get("target_history_plus", []))
        .union(groups.get("price_history", []))
    )
    forecast_core_group_names = [
        name
        for name, policy in policies.items()
        if policy["usage_policy"] == "forecast_core" and name not in baseline_groups
    ]
    promo_strict_features = [
        col
        for col in groups.get("promo", [])
        if not any(col == stem or col.startswith(f"{stem}_") for stem in PROMO_TARGET_ENCODING_COLUMNS)
    ]
    forecast_core_union: set[str] = set(baseline_features)
    for group_name in forecast_core_group_names:
        if group_name == "promo":
            forecast_core_union.update(promo_strict_features)
        else:
            forecast_core_union.update(groups.get(group_name, []))
    experiments["forecast_core_strict"] = sorted(forecast_core_union)
    experiments["forecast_core_plus_promo_detail"] = sorted(
        forecast_core_union.union(groups.get("promo_detail", []))
    )
    experiments["forecast_core_plus_geo_logistics"] = sorted(
        forecast_core_union.union(groups.get("geo_logistics", []))
    )
    experiments["forecast_core_plus_mix_light"] = sorted(
        forecast_core_union.union(groups.get("mix_light", []))
    )
    forecast_core_promo_slim = set(baseline_features)
    forecast_core_promo_slim.update(groups.get("cogs_history", []))
    forecast_core_promo_slim.update(groups.get("promo_slim", []))
    experiments["forecast_core_promo_slim"] = sorted(forecast_core_promo_slim)
    experiments["forecast_core_promo_slim_hierarchy_lite"] = sorted(
        forecast_core_promo_slim.union(groups.get("hierarchy_lite", []))
    )
    experiments["forecast_core_strict_hierarchy_lite"] = sorted(
        forecast_core_union.union(groups.get("hierarchy_lite", []))
    )
    experiments["curated_promo_slim_cogs"] = experiments["forecast_core_promo_slim"]
    experiments["curated_promo_slim_cogs_hierarchy_lite"] = experiments[
        "forecast_core_promo_slim_hierarchy_lite"
    ]
    experiments["curated_context_promo_cogs"] = sorted(
        set(baseline_features)
        .union(groups.get("promo", []))
        .union(groups.get("cogs_history", []))
        .union(groups.get("geo_logistics", []))
    )
    curated_pruned_full_groups = ["cogs_history", "traffic", "promo", "mix"]
    curated_pruned_no_traffic_groups = ["cogs_history", "promo", "mix"]
    experiments["curated_pruned_full"] = sorted(
        set(baseline_features).union(*(groups[name] for name in curated_pruned_full_groups if groups.get(name)))
    )
    experiments["curated_pruned_no_traffic"] = sorted(
        set(baseline_features).union(*(groups[name] for name in curated_pruned_no_traffic_groups if groups.get(name)))
    )

    experiments["full_model"] = full_features

    for group_name in additive_groups:
        experiments[f"full_minus_{group_name}"] = [col for col in full_features if col not in set(groups[group_name])]

    return groups, experiments


def evaluate_experiment(df: pd.DataFrame, experiment_name: str, features: list[str]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []

    for fold_id, (start_date, end_date) in enumerate(FOLDS, start=1):
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)

        train_df = df[df["Date"] < start_ts].copy()
        valid_df = df[(df["Date"] >= start_ts) & (df["Date"] <= end_ts)].copy()

        X_train = train_df[features]
        y_train = train_df["Revenue"]
        X_valid = valid_df[features]
        y_valid = valid_df["Revenue"]

        model = xgb.XGBRegressor(**MODEL_PARAMS)
        model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], verbose=False)

        preds = model.predict(X_valid)

        results.append(
            {
                "experiment": experiment_name,
                "fold": fold_id,
                "start_date": start_date,
                "end_date": end_date,
                "n_features": len(features),
                "mae": mean_absolute_error(y_valid, preds),
                "rmse": np.sqrt(mean_squared_error(y_valid, preds)),
                "r2": r2_score(y_valid, preds),
            }
        )

    return results


def make_markdown_report(
    groups: dict[str, list[str]],
    fold_results: pd.DataFrame,
    summary: pd.DataFrame,
) -> None:
    report_path = OUT_DIR / "ablation_report.md"

    group_sizes = (
        pd.DataFrame(
            [{"group": group_name, "n_columns": len(columns)} for group_name, columns in groups.items() if columns]
        )
        .sort_values("group")
    )

    ranking_cols = [
        "experiment",
        "n_features_mean",
        "mae_mean",
        "mae_std",
        "rmse_mean",
        "r2_mean",
        "delta_mae_vs_baseline",
        "delta_mae_vs_full_model",
    ]

    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Feature Ablation Report\n\n")
        f.write("## Feature Group Sizes\n")
        f.write(group_sizes.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Experiment Ranking by Mean MAE\n")
        f.write(summary[ranking_cols].sort_values("mae_mean").to_markdown(index=False))
        f.write("\n\n")

        f.write("## Fold-Level Results\n")
        f.write(
            fold_results[
                ["experiment", "fold", "start_date", "end_date", "n_features", "mae", "rmse", "r2"]
            ].to_markdown(index=False)
        )
        f.write("\n")


def main() -> None:
    print("Loading feature store...")
    df = load_training_frame()

    print("Building ablation groups...")
    groups, experiments = build_experiments(df)

    all_results: list[dict[str, object]] = []
    for name, features in experiments.items():
        print(f"Running {name} with {len(features)} features...")
        all_results.extend(evaluate_experiment(df, name, features))

    fold_results = pd.DataFrame(all_results)
    fold_results.to_csv(OUT_DIR / "ablation_fold_results.csv", index=False)

    summary = (
        fold_results.groupby("experiment")
        .agg(
            n_features_mean=("n_features", "mean"),
            mae_mean=("mae", "mean"),
            mae_std=("mae", "std"),
            rmse_mean=("rmse", "mean"),
            rmse_std=("rmse", "std"),
            r2_mean=("r2", "mean"),
            r2_std=("r2", "std"),
        )
        .reset_index()
    )

    baseline_mae = float(
        summary.loc[summary["experiment"] == "baseline_calendar_revenue_history", "mae_mean"].iloc[0]
    )
    full_model_mae = float(summary.loc[summary["experiment"] == "full_model", "mae_mean"].iloc[0])
    summary["delta_mae_vs_baseline"] = summary["mae_mean"] - baseline_mae
    summary["delta_mae_vs_full_model"] = summary["mae_mean"] - full_model_mae
    summary = summary.sort_values("mae_mean").reset_index(drop=True)
    summary.to_csv(OUT_DIR / "ablation_summary.csv", index=False)

    make_markdown_report(groups, fold_results, summary)
    print(f"Saved fold results to {OUT_DIR / 'ablation_fold_results.csv'}")
    print(f"Saved summary to {OUT_DIR / 'ablation_summary.csv'}")
    print(f"Saved report to {OUT_DIR / 'ablation_report.md'}")


if __name__ == "__main__":
    main()
