from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from lunar_calendar_features import solar_to_lunar, tet_date_for_solar_year

from build_feature_store import BASE_OUT_PATH, OUT_PATH as FEATURE_STORE_PATH, build_feature_store
from feature_pipeline import (
    CONTEXT_BASE_COLUMNS,
    PROMO_BASE_COLUMNS,
    PROMO_MODEL_COLUMNS,
    PROMO_RESEARCH_BASE_COLUMNS,
    PRICE_SIGNAL_COLUMNS,
    TARGET_LAG_PERIODS,
    TARGET_ROLL_WINDOWS,
    TARGET_SEASONAL_PRIOR_COLUMNS,
    add_promo_target_encoding_features,
    get_hierarchy_lite_raw_columns,
)
from run_ablation import MODEL_PARAMS, build_experiments


OUT_DIR = Path("outputs/final")
OUT_DIR.mkdir(parents=True, exist_ok=True)
TRAIN_END = pd.Timestamp("2022-12-31")

PROMO_POLICY_COLUMNS = list(PROMO_BASE_COLUMNS) + list(PROMO_RESEARCH_BASE_COLUMNS)
PROMO_RAW_COLUMNS = list(PROMO_MODEL_COLUMNS) + list(PROMO_RESEARCH_BASE_COLUMNS)
PROMO_LAG_WINDOWS = [1, 7, 14, 28]
PROMO_ROLL_WINDOWS = [7, 28, 91]
PROMO_REQUIRED_FEATURE_STORE_COLUMNS = sorted(
    set(PROMO_RAW_COLUMNS)
    .union(f"{col}_lag_1" for col in PROMO_RAW_COLUMNS)
    .union(f"{col}_rollmean_7" for col in PROMO_RAW_COLUMNS)
)
CONTEXT_POLICY_COLUMNS = list(CONTEXT_BASE_COLUMNS)
CONTEXT_LAG_WINDOWS = [1, 7, 14, 28]
CONTEXT_ROLL_WINDOWS = [7, 28, 91]
CONTEXT_REQUIRED_FEATURE_STORE_COLUMNS = sorted(
    set(CONTEXT_POLICY_COLUMNS)
    .union(f"{col}_lag_1" for col in CONTEXT_POLICY_COLUMNS)
    .union(f"{col}_rollmean_7" for col in CONTEXT_POLICY_COLUMNS)
)
PRICE_LAG_WINDOWS = [1, 7, 14, 28]
PRICE_ROLL_WINDOWS = [7, 28, 91]
FEATURE_STORE_SENTINEL_COLUMNS = [
    "sin_dayofyear_k2",
    "cos_dayofyear_k2",
    "sin_dayofyear_k3",
    "cos_dayofyear_k3",
    "rev_ewm_182",
    "rev_ewm_365",
    "rev_ewm_730",
    "cogs_ewm_182",
    "cogs_ewm_365",
    "cogs_ewm_730",
    *TARGET_SEASONAL_PRIOR_COLUMNS,
    "revplus_rollmedian_7",
    "cogsplus_rollmedian_7",
    "promo_days_since_start_mean",
    "pricehist_avg_unit_price_ratio_1_7",
]
TARGET_TRANSFORMS = {"none", "log1p"}
COGS_TARGET_MODES = {"direct", "ratio"}
SAMPLE_WEIGHT_MODES = {"none", "exp_years", "piecewise_exp"}
PROMO_FUTURE_POLICIES = {
    "zero": {"mode": "zero"},
    "seasonal_month_day_recent_1y": {
        "mode": "seasonal_by_keys",
        "recent_years": 1,
        "date_keys": ["month", "day"],
        "agg": "mean",
    },
    "seasonal_month_day_recent_2y": {
        "mode": "seasonal_by_keys",
        "recent_years": 2,
        "date_keys": ["month", "day"],
        "agg": "mean",
    },
    "seasonal_month_day_recent_3y": {
        "mode": "seasonal_by_keys",
        "recent_years": 3,
        "date_keys": ["month", "day"],
        "agg": "mean",
    },
    "seasonal_month_day_recent_2y_median": {
        "mode": "seasonal_by_keys",
        "recent_years": 2,
        "date_keys": ["month", "day"],
        "agg": "median",
    },
    "seasonal_month_weekday_recent_2y": {
        "mode": "seasonal_by_keys",
        "recent_years": 2,
        "date_keys": ["month", "dayofweek"],
        "agg": "mean",
    },
}
CONTEXT_FUTURE_POLICIES = PROMO_FUTURE_POLICIES
HIERARCHY_FUTURE_POLICIES = PROMO_FUTURE_POLICIES
PRICE_FUTURE_POLICIES = PROMO_FUTURE_POLICIES
COGS_POSTPROCESS_VARIANTS = {
    "raw": {"mode": "raw"},
    "blend40_clip_q99": {"mode": "blend_clip", "raw_weight": 0.4, "upper_quantile_key": "q99"},
    "blend60_clip_q99": {"mode": "blend_clip", "raw_weight": 0.6, "upper_quantile_key": "q99"},
    "blend60_clip_q995": {"mode": "blend_clip", "raw_weight": 0.6, "upper_quantile_key": "q995"},
    "blend80_clip_q99": {"mode": "blend_clip", "raw_weight": 0.8, "upper_quantile_key": "q99"},
    "ratio_bucket_shrink": {
        "mode": "ratio_bucket_shrink",
        "near_raw_weight": 0.85,
        "far_raw_weight": 0.55,
        "hist_anchor_weight": 0.50,
        "near_lower_key": "q05",
        "far_lower_key": "q10",
        "near_upper_key": "q95",
        "far_upper_key": "q90",
        "soft_clip_beta": 0.25,
        "clamp_epsilon": 0.005,
    },
    "ratio_bucket_shrink_tight": {
        "mode": "ratio_bucket_shrink",
        "near_raw_weight": 0.75,
        "far_raw_weight": 0.40,
        "hist_anchor_weight": 0.45,
        "near_lower_key": "q10",
        "far_lower_key": "q20",
        "near_upper_key": "q90",
        "far_upper_key": "q80",
        "soft_clip_beta": 0.15,
        "clamp_epsilon": 0.005,
    },
}
REVENUE_REGIME_VARIANTS = {
    "none": {"mode": "primary"},
    "promo_heavy_switch_loose": {
        "mode": "threshold_switch",
        "min_promo_line_share": 0.5,
        "min_active_promo_count": 1.0,
        "min_avg_discount_rate": 0.05,
    },
    "promo_heavy_switch": {
        "mode": "threshold_switch",
        "min_promo_line_share": 0.6,
        "min_active_promo_count": 1.0,
        "min_avg_discount_rate": 0.08,
    },
    "promo_heavy_switch_strict": {
        "mode": "threshold_switch",
        "min_promo_line_share": 0.7,
        "min_active_promo_count": 2.0,
        "min_avg_discount_rate": 0.1,
    },
}

SYSTEMS = {
    "system_promo_only": {
        "revenue_experiment": "baseline_plus_promo",
        "cogs_experiment": "curated_promo_cogs",
        "cogs_postprocess_variant": "raw",
    },
    "system_promo_plus_cogs": {
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "cogs_postprocess_variant": "raw",
    },
    "system_promo_plus_cogs_blend60_clip_q99": {
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "cogs_postprocess_variant": "blend60_clip_q99",
    },
    "system_promo_plus_cogs_md2y": {
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "promo_future_policy": "seasonal_month_day_recent_2y",
    },
    "system_promo_plus_cogs_md2y_log1p": {
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "revenue_target_transform": "log1p",
    },
    "system_promo_plus_cogs_md2y_revenue_switch": {
        "revenue_experiment": "curated_promo_cogs",
        "secondary_revenue_experiment": "baseline_plus_promo",
        "revenue_regime_variant": "promo_heavy_switch",
        "cogs_experiment": "curated_promo_cogs",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "promo_future_policy": "seasonal_month_day_recent_2y",
    },
    "system_context_promo_plus_cogs_md2y": {
        "revenue_experiment": "curated_context_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "seasonal_month_day_recent_2y",
    },
    "system_promo_plus_cogs_md2y_ratio_bucket": {
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "cogs_postprocess_variant": "ratio_bucket_shrink",
        "cogs_target_mode": "ratio",
        "promo_future_policy": "seasonal_month_day_recent_2y",
    },
}

