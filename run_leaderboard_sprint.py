from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
except Exception:
    ExponentialSmoothing = None

from logging_utils import create_run_dir, setup_logger, write_json
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


RUN_PREFIX = "leaderboard_sprint"
SPRINT_FOLDS = [
    ("2020-01-01", "2020-12-31"),
    ("2021-01-01", "2021-12-31"),
    ("2022-01-01", "2022-12-31"),
]
SELECTOR_STABILITY_WEIGHT = 0.10
SUBMIT_GATE_RECENT_MAE_MULTIPLIER = 1.01
SUBMIT_GATE_RMSE_MULTIPLIER = 1.03
SUBMIT_GATE_R2_TOLERANCE = 0.02
SUBMIT_GATE_COGS_MAE_MULTIPLIER = 1.05
FORECAST_START = pd.Timestamp("2023-01-01")
FORECAST_END = pd.Timestamp("2024-07-01")

BASELINE_CANDIDATES = [
    {"candidate_id": "baseline_seasonal_md2y", "kind": "baseline", "method": "seasonal_md2y"},
    {"candidate_id": "baseline_weekly_recursive", "kind": "baseline", "method": "weekly_recursive"},
    {"candidate_id": "baseline_ets_weekly", "kind": "baseline", "method": "ets_weekly"},
]
MODEL_CANDIDATES = [
    {
        "candidate_id": "xgb_md2y_core",
        "kind": "model",
        "model_family": "xgb",
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
    },
    {
        "candidate_id": "xgb_md2y_context",
        "kind": "model",
        "model_family": "xgb",
        "revenue_experiment": "curated_context_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "seasonal_month_day_recent_2y",
        "cogs_postprocess_variant": "blend60_clip_q99",
    },
    {
        "candidate_id": "lightgbm_md2y_core",
        "kind": "model",
        "model_family": "lightgbm",
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
    },
    {
        "candidate_id": "lightgbm_md2y_context",
        "kind": "model",
        "model_family": "lightgbm",
        "revenue_experiment": "curated_context_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "seasonal_month_day_recent_2y",
        "cogs_postprocess_variant": "blend60_clip_q99",
    },
    {
        "candidate_id": "catboost_md2y_core",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
    },
    {
        "candidate_id": "catboost_md2y_core_target_seasonal_priors",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs_target_seasonal",
        "cogs_experiment": "curated_promo_cogs_target_seasonal",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
    },
    {
        "candidate_id": "catboost_md2y_core_cogs_ratio_bucket",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "ratio_bucket_shrink",
        "cogs_target_mode": "ratio",
    },
    {
        "candidate_id": "catboost_md2y_core_cogs_ratio_bucket_tight",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "ratio_bucket_shrink_tight",
        "cogs_target_mode": "ratio",
    },
    {
        "candidate_id": "catboost_core_log1p",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "revenue_target_transform": "log1p",
    },
    {
        "candidate_id": "catboost_md2y_core_seasonal_tail_blend",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "seasonal_repair_strategy": "tail_ramp_30",
    },
    {
        "candidate_id": "catboost_core_strict",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "forecast_core_strict",
        "cogs_experiment": "forecast_core_strict",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "model_params_override": {
            "iterations": 1200,
            "learning_rate": 0.025,
            "depth": 5,
            "l2_leaf_reg": 8.0,
        },
    },
    {
        "candidate_id": "catboost_md2y_medium_core",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "train_window_days": 1825,
    },
    {
        "candidate_id": "catboost_md2y_recent_core",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "train_window_days": 1095,
    },
    {
        "candidate_id": "catboost_md2y_context",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_context_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "seasonal_month_day_recent_2y",
        "cogs_postprocess_variant": "blend60_clip_q99",
    },
]
CANDIDATES = BASELINE_CANDIDATES + MODEL_CANDIDATES


