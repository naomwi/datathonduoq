from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from logging_utils import create_run_dir, setup_logger, write_json


RUN_PREFIX = "promo_window_core_v2"
SOURCE_RUN_DIR = Path("logs/20260421_181237_tabpfn_api_optimized_sprint")
DATASET_DIR = Path("dataset")
ANCHOR_PATH = DATASET_DIR / "submission_catboost_md2y_core_recencyexp20.csv"
BEST_PATH = DATASET_DIR / "submission_tabpfn_promo_windowmix_v1.csv"

BASE_TARGETS = {"marapr": 0.08, "junjul": 0.10, "augoct": 0.08, "novjan": 0.06}
WEIGHTED_PROMO_MEAN_TARGET = 0.08


@dataclass(frozen=True)
class WindowSpec:
    name: str
    start_md: str
    end_md: str


WINDOWS = [
    WindowSpec("marapr", "03-18", "04-17"),
    WindowSpec("junjul", "06-23", "07-22"),
    WindowSpec("augoct", "08-30", "10-02"),
    WindowSpec("novjan", "11-18", "01-02"),
]


PROMO_INTENSITY_COLS = [
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
    "active_promo_channel_all_channels_count",
    "active_promo_channel_email_count",
    "active_promo_channel_online_count",
    "active_promo_channel_social_media_count",
    "active_promo_channel_in_store_count",
    "active_promo_category_global_count",
    "active_promo_category_outdoor_count",
    "active_promo_category_streetwear_count",
    "active_promo_discount_value_percentage_mean",
    "active_promo_discount_value_fixed_mean",
    "promo_days_since_start_mean",
    "promo_days_to_end_mean",
    "promo_duration_days_mean",
    "promo_start_count",
    "promo_end_count",
]


ANCHOR_CONTEXT_COLS = [
    "forecast_step",
    "month",
    "day",
    "dayofweek",
    "weekofyear",
    "dayofyear",
    "quarter",
    "is_weekend",
    "is_month_start",
    "is_month_end",
    "sin_dayofyear",
    "cos_dayofyear",
    "sin_dayofweek",
    "cos_dayofweek",
    "anchor_log_revenue",
    "anchor_log_cogs",
    "anchor_cogs_ratio",
    "anchor_margin_ratio",
    "anchor_rev_roll7",
    "anchor_rev_roll28",
    "anchor_rev_ewm28",
    "anchor_cogs_ratio_roll28",
]


def parse_md(md: str) -> tuple[int, int]:
    month, day = md.split("-")
    return int(month), int(day)


def window_bounds_for_date(date: pd.Timestamp, spec: WindowSpec) -> tuple[pd.Timestamp, pd.Timestamp]:
    start_month, start_day = parse_md(spec.start_md)
    end_month, end_day = parse_md(spec.end_md)
    crosses_year = spec.start_md > spec.end_md

    if not crosses_year:
        return (
            pd.Timestamp(year=date.year, month=start_month, day=start_day),
            pd.Timestamp(year=date.year, month=end_month, day=end_day),
        )

    month_day = date.strftime("%m-%d")
    if month_day >= spec.start_md:
        start_year = date.year
        end_year = date.year + 1
    else:
        start_year = date.year - 1
        end_year = date.year
    return (
        pd.Timestamp(year=start_year, month=start_month, day=start_day),
        pd.Timestamp(year=end_year, month=end_month, day=end_day),
    )