BACKTEST_FOLDS = [
    ("2020-01-01", "2020-12-31"),
    ("2021-01-01", "2021-12-31"),
    ("2022-01-01", "2022-12-31"),
]
XGB_FIT_MODEL_PARAMS = {key: value for key, value in MODEL_PARAMS.items() if key != "early_stopping_rounds"}
LIGHTGBM_FIT_MODEL_PARAMS = {
    "objective": "regression",
    "n_estimators": 900,
    "learning_rate": 0.03,
    "num_leaves": 31,
    "max_depth": -1,
    "min_child_samples": 20,
    "subsample": 0.8,
    "colsample_bytree": 0.7,
    "reg_alpha": 0.0,
    "reg_lambda": 1.0,
    "random_state": 42,
    "n_jobs": -1,
    "verbosity": -1,
}
CATBOOST_FIT_MODEL_PARAMS = {
    "loss_function": "RMSE",
    "iterations": 900,
    "learning_rate": 0.03,
    "depth": 6,
    "l2_leaf_reg": 3.0,
    "subsample": 0.8,
    "random_seed": 42,
    "verbose": False,
    "allow_writing_files": False,
}


def make_regressor(model_family: str, model_params_override: dict[str, float | int | bool] | None = None):
    if model_family == "xgb":
        params = XGB_FIT_MODEL_PARAMS.copy()
        if model_params_override:
            params.update(model_params_override)
        return xgb.XGBRegressor(**params)
    if model_family == "lightgbm":
        import lightgbm as lgb

        params = LIGHTGBM_FIT_MODEL_PARAMS.copy()
        if model_params_override:
            params.update(model_params_override)
        return lgb.LGBMRegressor(**params)
    if model_family == "catboost":
        from catboost import CatBoostRegressor

        params = CATBOOST_FIT_MODEL_PARAMS.copy()
        if model_params_override:
            params.update(model_params_override)
        return CatBoostRegressor(**params)
    raise ValueError(f"Unknown model family: {model_family}")


def fit_regressor(
    model,
    X: pd.DataFrame,
    y: pd.Series,
    model_family: str,
    sample_weight: pd.Series | np.ndarray | None = None,
):
    if model_family == "xgb":
        model.fit(X, y, sample_weight=sample_weight, verbose=False)
        return model
    if model_family == "lightgbm":
        model.fit(X, y, sample_weight=sample_weight)
        return model
    if model_family == "catboost":
        model.fit(X, y, sample_weight=sample_weight, verbose=False)
        return model
    raise ValueError(f"Unknown model family: {model_family}")


def build_sample_weights(
    train_dates: pd.Series,
    train_end_date: pd.Timestamp,
    sample_weight_mode: str = "none",
    sample_weight_decay: float = 0.0,
) -> pd.Series | None:
    if sample_weight_mode not in SAMPLE_WEIGHT_MODES:
        raise ValueError(f"Unknown sample weight mode: {sample_weight_mode}")
    if sample_weight_mode == "none" or sample_weight_decay == 0.0:
        return None
    days_ago = (train_end_date - pd.to_datetime(train_dates)).dt.days.clip(lower=0).astype(float)
    years_ago = days_ago / 365.25
    weights = np.exp(-float(sample_weight_decay) * years_ago)
    
    if sample_weight_mode == "piecewise_exp":
        cutoff_date = pd.Timestamp("2020-12-31")
        if train_end_date > cutoff_date:
            flat_weight_years = (train_end_date - cutoff_date).days / 365.25
            flat_weight = np.exp(-float(sample_weight_decay) * flat_weight_years)
            before_2021_mask = pd.to_datetime(train_dates).dt.year <= 2020
            weights[before_2021_mask] = float(flat_weight)
            
    return pd.Series(weights, index=train_dates.index, dtype=float)


def _transform_target_series(values: pd.Series, transform_name: str) -> pd.Series:
    if transform_name not in TARGET_TRANSFORMS:
        raise ValueError(f"Unknown target transform: {transform_name}")
    if transform_name == "none":
        return values.astype(float)
    if transform_name == "log1p":
        return np.log1p(values.astype(float).clip(lower=0.0))
    raise ValueError(f"Unsupported target transform: {transform_name}")


def _inverse_transform_scalar(value: float, transform_name: str) -> float:
    if transform_name not in TARGET_TRANSFORMS:
        raise ValueError(f"Unknown target transform: {transform_name}")
    if transform_name == "none":
        return float(value)
    if transform_name == "log1p":
        return float(np.expm1(value))
    raise ValueError(f"Unsupported target transform: {transform_name}")


def _compute_cogs_ratio_series(df: pd.DataFrame) -> pd.Series:
    revenue = df["Revenue"].replace(0, np.nan)
    ratio = (df["COGS"] / revenue).replace([np.inf, -np.inf], np.nan)
    return ratio


def _missing_required_columns(df: pd.DataFrame, required_columns: list[str]) -> list[str]:
    return sorted(col for col in required_columns if col not in df.columns)


def ensure_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    needs_rebuild = not FEATURE_STORE_PATH.exists() or not BASE_OUT_PATH.exists()
    if not needs_rebuild:
        feature_store_columns = pd.read_csv(FEATURE_STORE_PATH, nrows=0).columns.tolist()
        base_columns = pd.read_csv(BASE_OUT_PATH, nrows=0).columns.tolist()
        if _missing_required_columns(pd.DataFrame(columns=feature_store_columns), FEATURE_STORE_SENTINEL_COLUMNS):
            needs_rebuild = True
        if _missing_required_columns(pd.DataFrame(columns=feature_store_columns), PROMO_REQUIRED_FEATURE_STORE_COLUMNS):
            needs_rebuild = True
        if _missing_required_columns(pd.DataFrame(columns=feature_store_columns), CONTEXT_REQUIRED_FEATURE_STORE_COLUMNS):
            needs_rebuild = True
        if _missing_required_columns(pd.DataFrame(columns=base_columns), PROMO_RAW_COLUMNS):
            needs_rebuild = True
        if _missing_required_columns(pd.DataFrame(columns=base_columns), CONTEXT_POLICY_COLUMNS):
            needs_rebuild = True
        if _missing_required_columns(pd.DataFrame(columns=base_columns), PRICE_SIGNAL_COLUMNS):
            needs_rebuild = True
    if needs_rebuild:
        build_feature_store()
    feature_store = pd.read_csv(FEATURE_STORE_PATH, parse_dates=["Date"], low_memory=False)
    base = pd.read_csv(BASE_OUT_PATH, parse_dates=["Date"], low_memory=False)
    return feature_store, base


def get_candidate_feature_sets(feature_store: pd.DataFrame) -> dict[str, list[str]]:
    groups, experiments = build_experiments(feature_store)
    _ = groups
    return experiments


