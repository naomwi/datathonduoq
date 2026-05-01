from __future__ import annotations

import hashlib
import json
import os
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from logging_utils import create_run_dir, setup_logger, write_json
from train_recursive_forecast import (
    TRAIN_END,
    apply_future_promo_policy,
    ensure_inputs,
    get_candidate_feature_sets,
    recursive_forecast,
)


RUN_PREFIX = "five_hour_sweep"
BACKTEST_FOLDS = [
    ("2020-01-01", "2020-12-31"),
    ("2021-01-01", "2021-12-31"),
    ("2022-01-01", "2022-12-31"),
]
LONG_HORIZON_FOLDS = [
    ("2018-01-01", "2019-07-02"),
    ("2019-01-01", "2020-07-01"),
    ("2020-01-01", "2021-07-01"),
    ("2021-01-01", "2022-07-02"),
]
PRIMARY_REVENUE_EXPERIMENTS = ["curated_promo_cogs", "baseline_plus_promo"]
STAGE1_POLICIES = [
    "zero",
    "seasonal_month_day_recent_1y",
    "seasonal_month_day_recent_2y",
    "seasonal_month_day_recent_3y",
    "seasonal_month_weekday_recent_2y",
]
STAGE1_COGS_VARIANT = "blend60_clip_q99"
STAGE1_TOP_K = 8
LONG_HORIZON_TOP_K = 10
BLEND_WEIGHTS = [0.25, 0.5, 0.75]
NEW_PROMO_RAW_STEMS = [
    "active_promo_stackable_share",
    "active_promo_min_order_value_mean",
    "active_promo_type_",
    "active_promo_channel_",
    "active_promo_category_",
    "active_promo_discount_value_percentage_mean",
    "active_promo_discount_value_fixed_mean",
]
NEW_PROMO_TE_STEMS = [
    "promo_type_revenue_te",
    "promo_channel_revenue_te",
    "promo_category_revenue_te",
    "promo_type_cogs_ratio_te",
    "promo_channel_cogs_ratio_te",
    "promo_category_cogs_ratio_te",
]


