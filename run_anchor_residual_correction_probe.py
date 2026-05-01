from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.metrics import mean_absolute_error

from feature_pipeline import (
    PROMO_BASE_COLUMNS,
    PROMO_RESEARCH_BASE_COLUMNS,
    PROMO_TARGET_ENCODING_COLUMNS,
    TARGET_SEASONAL_PRIOR_COLUMNS,
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


RUN_PREFIX = "anchor_residual_correction_probe"
DATASET_DIR = Path("dataset")
ANCHOR_SUBMISSION = DATASET_DIR / "submission_catboost_md2y_core_recencyexp20.csv"
FORECAST_START = pd.Timestamp("2023-01-01")
FORECAST_END = pd.Timestamp("2024-07-01")

STRENGTHS = [0.25, 0.50, 0.75]
CLIPS = [0.08, 0.12, 0.16]

BASE_SIGNAL_COLUMNS = (
    list(PROMO_BASE_COLUMNS)
    + list(PROMO_TARGET_ENCODING_COLUMNS)
    + list(PROMO_RESEARCH_BASE_COLUMNS)
    + list(TARGET_SEASONAL_PRIOR_COLUMNS)
)


def _ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    return num.astype(float) / den.astype(float).replace(0.0, np.nan)


def add_correction_features(frame: pd.DataFrame, forecast_start: pd.Timestamp) -> pd.DataFrame:
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
    out["is_weekend"] = dates.dt.dayofweek.isin([5, 6]).astype(float)
    out["is_month_start"] = dates.dt.is_month_start.astype(float)
    out["is_month_end"] = dates.dt.is_month_end.astype(float)
    out["sin_dayofyear"] = np.sin(2.0 * np.pi * out["dayofyear"] / 365.25)
    out["cos_dayofyear"] = np.cos(2.0 * np.pi * out["dayofyear"] / 365.25)
    out["sin_dayofweek"] = np.sin(2.0 * np.pi * out["dayofweek"] / 7.0)
    out["cos_dayofweek"] = np.cos(2.0 * np.pi * out["dayofweek"] / 7.0)

    out["anchor_revenue"] = out["Revenue_pred"].astype(float)
    out["anchor_cogs"] = out["COGS_pred"].astype(float)
    out["anchor_log_revenue"] = np.log1p(out["anchor_revenue"].clip(lower=0.0))
    out["anchor_log_cogs"] = np.log1p(out["anchor_cogs"].clip(lower=0.0))
    out["anchor_cogs_ratio"] = _ratio(out["anchor_cogs"], out["anchor_revenue"]).fillna(0.0)
    out["anchor_margin"] = out["anchor_revenue"] - out["anchor_cogs"]
    out["anchor_margin_ratio"] = _ratio(out["anchor_margin"], out["anchor_revenue"]).fillna(0.0)
    return out


def build_anchor_oof(feature_store: pd.DataFrame, base: pd.DataFrame, feature_sets: dict[str, list[str]]) -> pd.DataFrame:
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

        safe_base_cols = [col for col in BASE_SIGNAL_COLUMNS if col in adjusted_base.columns]
        base_frame = adjusted_base[["Date"] + safe_base_cols].copy()
        fold_frame = truth.merge(preds, on="Date", how="left").merge(base_frame, on="Date", how="left")
        fold_frame["fold"] = fold_id
        fold_frame["fold_start"] = start_ts
        fold_frame = add_correction_features(fold_frame, start_ts)
        fold_frame["target_log_residual"] = (
            np.log1p(fold_frame["Revenue"].clip(lower=0.0))
            - np.log1p(fold_frame["Revenue_pred"].clip(lower=0.0))
        )
        rows.append(fold_frame)

    return pd.concat(rows, ignore_index=True)


def get_feature_columns(frame: pd.DataFrame) -> list[str]:
    blocked = {
        "Date",
        "Revenue",
        "COGS",
        "Revenue_pred",
        "COGS_pred",
        "fold",
        "fold_start",
        "target_log_residual",
    }
    cols = []
    for col in frame.columns:
        if col in blocked:
            continue
        if pd.api.types.is_numeric_dtype(frame[col]):
            cols.append(col)
    return cols


def fit_residual_model(train_df: pd.DataFrame, feature_cols: list[str]) -> CatBoostRegressor:
    max_date = pd.to_datetime(train_df["Date"]).max()
    years_ago = (max_date - pd.to_datetime(train_df["Date"])).dt.days.clip(lower=0) / 365.25
    weights = np.exp(-0.35 * years_ago)
    model = CatBoostRegressor(
        loss_function="RMSE",
        eval_metric="MAE",
        iterations=500,
        learning_rate=0.035,
        depth=4,
        l2_leaf_reg=20.0,
        subsample=0.85,
        random_seed=42,
        verbose=False,
        allow_writing_files=False,
    )
    model.fit(
        train_df[feature_cols].fillna(0.0),
        train_df["target_log_residual"],
        sample_weight=weights,
    )
    return model


def apply_residual_correction(frame: pd.DataFrame, raw_log_delta: np.ndarray, strength: float, clip: float) -> pd.Series:
    bounded = np.clip(raw_log_delta, -clip, clip) * strength
    corrected = np.expm1(np.log1p(frame["Revenue_pred"].clip(lower=0.0)) + bounded)
    return pd.Series(np.clip(corrected, 0.0, None), index=frame.index)


def evaluate_time_forward(oof: pd.DataFrame, feature_cols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    prediction_frames = []
    metric_rows = []

    for eval_fold in sorted(oof["fold"].unique()):
        train_df = oof[oof["fold"] < eval_fold].copy()
        eval_df = oof[oof["fold"] == eval_fold].copy()
        if train_df.empty:
            continue

        model = fit_residual_model(train_df, feature_cols)
        raw_log_delta = model.predict(eval_df[feature_cols].fillna(0.0))

        anchor_rev_mae = mean_absolute_error(eval_df["Revenue"], eval_df["Revenue_pred"])
        anchor_cogs_mae = mean_absolute_error(eval_df["COGS"], eval_df["COGS_pred"])
        anchor_combined = 0.5 * (anchor_rev_mae + anchor_cogs_mae)

        for strength in STRENGTHS:
            for clip in CLIPS:
                candidate_id = f"residual_logcb_s{int(strength * 100):02d}_c{int(clip * 100):02d}"
                corrected = apply_residual_correction(eval_df, raw_log_delta, strength, clip)
                rev_mae = mean_absolute_error(eval_df["Revenue"], corrected)
                combined = 0.5 * (rev_mae + anchor_cogs_mae)
                metric_rows.append(
                    {
                        "candidate_id": candidate_id,
                        "fold": int(eval_fold),
                        "strength": strength,
                        "clip": clip,
                        "revenue_mae": rev_mae,
                        "cogs_mae": anchor_cogs_mae,
                        "combined_mae": combined,
                        "anchor_revenue_mae": anchor_rev_mae,
                        "anchor_combined_mae": anchor_combined,
                        "delta_combined_vs_anchor": combined - anchor_combined,
                    }
                )

                pred_frame = eval_df[["Date", "fold", "Revenue", "COGS", "Revenue_pred", "COGS_pred"]].copy()
                pred_frame["candidate_id"] = candidate_id
                pred_frame["Revenue_corrected"] = corrected
                pred_frame["raw_log_delta"] = raw_log_delta
                prediction_frames.append(pred_frame)

    return pd.DataFrame(metric_rows), pd.concat(prediction_frames, ignore_index=True)


def build_public_frame(base: pd.DataFrame) -> pd.DataFrame:
    if not ANCHOR_SUBMISSION.exists():
        raise FileNotFoundError(f"Missing anchor submission: {ANCHOR_SUBMISSION}")

    anchor = pd.read_csv(ANCHOR_SUBMISSION, parse_dates=["Date"])
    anchor = anchor.rename(columns={"Revenue": "Revenue_pred", "COGS": "COGS_pred"})
    adjusted_base = apply_future_promo_policy(base, TRAIN_END, "seasonal_month_day_recent_2y")
    safe_base_cols = [col for col in BASE_SIGNAL_COLUMNS if col in adjusted_base.columns]
    public_frame = anchor.merge(adjusted_base[["Date"] + safe_base_cols], on="Date", how="left")
    return add_correction_features(public_frame, FORECAST_START)


def export_public_candidates(
    oof: pd.DataFrame,
    public_frame: pd.DataFrame,
    feature_cols: list[str],
    summary: pd.DataFrame,
    run_dir: Path,
) -> pd.DataFrame:
    model = fit_residual_model(oof, feature_cols)
    raw_log_delta = model.predict(public_frame[feature_cols].fillna(0.0))
    exported_rows = []

    selected = summary.sort_values(["combined_mae", "delta_combined_vs_anchor"]).head(3)
    for row in selected.itertuples(index=False):
        corrected = apply_residual_correction(public_frame, raw_log_delta, float(row.strength), float(row.clip))
        submission = pd.DataFrame(
            {
                "Date": pd.to_datetime(public_frame["Date"]).dt.strftime("%Y-%m-%d"),
                "Revenue": corrected,
                "COGS": public_frame["COGS_pred"],
            }
        )
        out_name = f"submission_{row.candidate_id}.csv"
        dataset_path = DATASET_DIR / out_name
        run_path = run_dir / out_name
        submission.to_csv(run_path, index=False)
        publish_to_dataset = float(row.delta_combined_vs_anchor) < 0.0
        if publish_to_dataset:
            submission.to_csv(dataset_path, index=False)

        delta = corrected - public_frame["Revenue_pred"]
        exported_rows.append(
            {
                "candidate_id": row.candidate_id,
                "dataset_path": str(dataset_path) if publish_to_dataset else "",
                "run_path": str(run_path),
                "publish_to_dataset": publish_to_dataset,
                "mean_revenue_delta": float(delta.mean()),
                "mean_abs_revenue_delta": float(delta.abs().mean()),
                "max_abs_revenue_delta": float(delta.abs().max()),
                "total_revenue_ratio_vs_anchor": float(corrected.sum() / public_frame["Revenue_pred"].sum()),
            }
        )

    return pd.DataFrame(exported_rows)


def write_report(run_dir: Path, summary: pd.DataFrame, exports: pd.DataFrame) -> None:
    with (run_dir / "report.md").open("w", encoding="utf-8") as f:
        f.write("# Anchor Residual Correction Probe\n\n")
        f.write("## Framing\n")
        f.write("- Backbone: public-best `catboost_md2y_core_recencyexp20` anchor.\n")
        f.write("- Target: learn bounded Revenue log-residual corrections from anchor OOF errors.\n")
        f.write("- COGS is frozen from the anchor to avoid cross-target instability.\n")
        f.write("- Time-forward validation only trains correction on earlier folds and evaluates later folds.\n\n")
        f.write("## Time-Forward Summary\n")
        f.write(summary.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Exported Candidates\n")
        f.write(exports.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting anchor residual correction probe in %s", run_dir)
    write_json(run_dir / "config.json", {"strengths": STRENGTHS, "clips": CLIPS})

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))

    logger.info("Building anchor OOF predictions")
    oof = build_anchor_oof(feature_store, base, feature_sets)
    oof.to_csv(run_dir / "anchor_oof_predictions.csv", index=False)

    feature_cols = get_feature_columns(oof)
    pd.Series(feature_cols, name="feature").to_csv(run_dir / "correction_features.csv", index=False)
    logger.info("Correction feature count: %s", len(feature_cols))

    fold_metrics, predictions = evaluate_time_forward(oof, feature_cols)
    fold_metrics.to_csv(run_dir / "fold_metrics.csv", index=False)
    predictions.to_csv(run_dir / "time_forward_predictions.csv", index=False)

    summary = (
        fold_metrics.groupby(["candidate_id", "strength", "clip"], as_index=False)
        .agg(
            revenue_mae=("revenue_mae", "mean"),
            cogs_mae=("cogs_mae", "mean"),
            combined_mae=("combined_mae", "mean"),
            anchor_revenue_mae=("anchor_revenue_mae", "mean"),
            anchor_combined_mae=("anchor_combined_mae", "mean"),
            delta_combined_vs_anchor=("delta_combined_vs_anchor", "mean"),
        )
        .sort_values(["combined_mae", "delta_combined_vs_anchor"])
    )
    summary.to_csv(run_dir / "summary.csv", index=False)

    public_frame = build_public_frame(base)
    exports = export_public_candidates(oof, public_frame, feature_cols, summary, run_dir)
    exports.to_csv(run_dir / "exports.csv", index=False)
    write_report(run_dir, summary, exports)

    logger.info("Best candidate: %s", summary.iloc[0]["candidate_id"])
    logger.info("Saved summary to %s", run_dir / "summary.csv")


if __name__ == "__main__":
    main()