def apply_future_promo_policy(
    base: pd.DataFrame,
    cutoff_date: pd.Timestamp,
    policy_name: str = "zero",
) -> pd.DataFrame:
    if policy_name not in PROMO_FUTURE_POLICIES:
        raise ValueError(f"Unknown promo future policy: {policy_name}")

    adjusted = base.copy()
    for col in PROMO_POLICY_COLUMNS:
        if col not in adjusted.columns:
            adjusted[col] = 0.0
    future_mask = adjusted["Date"] > cutoff_date
    if not future_mask.any():
        return add_promo_target_encoding_features(adjusted, freeze_after=cutoff_date)

    spec = PROMO_FUTURE_POLICIES[policy_name]
    if spec["mode"] == "zero":
        adjusted.loc[future_mask, PROMO_POLICY_COLUMNS] = 0.0
        return add_promo_target_encoding_features(adjusted, freeze_after=cutoff_date)

    history = adjusted.loc[~future_mask, ["Date"] + PROMO_POLICY_COLUMNS].copy()
    if spec["mode"] in {"seasonal_month_day", "seasonal_by_keys"}:
        recent_years = spec.get("recent_years")
        if recent_years is not None:
            min_date = cutoff_date - pd.DateOffset(years=recent_years)
            recent_history = history.loc[history["Date"] > min_date].copy()
            if not recent_history.empty:
                history = recent_history

        history["month"] = history["Date"].dt.month
        history["day"] = history["Date"].dt.day
        history["dayofweek"] = history["Date"].dt.dayofweek
        date_keys = spec.get("date_keys", ["month", "day"])
        agg_name = spec.get("agg", "mean")
        grouped_history = history.groupby(date_keys)[PROMO_POLICY_COLUMNS]
        if agg_name == "median":
            month_day_priors = grouped_history.median().reset_index()
        else:
            month_day_priors = grouped_history.mean().reset_index()
        overall_prior = history[PROMO_POLICY_COLUMNS].mean().fillna(0.0)

        future = adjusted.loc[future_mask, ["Date"]].copy()
        future["month"] = future["Date"].dt.month
        future["day"] = future["Date"].dt.day
        future["dayofweek"] = future["Date"].dt.dayofweek
        future = future.merge(month_day_priors, on=date_keys, how="left")

        for col in PROMO_POLICY_COLUMNS:
            future[col] = future[col].fillna(float(overall_prior[col]))

        adjusted.loc[future_mask, PROMO_POLICY_COLUMNS] = future[PROMO_POLICY_COLUMNS].to_numpy()
        return add_promo_target_encoding_features(adjusted, freeze_after=cutoff_date)

    raise ValueError(f"Unsupported promo future policy mode: {spec['mode']}")


def zero_unknown_promo_signals(base: pd.DataFrame, cutoff_date: pd.Timestamp) -> pd.DataFrame:
    adjusted = apply_future_promo_policy(base, cutoff_date, policy_name="zero")
    return adjusted


def apply_future_context_policy(
    base: pd.DataFrame,
    cutoff_date: pd.Timestamp,
    policy_name: str = "zero",
) -> pd.DataFrame:
    if policy_name not in CONTEXT_FUTURE_POLICIES:
        raise ValueError(f"Unknown context future policy: {policy_name}")

    adjusted = base.copy()
    for col in CONTEXT_POLICY_COLUMNS:
        if col not in adjusted.columns:
            adjusted[col] = 0.0
    future_mask = adjusted["Date"] > cutoff_date
    if not future_mask.any():
        return adjusted

    spec = CONTEXT_FUTURE_POLICIES[policy_name]
    if spec["mode"] == "zero":
        adjusted.loc[future_mask, CONTEXT_POLICY_COLUMNS] = 0.0
        return adjusted

    history = adjusted.loc[~future_mask, ["Date"] + CONTEXT_POLICY_COLUMNS].copy()
    if spec["mode"] in {"seasonal_month_day", "seasonal_by_keys"}:
        recent_years = spec.get("recent_years")
        if recent_years is not None:
            min_date = cutoff_date - pd.DateOffset(years=recent_years)
            recent_history = history.loc[history["Date"] > min_date].copy()
            if not recent_history.empty:
                history = recent_history

        history["month"] = history["Date"].dt.month
        history["day"] = history["Date"].dt.day
        history["dayofweek"] = history["Date"].dt.dayofweek
        date_keys = spec.get("date_keys", ["month", "day"])
        agg_name = spec.get("agg", "mean")
        grouped_history = history.groupby(date_keys)[CONTEXT_POLICY_COLUMNS]
        if agg_name == "median":
            priors = grouped_history.median().reset_index()
        else:
            priors = grouped_history.mean().reset_index()
        overall_prior = history[CONTEXT_POLICY_COLUMNS].mean().fillna(0.0)

        future = adjusted.loc[future_mask, ["Date"]].copy()
        future["month"] = future["Date"].dt.month
        future["day"] = future["Date"].dt.day
        future["dayofweek"] = future["Date"].dt.dayofweek
        future = future.merge(priors, on=date_keys, how="left")

        for col in CONTEXT_POLICY_COLUMNS:
            future[col] = future[col].fillna(float(overall_prior[col]))

        adjusted.loc[future_mask, CONTEXT_POLICY_COLUMNS] = future[CONTEXT_POLICY_COLUMNS].to_numpy()
        return adjusted

    raise ValueError(f"Unsupported context future policy mode: {spec['mode']}")


def apply_future_price_policy(
    base: pd.DataFrame,
    cutoff_date: pd.Timestamp,
    policy_name: str = "zero",
) -> pd.DataFrame:
    if policy_name not in PRICE_FUTURE_POLICIES:
        raise ValueError(f"Unknown price future policy: {policy_name}")

    adjusted = base.copy()
    for col in PRICE_SIGNAL_COLUMNS:
        if col not in adjusted.columns:
            adjusted[col] = 0.0
    future_mask = adjusted["Date"] > cutoff_date
    if not future_mask.any():
        return adjusted

    spec = PRICE_FUTURE_POLICIES[policy_name]
    if spec["mode"] == "zero":
        adjusted.loc[future_mask, PRICE_SIGNAL_COLUMNS] = 0.0
        return adjusted

    history = adjusted.loc[~future_mask, ["Date"] + PRICE_SIGNAL_COLUMNS].copy()
    if spec["mode"] in {"seasonal_month_day", "seasonal_by_keys"}:
        recent_years = spec.get("recent_years")
        if recent_years is not None:
            min_date = cutoff_date - pd.DateOffset(years=recent_years)
            recent_history = history.loc[history["Date"] > min_date].copy()
            if not recent_history.empty:
                history = recent_history

        history["month"] = history["Date"].dt.month
        history["day"] = history["Date"].dt.day
        history["dayofweek"] = history["Date"].dt.dayofweek
        date_keys = spec.get("date_keys", ["month", "day"])
        agg_name = spec.get("agg", "mean")
        grouped_history = history.groupby(date_keys)[PRICE_SIGNAL_COLUMNS]
        if agg_name == "median":
            priors = grouped_history.median().reset_index()
        else:
            priors = grouped_history.mean().reset_index()
        overall_prior = history[PRICE_SIGNAL_COLUMNS].mean().fillna(0.0)

        future = adjusted.loc[future_mask, ["Date"]].copy()
        future["month"] = future["Date"].dt.month
        future["day"] = future["Date"].dt.day
        future["dayofweek"] = future["Date"].dt.dayofweek
        future = future.merge(priors, on=date_keys, how="left")

        for col in PRICE_SIGNAL_COLUMNS:
            future[col] = future[col].fillna(float(overall_prior[col]))

        adjusted.loc[future_mask, PRICE_SIGNAL_COLUMNS] = future[PRICE_SIGNAL_COLUMNS].to_numpy()
        return adjusted

    raise ValueError(f"Unsupported price future policy mode: {spec['mode']}")


