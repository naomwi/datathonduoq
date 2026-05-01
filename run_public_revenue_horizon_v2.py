"""
Evaluate Revenue Horizon-binned models v2 (Recursive Feature Pruning).
Model A (Early) is used for forecast_step <= cut.
Model B (Late) is used for forecast_step > cut.
Model B aggressively prunes short-term recursive lags/rollmeans to prevent runaway feedback.
"""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from logging_utils import create_run_dir, setup_logger, write_json
from train_recursive_forecast import (
    ensure_inputs,
    get_candidate_feature_sets,
    apply_future_promo_policy,
    apply_future_context_policy,
    apply_future_price_policy,
    build_sample_weights,
    make_regressor,
    fit_regressor,
    _compute_ratio_stats,
    _compute_ratio_bucket_table,
    _transform_target_series,
    _inverse_transform_scalar,
    build_feature_row,
    _trailing_ratio,
    _apply_cogs_postprocess,
    _compute_cogs_ratio_series,
    BACKTEST_FOLDS,
    TRAIN_END,
    PROMO_RAW_COLUMNS,
    CONTEXT_POLICY_COLUMNS,
    PRICE_SIGNAL_COLUMNS,
    get_hierarchy_lite_raw_columns
)

RUN_PREFIX = "public_revenue_horizon_v2"
DATASET_DIR = Path("dataset")

CANDIDATES = [
    {
        "candidate_id": "revenue_horizon_v2_cut15",
        "horizon_cut": 15,
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "price_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "sample_weight_mode": "exp_years",
        "sample_weight_decay": 0.20,
    },
    {
        "candidate_id": "revenue_horizon_v2_cut30",
        "horizon_cut": 30,
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "price_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "sample_weight_mode": "exp_years",
        "sample_weight_decay": 0.20,
    },
    {
        "candidate_id": "revenue_horizon_v2_cut45",
        "horizon_cut": 45,
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "price_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "sample_weight_mode": "exp_years",
        "sample_weight_decay": 0.20,
    }
]

def is_stable_late_feature(f: str) -> bool:
    if f.startswith("rev_") or f.startswith("revplus_") or f.startswith("cogs_") or f.startswith("cogsplus_"):
        if f.endswith("_lag_364"): return True
        if "_ewm_" in f: return True
        return False
    if f.startswith("pricehist_"):
        return False
    return True

