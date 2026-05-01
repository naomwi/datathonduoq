"""
TabPFN v2 Recursive Revenue Forecasting
Uses TabPFNRegressor as a drop-in replacement for CatBoost in the recursive pipeline.
- Feature subset: top importance features from CatBoost (TabPFN works best with <500 features)
- COGS: frozen to recencyexp20 anchor
- Recency weighting: not natively supported by TabPFN, so we use recent-window training
"""
from __future__ import annotations

from pathlib import Path
import os
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error
from datetime import datetime

from train_recursive_forecast import (
    ensure_inputs, get_candidate_feature_sets, apply_future_promo_policy,
    BACKTEST_FOLDS, TRAIN_END, build_feature_row, build_sample_weights,
    recursive_forecast, make_regressor, fit_regressor,
)
from feature_pipeline import get_ablation_feature_groups

RUN_PREFIX = "tabpfn_recursive"
DATASET_DIR = Path("dataset")
LOGS_DIR = Path("logs")

# TabPFN works best with fewer features — we'll use importance-based selection
MAX_FEATURES = int(os.getenv("TABPFN_MAX_FEATURES", "50"))
N_ESTIMATORS = int(os.getenv("TABPFN_N_ESTIMATORS", "2"))
PUBLISH_TO_DATASET = False


def get_tabpfn_device() -> str:
    """Prefer CUDA when available, but keep the probe runnable on CPU-only machines."""
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def get_top_catboost_features(feature_store, features, n_top=100, train_end_date="2019-12-31"):
    """Train a quick CatBoost to extract top feature importances for TabPFN."""
    from catboost import CatBoostRegressor
    
    train_mask = feature_store["Date"] <= pd.Timestamp(train_end_date)
    train_df = feature_store.loc[train_mask]
    
    # Quick CatBoost for feature importance
    model = CatBoostRegressor(
        iterations=300, learning_rate=0.05, depth=6,
        verbose=False, allow_writing_files=False, random_seed=42
    )
    X = train_df[features].fillna(0)
    y = train_df["Revenue"]
    model.fit(X, y)
    
    importances = pd.Series(model.feature_importances_, index=features)
    top_features = importances.nlargest(n_top).index.tolist()
    print(f"Selected top {len(top_features)} features from CatBoost importance ranking through {train_end_date}")
    return top_features