def apply_future_hierarchy_policy(
    base: pd.DataFrame,
    cutoff_date: pd.Timestamp,
    policy_name: str = "zero",
) -> pd.DataFrame:
    if policy_name not in HIERARCHY_FUTURE_POLICIES:
        raise ValueError(f"Unknown hierarchy future policy: {policy_name}")

    adjusted = base.copy()
    hierarchy_columns = get_hierarchy_lite_raw_columns(adjusted.columns)
    if not hierarchy_columns:
        return adjusted

    future_mask = adjusted["Date"] > cutoff_date
    if not future_mask.any():
        return adjusted

    spec = HIERARCHY_FUTURE_POLICIES[policy_name]
    if spec["mode"] == "zero":
        adjusted.loc[future_mask, hierarchy_columns] = 0.0
        return adjusted

    history = adjusted.loc[~future_mask, ["Date"] + hierarchy_columns].copy()
    if spec["mode"] in {"seasonal_month_day", "seasonal_by_keys"}:
        recent_years = spec.get("recent_years")
        if recent_years is not None:
            min_date = cutoff_date - pd.DateOffset(years=recent_years)
            recent_history = history.loc[history["Date"] > min_date].copy()
            if not recent_history.empty:
                history = recent_history

        history["month"] = history["Date"].dt.month
        history["day"] = history["Date"].dt.day
        history["dayofweek"] = history["Date"].dt.dayofweek
        date_keys = spec.get("date_keys", ["month", "day"])
        agg_name = spec.get("agg", "mean")
        grouped_history = history.groupby(date_keys)[hierarchy_columns]
        if agg_name == "median":
            priors = grouped_history.median().reset_index()
        else:
            priors = grouped_history.mean().reset_index()
        overall_prior = history[hierarchy_columns].mean().fillna(0.0)

        future = adjusted.loc[future_mask, ["Date"]].copy()
        future["month"] = future["Date"].dt.month
        future["day"] = future["Date"].dt.day
        future["dayofweek"] = future["Date"].dt.dayofweek
        future = future.merge(priors, on=date_keys, how="left")

        for col in hierarchy_columns:
            future[col] = future[col].fillna(float(overall_prior[col]))

        adjusted.loc[future_mask, hierarchy_columns] = future[hierarchy_columns].to_numpy()
        return adjusted

    raise ValueError(f"Unsupported hierarchy future policy mode: {spec['mode']}")


def _compute_ratio_stats(train_df: pd.DataFrame) -> dict[str, float]:
    ratio = _compute_cogs_ratio_series(train_df).dropna()
    return {
        "median": float(ratio.median()),
        "q05": float(ratio.quantile(0.05)),
        "q10": float(ratio.quantile(0.10)),
        "q20": float(ratio.quantile(0.20)),
        "q80": float(ratio.quantile(0.80)),
        "q90": float(ratio.quantile(0.90)),
        "q95": float(ratio.quantile(0.95)),
        "q99": float(ratio.quantile(0.99)),
        "q995": float(ratio.quantile(0.995)),
    }


def _trailing_ratio(history: pd.DataFrame, fallback: float, window: int = 28) -> float:
    recent = history.tail(window).copy()
    ratio = _compute_cogs_ratio_series(recent).dropna()
    if ratio.empty:
        return fallback
    return float(ratio.mean())


def _compute_ratio_bucket_table(train_df: pd.DataFrame) -> pd.DataFrame:
    ratio_df = train_df[["Date"]].copy()
    ratio_df["ratio"] = _compute_cogs_ratio_series(train_df)
    ratio_df = ratio_df.dropna(subset=["ratio"]).copy()
    ratio_df["month"] = ratio_df["Date"].dt.month
    ratio_df["dayofweek"] = ratio_df["Date"].dt.dayofweek
    bucket_table = (
        ratio_df.groupby(["month", "dayofweek"])["ratio"]
        .agg(
            median="median",
            q05=lambda s: s.quantile(0.05),
            q10=lambda s: s.quantile(0.10),
            q20=lambda s: s.quantile(0.20),
            q80=lambda s: s.quantile(0.80),
            q90=lambda s: s.quantile(0.90),
            q95=lambda s: s.quantile(0.95),
        )
        .sort_index()
    )
    return bucket_table


def _lookup_ratio_bucket_stats(
    current_date: pd.Timestamp,
    ratio_bucket_table: pd.DataFrame,
    ratio_stats: dict[str, float],
) -> dict[str, float]:
    key = (current_date.month, current_date.dayofweek)
    if key in ratio_bucket_table.index:
        row = ratio_bucket_table.loc[key]
        return {name: float(row[name]) for name in row.index}
    return {
        "median": ratio_stats["median"],
        "q05": ratio_stats["q05"],
        "q10": ratio_stats["q10"],
        "q20": ratio_stats["q20"],
        "q80": ratio_stats["q80"],
        "q90": ratio_stats["q90"],
        "q95": ratio_stats["q95"],
    }


def _interpolate_scalar(start_value: float, end_value: float, progress: float) -> float:
    return float(start_value + progress * (end_value - start_value))


def _soft_clip(value: float, lower: float, upper: float, beta: float) -> float:
    if value < lower:
        return float(lower + beta * (value - lower))
    if value > upper:
        return float(upper + beta * (value - upper))
    return float(value)


def _apply_cogs_postprocess(
    variant_name: str,
    pred_revenue: float,
    pred_cogs_signal: float,
    hist_ratio: float,
    ratio_stats: dict[str, float],
    ratio_bucket_table: pd.DataFrame,
    current_date: pd.Timestamp,
    cogs_target_mode: str = "direct",
    horizon_index: int = 0,
    horizon_size: int = 1,
) -> float:
    revenue = max(pred_revenue, 0.0)
    if revenue <= 0:
        return 0.0
    if cogs_target_mode not in COGS_TARGET_MODES:
        raise ValueError(f"Unknown COGS target mode: {cogs_target_mode}")

    if cogs_target_mode == "ratio":
        raw_ratio = float(max(pred_cogs_signal, 0.0))
    else:
        raw_cogs = max(pred_cogs_signal, 0.0)
        raw_ratio = raw_cogs / revenue if revenue > 0 else ratio_stats["median"]
    spec = COGS_POSTPROCESS_VARIANTS[variant_name]
    mode = spec["mode"]
    corrected_ratio = raw_ratio

    if mode == "blend_clip":
        blended = spec["raw_weight"] * raw_ratio + (1.0 - spec["raw_weight"]) * hist_ratio
        upper_quantile_key = spec.get("upper_quantile_key", "q99")
        corrected_ratio = min(blended, ratio_stats[upper_quantile_key])
    elif mode == "ratio_bucket_shrink":
        progress = 0.0 if horizon_size <= 1 else float(horizon_index / (horizon_size - 1))
        bucket_stats = _lookup_ratio_bucket_stats(current_date, ratio_bucket_table, ratio_stats)
        anchor_ratio = spec["hist_anchor_weight"] * hist_ratio + (1.0 - spec["hist_anchor_weight"]) * bucket_stats["median"]
        raw_weight = _interpolate_scalar(spec["near_raw_weight"], spec["far_raw_weight"], progress)
        blended_ratio = raw_weight * raw_ratio + (1.0 - raw_weight) * anchor_ratio
        lower_band = _interpolate_scalar(bucket_stats[spec["near_lower_key"]], bucket_stats[spec["far_lower_key"]], progress)
        upper_band = _interpolate_scalar(bucket_stats[spec["near_upper_key"]], bucket_stats[spec["far_upper_key"]], progress)
        corrected_ratio = _soft_clip(
            blended_ratio,
            lower=lower_band,
            upper=upper_band,
            beta=float(spec.get("soft_clip_beta", 0.0)),
        )

    clamp_epsilon = float(spec.get("clamp_epsilon", 0.005))
    corrected_ratio = max(corrected_ratio, 0.0)
    corrected_ratio = min(corrected_ratio, min(ratio_stats.get("q995", 1.0 - clamp_epsilon), 1.0 - clamp_epsilon))
    return min(revenue * corrected_ratio, revenue * (1.0 - clamp_epsilon))


