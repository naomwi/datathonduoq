from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from feature_pipeline import CALENDAR_COLUMNS, add_calendar_features
from logging_utils import create_run_dir, setup_logger, write_json
from run_bottomup_sprint import (
    _load_order_details,
    blend_predictions as blend_bottomup_predictions,
    build_group_panel as build_bottomup_panel,
    evaluate_variant as evaluate_bottomup_variant,
)
from run_leaderboard_sprint import CANDIDATES, FORECAST_END, FORECAST_START, SPRINT_FOLDS
from train_recursive_forecast import (
    TRAIN_END,
    apply_future_context_policy,
    apply_future_hierarchy_policy,
    apply_future_price_policy,
    apply_future_promo_policy,
    ensure_inputs,
    get_candidate_feature_sets,
    recursive_forecast,
)


RUN_PREFIX = "public_revenue_router_v1"
DATASET_DIR = Path("dataset")

PUBLIC_ANCHOR_PATH = DATASET_DIR / "submission_blend_catboost_core_lightgbm_context_rev70_cogs100.csv"
PUBLIC_REVSWITCH_PATH = DATASET_DIR / "submission_blend_md2y_revswitch_60_40.csv"
PUBLIC_BOTTOMUP_CATEGORY_PATH = DATASET_DIR / "submission_bottomup_category.csv"
PUBLIC_BOTTOMUP_CATSEG_PATH = DATASET_DIR / "submission_bottomup_category_segment_blend50.csv"

PROMO_POLICY = "seasonal_month_day_recent_2y"
CONTEXT_POLICY = "seasonal_month_day_recent_2y"
CLAMP_EPSILON = 0.005
SWITCH_PROXY_WEIGHT = 0.40
ROUTER_FOLD_WEIGHT_MAP = {1: 1.0, 2: 1.5, 3: 2.0}

ROUTER_VARIANTS = [
    {
        "candidate_id": "public_revenue_router_v1_clip",
        "priority": 1,
        "clamp_expansion": 0.00,
        "thesis": "residual router clipped to the convex hull of structural donors.",
    },
    {
        "candidate_id": "public_revenue_router_v1_relax05",
        "priority": 2,
        "clamp_expansion": 0.05,
        "thesis": "residual router with a small 5% hull expansion for higher upside.",
    },
]

ROUTER_MODEL_PARAMS = {
    "loss_function": "RMSE",
    "iterations": 700,
    "learning_rate": 0.03,
    "depth": 4,
    "l2_leaf_reg": 10.0,
    "subsample": 0.8,
    "random_seed": 42,
    "verbose": False,
    "allow_writing_files": False,
}

ROUTER_BASE_FEATURE_COLUMNS = [
    "active_promo_count",
    "active_stackable_promo_count",
    "active_promo_discount_value_mean",
    "total_discount",
    "avg_discount_rate",
    "promo_line_share",
    "promo_2_share",
    "active_promo_stackable_share",
    "active_promo_min_order_value_mean",
    "active_promo_type_percentage_count",
    "active_promo_type_fixed_count",
    "active_promo_type_percentage_share",
    "active_promo_type_fixed_share",
    "active_promo_channel_all_channels_count",
    "active_promo_channel_email_count",
    "active_promo_channel_online_count",
    "active_promo_channel_social_media_count",
    "active_promo_channel_in_store_count",
    "active_promo_channel_all_channels_share",
    "active_promo_channel_email_share",
    "active_promo_channel_online_share",
    "active_promo_channel_social_media_share",
    "active_promo_channel_in_store_share",
    "active_promo_category_global_count",
    "active_promo_category_outdoor_count",
    "active_promo_category_streetwear_count",
    "active_promo_category_global_share",
    "active_promo_category_outdoor_share",
    "active_promo_category_streetwear_share",
    "active_promo_discount_value_percentage_mean",
    "active_promo_discount_value_fixed_mean",
    "promo_type_revenue_te",
    "promo_channel_revenue_te",
    "promo_category_revenue_te",
    "new_customers",
    "shipping_fee_total",
    "shipping_fee_mean",
    "shipping_fee_per_order",
    "shipment_order_share",
    "order_to_ship_days_mean",
    "ship_to_delivery_days_mean",
    "fast_delivery_share",
    "slow_delivery_share",
    "signup_channel_share_direct",
    "signup_channel_share_email_campaign",
    "signup_channel_share_organic_search",
    "signup_channel_share_paid_search",
    "signup_channel_share_referral",
    "signup_channel_share_social_media",
    "order_region_share_central",
    "order_region_share_east",
    "order_region_share_west",
]