def _rmse(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def _build_recency_weights(folds: list[int]) -> dict[int, float]:
    ordered = sorted(set(int(fold) for fold in folds))
    raw = np.arange(1, len(ordered) + 1, dtype=float)
    weights = raw / raw.sum()
    return {fold: float(weight) for fold, weight in zip(ordered, weights, strict=False)}


def _weighted_metric(group: pd.DataFrame, metric: str, weight_map: dict[int, float]) -> float:
    weights = group["fold"].map(weight_map).astype(float)
    return float(np.average(group[metric], weights=weights))


def apply_seasonal_repair(
    preds: pd.DataFrame,
    seasonal_preds: pd.DataFrame,
    strategy_name: str,
) -> pd.DataFrame:
    if strategy_name == "none":
        return preds.copy()
    if strategy_name != "tail_ramp_30":
        raise ValueError(f"Unknown seasonal repair strategy: {strategy_name}")

    merged = preds.merge(
        seasonal_preds.rename(
            columns={
                "Revenue_pred": "Revenue_pred_seasonal",
                "COGS_pred": "COGS_pred_seasonal",
            }
        ),
        on="Date",
        how="left",
    )
    horizon = len(merged)
    if horizon <= 1:
        seasonal_weights = np.array([0.30], dtype=float)
    else:
        seasonal_weights = np.linspace(0.0, 0.30, horizon, dtype=float)

    merged["Revenue_pred"] = (
        (1.0 - seasonal_weights) * merged["Revenue_pred"] + seasonal_weights * merged["Revenue_pred_seasonal"]
    )
    merged["COGS_pred"] = (
        (1.0 - seasonal_weights) * merged["COGS_pred"] + seasonal_weights * merged["COGS_pred_seasonal"]
    )
    return merged[["Date", "Revenue_pred", "COGS_pred"]]


def _fit_ets(history: pd.Series) -> ExponentialSmoothing:
    if ExponentialSmoothing is None:
        raise ImportError("statsmodels ExponentialSmoothing is unavailable in this environment")
    return ExponentialSmoothing(
        history.astype(float),
        trend="add",
        damped_trend=True,
        seasonal="add",
        seasonal_periods=7,
        initialization_method="estimated",
    ).fit(optimized=True, use_brute=False)


def forecast_baseline(
    method: str,
    history_df: pd.DataFrame,
    forecast_start: pd.Timestamp,
    forecast_end: pd.Timestamp,
) -> pd.DataFrame:
    history = history_df.copy().sort_values("Date").set_index("Date")
    forecast_dates = pd.date_range(forecast_start, forecast_end, freq="D")
    rows: list[dict[str, object]] = []

    if method == "seasonal_md2y":
        history_lookup = history.reset_index().copy()
        history_lookup["month"] = history_lookup["Date"].dt.month
        history_lookup["day"] = history_lookup["Date"].dt.day
        cutoff = forecast_start - pd.Timedelta(days=1)
        min_date = cutoff - pd.DateOffset(years=2)
        history_lookup = history_lookup.loc[history_lookup["Date"] > min_date].copy()
        priors = history_lookup.groupby(["month", "day"])[["Revenue", "COGS"]].mean().reset_index()
        overall = history_lookup[["Revenue", "COGS"]].mean()
        for current_date in forecast_dates:
            match = priors.loc[(priors["month"] == current_date.month) & (priors["day"] == current_date.day)]
            if match.empty:
                revenue_pred = float(overall["Revenue"])
                cogs_pred = float(overall["COGS"])
            else:
                revenue_pred = float(match["Revenue"].iloc[0])
                cogs_pred = float(match["COGS"].iloc[0])
            rows.append({"Date": current_date, "Revenue_pred": max(revenue_pred, 0.0), "COGS_pred": max(cogs_pred, 0.0)})
        return pd.DataFrame(rows)

    if method == "weekly_recursive":
        for current_date in forecast_dates:
            lag_date = current_date - pd.Timedelta(days=7)
            if lag_date in history.index:
                revenue_pred = float(history.at[lag_date, "Revenue"])
                cogs_pred = float(history.at[lag_date, "COGS"])
            else:
                revenue_pred = float(history["Revenue"].tail(7).mean())
                cogs_pred = float(history["COGS"].tail(7).mean())
            revenue_pred = max(revenue_pred, 0.0)
            cogs_pred = max(cogs_pred, 0.0)
            history.loc[current_date, ["Revenue", "COGS"]] = [revenue_pred, cogs_pred]
            rows.append({"Date": current_date, "Revenue_pred": revenue_pred, "COGS_pred": cogs_pred})
        return pd.DataFrame(rows)

    if method == "ets_weekly":
        revenue_model = _fit_ets(history["Revenue"])
        cogs_model = _fit_ets(history["COGS"])
        horizon = len(forecast_dates)
        revenue_fc = np.clip(revenue_model.forecast(horizon).to_numpy(), 0.0, None)
        cogs_fc = np.clip(cogs_model.forecast(horizon).to_numpy(), 0.0, None)
        return pd.DataFrame(
            {
                "Date": forecast_dates,
                "Revenue_pred": revenue_fc,
                "COGS_pred": cogs_fc,
            }
        )

    raise ValueError(f"Unknown baseline method: {method}")


def evaluate_candidate(
    candidate: dict[str, object],
    feature_store: pd.DataFrame,
    base: pd.DataFrame,
    feature_sets: dict[str, list[str]],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for fold_id, (start_date, end_date) in enumerate(SPRINT_FOLDS, start=1):
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        cutoff = start_ts - pd.Timedelta(days=1)
        history_df = feature_store.loc[feature_store["Date"] <= cutoff, ["Date", "Revenue", "COGS"]].copy()

        if candidate["kind"] == "baseline":
            preds = forecast_baseline(str(candidate["method"]), history_df, start_ts, end_ts)
        else:
            adjusted_base = apply_future_promo_policy(base, cutoff, str(candidate["promo_future_policy"]))
            adjusted_base = apply_future_context_policy(adjusted_base, cutoff, str(candidate["context_future_policy"]))
            adjusted_base = apply_future_price_policy(
                adjusted_base,
                cutoff,
                str(candidate.get("price_future_policy", "zero")),
            )
            adjusted_base = apply_future_hierarchy_policy(
                adjusted_base,
                cutoff,
                str(candidate.get("hierarchy_future_policy", "zero")),
            )
            preds = recursive_forecast(
                feature_store=feature_store,
                full_base=adjusted_base,
                train_end_date=cutoff,
                forecast_start=start_ts,
                forecast_end=end_ts,
                revenue_features=feature_sets[str(candidate["revenue_experiment"])],
                cogs_features=feature_sets[str(candidate["cogs_experiment"])],
                cogs_postprocess_variant=str(candidate["cogs_postprocess_variant"]),
                model_family=str(candidate["model_family"]),
                train_window_days=candidate.get("train_window_days"),
                model_params_override=candidate.get("model_params_override"),
                revenue_target_transform=str(candidate.get("revenue_target_transform", "none")),
                cogs_target_transform=str(candidate.get("cogs_target_transform", "none")),
                cogs_target_mode=str(candidate.get("cogs_target_mode", "direct")),
                sample_weight_mode=str(candidate.get("sample_weight_mode", "none")),
                sample_weight_decay=float(candidate.get("sample_weight_decay", 0.0)),
            )
            seasonal_repair_strategy = str(candidate.get("seasonal_repair_strategy", "none"))
            if seasonal_repair_strategy != "none":
                seasonal_preds = forecast_baseline("seasonal_md2y", history_df, start_ts, end_ts)
                preds = apply_seasonal_repair(preds, seasonal_preds, seasonal_repair_strategy)

        truth = feature_store.loc[
            (feature_store["Date"] >= start_ts) & (feature_store["Date"] <= end_ts),
            ["Date", "Revenue", "COGS"],
        ].copy()
        merged = truth.merge(preds, on="Date", how="left")
        rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "kind": candidate["kind"],
                "model_family": candidate.get("model_family"),
                "fold": fold_id,
                "start_date": start_date,
                "end_date": end_date,
                "revenue_experiment": candidate.get("revenue_experiment"),
                "cogs_experiment": candidate.get("cogs_experiment"),
                "train_window_days": candidate.get("train_window_days"),
                "promo_future_policy": candidate.get("promo_future_policy"),
                "context_future_policy": candidate.get("context_future_policy"),
                "price_future_policy": candidate.get("price_future_policy"),
                "hierarchy_future_policy": candidate.get("hierarchy_future_policy"),
                "revenue_target_transform": candidate.get("revenue_target_transform"),
                "cogs_target_transform": candidate.get("cogs_target_transform"),
                "cogs_target_mode": candidate.get("cogs_target_mode"),
                "sample_weight_mode": candidate.get("sample_weight_mode"),
                "sample_weight_decay": candidate.get("sample_weight_decay"),
                "seasonal_repair_strategy": candidate.get("seasonal_repair_strategy"),
                "baseline_method": candidate.get("method"),
                "revenue_mae": mean_absolute_error(merged["Revenue"], merged["Revenue_pred"]),
                "revenue_rmse": _rmse(merged["Revenue"], merged["Revenue_pred"]),
                "revenue_r2": r2_score(merged["Revenue"], merged["Revenue_pred"]),
                "cogs_mae": mean_absolute_error(merged["COGS"], merged["COGS_pred"]),
                "cogs_rmse": _rmse(merged["COGS"], merged["COGS_pred"]),
                "cogs_r2": r2_score(merged["COGS"], merged["COGS_pred"]),
            }
        )

    return pd.DataFrame(rows)