def _apply_revenue_regime_variant(
    variant_name: str,
    pred_revenue_primary: float,
    pred_revenue_fallback: float | None,
    promo_row: pd.Series,
) -> float:
    if pred_revenue_fallback is None:
        return pred_revenue_primary
    if variant_name not in REVENUE_REGIME_VARIANTS:
        raise ValueError(f"Unknown revenue regime variant: {variant_name}")

    spec = REVENUE_REGIME_VARIANTS[variant_name]
    if spec["mode"] == "primary":
        return pred_revenue_primary

    if spec["mode"] == "threshold_switch":
        promo_line_share = float(promo_row.get("promo_line_share", 0.0) or 0.0)
        active_promo_count = float(promo_row.get("active_promo_count", 0.0) or 0.0)
        avg_discount_rate = float(promo_row.get("avg_discount_rate", 0.0) or 0.0)
        is_promo_heavy = (
            promo_line_share >= spec["min_promo_line_share"]
            or active_promo_count >= spec["min_active_promo_count"]
            or avg_discount_rate >= spec["min_avg_discount_rate"]
        )
        return pred_revenue_fallback if is_promo_heavy else pred_revenue_primary

    raise ValueError(f"Unsupported revenue regime mode: {spec['mode']}")


def _calendar_features_for_date(date: pd.Timestamp) -> dict[str, float]:
    iso = date.isocalendar()
    dayofweek = date.dayofweek
    month = date.month
    dayofyear = date.dayofyear
    
    lunar_day, lunar_month, lunar_year, lunar_is_leap_month, julian_day = solar_to_lunar(date)
    tet_date = tet_date_for_solar_year(date.year)
    days_from_tet = (date - tet_date).days
    
    return {
        "year": date.year,
        "month": month,
        "day": date.day,
        "dayofweek": dayofweek,
        "weekofyear": int(iso.week),
        "quarter": date.quarter,
        "dayofyear": dayofyear,
        "is_weekend": int(dayofweek in [5, 6]),
        "is_month_start": int(date.is_month_start),
        "is_month_end": int(date.is_month_end),
        "is_quarter_start": int(date.is_quarter_start),
        "is_quarter_end": int(date.is_quarter_end),
        "sin_dayofyear": float(np.sin(2 * np.pi * dayofyear / 365.25)),
        "cos_dayofyear": float(np.cos(2 * np.pi * dayofyear / 365.25)),
        "sin_dayofyear_k2": float(np.sin(4 * np.pi * dayofyear / 365.25)),
        "cos_dayofyear_k2": float(np.cos(4 * np.pi * dayofyear / 365.25)),
        "sin_dayofyear_k3": float(np.sin(6 * np.pi * dayofyear / 365.25)),
        "cos_dayofyear_k3": float(np.cos(6 * np.pi * dayofyear / 365.25)),
        "sin_dayofweek": float(np.sin(2 * np.pi * dayofweek / 7.0)),
        "cos_dayofweek": float(np.cos(2 * np.pi * dayofweek / 7.0)),
        "sin_month": float(np.sin(2 * np.pi * month / 12.0)),
        "cos_month": float(np.cos(2 * np.pi * month / 12.0)),
        "days_to_eom": float(date.days_in_month - date.day),
        "days_from_bom": float(date.day - 1),
        "is_tet_month": int(month in [1, 2]),
        "month_weekday_interact": float(month * 10 + dayofweek),
        "lunar_month": float(lunar_month),
        "lunar_day": float(lunar_day),
        "lunar_month_sin": float(np.sin(2 * np.pi * lunar_month / 12.0)),
        "lunar_month_cos": float(np.cos(2 * np.pi * lunar_month / 12.0)),
        "lunar_day_sin": float(np.sin(2 * np.pi * lunar_day / 30.0)),
        "lunar_day_cos": float(np.cos(2 * np.pi * lunar_day / 30.0)),
        "is_lunar_new_year": int(lunar_month == 1 and lunar_day == 1),
        "days_from_tet": float(days_from_tet),
        "days_to_tet": float(-days_from_tet),
        "win_tet_pre14_1": int(-14 <= days_from_tet <= -1),
        "win_tet_pre7_1": int(-7 <= days_from_tet <= -1),
        "win_tet_0_3": int(0 <= days_from_tet <= 3),
        "win_tet_0_6": int(0 <= days_from_tet <= 6),
        "win_tet_post4_14": int(4 <= days_from_tet <= 14),
        "win_tet_post15_35": int(15 <= days_from_tet <= 35),
        "win_tet_wide": int(-14 <= days_from_tet <= 35),
        "lunar_year": float(lunar_year),
        "lunar_is_leap_month": int(lunar_is_leap_month),
        "julian_day": float(julian_day),
    }


def _past_series(series: pd.Series, current_date: pd.Timestamp) -> pd.Series:
    cutoff = current_date - pd.Timedelta(days=1)
    return series.loc[:cutoff]


def _seasonal_target_prior(
    past: pd.Series,
    current_date: pd.Timestamp,
    date_keys: tuple[str, ...],
    recent_days: int = 730,
) -> float:
    if past.empty:
        return np.nan

    recent = past.loc[past.index > (current_date - pd.Timedelta(days=recent_days))]
    if recent.empty:
        return np.nan

    mask = pd.Series(True, index=recent.index)
    if "month" in date_keys:
        mask &= recent.index.month == current_date.month
    if "day" in date_keys:
        mask &= recent.index.day == current_date.day
    if "dayofweek" in date_keys:
        mask &= recent.index.dayofweek == current_date.dayofweek

    matched = recent.loc[mask]
    if matched.empty:
        return np.nan
    return float(matched.mean())