def evaluate_tabpfn_candidate(
    candidate_id, revenue_features, feature_store, base, cogs_preds_by_fold,
    train_window_days=1095  # 3 years — TabPFN works better with recent data
):
    """Recursive forecast using TabPFN for Revenue prediction."""
    from tabpfn import TabPFNRegressor
    
    rows = []
    for fold_id, (start_date, end_date) in enumerate(BACKTEST_FOLDS, start=1):
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        cutoff = start_ts - pd.Timedelta(days=1)
        
        adjusted_base = apply_future_promo_policy(base, cutoff, "seasonal_month_day_recent_2y")
        
        # Filter training data — TabPFN benefits from recent, smaller datasets
        train_start = cutoff - pd.Timedelta(days=train_window_days)
        train_mask = (feature_store["Date"] >= train_start) & (feature_store["Date"] <= cutoff)
        train_df = feature_store.loc[train_mask].copy()
        frozen_cogs = cogs_preds_by_fold[fold_id].copy()
        frozen_cogs["Date"] = pd.to_datetime(frozen_cogs["Date"])
        cogs_map = frozen_cogs.set_index("Date")["COGS_pred"].to_dict()
        
        print(f"  Fold {fold_id}: Training TabPFN on {len(train_df)} samples, {len(revenue_features)} features")
        
        # Fit TabPFN
        X_train = train_df[revenue_features].fillna(0).values
        y_train = train_df["Revenue"].values
        
        model = TabPFNRegressor(device=get_tabpfn_device(), n_estimators=N_ESTIMATORS)
        model.fit(X_train, y_train)
        
        # Recursive inference
        history = train_df[["Date", "Revenue", "COGS"]].copy().set_index("Date").sort_index()
        promo_indexed = adjusted_base.set_index("Date")
        
        forecast_mask = (adjusted_base["Date"] >= start_ts) & (adjusted_base["Date"] <= end_ts)
        forecast_dates = adjusted_base.loc[forecast_mask, "Date"].tolist()
        
        results = []
        for current_date in forecast_dates:
            row_features = build_feature_row(
                current_date, history, promo_indexed, None, revenue_features
            )
            X_pred = row_features[revenue_features].fillna(0).values
            pred_rev = float(model.predict(X_pred)[0])
            pred_rev = max(pred_rev, 0.0)
            pred_cogs = float(cogs_map.get(current_date, 0.0))

            history.loc[current_date, "Revenue"] = pred_rev
            history.loc[current_date, "COGS"] = pred_cogs
            results.append({"Date": current_date, "Revenue_pred": pred_rev})
        
        preds = pd.DataFrame(results)
        merged_preds = preds.merge(frozen_cogs, on="Date", how="left")
        
        truth = feature_store.loc[
            (feature_store["Date"] >= start_ts) & (feature_store["Date"] <= end_ts),
            ["Date", "Revenue", "COGS"]
        ].copy()
        eval_df = truth.merge(merged_preds, on="Date", how="left")
        
        rev_mae = mean_absolute_error(eval_df["Revenue"], eval_df["Revenue_pred"])
        cogs_mae = mean_absolute_error(eval_df["COGS"], eval_df["COGS_pred"])
        combined_mae = 0.5 * (rev_mae + cogs_mae)
        
        print(f"    Revenue MAE: {rev_mae:,.0f} | COGS MAE: {cogs_mae:,.0f} | Combined: {combined_mae:,.0f}")
        
        rows.append({
            "candidate_id": candidate_id,
            "fold": fold_id,
            "revenue_mae": rev_mae,
            "cogs_mae": cogs_mae,
            "combined_mae": combined_mae,
        })
    
    return pd.DataFrame(rows)


def get_base_cogs_predictions(feature_store, base, feature_sets):
    """Compute frozen COGS from recencyexp20 anchor."""
    print("Pre-computing Anchor COGS predictions across all folds...")
    cogs_preds_by_fold = {}
    for fold_id, (start_date, end_date) in enumerate(BACKTEST_FOLDS, start=1):
        cutoff = pd.Timestamp(start_date) - pd.Timedelta(days=1)
        adjusted_base = apply_future_promo_policy(base, cutoff, "seasonal_month_day_recent_2y")
        preds = recursive_forecast(
            feature_store=feature_store, full_base=adjusted_base,
            train_end_date=cutoff,
            forecast_start=pd.Timestamp(start_date), forecast_end=pd.Timestamp(end_date),
            revenue_features=feature_sets["curated_promo_cogs"],
            cogs_features=feature_sets["curated_promo_cogs"],
            cogs_postprocess_variant="blend60_clip_q99",
            sample_weight_mode="exp_years", sample_weight_decay=0.20
        )
        cogs_preds_by_fold[fold_id] = preds[["Date", "COGS_pred"]].copy()
    return cogs_preds_by_fold


