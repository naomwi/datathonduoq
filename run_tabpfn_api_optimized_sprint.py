from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error

from feature_pipeline import (
    PROMO_BASE_COLUMNS,
    PROMO_RESEARCH_BASE_COLUMNS,
    PROMO_TARGET_ENCODING_COLUMNS,
)
from logging_utils import create_run_dir, setup_logger, write_json
from train_recursive_forecast import (
    BACKTEST_FOLDS,
    TRAIN_END,
    apply_future_promo_policy,
    ensure_inputs,
    get_candidate_feature_sets,
    recursive_forecast,
)


RUN_PREFIX = "tabpfn_api_optimized_sprint"
DATASET_DIR = Path("dataset")
ANCHOR_PATH = DATASET_DIR / "submission_catboost_md2y_core_recencyexp20.csv"
FORECAST_START = pd.Timestamp("2023-01-01")
FORECAST_END = pd.Timestamp("2024-07-01")
MODEL_PATHS = ["default", "v2.5_default", "v2.5_real", "v2.5_small-samples", "v2.5_low-skew"]


def authorize_api() -> None:
    token = os.getenv("PRIORLABS_TABPFN_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Set PRIORLABS_TABPFN_TOKEN before running this script.")

    # Avoid tabpfn_client.set_access_token(), because it writes the token to package cache.
    from tabpfn_client.client import ServiceClient
    from tabpfn_client.config import Config

    ServiceClient.authorize(token)
    Config.use_server = True
    Config.is_initialized = True


def verify_api_auth() -> dict[str, object]:
    from tabpfn_client import TabPFNRegressor

    X = pd.DataFrame({"x": [0.0, 1.0, 2.0, 3.0], "flag": [0.0, 1.0, 0.0, 1.0]})
    y = np.array([0.0, 1.0, 2.0, 3.0], dtype=float)
    model = TabPFNRegressor(model_path="default", n_estimators=1, random_state=42)
    model.fit(X, y)
    pred = np.asarray(model.predict(pd.DataFrame({"x": [4.0], "flag": [0.0]})), dtype=float)
    return {"ok": bool(np.isfinite(pred).all()), "prediction": float(pred[0])}


def mask_between_month_day(dates: pd.Series, start: str, end: str) -> pd.Series:
    month_day = dates.dt.strftime("%m-%d")
    if start <= end:
        return month_day.between(start, end)
    return month_day.between(start, "12-31") | month_day.between("01-01", end)