def _add_target_history(
    feature_values: dict[str, float],
    history: pd.DataFrame,
    current_date: pd.Timestamp,
    target_col: str,
    prefix: str,
) -> None:
    series = history[target_col]
    past = _past_series(series, current_date)
    plus_prefix = f"{prefix}plus"
    zero_indicator = past.eq(0).where(past.notna(), np.nan)

    for lag in TARGET_LAG_PERIODS:
        past_date = current_date - pd.Timedelta(days=lag)
        feature_values[f"{prefix}_lag_{lag}"] = float(series.get(past_date, np.nan))

    for window in TARGET_ROLL_WINDOWS:
        window_values = past.tail(window)
        feature_values[f"{prefix}_rollmean_{window}"] = float(window_values.mean()) if len(window_values) else np.nan
        feature_values[f"{prefix}_rollstd_{window}"] = float(window_values.std()) if len(window_values) else np.nan
        feature_values[f"{prefix}_rollmin_{window}"] = float(window_values.min()) if len(window_values) else np.nan
        feature_values[f"{prefix}_rollmax_{window}"] = float(window_values.max()) if len(window_values) else np.nan
        feature_values[f"{prefix}_ewm_{window}"] = (
            float(past.ewm(span=window, adjust=False).mean().iloc[-1]) if len(past) else np.nan
        )
        feature_values[f"{plus_prefix}_rollmedian_{window}"] = (
            float(window_values.median()) if len(window_values) else np.nan
        )
        feature_values[f"{plus_prefix}_zero_share_{window}"] = (
            float(zero_indicator.tail(window).mean()) if len(zero_indicator) else np.nan
        )

    feature_values[f"{prefix}_mom_1_7"] = feature_values.get(f"{prefix}_lag_1", np.nan) - feature_values.get(
        f"{prefix}_lag_7", np.nan
    )
    feature_values[f"{prefix}_mom_7_28"] = feature_values.get(f"{prefix}_lag_7", np.nan) - feature_values.get(
        f"{prefix}_lag_28", np.nan
    )
    feature_values[f"{prefix}_mom_28_364"] = feature_values.get(f"{prefix}_lag_28", np.nan) - feature_values.get(
        f"{prefix}_lag_364", np.nan
    )

    rollmean_7 = feature_values.get(f"{prefix}_rollmean_7", np.nan)
    rollmean_28 = feature_values.get(f"{prefix}_rollmean_28", np.nan)
    lag_364 = feature_values.get(f"{prefix}_lag_364", np.nan)
    feature_values[f"{prefix}_ratio_1_7"] = (
        feature_values.get(f"{prefix}_lag_1", np.nan) / rollmean_7 if pd.notna(rollmean_7) and rollmean_7 != 0 else np.nan
    )
    feature_values[f"{prefix}_ratio_7_28"] = (
        feature_values.get(f"{prefix}_lag_7", np.nan) / rollmean_28
        if pd.notna(rollmean_28) and rollmean_28 != 0
        else np.nan
    )
    feature_values[f"{prefix}_yoy_ratio"] = (
        feature_values.get(f"{prefix}_lag_7", np.nan) / lag_364 if pd.notna(lag_364) and lag_364 != 0 else np.nan
    )

    seasonal_prefix = "target_seasonal_rev" if prefix == "rev" else "target_seasonal_cogs"
    feature_values[f"{seasonal_prefix}_md_mean_recent_2y"] = _seasonal_target_prior(
        past=past,
        current_date=current_date,
        date_keys=("month", "day"),
    )
    feature_values[f"{seasonal_prefix}_mwd_mean_recent_2y"] = _seasonal_target_prior(
        past=past,
        current_date=current_date,
        date_keys=("month", "dayofweek"),
    )


def _add_promo_history(
    feature_values: dict[str, float],
    promo_indexed: pd.DataFrame,
    current_date: pd.Timestamp,
) -> None:
    promo_row = promo_indexed.reindex([current_date]).iloc[0]
    for col in PROMO_RAW_COLUMNS:
        current_value = promo_row.get(col, np.nan)
        feature_values[col] = float(current_value) if pd.notna(current_value) else np.nan
        series = promo_indexed[col]
        past = _past_series(series, current_date)
        for lag in PROMO_LAG_WINDOWS:
            past_date = current_date - pd.Timedelta(days=lag)
            feature_values[f"{col}_lag_{lag}"] = float(series.get(past_date, np.nan))
        for window in PROMO_ROLL_WINDOWS:
            window_values = past.tail(window)
            feature_values[f"{col}_rollmean_{window}"] = float(window_values.mean()) if len(window_values) else np.nan
            feature_values[f"{col}_rollstd_{window}"] = float(window_values.std()) if len(window_values) else np.nan


def _add_context_history(
    feature_values: dict[str, float],
    context_indexed: pd.DataFrame,
    current_date: pd.Timestamp,
) -> None:
    context_row = context_indexed.reindex([current_date]).iloc[0]
    for col in CONTEXT_POLICY_COLUMNS:
        current_value = context_row.get(col, np.nan)
        feature_values[col] = float(current_value) if pd.notna(current_value) else np.nan
        series = context_indexed[col]
        past = _past_series(series, current_date)
        for lag in CONTEXT_LAG_WINDOWS:
            past_date = current_date - pd.Timedelta(days=lag)
            feature_values[f"{col}_lag_{lag}"] = float(series.get(past_date, np.nan))
        for window in CONTEXT_ROLL_WINDOWS:
            window_values = past.tail(window)
            feature_values[f"{col}_rollmean_{window}"] = float(window_values.mean()) if len(window_values) else np.nan
            feature_values[f"{col}_rollstd_{window}"] = float(window_values.std()) if len(window_values) else np.nan


def _add_hierarchy_history(
    feature_values: dict[str, float],
    hierarchy_indexed: pd.DataFrame,
    current_date: pd.Timestamp,
) -> None:
    hierarchy_row = hierarchy_indexed.reindex([current_date]).iloc[0]
    for col in hierarchy_indexed.columns.tolist():
        current_value = hierarchy_row.get(col, np.nan)
        feature_values[col] = float(current_value) if pd.notna(current_value) else np.nan
        series = hierarchy_indexed[col]
        past = _past_series(series, current_date)
        for lag in CONTEXT_LAG_WINDOWS:
            past_date = current_date - pd.Timedelta(days=lag)
            feature_values[f"{col}_lag_{lag}"] = float(series.get(past_date, np.nan))
        for window in CONTEXT_ROLL_WINDOWS:
            window_values = past.tail(window)
            feature_values[f"{col}_rollmean_{window}"] = float(window_values.mean()) if len(window_values) else np.nan
            feature_values[f"{col}_rollstd_{window}"] = float(window_values.std()) if len(window_values) else np.nan


def _add_price_history(
    feature_values: dict[str, float],
    price_indexed: pd.DataFrame,
    current_date: pd.Timestamp,
) -> None:
    price_stats: dict[str, float] = {}
    for col in PRICE_SIGNAL_COLUMNS:
        series = price_indexed[col]
        past = _past_series(series, current_date)
        for lag in PRICE_LAG_WINDOWS:
            past_date = current_date - pd.Timedelta(days=lag)
            price_stats[f"{col}_lag_{lag}"] = float(series.get(past_date, np.nan))
        for window in PRICE_ROLL_WINDOWS:
            window_values = past.tail(window)
            price_stats[f"{col}_rollmean_{window}"] = float(window_values.mean()) if len(window_values) else np.nan

    unit_rollmean_7 = price_stats.get("avg_unit_price_rollmean_7", np.nan)
    unit_rollmean_28 = price_stats.get("avg_unit_price_rollmean_28", np.nan)
    margin_rollmean_28 = price_stats.get("margin_rate_rollmean_28", np.nan)
    unit_lag_1 = price_stats.get("avg_unit_price_lag_1", np.nan)
    unit_lag_7 = price_stats.get("avg_unit_price_lag_7", np.nan)
    margin_lag_1 = price_stats.get("margin_rate_lag_1", np.nan)
    avg_discount_rollmean_7 = feature_values.get("avg_discount_rate_rollmean_7", np.nan)

    feature_values["pricehist_avg_unit_price_ratio_1_7"] = (
        unit_lag_1 / unit_rollmean_7 if pd.notna(unit_rollmean_7) and unit_rollmean_7 != 0 else np.nan
    )
    feature_values["pricehist_avg_unit_price_ratio_7_28"] = (
        unit_lag_7 / unit_rollmean_28 if pd.notna(unit_rollmean_28) and unit_rollmean_28 != 0 else np.nan
    )
    feature_values["pricehist_avg_unit_price_mom_1_7"] = (
        unit_lag_1 - unit_lag_7 if pd.notna(unit_lag_1) and pd.notna(unit_lag_7) else np.nan
    )
    feature_values["pricehist_margin_rate_ratio_1_28"] = (
        margin_lag_1 / margin_rollmean_28
        if pd.notna(margin_rollmean_28) and margin_rollmean_28 != 0
        else np.nan
    )
    price_ratio_1_7 = feature_values.get("pricehist_avg_unit_price_ratio_1_7", np.nan)
    feature_values["pricehist_discount_x_price_ratio_1_7"] = (
        avg_discount_rollmean_7 * price_ratio_1_7
        if pd.notna(avg_discount_rollmean_7) and pd.notna(price_ratio_1_7)
        else np.nan
    )