def build_summary(fold_df: pd.DataFrame) -> pd.DataFrame:
    group_keys = ["candidate_id", "kind", "model_family", "revenue_experiment", "cogs_experiment", "train_window_days"]
    recency_weights = _build_recency_weights(fold_df["fold"].tolist())
    ordered_folds = sorted(recency_weights)
    tail_folds = ordered_folds[-2:] if len(ordered_folds) >= 2 else ordered_folds
    tail_weight_map = _build_recency_weights(tail_folds)

    summary_rows: list[dict[str, object]] = []
    grouped = fold_df.groupby(group_keys, dropna=False)
    for key, group in grouped:
        if not isinstance(key, tuple):
            key = (key,)
        row = dict(zip(group_keys, key, strict=False))
        tail_group = group[group["fold"].isin(tail_folds)].copy()
        row.update(
            {
                "revenue_mae_mean": float(group["revenue_mae"].mean()),
                "revenue_mae_std": float(group["revenue_mae"].std()),
                "revenue_rmse_mean": float(group["revenue_rmse"].mean()),
                "revenue_r2_mean": float(group["revenue_r2"].mean()),
                "cogs_mae_mean": float(group["cogs_mae"].mean()),
                "cogs_mae_std": float(group["cogs_mae"].std()),
                "cogs_rmse_mean": float(group["cogs_rmse"].mean()),
                "cogs_r2_mean": float(group["cogs_r2"].mean()),
                "recent_weighted_revenue_mae": _weighted_metric(group, "revenue_mae", recency_weights),
                "recent_weighted_revenue_rmse": _weighted_metric(group, "revenue_rmse", recency_weights),
                "recent_weighted_revenue_r2": _weighted_metric(group, "revenue_r2", recency_weights),
                "recent_weighted_cogs_mae": _weighted_metric(group, "cogs_mae", recency_weights),
                "recent_tail_revenue_mae": _weighted_metric(tail_group, "revenue_mae", tail_weight_map),
                "recent_tail_revenue_rmse": _weighted_metric(tail_group, "revenue_rmse", tail_weight_map),
                "recent_tail_revenue_r2": _weighted_metric(tail_group, "revenue_r2", tail_weight_map),
                "recent_tail_cogs_mae": _weighted_metric(tail_group, "cogs_mae", tail_weight_map),
            }
        )
        row["combined_mae_mean"] = float(0.5 * (row["revenue_mae_mean"] + row["cogs_mae_mean"]))
        row["combined_mae_std"] = float(0.5 * (row["revenue_mae_std"] + row["cogs_mae_std"]))
        row["recent_weighted_combined_mae"] = float(
            0.5 * (row["recent_weighted_revenue_mae"] + row["recent_weighted_cogs_mae"])
        )
        row["recent_tail_combined_mae"] = float(
            0.5 * (row["recent_tail_revenue_mae"] + row["recent_tail_cogs_mae"])
        )
        row["selector_score"] = float(
            row["recent_weighted_combined_mae"] + SELECTOR_STABILITY_WEIGHT * row["combined_mae_std"]
        )
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    summary_df = summary_df.sort_values(
        [
            "selector_score",
            "recent_tail_combined_mae",
            "revenue_rmse_mean",
            "cogs_rmse_mean",
            "revenue_mae_mean",
            "cogs_mae_mean",
        ],
        ascending=[True, True, True, True, True, True],
    ).reset_index(drop=True)

    anchor = summary_df.iloc[0]
    summary_df["recent_weighted_combined_mae_delta_vs_anchor"] = (
        summary_df["recent_weighted_combined_mae"] - float(anchor["recent_weighted_combined_mae"])
    )
    summary_df["recent_tail_combined_mae_delta_vs_anchor"] = (
        summary_df["recent_tail_combined_mae"] - float(anchor["recent_tail_combined_mae"])
    )
    summary_df["recent_weighted_revenue_mae_delta_vs_anchor"] = (
        summary_df["recent_weighted_revenue_mae"] - float(anchor["recent_weighted_revenue_mae"])
    )
    summary_df["recent_tail_revenue_mae_delta_vs_anchor"] = (
        summary_df["recent_tail_revenue_mae"] - float(anchor["recent_tail_revenue_mae"])
    )
    summary_df["revenue_rmse_mean_delta_vs_anchor"] = summary_df["revenue_rmse_mean"] - float(anchor["revenue_rmse_mean"])
    summary_df["revenue_r2_mean_delta_vs_anchor"] = summary_df["revenue_r2_mean"] - float(anchor["revenue_r2_mean"])
    summary_df["cogs_mae_mean_delta_vs_anchor"] = summary_df["cogs_mae_mean"] - float(anchor["cogs_mae_mean"])
    summary_df["passes_recent_gate"] = (
        summary_df["recent_weighted_combined_mae"]
        <= float(anchor["recent_weighted_combined_mae"]) * SUBMIT_GATE_RECENT_MAE_MULTIPLIER
    )
    summary_df["passes_breadth_gate"] = (
        (summary_df["revenue_rmse_mean"] <= float(anchor["revenue_rmse_mean"]) * SUBMIT_GATE_RMSE_MULTIPLIER)
        & (summary_df["revenue_r2_mean"] >= float(anchor["revenue_r2_mean"]) - SUBMIT_GATE_R2_TOLERANCE)
        & (summary_df["cogs_mae_mean"] <= float(anchor["cogs_mae_mean"]) * SUBMIT_GATE_COGS_MAE_MULTIPLIER)
    )
    summary_df["passes_submit_gate"] = summary_df["passes_recent_gate"] & summary_df["passes_breadth_gate"]
    return summary_df