def recursive_horizon_forecast(
    feature_store: pd.DataFrame,
    full_base: pd.DataFrame,
    train_end_date: pd.Timestamp,
    forecast_start: pd.Timestamp,
    forecast_end: pd.Timestamp,
    revenue_features: list[str],
    cogs_features: list[str],
    horizon_cut: int,
    cogs_postprocess_variant: str = "raw",
    sample_weight_mode: str = "none",
    sample_weight_decay: float = 0.0,
) -> pd.DataFrame:
    train_mask = feature_store["Date"] <= train_end_date
    forecast_mask = (full_base["Date"] >= forecast_start) & (full_base["Date"] <= forecast_end)

    train_df = feature_store.loc[train_mask].copy()
    promo_indexed = full_base[["Date"] + PROMO_RAW_COLUMNS].copy().set_index("Date")
    context_indexed = full_base[["Date"] + CONTEXT_POLICY_COLUMNS].copy().set_index("Date")
    price_indexed = full_base[["Date"] + PRICE_SIGNAL_COLUMNS].copy().set_index("Date")
    hierarchy_columns = get_hierarchy_lite_raw_columns(full_base.columns)
    hierarchy_indexed = (
        full_base[["Date"] + hierarchy_columns].copy().set_index("Date") if hierarchy_columns else None
    )

    ratio_stats = _compute_ratio_stats(train_df)
    ratio_bucket_table = _compute_ratio_bucket_table(train_df)
    sample_weights = build_sample_weights(
        train_df["Date"],
        train_end_date=train_end_date,
        sample_weight_mode=sample_weight_mode,
        sample_weight_decay=sample_weight_decay,
    )
    
    revenue_late_features = [f for f in revenue_features if is_stable_late_feature(f)]

    revenue_model_early = make_regressor("catboost")
    revenue_model_late = make_regressor("catboost")
    cogs_model = make_regressor("catboost")

    # print(f"    -> Fitting Model A (Early, {len(revenue_features)} features)")
    fit_regressor(
        revenue_model_early,
        train_df[revenue_features],
        _transform_target_series(train_df["Revenue"], "none"),
        "catboost",
        sample_weight=sample_weights,
    )
    
    # print(f"    -> Fitting Model B (Late, {len(revenue_late_features)} features pruned)")
    fit_regressor(
        revenue_model_late,
        train_df[revenue_late_features],
        _transform_target_series(train_df["Revenue"], "none"),
        "catboost",
        sample_weight=sample_weights,
    )

    # print(f"    -> Fitting COGS")
    fit_regressor(
        cogs_model,
        train_df[cogs_features],
        _transform_target_series(train_df["COGS"], "none"),
        "catboost",
        sample_weight=sample_weights,
    )

    history = train_df[["Date", "Revenue", "COGS"]].copy().set_index("Date").sort_index()
    results: list[dict[str, float | str]] = []
    forecast_dates = full_base.loc[forecast_mask, "Date"].tolist()

    for horizon_index, current_date in enumerate(forecast_dates):
        forecast_step = horizon_index + 1
        
        promo_row = promo_indexed.loc[current_date]
        
        if forecast_step <= horizon_cut:
            active_revenue_features = revenue_features
            active_revenue_model = revenue_model_early
        else:
            active_revenue_features = revenue_late_features
            active_revenue_model = revenue_model_late

        revenue_row = build_feature_row(
            current_date,
            history,
            promo_indexed,
            context_indexed,
            active_revenue_features,
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
        
        pred_revenue = _inverse_transform_scalar(
            float(active_revenue_model.predict(revenue_row)[0]),
            "none",
        )
        
        pred_cogs_raw = _inverse_transform_scalar(
            float(cogs_model.predict(cogs_row)[0]),
            "none",
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
            cogs_target_mode="direct",
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

def evaluate_horizon_candidate(
    candidate: dict,
    feature_store: pd.DataFrame,
    base: pd.DataFrame,
    feature_sets: dict[str, list[str]],
) -> pd.DataFrame:
    c_id = candidate["candidate_id"]
    revenue_features = feature_sets[candidate["revenue_experiment"]]
    cogs_features = feature_sets[candidate["cogs_experiment"]]
    horizon_cut = candidate["horizon_cut"]

    rows = []
    print(f"Evaluating {c_id} (cut={horizon_cut})...")

    for fold_id, (start_date, end_date) in enumerate(BACKTEST_FOLDS, start=1):
        print(f"  Fold {fold_id} ({start_date} to {end_date})")
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        cutoff = start_ts - pd.Timedelta(days=1)

        adjusted_base = apply_future_promo_policy(base, cutoff, candidate["promo_future_policy"])
        adjusted_base = apply_future_context_policy(adjusted_base, cutoff, candidate["context_future_policy"])
        adjusted_base = apply_future_price_policy(adjusted_base, cutoff, candidate["price_future_policy"])

        preds = recursive_horizon_forecast(
            feature_store=feature_store,
            full_base=adjusted_base,
            train_end_date=cutoff,
            forecast_start=start_ts,
            forecast_end=end_ts,
            revenue_features=revenue_features,
            cogs_features=cogs_features,
            horizon_cut=horizon_cut,
            cogs_postprocess_variant=candidate["cogs_postprocess_variant"],
            sample_weight_mode=candidate["sample_weight_mode"],
            sample_weight_decay=candidate["sample_weight_decay"],
        )

        truth = feature_store.loc[
            (feature_store["Date"] >= start_ts) & (feature_store["Date"] <= end_ts),
            ["Date", "Revenue", "COGS"],
        ].copy()
        
        merged = truth.merge(preds, on="Date", how="left")
        merged["forecast_step"] = np.arange(1, len(merged) + 1)
        
        early_mask = merged["forecast_step"] <= horizon_cut
        late_mask = merged["forecast_step"] > horizon_cut

        rev_mae = mean_absolute_error(merged["Revenue"], merged["Revenue_pred"])
        cogs_mae = mean_absolute_error(merged["COGS"], merged["COGS_pred"])
        comb_mae = (rev_mae + cogs_mae) / 2.0
        
        rev_early_mae = mean_absolute_error(merged.loc[early_mask, "Revenue"], merged.loc[early_mask, "Revenue_pred"]) if early_mask.any() else np.nan
        rev_late_mae = mean_absolute_error(merged.loc[late_mask, "Revenue"], merged.loc[late_mask, "Revenue_pred"]) if late_mask.any() else np.nan

        rows.append({
            "candidate_id": c_id,
            "fold": fold_id,
            "horizon_cut": horizon_cut,
            "revenue_mae": rev_mae,
            "cogs_mae": cogs_mae,
            "combined_mae": comb_mae,
            "revenue_early_mae": rev_early_mae,
            "revenue_late_mae": rev_late_mae,
        })
        
    return pd.DataFrame(rows)


def build_summary(fold_df: pd.DataFrame) -> pd.DataFrame:
    summary = fold_df.groupby("candidate_id").agg(
        combined_mae_mean=("combined_mae", "mean"),
        revenue_mae_mean=("revenue_mae", "mean"),
        cogs_mae_mean=("cogs_mae", "mean"),
        revenue_early_mae_mean=("revenue_early_mae", "mean"),
        revenue_late_mae_mean=("revenue_late_mae", "mean"),
    ).reset_index()

    tail_df = fold_df[fold_df["fold"] >= 2].groupby("candidate_id").agg(
        tail_combined_mae=("combined_mae", "mean"),
        tail_revenue_late_mae=("revenue_late_mae", "mean"),
    ).reset_index()

    summary = summary.merge(tail_df, on="candidate_id", how="left")
    summary = summary.sort_values("combined_mae_mean").reset_index(drop=True)
    
    summary["beats_anchor"] = summary["combined_mae_mean"] < 603855.27
    return summary


def write_report(run_dir: Path, summary_df: pd.DataFrame, fold_df: pd.DataFrame, top_ids: list[str]) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Revenue Horizon V2 Sprint (Recursive Feature Pruning)\n\n")
        f.write("## Hypothesis\n")
        f.write("- Model A (Early) handles forecast_step <= cut using standard features.\n")
        f.write("- Model B (Late) drops short-term recursive lags to prevent exponential drift.\n")
        f.write("- Weights and hyperparameters remain identical (depth=6, recencyexp20).\n\n")
        f.write("## Candidate Ranking\n")
        f.write(summary_df.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Fold Metrics\n")
        f.write(fold_df.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Submitted Files\n")
        for candidate_id in top_ids:
            f.write(f"- `dataset/submission_{candidate_id}.csv`\n")

def export_candidate(candidate: dict, feature_store: pd.DataFrame, base: pd.DataFrame, feature_sets: dict[str, list[str]], out_path: Path):
    adjusted_base = apply_future_promo_policy(base, TRAIN_END, candidate["promo_future_policy"])
    adjusted_base = apply_future_context_policy(adjusted_base, TRAIN_END, candidate["context_future_policy"])
    adjusted_base = apply_future_price_policy(adjusted_base, TRAIN_END, candidate["price_future_policy"])

    preds = recursive_horizon_forecast(
        feature_store=feature_store,
        full_base=adjusted_base,
        train_end_date=TRAIN_END,
        forecast_start=pd.Timestamp("2023-01-01"),
        forecast_end=pd.Timestamp("2024-07-01"),
        revenue_features=feature_sets[candidate["revenue_experiment"]],
        cogs_features=feature_sets[candidate["cogs_experiment"]],
        horizon_cut=candidate["horizon_cut"],
        cogs_postprocess_variant=candidate["cogs_postprocess_variant"],
        sample_weight_mode=candidate["sample_weight_mode"],
        sample_weight_decay=candidate["sample_weight_decay"],
    )
    
    submission = preds.rename(columns={"Revenue_pred": "Revenue", "COGS_pred": "COGS"})[["Date", "Revenue", "COGS"]]
    submission["Date"] = pd.to_datetime(submission["Date"]).dt.strftime("%Y-%m-%d")
    submission.to_csv(out_path, index=False)


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting public revenue horizon v2 sprint in %s", run_dir)
    write_json(run_dir / "config.json", {"candidates": CANDIDATES})

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))

    fold_frames = [evaluate_horizon_candidate(c, feature_store, base, feature_sets) for c in CANDIDATES]
    fold_df = pd.concat(fold_frames, ignore_index=True)
    fold_df.to_csv(run_dir / "fold_results.csv", index=False)

    summary_df = build_summary(fold_df)
    summary_df.to_csv(run_dir / "summary.csv", index=False)

    top_ids = summary_df.loc[summary_df["beats_anchor"], "candidate_id"].tolist()
    if not top_ids:
        logger.info("No candidates beat anchor threshold (603,855.27). Submitting best one anyway.")
        top_ids = summary_df["candidate_id"].head(1).tolist()

    candidate_map = {str(c["candidate_id"]): c for c in CANDIDATES}
    for candidate_id in top_ids:
        dataset_path = DATASET_DIR / f"submission_{candidate_id}.csv"
        export_candidate(candidate_map[candidate_id], feature_store, base, feature_sets, dataset_path)
        logger.info("Exported submission: %s", dataset_path)

    write_report(run_dir, summary_df, fold_df, top_ids)
    logger.info("Saved summary to %s", run_dir / "summary.csv")


if __name__ == "__main__":
    main()