def build_feature_row(
    current_date: pd.Timestamp,
    history: pd.DataFrame,
    promo_indexed: pd.DataFrame,
    context_indexed_or_required_features: pd.DataFrame | list[str] | None,
    required_features: list[str] | None = None,
    hierarchy_indexed: pd.DataFrame | None = None,
    price_indexed: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if required_features is None:
        context_indexed = None
        resolved_required_features = list(context_indexed_or_required_features or [])
    else:
        context_indexed = context_indexed_or_required_features
        resolved_required_features = required_features

    feature_values: dict[str, float] = {}
    feature_values.update(_calendar_features_for_date(current_date))
    _add_target_history(feature_values, history, current_date, target_col="Revenue", prefix="rev")
    _add_target_history(feature_values, history, current_date, target_col="COGS", prefix="cogs")
    _add_promo_history(feature_values, promo_indexed, current_date)
    if isinstance(context_indexed, pd.DataFrame) and not context_indexed.empty:
        _add_context_history(feature_values, context_indexed, current_date)
    if isinstance(hierarchy_indexed, pd.DataFrame) and not hierarchy_indexed.empty:
        _add_hierarchy_history(feature_values, hierarchy_indexed, current_date)
    if isinstance(price_indexed, pd.DataFrame) and not price_indexed.empty:
        _add_price_history(feature_values, price_indexed, current_date)
    row = pd.DataFrame(
        [{feature: feature_values.get(feature, np.nan) for feature in resolved_required_features}]
    )
    return row


def recursive_forecast(
    feature_store: pd.DataFrame,
    full_base: pd.DataFrame,
    train_end_date: pd.Timestamp,
    forecast_start: pd.Timestamp,
    forecast_end: pd.Timestamp,
    revenue_features: list[str],
    cogs_features: list[str],
    cogs_postprocess_variant: str = "raw",
    secondary_revenue_features: list[str] | None = None,
    revenue_regime_variant: str = "none",
    model_family: str = "xgb",
    train_window_days: int | None = None,
    model_params_override: dict[str, float | int | bool] | None = None,
    revenue_target_transform: str = "none",
    cogs_target_transform: str = "none",
    cogs_target_mode: str = "direct",
    sample_weight_mode: str = "none",
    sample_weight_decay: float = 0.0,
) -> pd.DataFrame:
    train_mask = feature_store["Date"] <= train_end_date
    if train_window_days is not None:
        train_start_date = train_end_date - pd.Timedelta(days=int(train_window_days) - 1)
        train_mask &= feature_store["Date"] >= train_start_date
    forecast_mask = (full_base["Date"] >= forecast_start) & (full_base["Date"] <= forecast_end)

    train_df = feature_store.loc[train_mask].copy()
    promo_indexed = full_base[["Date"] + PROMO_RAW_COLUMNS].copy().set_index("Date")
    context_indexed = full_base[["Date"] + CONTEXT_POLICY_COLUMNS].copy().set_index("Date")
    price_indexed = full_base[["Date"] + PRICE_SIGNAL_COLUMNS].copy().set_index("Date")
    hierarchy_columns = get_hierarchy_lite_raw_columns(full_base.columns)
    hierarchy_indexed = (
        full_base[["Date"] + hierarchy_columns].copy().set_index("Date") if hierarchy_columns else None
    )

    if cogs_target_mode not in COGS_TARGET_MODES:
        raise ValueError(f"Unknown COGS target mode: {cogs_target_mode}")

    ratio_stats = _compute_ratio_stats(train_df)
    ratio_bucket_table = _compute_ratio_bucket_table(train_df)
    sample_weights = build_sample_weights(
        train_df["Date"],
        train_end_date=train_end_date,
        sample_weight_mode=sample_weight_mode,
        sample_weight_decay=sample_weight_decay,
    )
    revenue_model = make_regressor(model_family, model_params_override=model_params_override)
    fallback_revenue_model = None
    cogs_model = make_regressor(model_family, model_params_override=model_params_override)

    fit_regressor(
        revenue_model,
        train_df[revenue_features],
        _transform_target_series(train_df["Revenue"], revenue_target_transform),
        model_family,
        sample_weight=sample_weights,
    )
    if secondary_revenue_features is not None:
        fallback_revenue_model = make_regressor(model_family, model_params_override=model_params_override)
        fit_regressor(
            fallback_revenue_model,
            train_df[secondary_revenue_features],
            _transform_target_series(train_df["Revenue"], revenue_target_transform),
            model_family,
            sample_weight=sample_weights,
        )
    if cogs_target_mode == "ratio":
        cogs_target = _compute_cogs_ratio_series(train_df).fillna(ratio_stats["median"]).clip(lower=0.0)
    else:
        cogs_target = train_df["COGS"].astype(float)
    fit_regressor(
        cogs_model,
        train_df[cogs_features],
        _transform_target_series(cogs_target, cogs_target_transform),
        model_family,
        sample_weight=sample_weights,
    )

    history = train_df[["Date", "Revenue", "COGS"]].copy().set_index("Date").sort_index()
    results: list[dict[str, float | str]] = []
    forecast_dates = full_base.loc[forecast_mask, "Date"].tolist()

    for horizon_index, current_date in enumerate(forecast_dates):
        promo_row = promo_indexed.loc[current_date]
        revenue_row = build_feature_row(
            current_date,
            history,
            promo_indexed,
            context_indexed,
            revenue_features,
            hierarchy_indexed=hierarchy_indexed,
            price_indexed=price_indexed,
        )
        cogs_row = build_feature_row(
            current_date,
            history,
            promo_indexed,
            context_indexed,
            cogs_features,
            hierarchy_indexed=hierarchy_indexed,
            price_indexed=price_indexed,
        )

        pred_revenue_primary = _inverse_transform_scalar(
            float(revenue_model.predict(revenue_row)[0]),
            revenue_target_transform,
        )
        pred_revenue_fallback: float | None = None
        if fallback_revenue_model is not None and secondary_revenue_features is not None:
            fallback_revenue_row = build_feature_row(
                current_date,
                history,
                promo_indexed,
                context_indexed,
                secondary_revenue_features,
                hierarchy_indexed=hierarchy_indexed,
                price_indexed=price_indexed,
            )
            pred_revenue_fallback = _inverse_transform_scalar(
                float(fallback_revenue_model.predict(fallback_revenue_row)[0]),
                revenue_target_transform,
            )
        pred_revenue = _apply_revenue_regime_variant(
            revenue_regime_variant,
            pred_revenue_primary,
            pred_revenue_fallback,
            promo_row,
        )
        pred_cogs_raw = _inverse_transform_scalar(
            float(cogs_model.predict(cogs_row)[0]),
            cogs_target_transform,
        )

        pred_revenue = max(pred_revenue, 0.0)
        hist_ratio = _trailing_ratio(history, fallback=ratio_stats["median"])
        pred_cogs = _apply_cogs_postprocess(
            cogs_postprocess_variant,
            pred_revenue,
            pred_cogs_raw,
            hist_ratio,
            ratio_stats,
            ratio_bucket_table,
            current_date,
            cogs_target_mode=cogs_target_mode,
            horizon_index=horizon_index,
            horizon_size=len(forecast_dates),
        )
        pred_cogs = max(pred_cogs, 0.0)

        history.loc[current_date, ["Revenue", "COGS"]] = [pred_revenue, pred_cogs]
        results.append(
            {
                "Date": current_date,
                "Revenue_pred": pred_revenue,
                "COGS_pred": pred_cogs,
            }
        )

    return pd.DataFrame(results)


def evaluate_system(
    system_name: str,
    feature_store: pd.DataFrame,
    base: pd.DataFrame,
    feature_sets: dict[str, list[str]],
) -> list[dict[str, object]]:
    config = SYSTEMS[system_name]
    revenue_features = feature_sets[config["revenue_experiment"]]
    secondary_revenue_features = (
        feature_sets[config["secondary_revenue_experiment"]]
        if config.get("secondary_revenue_experiment")
        else None
    )
    revenue_regime_variant = config.get("revenue_regime_variant", "none")
    revenue_target_transform = config.get("revenue_target_transform", "none")
    cogs_target_transform = config.get("cogs_target_transform", "none")
    cogs_target_mode = config.get("cogs_target_mode", "direct")
    promo_future_policy = config.get("promo_future_policy", "zero")
    context_future_policy = config.get("context_future_policy", "zero")
    price_future_policy = config.get("price_future_policy", "zero")
    train_window_days = config.get("train_window_days")
    model_params_override = config.get("model_params_override")
    cogs_features = feature_sets[config["cogs_experiment"]]
    cogs_postprocess_variant = config["cogs_postprocess_variant"]
    rows: list[dict[str, object]] = []

    for fold_id, (start_date, end_date) in enumerate(BACKTEST_FOLDS, start=1):
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        cutoff = start_ts - pd.Timedelta(days=1)

        adjusted_base = apply_future_promo_policy(base, cutoff, promo_future_policy)
        adjusted_base = apply_future_context_policy(adjusted_base, cutoff, context_future_policy)
        adjusted_base = apply_future_price_policy(adjusted_base, cutoff, price_future_policy)
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
            train_window_days=train_window_days,
            model_params_override=model_params_override,
            revenue_target_transform=revenue_target_transform,
            cogs_target_transform=cogs_target_transform,
            cogs_target_mode=cogs_target_mode,
        )

        truth = feature_store.loc[
            (feature_store["Date"] >= start_ts) & (feature_store["Date"] <= end_ts),
            ["Date", "Revenue", "COGS"],
        ].copy()
        merged = truth.merge(preds, on="Date", how="left")

        rows.append(
            {
                "system": system_name,
                "fold": fold_id,
                "start_date": start_date,
                "end_date": end_date,
                "revenue_features": config["revenue_experiment"],
                "secondary_revenue_features": config.get("secondary_revenue_experiment"),
                "revenue_regime_variant": revenue_regime_variant,
                "revenue_target_transform": revenue_target_transform,
                "cogs_target_transform": cogs_target_transform,
                "cogs_target_mode": cogs_target_mode,
                "promo_future_policy": promo_future_policy,
                "context_future_policy": context_future_policy,
                "price_future_policy": price_future_policy,
                "cogs_features": config["cogs_experiment"],
                "cogs_postprocess_variant": cogs_postprocess_variant,
                "revenue_mae": mean_absolute_error(merged["Revenue"], merged["Revenue_pred"]),
                "revenue_rmse": np.sqrt(mean_squared_error(merged["Revenue"], merged["Revenue_pred"])),
                "revenue_r2": r2_score(merged["Revenue"], merged["Revenue_pred"]),
                "cogs_mae": mean_absolute_error(merged["COGS"], merged["COGS_pred"]),
                "cogs_rmse": np.sqrt(mean_squared_error(merged["COGS"], merged["COGS_pred"])),
                "cogs_r2": r2_score(merged["COGS"], merged["COGS_pred"]),
            }
        )

    return rows