def add_window_core_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    dates = pd.to_datetime(out["Date"])
    out["core_window_id"] = "none"
    out["core_window_day"] = np.nan
    out["core_window_len"] = np.nan
    out["core_window_pos"] = np.nan
    out["core_days_to_start"] = np.nan
    out["core_days_to_end"] = np.nan

    for spec in WINDOWS:
        for idx, date in dates.items():
            if out.at[idx, "core_window_id"] != "none":
                continue
            start, end = window_bounds_for_date(pd.Timestamp(date), spec)
            if start <= date <= end:
                day_index = (pd.Timestamp(date) - start).days
                length = (end - start).days + 1
                out.at[idx, "core_window_id"] = spec.name
                out.at[idx, "core_window_day"] = float(day_index)
                out.at[idx, "core_window_len"] = float(length)
                out.at[idx, "core_window_pos"] = float(day_index / max(length - 1, 1))
                out.at[idx, "core_days_to_start"] = float(day_index)
                out.at[idx, "core_days_to_end"] = float((end - pd.Timestamp(date)).days)

    out["core_is_promo_window"] = (out["core_window_id"] != "none").astype(float)
    out["core_window_pos"] = out["core_window_pos"].fillna(0.0)
    out["core_window_day"] = out["core_window_day"].fillna(-1.0)
    out["core_window_len"] = out["core_window_len"].fillna(0.0)
    out["core_days_to_start"] = out["core_days_to_start"].fillna(-1.0)
    out["core_days_to_end"] = out["core_days_to_end"].fillna(-1.0)
    out["core_edge_distance"] = np.minimum(out["core_days_to_start"], out["core_days_to_end"]).clip(lower=0.0)
    out["core_is_first_3"] = ((out["core_is_promo_window"] > 0) & (out["core_days_to_start"] <= 2)).astype(float)
    out["core_is_last_3"] = ((out["core_is_promo_window"] > 0) & (out["core_days_to_end"] <= 2)).astype(float)
    out["core_is_edge_7"] = ((out["core_is_promo_window"] > 0) & (out["core_edge_distance"] <= 6)).astype(float)
    out["core_pos_sin"] = np.sin(2.0 * np.pi * out["core_window_pos"])
    out["core_pos_cos"] = np.cos(2.0 * np.pi * out["core_window_pos"])
    for spec in WINDOWS:
        out[f"core_win_{spec.name}"] = (out["core_window_id"] == spec.name).astype(float)
    return out


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    oof_path = SOURCE_RUN_DIR / "anchor_oof_table.csv"
    public_path = SOURCE_RUN_DIR / "public_feature_frame.csv"
    tabpfn_path = SOURCE_RUN_DIR / "tabpfn_residual_ensemble.csv"
    if not oof_path.exists() or not public_path.exists():
        raise FileNotFoundError(f"Missing source TabPFN sprint frames in {SOURCE_RUN_DIR}")
    oof = pd.read_csv(oof_path, parse_dates=["Date"])
    public = pd.read_csv(public_path, parse_dates=["Date"])
    if tabpfn_path.exists():
        tabpfn = pd.read_csv(tabpfn_path).iloc[:, 0].astype(float)
    else:
        tabpfn = pd.Series(np.zeros(len(public)), index=public.index, dtype=float)
    oof = add_window_core_features(oof)
    public = add_window_core_features(public)
    return oof, public, pd.Series(tabpfn.to_numpy(), index=public.index)


def add_targets(oof: pd.DataFrame) -> pd.DataFrame:
    out = oof.copy()
    revenue_pred = out["Revenue_pred"].astype(float).clip(lower=1.0)
    cogs_pred = out["COGS_pred"].astype(float).clip(lower=1.0)
    revenue_actual = out["Revenue"].astype(float).clip(lower=0.0)
    cogs_actual = out["COGS"].astype(float).clip(lower=0.0)
    out["core_rev_log_resid"] = np.log1p(revenue_actual) - np.log1p(revenue_pred)
    out["core_rev_uplift_target"] = (revenue_actual / revenue_pred - 1.0).clip(-0.50, 0.75)
    actual_ratio = (cogs_actual / revenue_actual.replace(0.0, np.nan)).replace([np.inf, -np.inf], np.nan)
    anchor_ratio = (cogs_pred / revenue_pred).replace([np.inf, -np.inf], np.nan)
    out["core_cogs_ratio_delta"] = (actual_ratio - anchor_ratio).replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(-0.20, 0.20)
    return out