def _rmse(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def _stem_matches(column: str, stem: str) -> bool:
    if stem.endswith("_"):
        return column.startswith(stem)
    return column == stem or column.startswith(f"{stem}_")


def _filter_features(features: list[str], branch_name: str) -> list[str]:
    raw_stems = NEW_PROMO_RAW_STEMS
    te_stems = NEW_PROMO_TE_STEMS
    exclude_stems: list[str] = []

    if branch_name == "legacy":
        exclude_stems = raw_stems + te_stems
    elif branch_name == "raw_only":
        exclude_stems = te_stems
    elif branch_name == "te_only":
        exclude_stems = raw_stems
    elif branch_name == "full":
        exclude_stems = []
    else:
        raise ValueError(f"Unknown feature branch: {branch_name}")

    return [feature for feature in features if not any(_stem_matches(feature, stem) for stem in exclude_stems)]


def build_branch_feature_sets(feature_sets: dict[str, list[str]]) -> dict[str, dict[str, list[str]]]:
    branch_feature_sets: dict[str, dict[str, list[str]]] = {}
    for branch_name in ["legacy", "raw_only", "te_only", "full"]:
        branch_feature_sets[branch_name] = {
            name: _filter_features(features, branch_name) for name, features in feature_sets.items()
        }
    return branch_feature_sets


def make_config_id(stage: str, payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return f"{stage}_{hashlib.md5(encoded).hexdigest()[:10]}"


def build_stage1_configs(branch_feature_sets: dict[str, dict[str, list[str]]]) -> list[dict[str, object]]:
    configs: list[dict[str, object]] = []
    for branch_name, feature_sets in branch_feature_sets.items():
        for revenue_experiment in PRIMARY_REVENUE_EXPERIMENTS:
            if revenue_experiment not in feature_sets:
                continue
            for promo_future_policy in STAGE1_POLICIES:
                payload = {
                    "branch": branch_name,
                    "revenue_experiment": revenue_experiment,
                    "secondary_revenue_experiment": None,
                    "revenue_regime_variant": "none",
                    "promo_future_policy": promo_future_policy,
                    "cogs_postprocess_variant": STAGE1_COGS_VARIANT,
                }
                configs.append(
                    {
                        "config_id": make_config_id("s1", payload),
                        **payload,
                    }
                )
    return configs


def build_stage2_configs(stage1_summary: pd.DataFrame) -> list[dict[str, object]]:
    top_stage1 = stage1_summary.sort_values("revenue_mae_mean").head(STAGE1_TOP_K)
    configs: list[dict[str, object]] = []

    for row in top_stage1.to_dict("records"):
        base_payload = {
            "branch": row["branch"],
            "revenue_experiment": row["revenue_experiment"],
            "promo_future_policy": row["promo_future_policy"],
        }

        for cogs_variant in ["raw", "blend40_clip_q99", "blend60_clip_q99", "blend60_clip_q995", "blend80_clip_q99"]:
            payload = {
                **base_payload,
                "secondary_revenue_experiment": None,
                "revenue_regime_variant": "none",
                "cogs_postprocess_variant": cogs_variant,
            }
            configs.append({"config_id": make_config_id("s2", payload), **payload})

        alternate_revenue = (
            "baseline_plus_promo"
            if row["revenue_experiment"] == "curated_promo_cogs"
            else "curated_promo_cogs"
        )
        for regime_variant in [
            "promo_heavy_switch_loose",
            "promo_heavy_switch",
            "promo_heavy_switch_strict",
        ]:
            payload = {
                **base_payload,
                "secondary_revenue_experiment": alternate_revenue,
                "revenue_regime_variant": regime_variant,
                "cogs_postprocess_variant": "blend60_clip_q99",
            }
            configs.append({"config_id": make_config_id("s2", payload), **payload})

    deduped = {config["config_id"]: config for config in configs}
    return list(deduped.values())


def evaluate_configs(
    configs: list[dict[str, object]],
    folds: list[tuple[str, str]],
    fold_set_name: str,
    feature_store: pd.DataFrame,
    base: pd.DataFrame,
    branch_feature_sets: dict[str, dict[str, list[str]]],
    logger,
    daily_output_dir: Path | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for idx, config in enumerate(configs, start=1):
        logger.info("[%s %s/%s] Running %s", fold_set_name, idx, len(configs), config["config_id"])
        feature_sets = branch_feature_sets[str(config["branch"])]
        revenue_features = feature_sets[str(config["revenue_experiment"])]
        secondary_revenue_features = (
            feature_sets[str(config["secondary_revenue_experiment"])]
            if config["secondary_revenue_experiment"]
            else None
        )
        cogs_features = feature_sets["curated_promo_cogs"]

        for fold_id, (start_date, end_date) in enumerate(folds, start=1):
            start_ts = pd.Timestamp(start_date)
            end_ts = pd.Timestamp(end_date)
            cutoff = start_ts - pd.Timedelta(days=1)

            adjusted_base = apply_future_promo_policy(base, cutoff, str(config["promo_future_policy"]))
            preds = recursive_forecast(
                feature_store=feature_store,
                full_base=adjusted_base,
                train_end_date=cutoff,
                forecast_start=start_ts,
                forecast_end=end_ts,
                revenue_features=revenue_features,
                cogs_features=cogs_features,
                cogs_postprocess_variant=str(config["cogs_postprocess_variant"]),
                secondary_revenue_features=secondary_revenue_features,
                revenue_regime_variant=str(config["revenue_regime_variant"]),
            )

            truth = feature_store.loc[
                (feature_store["Date"] >= start_ts) & (feature_store["Date"] <= end_ts),
                ["Date", "Revenue", "COGS"],
            ].copy()
            merged = truth.merge(preds, on="Date", how="left").sort_values("Date").reset_index(drop=True)
            merged["horizon_day"] = np.arange(1, len(merged) + 1)

            rows.append(
                {
                    "config_id": config["config_id"],
                    "fold_set": fold_set_name,
                    "fold": fold_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "branch": config["branch"],
                    "revenue_experiment": config["revenue_experiment"],
                    "secondary_revenue_experiment": config["secondary_revenue_experiment"],
                    "revenue_regime_variant": config["revenue_regime_variant"],
                    "promo_future_policy": config["promo_future_policy"],
                    "cogs_postprocess_variant": config["cogs_postprocess_variant"],
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

            if daily_output_dir is not None:
                config_dir = daily_output_dir / str(config["config_id"])
                config_dir.mkdir(parents=True, exist_ok=True)
                merged.to_csv(config_dir / f"fold_{fold_id}.csv", index=False)

    return pd.DataFrame(rows)


def summarize_results(results_df: pd.DataFrame) -> pd.DataFrame:
    return (
        results_df.groupby("config_id")
        .agg(
            fold_set=("fold_set", "first"),
            branch=("branch", "first"),
            revenue_experiment=("revenue_experiment", "first"),
            secondary_revenue_experiment=("secondary_revenue_experiment", "first"),
            revenue_regime_variant=("revenue_regime_variant", "first"),
            promo_future_policy=("promo_future_policy", "first"),
            cogs_postprocess_variant=("cogs_postprocess_variant", "first"),
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


def evaluate_blends(
    long_summary_df: pd.DataFrame,
    daily_output_dir: Path,
) -> pd.DataFrame:
    top_configs = long_summary_df.head(4)["config_id"].tolist()
    rows: list[dict[str, object]] = []

    for left_id, right_id in combinations(top_configs, 2):
        for left_weight in BLEND_WEIGHTS:
            blend_id = f"blend_{left_id}_{right_id}_{int(left_weight * 100):02d}"
            fold_rows: list[dict[str, object]] = []
            for fold_id in range(1, len(LONG_HORIZON_FOLDS) + 1):
                left = pd.read_csv(daily_output_dir / left_id / f"fold_{fold_id}.csv", parse_dates=["Date"])
                right = pd.read_csv(daily_output_dir / right_id / f"fold_{fold_id}.csv", parse_dates=["Date"])
                merged = left[["Date", "Revenue", "COGS", "Revenue_pred", "COGS_pred"]].merge(
                    right[["Date", "Revenue_pred", "COGS_pred"]],
                    on="Date",
                    suffixes=("_left", "_right"),
                )
                revenue_pred = left_weight * merged["Revenue_pred_left"] + (1.0 - left_weight) * merged["Revenue_pred_right"]
                cogs_pred = left_weight * merged["COGS_pred_left"] + (1.0 - left_weight) * merged["COGS_pred_right"]
                fold_rows.append(
                    {
                        "blend_id": blend_id,
                        "left_id": left_id,
                        "right_id": right_id,
                        "left_weight": left_weight,
                        "fold": fold_id,
                        "revenue_mae": mean_absolute_error(merged["Revenue"], revenue_pred),
                        "cogs_mae": mean_absolute_error(merged["COGS"], cogs_pred),
                        "combined_mae": mean_absolute_error(merged["Revenue"], revenue_pred)
                        + mean_absolute_error(merged["COGS"], cogs_pred),
                    }
                )
            fold_df = pd.DataFrame(fold_rows)
            rows.append(
                {
                    "blend_id": blend_id,
                    "left_id": left_id,
                    "right_id": right_id,
                    "left_weight": left_weight,
                    "revenue_mae_mean": fold_df["revenue_mae"].mean(),
                    "revenue_mae_worst": fold_df["revenue_mae"].max(),
                    "cogs_mae_mean": fold_df["cogs_mae"].mean(),
                    "combined_mae_mean": fold_df["combined_mae"].mean(),
                }
            )

    return pd.DataFrame(rows).sort_values(["revenue_mae_mean", "revenue_mae_worst"]).reset_index(drop=True)


def export_submission_for_config(
    config: dict[str, object],
    feature_store: pd.DataFrame,
    base: pd.DataFrame,
    branch_feature_sets: dict[str, dict[str, list[str]]],
    output_path: Path,
) -> None:
    feature_sets = branch_feature_sets[str(config["branch"])]
    revenue_features = feature_sets[str(config["revenue_experiment"])]
    secondary_revenue_features = (
        feature_sets[str(config["secondary_revenue_experiment"])]
        if config["secondary_revenue_experiment"]
        else None
    )
    adjusted_base = apply_future_promo_policy(base, TRAIN_END, str(config["promo_future_policy"]))
    preds = recursive_forecast(
        feature_store=feature_store,
        full_base=adjusted_base,
        train_end_date=TRAIN_END,
        forecast_start=pd.Timestamp("2023-01-01"),
        forecast_end=pd.Timestamp("2024-07-01"),
        revenue_features=revenue_features,
        cogs_features=feature_sets["curated_promo_cogs"],
        cogs_postprocess_variant=str(config["cogs_postprocess_variant"]),
        secondary_revenue_features=secondary_revenue_features,
        revenue_regime_variant=str(config["revenue_regime_variant"]),
    )
    submission = preds.rename(columns={"Revenue_pred": "Revenue", "COGS_pred": "COGS"})[["Date", "Revenue", "COGS"]]
    submission["Date"] = pd.to_datetime(submission["Date"]).dt.strftime("%Y-%m-%d")
    submission.to_csv(output_path, index=False)


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting five-hour style search sweep in %s", run_dir)

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    branch_feature_sets = build_branch_feature_sets(feature_sets)
    write_json(
        run_dir / "config.json",
        {
            "branches": list(branch_feature_sets.keys()),
            "stage1_policies": STAGE1_POLICIES,
            "primary_revenue_experiments": PRIMARY_REVENUE_EXPERIMENTS,
            "stage1_top_k": STAGE1_TOP_K,
            "long_horizon_top_k": LONG_HORIZON_TOP_K,
            "blend_weights": BLEND_WEIGHTS,
        },
    )

    stage1_configs = build_stage1_configs(branch_feature_sets)
    stage1_limit = int(os.environ.get("SWEEP_STAGE1_LIMIT", "0") or 0)
    if stage1_limit > 0:
        stage1_configs = stage1_configs[:stage1_limit]
    pd.DataFrame(stage1_configs).to_csv(run_dir / "stage1_manifest.csv", index=False)
    stage1_fold_df = evaluate_configs(
        stage1_configs,
        BACKTEST_FOLDS,
        "stage1_backtest",
        feature_store,
        base,
        branch_feature_sets,
        logger,
    )
    stage1_fold_df.to_csv(run_dir / "stage1_fold_results.csv", index=False)
    stage1_summary_df = summarize_results(stage1_fold_df)
    stage1_summary_df.to_csv(run_dir / "stage1_summary.csv", index=False)
    logger.info("Best stage-1 config: %s", stage1_summary_df.iloc[0]["config_id"])

    stage2_configs = build_stage2_configs(stage1_summary_df)
    stage2_limit = int(os.environ.get("SWEEP_STAGE2_LIMIT", "0") or 0)
    if stage2_limit > 0:
        stage2_configs = stage2_configs[:stage2_limit]
    pd.DataFrame(stage2_configs).to_csv(run_dir / "stage2_manifest.csv", index=False)
    stage2_fold_df = evaluate_configs(
        stage2_configs,
        BACKTEST_FOLDS,
        "stage2_backtest",
        feature_store,
        base,
        branch_feature_sets,
        logger,
    )
    stage2_fold_df.to_csv(run_dir / "stage2_fold_results.csv", index=False)
    stage2_summary_df = summarize_results(stage2_fold_df)
    stage2_summary_df.to_csv(run_dir / "stage2_summary.csv", index=False)
    logger.info("Best stage-2 config: %s", stage2_summary_df.iloc[0]["config_id"])

    combined_backtest_summary = (
        pd.concat([stage1_summary_df, stage2_summary_df], ignore_index=True)
        .sort_values(["revenue_mae_mean", "revenue_mae_worst"])
        .drop_duplicates(subset=["config_id"])
        .reset_index(drop=True)
    )
    combined_backtest_summary.to_csv(run_dir / "combined_backtest_summary.csv", index=False)

    top_long_configs = combined_backtest_summary.head(LONG_HORIZON_TOP_K)["config_id"].tolist()
    long_limit = int(os.environ.get("SWEEP_LONG_LIMIT", "0") or 0)
    if long_limit > 0:
        top_long_configs = top_long_configs[:long_limit]
    config_lookup = {config["config_id"]: config for config in stage1_configs + stage2_configs}
    long_configs = [config_lookup[config_id] for config_id in top_long_configs]
    long_daily_dir = run_dir / "long_horizon_daily"
    long_fold_df = evaluate_configs(
        long_configs,
        LONG_HORIZON_FOLDS,
        "long_horizon",
        feature_store,
        base,
        branch_feature_sets,
        logger,
        daily_output_dir=long_daily_dir,
    )
    long_fold_df.to_csv(run_dir / "long_horizon_fold_results.csv", index=False)
    long_summary_df = summarize_results(long_fold_df)
    long_summary_df.to_csv(run_dir / "long_horizon_summary.csv", index=False)
    logger.info("Best long-horizon config: %s", long_summary_df.iloc[0]["config_id"])

    blend_summary_df = evaluate_blends(long_summary_df, long_daily_dir)
    blend_summary_df.to_csv(run_dir / "long_horizon_blend_summary.csv", index=False)
    if not blend_summary_df.empty:
        logger.info("Best long-horizon blend: %s", blend_summary_df.iloc[0]["blend_id"])

    best_config_id = str(long_summary_df.iloc[0]["config_id"])
    export_submission_for_config(
        config_lookup[best_config_id],
        feature_store,
        base,
        branch_feature_sets,
        run_dir / f"submission_{best_config_id}.csv",
    )
    logger.info("Exported submission for best single config to %s", run_dir / f"submission_{best_config_id}.csv")


if __name__ == "__main__":
    main()