def save_report(summary: pd.DataFrame, fold_results: pd.DataFrame, winner: str) -> None:
    report_path = OUT_DIR / "final_model_report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Recursive Model Selection\n\n")
        f.write(f"Selected system: `{winner}`\n\n")
        f.write("## Mean Backtest Metrics\n")
        f.write(summary.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Fold Metrics\n")
        f.write(fold_results.to_markdown(index=False))
        f.write("\n")


def fit_final_and_submit(
    winner: str,
    feature_store: pd.DataFrame,
    base: pd.DataFrame,
    feature_sets: dict[str, list[str]],
) -> pd.DataFrame:
    config = SYSTEMS[winner]
    revenue_features = feature_sets[config["revenue_experiment"]]
    secondary_revenue_features = (
        feature_sets[config["secondary_revenue_experiment"]]
        if config.get("secondary_revenue_experiment")
        else None
    )
    revenue_regime_variant = config.get("revenue_regime_variant", "none")
    revenue_target_transform = config.get("revenue_target_transform", "none")
    cogs_target_transform = config.get("cogs_target_transform", "none")
    cogs_target_mode = config.get("cogs_target_mode", "direct")
    promo_future_policy = config.get("promo_future_policy", "zero")
    context_future_policy = config.get("context_future_policy", "zero")
    price_future_policy = config.get("price_future_policy", "zero")
    train_window_days = config.get("train_window_days")
    model_params_override = config.get("model_params_override")
    cogs_features = feature_sets[config["cogs_experiment"]]
    cogs_postprocess_variant = config["cogs_postprocess_variant"]
    adjusted_base = apply_future_promo_policy(base, TRAIN_END, promo_future_policy)
    adjusted_base = apply_future_context_policy(adjusted_base, TRAIN_END, context_future_policy)
    adjusted_base = apply_future_price_policy(adjusted_base, TRAIN_END, price_future_policy)

    preds = recursive_forecast(
        feature_store=feature_store,
        full_base=adjusted_base,
        train_end_date=TRAIN_END,
        forecast_start=pd.Timestamp("2023-01-01"),
        forecast_end=pd.Timestamp("2024-07-01"),
        revenue_features=revenue_features,
        cogs_features=cogs_features,
        cogs_postprocess_variant=cogs_postprocess_variant,
        secondary_revenue_features=secondary_revenue_features,
        revenue_regime_variant=revenue_regime_variant,
        train_window_days=train_window_days,
        model_params_override=model_params_override,
        revenue_target_transform=revenue_target_transform,
        cogs_target_transform=cogs_target_transform,
        cogs_target_mode=cogs_target_mode,
    )
    submission = preds.rename(columns={"Revenue_pred": "Revenue", "COGS_pred": "COGS"})[["Date", "Revenue", "COGS"]]
    submission["Date"] = pd.to_datetime(submission["Date"]).dt.strftime("%Y-%m-%d")
    submission.to_csv(Path("dataset") / "submission.csv", index=False)
    submission.to_csv(OUT_DIR / "submission_final.csv", index=False)
    return submission


def main() -> None:
    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))

    all_rows: list[dict[str, object]] = []
    for system_name in SYSTEMS:
        print(f"Running recursive backtest for {system_name}...")
        all_rows.extend(evaluate_system(system_name, feature_store, base, feature_sets))

    fold_results = pd.DataFrame(all_rows)
    fold_results.to_csv(OUT_DIR / "recursive_backtest_folds.csv", index=False)

    summary = (
        fold_results.groupby("system")
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
    summary.to_csv(OUT_DIR / "recursive_backtest_summary.csv", index=False)

    winner = str(summary.iloc[0]["system"])
    save_report(summary, fold_results, winner)

    submission = fit_final_and_submit(winner, feature_store, base, feature_sets)
    print(f"Selected winner: {winner}")
    print(f"Saved recursive backtest summary to {OUT_DIR / 'recursive_backtest_summary.csv'}")
    print(f"Saved final report to {OUT_DIR / 'final_model_report.md'}")
    print(f"Saved final submission with {len(submission)} rows to dataset/submission.csv")


if __name__ == "__main__":
    main()