def main():
    run_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = LOGS_DIR / f"{run_time}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    print("Loading data...")
    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    
    # Get feature schema
    groups = get_ablation_feature_groups(feature_store.head(1))
    full_features = list(dict.fromkeys(
        groups["calendar"] + groups["revenue_history"] + groups["cogs_history"] +
        groups["promo"] + groups["promo_research"] + groups["promo_detail"]
    ))
    
    # Select top features for TabPFN efficiency
    print(f"Full feature set: {len(full_features)} features. Selecting top {MAX_FEATURES}...")
    top_features = get_top_catboost_features(
        feature_store,
        full_features,
        n_top=MAX_FEATURES,
        train_end_date=pd.Timestamp(BACKTEST_FOLDS[0][0]) - pd.Timedelta(days=1),
    )
    pd.Series(top_features, name="feature").to_csv(run_dir / "selected_features.csv", index=False)
    
    # Frozen COGS
    cogs_preds_by_fold = get_base_cogs_predictions(feature_store, base, feature_sets)
    
    # Candidates with different training windows
    candidates = [
        {"candidate_id": f"tabpfn_top{MAX_FEATURES}_3y_e{N_ESTIMATORS}", "train_window_days": 1095},
    ]
    
    all_results = []
    for candidate in candidates:
        c_id = candidate["candidate_id"]
        print(f"\n=== Evaluating {c_id} ===")
        fold_df = evaluate_tabpfn_candidate(
            c_id, top_features, feature_store, base, cogs_preds_by_fold,
            train_window_days=candidate["train_window_days"]
        )
        all_results.append(fold_df)
    
    summary = pd.concat(all_results, ignore_index=True)
    summary_agg = summary.groupby("candidate_id").agg(
        revenue_mae_mean=("revenue_mae", "mean"),
        cogs_mae_mean=("cogs_mae", "mean"),
        combined_mae_mean=("combined_mae", "mean"),
    ).sort_values("combined_mae_mean")
    
    summary.to_csv(run_dir / "fold_results.csv", index=False)
    summary_agg.to_csv(run_dir / "summary.csv")
    
    print("\n=== RESULTS ===")
    print(summary_agg.to_string())
    
    # Export best candidate submission
    best_id = summary_agg.index[0]
    best_config = next(c for c in candidates if c["candidate_id"] == best_id)
    print(f"\nExporting submission for {best_id}...")
    
    from tabpfn import TabPFNRegressor
    
    train_end = pd.Timestamp(TRAIN_END)
    train_start = train_end - pd.Timedelta(days=best_config["train_window_days"])
    train_mask = (feature_store["Date"] >= train_start) & (feature_store["Date"] <= train_end)
    train_df = feature_store.loc[train_mask]
    
    X_train = train_df[top_features].fillna(0).values
    y_train = train_df["Revenue"].values
    
    model = TabPFNRegressor(device=get_tabpfn_device(), n_estimators=N_ESTIMATORS)
    model.fit(X_train, y_train)
    
    adjusted_base = apply_future_promo_policy(base, train_end, "seasonal_month_day_recent_2y")
    history = train_df[["Date", "Revenue", "COGS"]].copy().set_index("Date").sort_index()
    promo_indexed = adjusted_base.set_index("Date")
    
    forecast_dates = pd.date_range("2023-01-01", "2024-07-01")
    
    # Load anchor COGS submission
    try:
        pub_cogs = pd.read_csv("dataset/submission_catboost_md2y_core_recencyexp20.csv")[["Date", "COGS"]]
        pub_cogs["Date"] = pd.to_datetime(pub_cogs["Date"])
        cogs_map = pub_cogs.set_index("Date")["COGS"].to_dict()
    except FileNotFoundError:
        cogs_map = {}
    
    results = []
    for d in forecast_dates:
        row_features = build_feature_row(d, history, promo_indexed, None, top_features)
        X_pred = row_features[top_features].fillna(0).values
        pred_rev = max(float(model.predict(X_pred)[0]), 0.0)
        
        history.loc[d, "Revenue"] = pred_rev
        history.loc[d, "COGS"] = cogs_map.get(d, 0.0)
        results.append({"Date": d, "Revenue": pred_rev, "COGS": cogs_map.get(d, 0.0)})
    
    submission = pd.DataFrame(results)
    submission["Date"] = submission["Date"].dt.strftime("%Y-%m-%d")
    out_path = run_dir / f"submission_{best_id}.csv"
    submission.to_csv(out_path, index=False)
    if PUBLISH_TO_DATASET:
        submission.to_csv(DATASET_DIR / f"submission_{best_id}.csv", index=False)
    print(f"Exported: {out_path}")
    print("Done.")


if __name__ == "__main__":
    main()