def feature_columns(frame: pd.DataFrame) -> list[str]:
    core_cols = [
        "core_window_day",
        "core_window_len",
        "core_window_pos",
        "core_days_to_start",
        "core_days_to_end",
        "core_edge_distance",
        "core_is_first_3",
        "core_is_last_3",
        "core_is_edge_7",
        "core_pos_sin",
        "core_pos_cos",
        *[f"core_win_{spec.name}" for spec in WINDOWS],
    ]
    cols = core_cols + [col for col in ANCHOR_CONTEXT_COLS + PROMO_INTENSITY_COLS if col in frame.columns]
    return [col for col in cols if col in frame.columns]


def fit_ridge() -> object:
    return make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        RidgeCV(alphas=np.logspace(-3, 3, 13)),
    )


def fit_hgb() -> object:
    return make_pipeline(
        SimpleImputer(strategy="median"),
        HistGradientBoostingRegressor(
            max_iter=250,
            learning_rate=0.035,
            max_leaf_nodes=12,
            min_samples_leaf=12,
            l2_regularization=0.15,
            random_state=42,
        ),
    )


def fit_trees() -> object:
    return make_pipeline(
        SimpleImputer(strategy="median"),
        ExtraTreesRegressor(
            n_estimators=400,
            min_samples_leaf=8,
            max_features=0.75,
            random_state=42,
            n_jobs=-1,
        ),
    )


def smoothed_prior(train: pd.DataFrame, target_col: str) -> tuple[dict[tuple[str, int], float], dict[str, float], float]:
    promo_train = train.loc[train["core_is_promo_window"] > 0].copy()
    global_mean = float(promo_train[target_col].mean()) if not promo_train.empty else 0.0
    window_mean = promo_train.groupby("core_window_id")[target_col].mean().to_dict()
    day_stats = (
        promo_train.groupby(["core_window_id", "core_window_day"])[target_col]
        .agg(["mean", "count"])
        .reset_index()
    )
    lookup: dict[tuple[str, int], float] = {}
    for row in day_stats.itertuples(index=False):
        win = str(row.core_window_id)
        day = int(row.core_window_day)
        n = float(row.count)
        win_mean = float(window_mean.get(win, global_mean))
        day_weight = n / (n + 3.0)
        win_weight = 0.65 * (1.0 - day_weight)
        global_weight = 0.35 * (1.0 - day_weight)
        lookup[(win, day)] = float(day_weight * row.mean + win_weight * win_mean + global_weight * global_mean)
    return lookup, {str(k): float(v) for k, v in window_mean.items()}, global_mean


def predict_prior(frame: pd.DataFrame, lookup: dict[tuple[str, int], float], window_mean: dict[str, float], global_mean: float) -> pd.Series:
    preds = []
    for row in frame[["core_window_id", "core_window_day"]].itertuples(index=False):
        win = str(row.core_window_id)
        day = int(row.core_window_day)
        preds.append(lookup.get((win, day), window_mean.get(win, global_mean)))
    return pd.Series(preds, index=frame.index, dtype=float)


def rank01(values: pd.Series, mask: pd.Series) -> pd.Series:
    out = pd.Series(0.5, index=values.index, dtype=float)
    if mask.any():
        out.loc[mask] = values.loc[mask].rank(method="average", pct=True).fillna(0.5)
    return out


def window_rank_score(values: pd.Series, frame: pd.DataFrame) -> pd.Series:
    out = pd.Series(0.5, index=frame.index, dtype=float)
    for spec in WINDOWS:
        mask = frame["core_window_id"].eq(spec.name)
        out.loc[mask] = rank01(values, mask).loc[mask]
    return out