def add_tabpfn_meta_features(frame: pd.DataFrame, forecast_start: pd.Timestamp) -> pd.DataFrame:
    out = frame.copy()
    dates = pd.to_datetime(out["Date"])
    step = (dates - pd.Timestamp(forecast_start)).dt.days + 1

    out["forecast_step"] = step.astype(float)
    out["horizon_bin_14"] = ((step - 1) // 14).clip(lower=0).astype(float)
    out["horizon_bin_30"] = ((step - 1) // 30).clip(lower=0).astype(float)
    out["month"] = dates.dt.month.astype(float)
    out["day"] = dates.dt.day.astype(float)
    out["dayofweek"] = dates.dt.dayofweek.astype(float)
    out["weekofyear"] = dates.dt.isocalendar().week.astype(float)
    out["dayofyear"] = dates.dt.dayofyear.astype(float)
    out["quarter"] = dates.dt.quarter.astype(float)
    out["is_weekend"] = dates.dt.dayofweek.isin([5, 6]).astype(float)
    out["is_month_start"] = dates.dt.is_month_start.astype(float)
    out["is_month_end"] = dates.dt.is_month_end.astype(float)
    out["sin_dayofyear"] = np.sin(2.0 * np.pi * out["dayofyear"] / 365.25)
    out["cos_dayofyear"] = np.cos(2.0 * np.pi * out["dayofyear"] / 365.25)
    out["sin_dayofweek"] = np.sin(2.0 * np.pi * out["dayofweek"] / 7.0)
    out["cos_dayofweek"] = np.cos(2.0 * np.pi * out["dayofweek"] / 7.0)
    out["is_2024"] = (dates.dt.year == 2024).astype(float)

    out["promo_win_marapr"] = mask_between_month_day(dates, "03-18", "04-17").astype(float)
    out["promo_win_junjul"] = mask_between_month_day(dates, "06-23", "07-22").astype(float)
    out["promo_win_augoct"] = mask_between_month_day(dates, "08-30", "10-02").astype(float)
    out["promo_win_novjan"] = mask_between_month_day(dates, "11-18", "01-02").astype(float)
    out["promo_window_any"] = (
        out["promo_win_marapr"]
        + out["promo_win_junjul"]
        + out["promo_win_augoct"]
        + out["promo_win_novjan"]
    ).clip(0.0, 1.0)

    out["anchor_revenue"] = out["Revenue_pred"].astype(float)
    out["anchor_cogs"] = out["COGS_pred"].astype(float)
    out["anchor_log_revenue"] = np.log1p(out["anchor_revenue"].clip(lower=0.0))
    out["anchor_log_cogs"] = np.log1p(out["anchor_cogs"].clip(lower=0.0))
    out["anchor_cogs_ratio"] = (
        out["anchor_cogs"] / out["anchor_revenue"].replace(0.0, np.nan)
    ).fillna(0.0)
    out["anchor_margin"] = out["anchor_revenue"] - out["anchor_cogs"]
    out["anchor_margin_ratio"] = (
        out["anchor_margin"] / out["anchor_revenue"].replace(0.0, np.nan)
    ).fillna(0.0)
    return out


def add_public_anchor_context(public_frame: pd.DataFrame) -> pd.DataFrame:
    out = public_frame.copy()
    out["anchor_rev_roll7"] = out["Revenue_pred"].rolling(7, min_periods=1).mean()
    out["anchor_rev_roll28"] = out["Revenue_pred"].rolling(28, min_periods=1).mean()
    out["anchor_rev_ewm28"] = out["Revenue_pred"].ewm(span=28, adjust=False).mean()
    out["anchor_cogs_ratio_roll28"] = (
        out["COGS_pred"] / out["Revenue_pred"].replace(0.0, np.nan)
    ).fillna(0.0).rolling(28, min_periods=1).mean()
    return out


def base_feature_columns(frame: pd.DataFrame) -> list[str]:
    promo_cols = [
        col
        for col in list(PROMO_BASE_COLUMNS) + list(PROMO_RESEARCH_BASE_COLUMNS) + list(PROMO_TARGET_ENCODING_COLUMNS)
        if col in frame.columns
    ]
    engineered_cols = [
        "forecast_step",
        "horizon_bin_14",
        "horizon_bin_30",
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
        "is_2024",
        "promo_win_marapr",
        "promo_win_junjul",
        "promo_win_augoct",
        "promo_win_novjan",
        "promo_window_any",
        "anchor_log_revenue",
        "anchor_log_cogs",
        "anchor_cogs_ratio",
        "anchor_margin_ratio",
        "anchor_rev_roll7",
        "anchor_rev_roll28",
        "anchor_rev_ewm28",
        "anchor_cogs_ratio_roll28",
    ]
    return [col for col in engineered_cols + promo_cols if col in frame.columns]


def build_anchor_oof(
    feature_store: pd.DataFrame,
    base: pd.DataFrame,
    feature_sets: dict[str, list[str]],
) -> pd.DataFrame:
    rows = []
    revenue_features = feature_sets["curated_promo_cogs"]
    cogs_features = feature_sets["curated_promo_cogs"]

    for fold_id, (start_date, end_date) in enumerate(BACKTEST_FOLDS, start=1):
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        cutoff = start_ts - pd.Timedelta(days=1)
        adjusted_base = apply_future_promo_policy(base, cutoff, "seasonal_month_day_recent_2y")

        preds = recursive_forecast(
            feature_store=feature_store,
            full_base=adjusted_base,
            train_end_date=cutoff,
            forecast_start=start_ts,
            forecast_end=end_ts,
            revenue_features=revenue_features,
            cogs_features=cogs_features,
            cogs_postprocess_variant="blend60_clip_q99",
            model_family="catboost",
            sample_weight_mode="exp_years",
            sample_weight_decay=0.20,
        )
        truth = feature_store.loc[
            (feature_store["Date"] >= start_ts) & (feature_store["Date"] <= end_ts),
            ["Date", "Revenue", "COGS"],
        ].copy()
        safe_cols = [
            col
            for col in list(PROMO_BASE_COLUMNS) + list(PROMO_RESEARCH_BASE_COLUMNS) + list(PROMO_TARGET_ENCODING_COLUMNS)
            if col in adjusted_base.columns
        ]
        fold = truth.merge(preds, on="Date", how="left").merge(adjusted_base[["Date"] + safe_cols], on="Date", how="left")
        fold["fold"] = fold_id
        fold["fold_start"] = start_ts
        fold = add_tabpfn_meta_features(fold, start_ts)
        fold = add_public_anchor_context(fold.rename(columns={"Revenue_pred": "Revenue_pred", "COGS_pred": "COGS_pred"}))
        fold["target_log_residual"] = (
            np.log1p(fold["Revenue"].clip(lower=0.0))
            - np.log1p(fold["Revenue_pred"].clip(lower=0.0))
        )
        rows.append(fold)

    return pd.concat(rows, ignore_index=True)


def build_public_frame(base: pd.DataFrame) -> pd.DataFrame:
    if not ANCHOR_PATH.exists():
        raise FileNotFoundError(f"Missing anchor submission: {ANCHOR_PATH}")
    anchor = pd.read_csv(ANCHOR_PATH, parse_dates=["Date"])
    anchor = anchor.rename(columns={"Revenue": "Revenue_pred", "COGS": "COGS_pred"})
    adjusted_base = apply_future_promo_policy(base, TRAIN_END, "seasonal_month_day_recent_2y")
    safe_cols = [
        col
        for col in list(PROMO_BASE_COLUMNS) + list(PROMO_RESEARCH_BASE_COLUMNS) + list(PROMO_TARGET_ENCODING_COLUMNS)
        if col in adjusted_base.columns
    ]
    public = anchor.merge(adjusted_base[["Date"] + safe_cols], on="Date", how="left")
    public = add_tabpfn_meta_features(public, FORECAST_START)
    public = add_public_anchor_context(public)
    return public


def safe_model_col(model_path: str) -> str:
    return "resid_" + "".join(ch if ch.isalnum() else "_" for ch in model_path)


def fit_predict_model_paths(
    model_paths: Iterable[str],
    oof: pd.DataFrame,
    public_frame: pd.DataFrame,
    feature_cols: list[str],
    run_dir: Path,
    logger,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    from tabpfn_client import TabPFNRegressor

    X_oof = oof[feature_cols].fillna(0.0)
    y_oof = oof["target_log_residual"].astype(float)
    X_public = public_frame[feature_cols].fillna(0.0)

    public_preds = pd.DataFrame({"Date": public_frame["Date"]})
    oof_preds = pd.DataFrame({"Date": oof["Date"], "fold": oof["fold"], "target_log_residual": y_oof})
    metric_rows = []

    for model_path in model_paths:
        col = safe_model_col(model_path)
        try:
            logger.info("Fitting TabPFN API residual model_path=%s rows=%s cols=%s", model_path, len(X_oof), len(feature_cols))
            model = TabPFNRegressor(model_path=model_path, n_estimators=8, random_state=42)
            model.fit(X_oof, y_oof)
            public_preds[col] = np.asarray(model.predict(X_public), dtype=float)
            oof_preds[col] = np.asarray(model.predict(X_oof), dtype=float)
            promo_mask = oof["promo_window_any"].astype(float) > 0
            metric_rows.append(
                {
                    "model_path": model_path,
                    "column": col,
                    "status": "ok",
                    "residual_mae_all": mean_absolute_error(y_oof, oof_preds[col]),
                    "zero_residual_mae_all": float(np.abs(y_oof).mean()),
                    "residual_mae_promo": mean_absolute_error(y_oof[promo_mask], oof_preds.loc[promo_mask, col]),
                    "zero_residual_mae_promo": float(np.abs(y_oof[promo_mask]).mean()),
                    "residual_mae_nonpromo": mean_absolute_error(y_oof[~promo_mask], oof_preds.loc[~promo_mask, col]),
                    "zero_residual_mae_nonpromo": float(np.abs(y_oof[~promo_mask]).mean()),
                }
            )
        except Exception as exc:
            logger.exception("TabPFN API model_path=%s failed", model_path)
            metric_rows.append({"model_path": model_path, "column": col, "status": f"failed: {exc}"})

    metrics = pd.DataFrame(metric_rows)
    public_preds.to_csv(run_dir / "raw_residual_predictions.csv", index=False)
    oof_preds.to_csv(run_dir / "oof_residual_predictions.csv", index=False)
    metrics.to_csv(run_dir / "model_path_metrics.csv", index=False)
    return public_preds, metrics


def weighted_ensemble(public_preds: pd.DataFrame, metrics: pd.DataFrame) -> pd.Series:
    ok = metrics.loc[metrics["status"] == "ok"].copy()
    if ok.empty:
        raise RuntimeError("No TabPFN API model path succeeded.")
    weights = 1.0 / ok["residual_mae_promo"].astype(float).clip(lower=1e-6)
    weights = weights / weights.sum()
    pred = np.zeros(len(public_preds), dtype=float)
    for weight, col in zip(weights, ok["column"], strict=False):
        pred += float(weight) * public_preds[col].astype(float).to_numpy()
    return pd.Series(pred, index=public_preds.index)


def uplift_shape_from_scores(scores: pd.Series, mask: pd.Series, target_mean: float) -> pd.Series:
    out = pd.Series(0.0, index=scores.index)
    if not mask.any():
        return out
    subset = scores.loc[mask].astype(float)
    ranks = subset.rank(method="average", pct=True).fillna(0.5)
    weights = np.exp((ranks - 0.5) * 1.4)
    weights = weights / weights.mean()
    uplift = np.clip(target_mean * weights, 0.015, 0.22)
    # Re-normalize after clipping to preserve intended average as closely as possible.
    uplift = uplift * (target_mean / max(float(uplift.mean()), 1e-9))
    out.loc[mask] = uplift
    return out


def window_masks(frame: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        "marapr": frame["promo_win_marapr"].astype(float) > 0,
        "junjul": frame["promo_win_junjul"].astype(float) > 0,
        "augoct": frame["promo_win_augoct"].astype(float) > 0,
        "novjan": frame["promo_win_novjan"].astype(float) > 0,
    }


def build_windowmix_uplift(public_frame: pd.DataFrame, scores: pd.Series) -> pd.Series:
    masks = window_masks(public_frame)
    base_targets = {"marapr": 0.08, "junjul": 0.10, "augoct": 0.08, "novjan": 0.06}
    uplift = pd.Series(0.0, index=public_frame.index)
    for name, mask in masks.items():
        uplift += uplift_shape_from_scores(scores, mask, base_targets[name])
    promo_mask = public_frame["promo_window_any"].astype(float) > 0
    if promo_mask.any():
        anchor_rev = public_frame["Revenue_pred"].astype(float)
        weighted_mean = float((uplift.loc[promo_mask] * anchor_rev.loc[promo_mask]).sum() / anchor_rev.loc[promo_mask].sum())
        uplift.loc[promo_mask] *= 0.08 / max(weighted_mean, 1e-9)
    return uplift


def export_candidate(
    run_dir: Path,
    public_frame: pd.DataFrame,
    candidate_id: str,
    uplift: pd.Series,
    cogs_pct: float = 0.0,
    publish: bool = True,
) -> dict[str, object]:
    promo_mask = public_frame["promo_window_any"].astype(float) > 0
    revenue = public_frame["Revenue_pred"].astype(float) * (1.0 + uplift.astype(float))
    cogs = public_frame["COGS_pred"].astype(float).copy()
    if cogs_pct:
        cogs.loc[promo_mask] *= 1.0 + cogs_pct

    submission = pd.DataFrame(
        {
            "Date": pd.to_datetime(public_frame["Date"]).dt.strftime("%Y-%m-%d"),
            "Revenue": np.clip(revenue, 0.0, None),
            "COGS": np.clip(cogs, 0.0, None),
        }
    )
    run_path = run_dir / f"submission_{candidate_id}.csv"
    dataset_path = DATASET_DIR / f"submission_{candidate_id}.csv"
    submission.to_csv(run_path, index=False)
    revenue_total_ratio = float(submission["Revenue"].sum() / public_frame["Revenue_pred"].sum())
    if publish and 1.00 <= revenue_total_ratio <= 1.05:
        submission.to_csv(dataset_path, index=False)
        dataset_path_out = str(dataset_path)
    else:
        dataset_path_out = ""

    rev_delta = submission["Revenue"] - public_frame["Revenue_pred"]
    cogs_delta = submission["COGS"] - public_frame["COGS_pred"]
    nonpromo_rev_delta = rev_delta.loc[~promo_mask]
    return {
        "candidate_id": candidate_id,
        "run_path": str(run_path),
        "dataset_path": dataset_path_out,
        "changed_rows": int(promo_mask.sum()),
        "promo_revenue_uplift_mean": float(uplift.loc[promo_mask].mean()) if promo_mask.any() else 0.0,
        "nonpromo_revenue_delta_max_abs": float(nonpromo_rev_delta.abs().max()) if len(nonpromo_rev_delta) else 0.0,
        "revenue_delta_mean": float(rev_delta.mean()),
        "revenue_delta_abs_mean": float(rev_delta.abs().mean()),
        "revenue_delta_max_abs": float(rev_delta.abs().max()),
        "revenue_total_ratio": revenue_total_ratio,
        "cogs_delta_mean": float(cogs_delta.mean()),
        "cogs_delta_abs_mean": float(cogs_delta.abs().mean()),
        "cogs_delta_max_abs": float(cogs_delta.abs().max()),
        "cogs_total_ratio": float(submission["COGS"].sum() / public_frame["COGS_pred"].sum()),
    }


def build_candidates(public_frame: pd.DataFrame, scores: pd.Series, run_dir: Path) -> pd.DataFrame:
    promo_mask = public_frame["promo_window_any"].astype(float) > 0
    is_2024 = public_frame["is_2024"].astype(float) > 0

    uplift_cal8 = uplift_shape_from_scores(scores, promo_mask, 0.08)
    uplift_cal10 = uplift_shape_from_scores(scores, promo_mask, 0.10)

    uplift_2024heavy = pd.Series(0.0, index=public_frame.index)
    uplift_2024heavy += uplift_shape_from_scores(scores, promo_mask & ~is_2024, 0.07)
    uplift_2024heavy += uplift_shape_from_scores(scores, promo_mask & is_2024, 0.14)

    uplift_windowmix = build_windowmix_uplift(public_frame, scores)

    rows = [
        export_candidate(run_dir, public_frame, "tabpfn_promo_shape_cal8", uplift_cal8),
        export_candidate(run_dir, public_frame, "tabpfn_promo_shape_cal10", uplift_cal10),
        export_candidate(run_dir, public_frame, "tabpfn_promo_2024heavy_cal", uplift_2024heavy),
        export_candidate(run_dir, public_frame, "tabpfn_promo_windowmix_v1", uplift_windowmix),
        export_candidate(run_dir, public_frame, "tabpfn_promo_shape_cogs4", uplift_cal8, cogs_pct=0.04),
        export_candidate(run_dir, public_frame, "tabpfn_promo_shape_cogs8", uplift_cal8, cogs_pct=0.08),
    ]
    return pd.DataFrame(rows)


def write_report(
    run_dir: Path,
    model_metrics: pd.DataFrame,
    candidate_summary: pd.DataFrame,
    auth_result: dict[str, object],
) -> None:
    with (run_dir / "report.md").open("w", encoding="utf-8") as f:
        f.write("# TabPFN API Optimized Sprint\n\n")
        f.write("Frame: TabPFN residual/uplift meta-model around the recencyexp20 anchor. Raw TabPFN Revenue is not submitted.\n\n")
        f.write(f"API smoke test ok: `{auth_result.get('ok')}`.\n\n")
        f.write("## Model Path Metrics\n")
        f.write(model_metrics.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Candidate Summary\n")
        f.write(candidate_summary.to_markdown(index=False))
        f.write("\n\n")
        f.write("Published candidates are the rows with non-empty `dataset_path`.\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    authorize_api()
    auth_result = verify_api_auth()

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))

    logger.info("Building anchor OOF table")
    oof = build_anchor_oof(feature_store, base, feature_sets)
    public_frame = build_public_frame(base)
    feature_cols = base_feature_columns(public_frame)
    feature_cols = [col for col in feature_cols if col in oof.columns and col in public_frame.columns]

    oof.to_csv(run_dir / "anchor_oof_table.csv", index=False)
    public_frame.to_csv(run_dir / "public_feature_frame.csv", index=False)
    pd.Series(feature_cols, name="feature").to_csv(run_dir / "features.csv", index=False)

    public_preds, model_metrics = fit_predict_model_paths(MODEL_PATHS, oof, public_frame, feature_cols, run_dir, logger)
    scores = weighted_ensemble(public_preds, model_metrics)
    scores.to_frame("tabpfn_residual_ensemble").to_csv(run_dir / "tabpfn_residual_ensemble.csv", index=False)

    candidate_summary = build_candidates(public_frame, scores, run_dir)
    candidate_summary.to_csv(run_dir / "summary.csv", index=False)

    write_json(
        run_dir / "config.json",
        {
            "model_paths": MODEL_PATHS,
            "n_features": len(feature_cols),
            "n_oof_rows": len(oof),
            "n_public_rows": len(public_frame),
            "current_best_public": {
                "submission_public_probe_promo_windows_rev_up8.csv": 887225.99926,
            },
            "note": "API token is read from environment and is not stored.",
        },
    )
    write_report(run_dir, model_metrics, candidate_summary, auth_result)
    logger.info("Saved optimized TabPFN sprint to %s", run_dir)
    print(candidate_summary.to_string(index=False))


if __name__ == "__main__":
    main()