def export_final_submission(
    candidate: dict[str, object],
    feature_store: pd.DataFrame,
    base: pd.DataFrame,
    feature_sets: dict[str, list[str]],
    output_path: Path,
) -> None:
    history_df = feature_store.loc[feature_store["Date"] <= TRAIN_END, ["Date", "Revenue", "COGS"]].copy()
    if candidate["kind"] == "baseline":
        preds = forecast_baseline(str(candidate["method"]), history_df, FORECAST_START, FORECAST_END)
    else:
        adjusted_base = apply_future_promo_policy(base, TRAIN_END, str(candidate["promo_future_policy"]))
        adjusted_base = apply_future_context_policy(adjusted_base, TRAIN_END, str(candidate["context_future_policy"]))
        adjusted_base = apply_future_price_policy(
            adjusted_base,
            TRAIN_END,
            str(candidate.get("price_future_policy", "zero")),
        )
        adjusted_base = apply_future_hierarchy_policy(
            adjusted_base,
            TRAIN_END,
            str(candidate.get("hierarchy_future_policy", "zero")),
        )
        preds = recursive_forecast(
            feature_store=feature_store,
            full_base=adjusted_base,
            train_end_date=TRAIN_END,
            forecast_start=FORECAST_START,
            forecast_end=FORECAST_END,
            revenue_features=feature_sets[str(candidate["revenue_experiment"])],
            cogs_features=feature_sets[str(candidate["cogs_experiment"])],
            cogs_postprocess_variant=str(candidate["cogs_postprocess_variant"]),
            model_family=str(candidate["model_family"]),
            train_window_days=candidate.get("train_window_days"),
            model_params_override=candidate.get("model_params_override"),
            revenue_target_transform=str(candidate.get("revenue_target_transform", "none")),
            cogs_target_transform=str(candidate.get("cogs_target_transform", "none")),
            cogs_target_mode=str(candidate.get("cogs_target_mode", "direct")),
            sample_weight_mode=str(candidate.get("sample_weight_mode", "none")),
            sample_weight_decay=float(candidate.get("sample_weight_decay", 0.0)),
        )
        seasonal_repair_strategy = str(candidate.get("seasonal_repair_strategy", "none"))
        if seasonal_repair_strategy != "none":
            seasonal_preds = forecast_baseline("seasonal_md2y", history_df, FORECAST_START, FORECAST_END)
            preds = apply_seasonal_repair(preds, seasonal_preds, seasonal_repair_strategy)
    submission = preds.rename(columns={"Revenue_pred": "Revenue", "COGS_pred": "COGS"})[["Date", "Revenue", "COGS"]]
    submission["Date"] = pd.to_datetime(submission["Date"]).dt.strftime("%Y-%m-%d")
    submission.to_csv(output_path, index=False)