def crossfit_models(oof: pd.DataFrame, feature_cols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    promo = oof.loc[oof["core_is_promo_window"] > 0].copy()
    preds = pd.DataFrame(
        {
            "Date": promo["Date"],
            "fold": promo["fold"],
            "core_window_id": promo["core_window_id"],
            "core_window_day": promo["core_window_day"],
            "core_rev_log_resid": promo["core_rev_log_resid"],
            "core_cogs_ratio_delta": promo["core_cogs_ratio_delta"],
        },
        index=promo.index,
    )
    metrics = []
    model_factories = {"ridge": fit_ridge, "hgb": fit_hgb, "trees": fit_trees}

    for fold in sorted(promo["fold"].unique()):
        train = promo.loc[promo["fold"] != fold].copy()
        valid = promo.loc[promo["fold"] == fold].copy()
        prior_lookup, prior_window, prior_global = smoothed_prior(train, "core_rev_log_resid")
        cogs_lookup, cogs_window, cogs_global = smoothed_prior(train, "core_cogs_ratio_delta")
        preds.loc[valid.index, "prior_rev"] = predict_prior(valid, prior_lookup, prior_window, prior_global)
        preds.loc[valid.index, "prior_cogs_ratio_delta"] = predict_prior(valid, cogs_lookup, cogs_window, cogs_global)
        for name, factory in model_factories.items():
            model = factory()
            model.fit(train[feature_cols], train["core_rev_log_resid"])
            preds.loc[valid.index, f"{name}_rev"] = model.predict(valid[feature_cols])

    for col in ["prior_rev", "ridge_rev", "hgb_rev", "trees_rev"]:
        metrics.append(
            {
                "model": col,
                "target": "promo_revenue_log_residual",
                "mae": mean_absolute_error(preds["core_rev_log_resid"], preds[col]),
                "zero_mae": float(np.abs(preds["core_rev_log_resid"]).mean()),
                "corr": float(preds[["core_rev_log_resid", col]].corr().iloc[0, 1]),
            }
        )
    metrics.append(
        {
            "model": "prior_cogs_ratio_delta",
            "target": "promo_cogs_ratio_delta",
            "mae": mean_absolute_error(preds["core_cogs_ratio_delta"], preds["prior_cogs_ratio_delta"]),
            "zero_mae": float(np.abs(preds["core_cogs_ratio_delta"]).mean()),
            "corr": float(preds[["core_cogs_ratio_delta", "prior_cogs_ratio_delta"]].corr().iloc[0, 1]),
        }
    )
    return preds.reset_index(drop=True), pd.DataFrame(metrics)


def fit_public_scores(
    oof: pd.DataFrame,
    public: pd.DataFrame,
    feature_cols: list[str],
    tabpfn_scores: pd.Series,
) -> pd.DataFrame:
    promo = oof.loc[oof["core_is_promo_window"] > 0].copy()
    public_out = public.copy()
    public_promo_mask = public_out["core_is_promo_window"] > 0

    prior_lookup, prior_window, prior_global = smoothed_prior(promo, "core_rev_log_resid")
    cogs_lookup, cogs_window, cogs_global = smoothed_prior(promo, "core_cogs_ratio_delta")
    public_out["score_prior"] = predict_prior(public_out, prior_lookup, prior_window, prior_global)
    public_out["score_cogs_ratio_delta"] = predict_prior(public_out, cogs_lookup, cogs_window, cogs_global)

    for name, factory in {"ridge": fit_ridge, "hgb": fit_hgb, "trees": fit_trees}.items():
        model = factory()
        model.fit(promo[feature_cols], promo["core_rev_log_resid"])
        public_out[f"score_{name}"] = model.predict(public_out[feature_cols])

    public_out["score_tabpfn_existing"] = pd.Series(tabpfn_scores.to_numpy(), index=public_out.index)
    public_out["rank_prior"] = window_rank_score(public_out["score_prior"], public_out)
    public_out["rank_model"] = (
        window_rank_score(public_out["score_ridge"], public_out)
        + window_rank_score(public_out["score_hgb"], public_out)
        + window_rank_score(public_out["score_trees"], public_out)
    ) / 3.0
    public_out["rank_tabpfn"] = window_rank_score(public_out["score_tabpfn_existing"], public_out)
    public_out["rank_hybrid"] = 0.25 * public_out["rank_prior"] + 0.35 * public_out["rank_model"] + 0.40 * public_out["rank_tabpfn"]
    public_out.loc[~public_promo_mask, ["rank_prior", "rank_model", "rank_tabpfn", "rank_hybrid"]] = 0.0
    return public_out


def uplift_from_rank(frame: pd.DataFrame, rank_col: str, sharpness: float = 1.4) -> pd.Series:
    uplift = pd.Series(0.0, index=frame.index, dtype=float)
    anchor_rev = frame["Revenue_pred"].astype(float)
    for spec in WINDOWS:
        mask = frame["core_window_id"].eq(spec.name)
        if not mask.any():
            continue
        ranks = frame.loc[mask, rank_col].astype(float).clip(0.0, 1.0)
        weights = np.exp((ranks - 0.5) * sharpness)
        weights = weights / max(float(weights.mean()), 1e-9)
        target_mean = BASE_TARGETS[spec.name]
        window_uplift = np.clip(target_mean * weights, 0.015, 0.22)
        window_uplift = window_uplift * (target_mean / max(float(window_uplift.mean()), 1e-9))
        uplift.loc[mask] = window_uplift

    promo_mask = frame["core_is_promo_window"] > 0
    weighted_mean = float((uplift.loc[promo_mask] * anchor_rev.loc[promo_mask]).sum() / anchor_rev.loc[promo_mask].sum())
    uplift.loc[promo_mask] *= WEIGHTED_PROMO_MEAN_TARGET / max(weighted_mean, 1e-9)
    return uplift


def export_candidate(
    run_dir: Path,
    public_frame: pd.DataFrame,
    candidate_id: str,
    uplift: pd.Series,
    cogs_ratio_alpha: float = 0.0,
) -> dict[str, object]:
    promo_mask = public_frame["core_is_promo_window"] > 0
    anchor_rev = public_frame["Revenue_pred"].astype(float)
    anchor_cogs = public_frame["COGS_pred"].astype(float)
    revenue = anchor_rev * (1.0 + uplift.astype(float))
    cogs = anchor_cogs.copy()

    if cogs_ratio_alpha != 0.0:
        ratio_delta = public_frame["score_cogs_ratio_delta"].astype(float).clip(-0.08, 0.08)
        anchor_ratio = (anchor_cogs / anchor_rev.replace(0.0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        desired_ratio = (anchor_ratio + cogs_ratio_alpha * ratio_delta).clip(0.65, 0.98)
        adjusted_cogs = revenue * desired_ratio
        raw_multiplier = (adjusted_cogs / anchor_cogs.replace(0.0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(1.0)
        raw_multiplier = raw_multiplier.clip(0.98, 1.02)
        cogs.loc[promo_mask] = anchor_cogs.loc[promo_mask] * raw_multiplier.loc[promo_mask]

    submission = pd.DataFrame(
        {
            "Date": pd.to_datetime(public_frame["Date"]).dt.strftime("%Y-%m-%d"),
            "Revenue": revenue.clip(lower=0.0),
            "COGS": cogs.clip(lower=0.0),
        }
    )
    run_path = run_dir / f"submission_{candidate_id}.csv"
    dataset_path = DATASET_DIR / f"submission_{candidate_id}.csv"
    submission.to_csv(run_path, index=False)
    submission.to_csv(dataset_path, index=False)

    rev_delta = submission["Revenue"] - anchor_rev
    cogs_delta = submission["COGS"] - anchor_cogs
    promo_anchor_rev = anchor_rev.loc[promo_mask]
    promo_uplift = uplift.loc[promo_mask]
    return {
        "candidate_id": candidate_id,
        "run_path": str(run_path),
        "dataset_path": str(dataset_path),
        "changed_rows": int(promo_mask.sum()),
        "promo_uplift_mean": float(promo_uplift.mean()),
        "promo_uplift_weighted_mean": float((promo_uplift * promo_anchor_rev).sum() / promo_anchor_rev.sum()),
        "promo_uplift_min": float(promo_uplift.min()),
        "promo_uplift_max": float(promo_uplift.max()),
        "revenue_total_ratio": float(submission["Revenue"].sum() / anchor_rev.sum()),
        "revenue_delta_mean": float(rev_delta.mean()),
        "revenue_delta_promo_mean": float(rev_delta.loc[promo_mask].mean()),
        "revenue_delta_nonpromo_max_abs": float(rev_delta.loc[~promo_mask].abs().max()),
        "cogs_ratio_alpha": cogs_ratio_alpha,
        "cogs_total_ratio": float(submission["COGS"].sum() / anchor_cogs.sum()),
        "cogs_delta_mean": float(cogs_delta.mean()),
        "cogs_delta_promo_mean": float(cogs_delta.loc[promo_mask].mean()),
        "cogs_delta_nonpromo_max_abs": float(cogs_delta.loc[~promo_mask].abs().max()),
    }


def export_best_revenue_cogs_candidate(
    run_dir: Path,
    public_frame: pd.DataFrame,
    candidate_id: str,
    cogs_ratio_alpha: float,
    multiplier_clip: float,
) -> dict[str, object]:
    if not BEST_PATH.exists():
        raise FileNotFoundError(f"Missing current best submission: {BEST_PATH}")
    best = pd.read_csv(BEST_PATH, parse_dates=["Date"])
    frame = public_frame[["Date", "Revenue_pred", "COGS_pred", "core_is_promo_window", "score_cogs_ratio_delta"]].merge(
        best.rename(columns={"Revenue": "Best_Revenue", "COGS": "Best_COGS"}),
        on="Date",
        how="left",
    )
    promo_mask = frame["core_is_promo_window"] > 0
    anchor_rev = frame["Revenue_pred"].astype(float)
    anchor_cogs = frame["COGS_pred"].astype(float)
    best_revenue = frame["Best_Revenue"].astype(float)

    ratio_delta = frame["score_cogs_ratio_delta"].astype(float).clip(-0.08, 0.08)
    anchor_ratio = (anchor_cogs / anchor_rev.replace(0.0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    desired_ratio = (anchor_ratio + cogs_ratio_alpha * ratio_delta).clip(0.65, 0.98)
    adjusted_cogs = best_revenue * desired_ratio
    raw_multiplier = (adjusted_cogs / anchor_cogs.replace(0.0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    raw_multiplier = raw_multiplier.clip(1.0 - multiplier_clip, 1.0 + multiplier_clip)
    cogs = anchor_cogs.copy()
    cogs.loc[promo_mask] = anchor_cogs.loc[promo_mask] * raw_multiplier.loc[promo_mask]

    submission = pd.DataFrame(
        {
            "Date": pd.to_datetime(frame["Date"]).dt.strftime("%Y-%m-%d"),
            "Revenue": best_revenue.clip(lower=0.0),
            "COGS": cogs.clip(lower=0.0),
        }
    )
    run_path = run_dir / f"submission_{candidate_id}.csv"
    dataset_path = DATASET_DIR / f"submission_{candidate_id}.csv"
    submission.to_csv(run_path, index=False)
    submission.to_csv(dataset_path, index=False)

    rev_delta = submission["Revenue"] - anchor_rev
    cogs_delta = submission["COGS"] - anchor_cogs
    return {
        "candidate_id": candidate_id,
        "run_path": str(run_path),
        "dataset_path": str(dataset_path),
        "changed_rows": int(promo_mask.sum()),
        "promo_uplift_mean": float((best_revenue.loc[promo_mask] / anchor_rev.loc[promo_mask] - 1.0).mean()),
        "promo_uplift_weighted_mean": float(
            (((best_revenue.loc[promo_mask] / anchor_rev.loc[promo_mask]) - 1.0) * anchor_rev.loc[promo_mask]).sum()
            / anchor_rev.loc[promo_mask].sum()
        ),
        "promo_uplift_min": float((best_revenue.loc[promo_mask] / anchor_rev.loc[promo_mask] - 1.0).min()),
        "promo_uplift_max": float((best_revenue.loc[promo_mask] / anchor_rev.loc[promo_mask] - 1.0).max()),
        "revenue_total_ratio": float(submission["Revenue"].sum() / anchor_rev.sum()),
        "revenue_delta_mean": float(rev_delta.mean()),
        "revenue_delta_promo_mean": float(rev_delta.loc[promo_mask].mean()),
        "revenue_delta_nonpromo_max_abs": float(rev_delta.loc[~promo_mask].abs().max()),
        "cogs_ratio_alpha": cogs_ratio_alpha,
        "cogs_multiplier_clip": multiplier_clip,
        "cogs_total_ratio": float(submission["COGS"].sum() / anchor_cogs.sum()),
        "cogs_delta_mean": float(cogs_delta.mean()),
        "cogs_delta_promo_mean": float(cogs_delta.loc[promo_mask].mean()),
        "cogs_delta_nonpromo_max_abs": float(cogs_delta.loc[~promo_mask].abs().max()),
    }


def oof_candidate_metrics(oof: pd.DataFrame, crossfit: pd.DataFrame) -> pd.DataFrame:
    promo = oof.loc[oof["core_is_promo_window"] > 0].copy().reset_index(drop=True)
    cf = crossfit.reset_index(drop=True)
    rows = []
    score_specs = {
        "prior": cf["prior_rev"],
        "model": (cf["ridge_rev"] + cf["hgb_rev"] + cf["trees_rev"]) / 3.0,
    }
    for name, score in score_specs.items():
        for fold in sorted(promo["fold"].unique()):
            valid = promo["fold"].eq(fold)
            ranks = score.loc[valid].rank(method="average", pct=True).fillna(0.5)
            weights = np.exp((ranks - 0.5) * 1.4)
            weights = weights / max(float(weights.mean()), 1e-9)
            uplift = 0.08 * weights
            revenue_pred = promo.loc[valid, "Revenue_pred"].to_numpy() * (1.0 + uplift.to_numpy())
            baseline_mae = mean_absolute_error(promo.loc[valid, "Revenue"], promo.loc[valid, "Revenue_pred"])
            candidate_mae = mean_absolute_error(promo.loc[valid, "Revenue"], revenue_pred)
            rows.append(
                {
                    "candidate_shape": name,
                    "fold": fold,
                    "promo_revenue_mae_anchor": baseline_mae,
                    "promo_revenue_mae_candidate": candidate_mae,
                    "delta_mae_vs_anchor": candidate_mae - baseline_mae,
                }
            )
    return pd.DataFrame(rows)


def write_report(
    run_dir: Path,
    feature_cols: list[str],
    model_metrics: pd.DataFrame,
    oof_metrics: pd.DataFrame,
    summary: pd.DataFrame,
) -> None:
    with (run_dir / "report.md").open("w", encoding="utf-8") as f:
        f.write("# Promo Window Core v2\n\n")
        f.write("Frame: forecast-safe promo-window feature set. Non-promo Revenue is unchanged for every exported candidate.\n\n")
        f.write(f"Feature count: `{len(feature_cols)}`.\n\n")
        f.write("## Feature Columns\n")
        f.write(pd.DataFrame({"feature": feature_cols}).to_markdown(index=False))
        f.write("\n\n")
        f.write("## Cross-Fit Residual Metrics\n")
        f.write(model_metrics.to_markdown(index=False))
        f.write("\n\n")
        f.write("## OOF Candidate Shape Metrics\n")
        f.write(oof_metrics.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Candidate Summary\n")
        f.write(summary.to_markdown(index=False))
        f.write("\n\n")
        f.write("Use public leaderboard only for final decision; local OOF is advisory because public has a high-scale regime shift.\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Loading source OOF/public frames from %s", SOURCE_RUN_DIR)
    oof, public, tabpfn_scores = load_inputs()
    oof = add_targets(oof)
    feature_cols = feature_columns(public)
    logger.info("Using %s promo-window core features", len(feature_cols))

    crossfit, model_metrics = crossfit_models(oof, feature_cols)
    public_scored = fit_public_scores(oof, public, feature_cols, tabpfn_scores)

    public_scored.to_csv(run_dir / "public_feature_frame_scored.csv", index=False)
    crossfit.to_csv(run_dir / "crossfit_residual_predictions.csv", index=False)
    model_metrics.to_csv(run_dir / "model_metrics.csv", index=False)
    pd.Series(feature_cols, name="feature").to_csv(run_dir / "features.csv", index=False)

    prior_uplift = uplift_from_rank(public_scored, "rank_prior", sharpness=1.4)
    model_uplift = uplift_from_rank(public_scored, "rank_model", sharpness=1.4)
    hybrid_uplift = uplift_from_rank(public_scored, "rank_hybrid", sharpness=1.4)
    hybrid_soft_uplift = uplift_from_rank(public_scored, "rank_hybrid", sharpness=0.9)
    hybrid_sharp_uplift = uplift_from_rank(public_scored, "rank_hybrid", sharpness=2.0)

    rows = [
        export_candidate(run_dir, public_scored, "promo_core_v2_prior_cal8", prior_uplift),
        export_candidate(run_dir, public_scored, "promo_core_v2_model_cal8", model_uplift),
        export_candidate(run_dir, public_scored, "promo_core_v2_hybrid_cal8", hybrid_uplift),
        export_candidate(run_dir, public_scored, "promo_core_v2_hybrid_soft_cal8", hybrid_soft_uplift),
        export_candidate(run_dir, public_scored, "promo_core_v2_hybrid_sharp_cal8", hybrid_sharp_uplift),
        export_candidate(run_dir, public_scored, "promo_core_v2_hybrid_cogsratio025", hybrid_uplift, cogs_ratio_alpha=0.25),
        export_best_revenue_cogs_candidate(
            run_dir,
            public_scored,
            "promo_core_v2_bestrev_cogsratio010",
            cogs_ratio_alpha=0.10,
            multiplier_clip=0.01,
        ),
        export_best_revenue_cogs_candidate(
            run_dir,
            public_scored,
            "promo_core_v2_bestrev_cogsratio020",
            cogs_ratio_alpha=0.20,
            multiplier_clip=0.015,
        ),
    ]
    summary = pd.DataFrame(rows)
    summary.to_csv(run_dir / "summary.csv", index=False)
    oof_metrics = oof_candidate_metrics(oof, crossfit)
    oof_metrics.to_csv(run_dir / "oof_candidate_metrics.csv", index=False)

    write_json(
        run_dir / "config.json",
        {
            "source_run_dir": str(SOURCE_RUN_DIR),
            "anchor_path": str(ANCHOR_PATH),
            "best_path": str(BEST_PATH),
            "weighted_promo_mean_target": WEIGHTED_PROMO_MEAN_TARGET,
            "base_window_targets": BASE_TARGETS,
            "n_features": len(feature_cols),
            "note": "All exported candidates keep non-promo Revenue unchanged.",
        },
    )
    write_report(run_dir, feature_cols, model_metrics, oof_metrics, summary)
    logger.info("Saved Promo Window Core v2 outputs to %s", run_dir)
    print(model_metrics.to_string(index=False))
    print(summary.to_string(index=False))
    print(f"\nSaved outputs to {run_dir}")


if __name__ == "__main__":
    main()