def _rmse(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def load_submission(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["Date"])
    return df.sort_values("Date").reset_index(drop=True)


def candidate_by_id(candidate_id: str) -> dict[str, object]:
    for candidate in CANDIDATES:
        if str(candidate["candidate_id"]) == candidate_id:
            return dict(candidate)
    raise KeyError(candidate_id)


def predict_candidate(
    candidate: dict[str, object],
    feature_store: pd.DataFrame,
    base: pd.DataFrame,
    feature_sets: dict[str, list[str]],
    forecast_start: pd.Timestamp,
    forecast_end: pd.Timestamp,
    cutoff_date: pd.Timestamp,
) -> pd.DataFrame:
    adjusted_base = apply_future_promo_policy(base, cutoff_date, str(candidate["promo_future_policy"]))
    adjusted_base = apply_future_context_policy(adjusted_base, cutoff_date, str(candidate["context_future_policy"]))
    adjusted_base = apply_future_price_policy(
        adjusted_base,
        cutoff_date,
        str(candidate.get("price_future_policy", "zero")),
    )
    adjusted_base = apply_future_hierarchy_policy(
        adjusted_base,
        cutoff_date,
        str(candidate.get("hierarchy_future_policy", "zero")),
    )
    return recursive_forecast(
        feature_store=feature_store,
        full_base=adjusted_base,
        train_end_date=cutoff_date,
        forecast_start=forecast_start,
        forecast_end=forecast_end,
        revenue_features=feature_sets[str(candidate["revenue_experiment"])],
        cogs_features=feature_sets[str(candidate["cogs_experiment"])],
        cogs_postprocess_variant=str(candidate["cogs_postprocess_variant"]),
        secondary_revenue_features=(
            feature_sets[str(candidate["secondary_revenue_experiment"])]
            if candidate.get("secondary_revenue_experiment")
            else None
        ),
        revenue_regime_variant=str(candidate.get("revenue_regime_variant", "none")),
        model_family=str(candidate["model_family"]),
        train_window_days=candidate.get("train_window_days"),
        model_params_override=candidate.get("model_params_override"),
        revenue_target_transform=str(candidate.get("revenue_target_transform", "none")),
        cogs_target_transform=str(candidate.get("cogs_target_transform", "none")),
        cogs_target_mode=str(candidate.get("cogs_target_mode", "direct")),
        sample_weight_mode=str(candidate.get("sample_weight_mode", "none")),
        sample_weight_decay=float(candidate.get("sample_weight_decay", 0.0)),
    ).sort_values("Date").reset_index(drop=True)


def build_router_feature_base(base: pd.DataFrame, cutoff_date: pd.Timestamp) -> pd.DataFrame:
    adjusted = apply_future_promo_policy(base, cutoff_date, PROMO_POLICY)
    adjusted = apply_future_context_policy(adjusted, cutoff_date, CONTEXT_POLICY)
    selected = [col for col in ROUTER_BASE_FEATURE_COLUMNS if col in adjusted.columns]
    feature_base = add_calendar_features(adjusted[["Date"] + selected].copy())
    return feature_base[["Date"] + [col for col in selected if col != "Date"] + [col for col in CALENDAR_COLUMNS if col in feature_base.columns]]


def zscore_align(anchor_series: pd.Series, donor_series: pd.Series) -> pd.Series:
    donor_std = float(donor_series.std())
    if donor_std <= 1e-12:
        aligned = pd.Series(float(anchor_series.mean()), index=donor_series.index, dtype=float)
    else:
        aligned = (
            (donor_series.astype(float) - float(donor_series.mean()))
            * (float(anchor_series.std()) / donor_std)
            + float(anchor_series.mean())
        )
    return aligned.clip(lower=0.0)


def blend_series(primary: pd.Series, secondary: pd.Series, primary_weight: float) -> pd.Series:
    return primary_weight * primary + (1.0 - primary_weight) * secondary


def build_daily_router_frame(
    *,
    truth_df: pd.DataFrame | None,
    feature_base: pd.DataFrame,
    anchor_df: pd.DataFrame,
    revswitch_df: pd.DataFrame,
    bottomup_category_df: pd.DataFrame,
    bottomup_catseg_df: pd.DataFrame,
    cogs_anchor_df: pd.DataFrame,
    fold_id: int | None,
    split_name: str,
) -> pd.DataFrame:
    merged = anchor_df[["Date", "Revenue_pred"]].rename(columns={"Revenue_pred": "anchor_rev70"})
    merged = merged.merge(revswitch_df[["Date", "Revenue_pred"]].rename(columns={"Revenue_pred": "revswitch_public_proxy"}), on="Date", how="left")
    merged = merged.merge(
        bottomup_category_df[["Date", "Revenue_pred"]].rename(columns={"Revenue_pred": "bottomup_category_raw"}),
        on="Date",
        how="left",
    )
    merged = merged.merge(
        bottomup_catseg_df[["Date", "Revenue_pred"]].rename(columns={"Revenue_pred": "bottomup_catseg_raw"}),
        on="Date",
        how="left",
    )
    merged = merged.merge(
        cogs_anchor_df[["Date", "COGS_pred"]].rename(columns={"COGS_pred": "cogs_anchor"}),
        on="Date",
        how="left",
    )
    merged = merged.merge(feature_base, on="Date", how="left")

    merged["revswitch_aligned"] = zscore_align(merged["anchor_rev70"], merged["revswitch_public_proxy"])
    merged["bottomup_category_aligned"] = zscore_align(merged["anchor_rev70"], merged["bottomup_category_raw"])
    merged["bottomup_catseg_aligned"] = zscore_align(merged["anchor_rev70"], merged["bottomup_catseg_raw"])

    donor_cols = [
        "anchor_rev70",
        "revswitch_aligned",
        "bottomup_category_aligned",
        "bottomup_catseg_aligned",
    ]
    merged["revswitch_delta"] = merged["revswitch_aligned"] - merged["anchor_rev70"]
    merged["bottomup_category_delta"] = merged["bottomup_category_aligned"] - merged["anchor_rev70"]
    merged["bottomup_catseg_delta"] = merged["bottomup_catseg_aligned"] - merged["anchor_rev70"]
    merged["revswitch_z20"] = blend_series(merged["anchor_rev70"], merged["revswitch_aligned"], primary_weight=0.8)
    merged["donor_mean"] = merged[donor_cols].mean(axis=1)
    merged["donor_std"] = merged[donor_cols].std(axis=1)
    merged["donor_min"] = merged[donor_cols].min(axis=1)
    merged["donor_max"] = merged[donor_cols].max(axis=1)
    merged["donor_span"] = merged["donor_max"] - merged["donor_min"]
    merged["donor_anchor_rank"] = (
        merged[donor_cols].rank(axis=1, method="average").loc[:, "anchor_rev70"].astype(float)
    )

    if truth_df is not None:
        merged = merged.merge(truth_df.rename(columns={"Revenue": "Revenue_true", "COGS": "COGS_true"}), on="Date", how="left")
        merged["target_residual"] = merged["Revenue_true"] - merged["anchor_rev70"]
        merged["fold"] = int(fold_id) if fold_id is not None else np.nan
        merged["sample_weight"] = float(ROUTER_FOLD_WEIGHT_MAP.get(int(fold_id), 1.0)) if fold_id is not None else 1.0
    else:
        merged["fold"] = int(fold_id) if fold_id is not None else np.nan
        merged["sample_weight"] = 1.0

    merged["split_name"] = split_name
    return merged.sort_values("Date").reset_index(drop=True)


def apply_router_variant(frame: pd.DataFrame, residual_pred: np.ndarray, clamp_expansion: float) -> pd.Series:
    raw_pred = frame["anchor_rev70"] + residual_pred
    lower = (frame["donor_min"] * (1.0 - clamp_expansion)).clip(lower=0.0)
    upper = frame["donor_max"] * (1.0 + clamp_expansion)
    return raw_pred.clip(lower=lower, upper=upper)


def build_summary(metrics_df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        metrics_df.groupby("candidate_id", as_index=False)
        .agg(
            revenue_mae_mean=("revenue_mae", "mean"),
            revenue_rmse_mean=("revenue_rmse", "mean"),
            revenue_r2_mean=("revenue_r2", "mean"),
            cogs_mae_mean=("cogs_mae", "mean"),
            cogs_rmse_mean=("cogs_rmse", "mean"),
            cogs_r2_mean=("cogs_r2", "mean"),
            combined_mae_mean=("combined_mae", "mean"),
        )
        .sort_values(["combined_mae_mean", "revenue_mae_mean"])
        .reset_index(drop=True)
    )
    return summary


def invalid_row_count(df: pd.DataFrame) -> int:
    invalid = (
        (df["Revenue"] < 0.0)
        | (df["COGS"] < 0.0)
        | (df["COGS"] > df["Revenue"] * (1.0 - CLAMP_EPSILON))
    )
    return int(invalid.sum())


def write_report(
    run_dir: Path,
    summary_df: pd.DataFrame,
    fold_metrics_df: pd.DataFrame,
    final_manifest_df: pd.DataFrame,
    feature_importance_df: pd.DataFrame,
) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Public Revenue Router V1\n\n")
        f.write("## Framing\n")
        f.write("- Objective: large structural move on Revenue without touching the current best public COGS path.\n")
        f.write("- Revenue anchor proxy offline: `0.70 * catboost_md2y_core + 0.30 * lightgbm_md2y_context`.\n")
        f.write("- Revenue donors: revenue-switch proxy, bottom-up category, bottom-up category/segment blend.\n")
        f.write("- Structural donors are z-score aligned to the anchor distribution before routing.\n")
        f.write("- Router target is residual over the anchor, not raw Revenue.\n")
        f.write("- Final submission freezes COGS from `submission_blend_catboost_core_lightgbm_context_rev70_cogs100.csv`.\n\n")
        f.write("## OOF Ranking\n")
        f.write(summary_df.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Fold Metrics\n")
        f.write(fold_metrics_df.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Final Manifest\n")
        f.write(final_manifest_df.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Final Router Feature Importance\n")
        f.write(feature_importance_df.head(20).to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting public revenue router v1 in %s", run_dir)

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))

    candidate_catboost = candidate_by_id("catboost_md2y_core")
    candidate_lgbm_context = candidate_by_id("lightgbm_md2y_context")
    candidate_switch = {
        "candidate_id": "catboost_md2y_revenue_switch_proxy",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs",
        "secondary_revenue_experiment": "baseline_plus_promo",
        "revenue_regime_variant": "promo_heavy_switch",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": PROMO_POLICY,
        "context_future_policy": "zero",
        "price_future_policy": "zero",
        "hierarchy_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
    }

    logger.info("Preparing bottom-up donor predictions")
    order_details = _load_order_details()
    category_panel = build_bottomup_panel(order_details, base, group_col="category")
    segment_panel = build_bottomup_panel(order_details, base, group_col="segment")
    _, bottomup_category_folds, _ = evaluate_bottomup_variant("bottomup_category", category_panel, base)
    _, bottomup_segment_folds, _ = evaluate_bottomup_variant("bottomup_segment", segment_panel, base)

    router_frames: list[pd.DataFrame] = []
    baseline_fold_rows: list[dict[str, object]] = []

    for fold_id, (start_date, end_date) in enumerate(SPRINT_FOLDS, start=1):
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        cutoff = start_ts - pd.Timedelta(days=1)
        logger.info("Generating fold donors for fold %s (%s to %s)", fold_id, start_date, end_date)

        catboost_preds = predict_candidate(candidate_catboost, feature_store, base, feature_sets, start_ts, end_ts, cutoff)
        lgbm_context_preds = predict_candidate(candidate_lgbm_context, feature_store, base, feature_sets, start_ts, end_ts, cutoff)
        switch_preds = predict_candidate(candidate_switch, feature_store, base, feature_sets, start_ts, end_ts, cutoff)
        bottomup_category_preds = bottomup_category_folds[fold_id].drop(columns=["fold"]).copy()
        bottomup_catseg_preds = blend_bottomup_predictions(
            bottomup_category_folds[fold_id].drop(columns=["fold"]).copy(),
            bottomup_segment_folds[fold_id].drop(columns=["fold"]).copy(),
            weight_a=0.5,
        )

        anchor_preds = pd.DataFrame(
            {
                "Date": catboost_preds["Date"],
                "Revenue_pred": 0.7 * catboost_preds["Revenue_pred"] + 0.3 * lgbm_context_preds["Revenue_pred"],
                "COGS_pred": catboost_preds["COGS_pred"],
            }
        )
        revswitch_proxy_preds = pd.DataFrame(
            {
                "Date": anchor_preds["Date"],
                "Revenue_pred": 0.6 * anchor_preds["Revenue_pred"] + SWITCH_PROXY_WEIGHT * switch_preds["Revenue_pred"],
            }
        )

        truth_df = base.loc[
            (base["Date"] >= start_ts) & (base["Date"] <= end_ts),
            ["Date", "Revenue", "COGS"],
        ].copy()
        feature_base = build_router_feature_base(base, cutoff)
        feature_base = feature_base.loc[(feature_base["Date"] >= start_ts) & (feature_base["Date"] <= end_ts)].copy()

        fold_frame = build_daily_router_frame(
            truth_df=truth_df,
            feature_base=feature_base,
            anchor_df=anchor_preds,
            revswitch_df=revswitch_proxy_preds,
            bottomup_category_df=bottomup_category_preds,
            bottomup_catseg_df=bottomup_catseg_preds,
            cogs_anchor_df=catboost_preds,
            fold_id=fold_id,
            split_name="oof",
        )
        router_frames.append(fold_frame)

        anchor_merged = truth_df.merge(anchor_preds, on="Date", how="left")
        revswitch_structural = fold_frame[["Date", "revswitch_z20"]].rename(columns={"revswitch_z20": "Revenue_pred"})
        revswitch_structural["COGS_pred"] = fold_frame["cogs_anchor"].to_numpy()
        revswitch_merged = truth_df.merge(revswitch_structural, on="Date", how="left")

        baseline_fold_rows.extend(
            [
                {
                    "candidate_id": "anchor_rev70_cogs100_proxy",
                    "fold": fold_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "revenue_mae": mean_absolute_error(anchor_merged["Revenue"], anchor_merged["Revenue_pred"]),
                    "revenue_rmse": _rmse(anchor_merged["Revenue"], anchor_merged["Revenue_pred"]),
                    "revenue_r2": r2_score(anchor_merged["Revenue"], anchor_merged["Revenue_pred"]),
                    "cogs_mae": mean_absolute_error(anchor_merged["COGS"], anchor_merged["COGS_pred"]),
                    "cogs_rmse": _rmse(anchor_merged["COGS"], anchor_merged["COGS_pred"]),
                    "cogs_r2": r2_score(anchor_merged["COGS"], anchor_merged["COGS_pred"]),
                    "combined_mae": 0.5
                    * (
                        mean_absolute_error(anchor_merged["Revenue"], anchor_merged["Revenue_pred"])
                        + mean_absolute_error(anchor_merged["COGS"], anchor_merged["COGS_pred"])
                    ),
                },
                {
                    "candidate_id": "structural_revswitch_z20_proxy",
                    "fold": fold_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "revenue_mae": mean_absolute_error(revswitch_merged["Revenue"], revswitch_merged["Revenue_pred"]),
                    "revenue_rmse": _rmse(revswitch_merged["Revenue"], revswitch_merged["Revenue_pred"]),
                    "revenue_r2": r2_score(revswitch_merged["Revenue"], revswitch_merged["Revenue_pred"]),
                    "cogs_mae": mean_absolute_error(revswitch_merged["COGS"], revswitch_merged["COGS_pred"]),
                    "cogs_rmse": _rmse(revswitch_merged["COGS"], revswitch_merged["COGS_pred"]),
                    "cogs_r2": r2_score(revswitch_merged["COGS"], revswitch_merged["COGS_pred"]),
                    "combined_mae": 0.5
                    * (
                        mean_absolute_error(revswitch_merged["Revenue"], revswitch_merged["Revenue_pred"])
                        + mean_absolute_error(revswitch_merged["COGS"], revswitch_merged["COGS_pred"])
                    ),
                },
            ]
        )

    router_df = pd.concat(router_frames, ignore_index=True)
    donor_feature_cols = [
        "anchor_rev70",
        "revswitch_aligned",
        "bottomup_category_aligned",
        "bottomup_catseg_aligned",
        "revswitch_delta",
        "bottomup_category_delta",
        "bottomup_catseg_delta",
        "revswitch_z20",
        "donor_mean",
        "donor_std",
        "donor_min",
        "donor_max",
        "donor_span",
        "donor_anchor_rank",
    ]
    base_feature_cols = [col for col in ROUTER_BASE_FEATURE_COLUMNS if col in router_df.columns]
    calendar_feature_cols = [col for col in CALENDAR_COLUMNS if col in router_df.columns]
    feature_cols = donor_feature_cols + base_feature_cols + calendar_feature_cols
    write_json(
        run_dir / "config.json",
        {
            "feature_cols": feature_cols,
            "router_variants": ROUTER_VARIANTS,
            "promo_policy": PROMO_POLICY,
            "context_policy": CONTEXT_POLICY,
            "switch_proxy_weight": SWITCH_PROXY_WEIGHT,
        },
    )

    logger.info("Running leave-one-fold-out router evaluation")
    router_fold_rows: list[dict[str, object]] = []
    oof_variant_frames: list[pd.DataFrame] = []
    for fold_id, (start_date, end_date) in enumerate(SPRINT_FOLDS, start=1):
        train_df = router_df.loc[router_df["fold"] != fold_id].copy()
        valid_df = router_df.loc[router_df["fold"] == fold_id].copy()

        model = CatBoostRegressor(**ROUTER_MODEL_PARAMS)
        model.fit(
            train_df[feature_cols],
            train_df["target_residual"],
            sample_weight=train_df["sample_weight"],
        )
        residual_pred = model.predict(valid_df[feature_cols])

        for spec in ROUTER_VARIANTS:
            revenue_pred = apply_router_variant(valid_df, residual_pred, float(spec["clamp_expansion"]))
            merged = valid_df[["Date", "Revenue_true", "COGS_true", "cogs_anchor"]].copy()
            merged["Revenue_pred"] = revenue_pred
            merged["COGS_pred"] = valid_df["cogs_anchor"].to_numpy()
            oof_variant_frames.append(
                pd.DataFrame(
                    {
                        "candidate_id": spec["candidate_id"],
                        "fold": fold_id,
                        "Date": valid_df["Date"],
                        "Revenue_true": valid_df["Revenue_true"],
                        "Revenue_pred": revenue_pred,
                        "COGS_true": valid_df["COGS_true"],
                        "COGS_pred": valid_df["cogs_anchor"],
                    }
                )
            )
            router_fold_rows.append(
                {
                    "candidate_id": spec["candidate_id"],
                    "fold": fold_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "revenue_mae": mean_absolute_error(merged["Revenue_true"], merged["Revenue_pred"]),
                    "revenue_rmse": _rmse(merged["Revenue_true"], merged["Revenue_pred"]),
                    "revenue_r2": r2_score(merged["Revenue_true"], merged["Revenue_pred"]),
                    "cogs_mae": mean_absolute_error(merged["COGS_true"], merged["COGS_pred"]),
                    "cogs_rmse": _rmse(merged["COGS_true"], merged["COGS_pred"]),
                    "cogs_r2": r2_score(merged["COGS_true"], merged["COGS_pred"]),
                    "combined_mae": 0.5
                    * (
                        mean_absolute_error(merged["Revenue_true"], merged["Revenue_pred"])
                        + mean_absolute_error(merged["COGS_true"], merged["COGS_pred"])
                    ),
                }
            )

    fold_metrics_df = pd.DataFrame(baseline_fold_rows + router_fold_rows).sort_values(["candidate_id", "fold"]).reset_index(drop=True)
    fold_metrics_df.to_csv(run_dir / "fold_metrics.csv", index=False)
    pd.concat(oof_variant_frames, ignore_index=True).to_csv(run_dir / "oof_daily_predictions.csv", index=False)
    summary_df = build_summary(fold_metrics_df)
    summary_df.to_csv(run_dir / "summary.csv", index=False)

    logger.info("Training final router on all backtest folds")
    final_model = CatBoostRegressor(**ROUTER_MODEL_PARAMS)
    final_model.fit(
        router_df[feature_cols],
        router_df["target_residual"],
        sample_weight=router_df["sample_weight"],
    )
    feature_importance_df = final_model.get_feature_importance(prettified=True)
    feature_importance_df.to_csv(run_dir / "feature_importance.csv", index=False)

    logger.info("Preparing final-horizon public donor frame")
    anchor_public = load_submission(PUBLIC_ANCHOR_PATH)
    revswitch_public = load_submission(PUBLIC_REVSWITCH_PATH)
    bottomup_category_public = load_submission(PUBLIC_BOTTOMUP_CATEGORY_PATH)
    bottomup_catseg_public = load_submission(PUBLIC_BOTTOMUP_CATSEG_PATH)
    final_feature_base = build_router_feature_base(base, TRAIN_END)
    final_feature_base = final_feature_base.loc[
        (final_feature_base["Date"] >= FORECAST_START) & (final_feature_base["Date"] <= FORECAST_END)
    ].copy()

    final_anchor_df = anchor_public.rename(columns={"Revenue": "Revenue_pred", "COGS": "COGS_pred"})[["Date", "Revenue_pred", "COGS_pred"]]
    final_revswitch_df = revswitch_public.rename(columns={"Revenue": "Revenue_pred"})[["Date", "Revenue_pred"]]
    final_bottomup_category_df = bottomup_category_public.rename(columns={"Revenue": "Revenue_pred"})[["Date", "Revenue_pred"]]
    final_bottomup_catseg_df = bottomup_catseg_public.rename(columns={"Revenue": "Revenue_pred"})[["Date", "Revenue_pred"]]

    final_router_df = build_daily_router_frame(
        truth_df=None,
        feature_base=final_feature_base,
        anchor_df=final_anchor_df,
        revswitch_df=final_revswitch_df,
        bottomup_category_df=final_bottomup_category_df,
        bottomup_catseg_df=final_bottomup_catseg_df,
        cogs_anchor_df=final_anchor_df,
        fold_id=None,
        split_name="final",
    )
    final_residual_pred = final_model.predict(final_router_df[feature_cols])
    final_router_df["residual_pred"] = final_residual_pred
    final_router_df.to_csv(run_dir / "final_daily_features.csv", index=False)

    final_manifest_rows: list[dict[str, object]] = []
    for spec in ROUTER_VARIANTS:
        revenue_pred = apply_router_variant(final_router_df, final_residual_pred, float(spec["clamp_expansion"]))
        submission = pd.DataFrame(
            {
                "Date": pd.to_datetime(final_router_df["Date"]).dt.strftime("%Y-%m-%d"),
                "Revenue": revenue_pred,
                "COGS": anchor_public["COGS"].to_numpy(),
            }
        )
        output_name = f"submission_{spec['candidate_id']}.csv"
        dataset_path = DATASET_DIR / output_name
        run_path = run_dir / output_name
        submission.to_csv(dataset_path, index=False)
        submission.to_csv(run_path, index=False)
        logger.info("Exported %s", output_name)

        revenue_abs_diff = (submission["Revenue"] - anchor_public["Revenue"]).abs()
        combined_abs_diff = 0.5 * revenue_abs_diff
        final_manifest_rows.append(
            {
                "priority": spec["priority"],
                "candidate_id": spec["candidate_id"],
                "clamp_expansion": spec["clamp_expansion"],
                "rows_changed_revenue": int((revenue_abs_diff > 1e-9).sum()),
                "rows_changed_cogs": 0,
                "anchor_invalid_rows": invalid_row_count(anchor_public),
                "candidate_invalid_rows": invalid_row_count(submission),
                "mean_abs_diff_revenue_vs_anchor": float(revenue_abs_diff.mean()),
                "mean_abs_diff_combined_vs_anchor": float(combined_abs_diff.mean()),
                "thesis": spec["thesis"],
                "dataset_file": str(dataset_path),
            }
        )

    final_manifest_df = pd.DataFrame(final_manifest_rows).sort_values(["priority"]).reset_index(drop=True)
    final_manifest_df.to_csv(run_dir / "final_manifest.csv", index=False)
    write_json(run_dir / "final_manifest.json", {"candidates": final_manifest_rows})

    write_report(run_dir, summary_df, fold_metrics_df, final_manifest_df, feature_importance_df)
    logger.info("Saved summary to %s", run_dir / "summary.csv")
    if not summary_df.empty:
        logger.info("Top OOF candidate: %s", summary_df.iloc[0]["candidate_id"])


if __name__ == "__main__":
    main()