def write_report(run_dir: Path, summary_df: pd.DataFrame, fold_df: pd.DataFrame, top_ids: list[str]) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Leaderboard Sprint\n\n")
        f.write("## Framing\n")
        f.write("- Goal: improve public-style ranking with a forecast-safe core, not a full report stack\n")
        f.write("- Forecast core in this sprint: calendar + target history + COGS history + promo priors + optional context priors\n")
        f.write("- Strict-core candidate: excludes promo target encoding features and applies tighter CatBoost regularization\n")
        f.write("- Long-horizon anchor upgrade in this sprint: extra yearly Fourier harmonics and long EWMs (182/365/730)\n")
        f.write("- Window challengers in this sprint: long-history anchor vs medium/recent CatBoost variants\n")
        f.write("- Seasonal challenger in this sprint: CatBoost core with a seasonal baseline blend that ramps to 30% at the far end of the horizon\n")
        f.write("- Target-seasonal challenger in this sprint: CatBoost core plus month/day and month/weekday priors from historical Revenue and COGS\n")
        f.write("- Target-transform challenger in this sprint: CatBoost core with log1p revenue training and inverse transform at inference\n")
        f.write("- COGS specialist challenger in this sprint: ratio-based CatBoost with month/day-of-week ratio bands and horizon-aware shrinkage\n")
        f.write("- Selector now prioritizes recent-weighted combined Revenue+COGS MAE and stability before global mean\n")
        f.write("- Excluded from forecast core for now: raw future traffic, raw future inventory, raw future returns/reviews, raw future mix features\n\n")
        f.write("## Submit Gate\n")
        f.write(f"- Recent weighted combined Revenue+COGS MAE must be within {SUBMIT_GATE_RECENT_MAE_MULTIPLIER:.2f}x of the anchor\n")
        f.write(f"- Revenue RMSE mean must be within {SUBMIT_GATE_RMSE_MULTIPLIER:.2f}x of the anchor\n")
        f.write(f"- Revenue R2 mean must not drop by more than {SUBMIT_GATE_R2_TOLERANCE:.2f}\n")
        f.write(f"- COGS MAE mean must be within {SUBMIT_GATE_COGS_MAE_MULTIPLIER:.2f}x of the anchor\n\n")
        f.write("## Candidate Ranking\n")
        f.write(summary_df.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Fold Metrics\n")
        f.write(fold_df.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Submission Files\n")
        for candidate_id in top_ids:
            f.write(f"- `dataset/submission_{candidate_id}.csv`\n")


def filter_candidates() -> list[dict[str, object]]:
    raw = os.getenv("SPRINT_CANDIDATES", "").strip()
    if not raw:
        return CANDIDATES
    selected_ids = {part.strip() for part in raw.split(",") if part.strip()}
    return [candidate for candidate in CANDIDATES if str(candidate["candidate_id"]) in selected_ids]


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting leaderboard sprint in %s", run_dir)
    selected_candidates = filter_candidates()
    write_json(run_dir / "config.json", {"folds": SPRINT_FOLDS, "candidates": selected_candidates})

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))

    fold_frames: list[pd.DataFrame] = []
    for candidate in selected_candidates:
        logger.info("Evaluating %s", candidate["candidate_id"])
        fold_frames.append(evaluate_candidate(candidate, feature_store, base, feature_sets))

    fold_df = pd.concat(fold_frames, ignore_index=True)
    fold_df.to_csv(run_dir / "fold_results.csv", index=False)

    summary_df = build_summary(fold_df)
    summary_df.to_csv(run_dir / "summary.csv", index=False)

    top_ids = summary_df.loc[summary_df["passes_submit_gate"], "candidate_id"].head(3).tolist()
    candidate_map = {str(candidate["candidate_id"]): candidate for candidate in selected_candidates}
    for candidate_id in top_ids:
        dataset_path = Path("dataset") / f"submission_{candidate_id}.csv"
        run_path = run_dir / f"submission_{candidate_id}.csv"
        export_final_submission(candidate_map[candidate_id], feature_store, base, feature_sets, dataset_path)
        export_final_submission(candidate_map[candidate_id], feature_store, base, feature_sets, run_path)
        logger.info("Exported submission for %s", candidate_id)

    write_report(run_dir, summary_df, fold_df, top_ids)
    logger.info("Saved summary to %s", run_dir / "summary.csv")
    if not summary_df.empty:
        logger.info("Top candidate: %s", summary_df.iloc[0]["candidate_id"])
    else:
        logger.warning("No candidates were summarized")


if __name__ == "__main__":
    main()
