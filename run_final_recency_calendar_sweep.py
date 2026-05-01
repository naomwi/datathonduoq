import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import mean_absolute_error
from datetime import datetime
import json
import itertools

from train_recursive_forecast import (
    recursive_forecast, make_regressor, fit_regressor, build_sample_weights,
    apply_future_promo_policy, apply_future_context_policy, apply_future_price_policy,
    BACKTEST_FOLDS, _transform_target_series, _inverse_transform_scalar,
    _apply_revenue_regime_variant, _apply_cogs_postprocess,
    _compute_ratio_stats, _compute_ratio_bucket_table
)
from feature_pipeline import get_ablation_feature_groups

RUN_PREFIX = "final_recency_calendar_sweep"
LOGS_DIR = Path("logs")

def get_base_cogs_predictions(feature_store, base, feature_sets):
    # RecencyExp20 Anchor
    print("Pre-computing Anchor COGS predictions across all folds...")
    cogs_preds_by_fold = {}
    for fold_id, (start_date, end_date) in enumerate(BACKTEST_FOLDS, start=1):
        cutoff = pd.Timestamp(start_date) - pd.Timedelta(days=1)
        # Standard anchor configuration
        adjusted_base = apply_future_promo_policy(base, cutoff, "seasonal_month_day_recent_2y")
        
        preds = recursive_forecast(
            feature_store=feature_store,
            full_base=adjusted_base,
            train_end_date=cutoff,
            forecast_start=pd.Timestamp(start_date),
            forecast_end=pd.Timestamp(end_date),
            revenue_features=feature_sets["core_base"],
            cogs_features=feature_sets["core_base"],
            cogs_postprocess_variant="blend60_clip_q99",
            sample_weight_mode="exp_years",
            sample_weight_decay=0.20
        )
        cogs_preds_by_fold[fold_id] = preds[["Date", "COGS_pred"]].copy()
    return cogs_preds_by_fold

def evaluate_revenue_candidate(
    candidate_id, revenue_features, decay, weight_mode, promo_policy, 
    feature_store, base, cogs_preds_by_fold
):
    rows = []
    for fold_id, (start_date, end_date) in enumerate(BACKTEST_FOLDS, start=1):
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        cutoff = start_ts - pd.Timedelta(days=1)

        adjusted_base = apply_future_promo_policy(base, cutoff, promo_policy)
        
        # We only need to run recursive_forecast for Revenue, but for code simplicity and COGS decoupling,
        # we will run it, but we replace the COGS output with our frozen COGS.
        # Wait, `recursive_forecast` requires `cogs_features`. We can just pass `core_base` and ignore it,
        # but to save 50% of the training time, we should bypass COGS training entirely.
        
        train_mask = feature_store["Date"] <= cutoff
        train_df = feature_store.loc[train_mask]
        
        sample_weights = build_sample_weights(
            train_df["Date"], train_end_date=cutoff, 
            sample_weight_mode=weight_mode, sample_weight_decay=decay
        )
        
        revenue_model = make_regressor("catboost")
        fit_regressor(revenue_model, train_df[revenue_features], train_df["Revenue"], "catboost", sample_weight=sample_weights)
        
        history = train_df[["Date", "Revenue", "COGS"]].copy().set_index("Date").sort_index()
        forecast_mask = (adjusted_base["Date"] >= start_ts) & (adjusted_base["Date"] <= end_ts)
        forecast_dates = adjusted_base.loc[forecast_mask, "Date"].tolist()
        
        from train_recursive_forecast import build_feature_row
        promo_indexed = adjusted_base.set_index("Date")
        
        results = []
        for current_date in forecast_dates:
            row_features = build_feature_row(
                current_date, history, promo_indexed, None, revenue_features
            )
            pred_rev = float(revenue_model.predict(row_features)[0])
            pred_rev = max(pred_rev, 0.0)
            history.loc[current_date, "Revenue"] = pred_rev
            history.loc[current_date, "COGS"] = 0.0  # Dummy for feature construction
            results.append({"Date": current_date, "Revenue_pred": pred_rev})
            
        preds = pd.DataFrame(results)
        
        # Merge with frozen COGS
        frozen_cogs = cogs_preds_by_fold[fold_id]
        merged_preds = preds.merge(frozen_cogs, on="Date", how="left")
        
        truth = feature_store.loc[(feature_store["Date"] >= start_ts) & (feature_store["Date"] <= end_ts), ["Date", "Revenue", "COGS"]].copy()
        eval_df = truth.merge(merged_preds, on="Date", how="left")
        
        rows.append({
            "candidate_id": candidate_id,
            "fold": fold_id,
            "revenue": revenue_features,
            "decay": decay,
            "weight_mode": weight_mode,
            "promo_policy": promo_policy,
            "revenue_mae": mean_absolute_error(eval_df["Revenue"], eval_df["Revenue_pred"]),
            "cogs_mae": mean_absolute_error(eval_df["COGS"], eval_df["COGS_pred"]),
            "combined_mae": mean_absolute_error(eval_df["Revenue"], eval_df["Revenue_pred"]) + mean_absolute_error(eval_df["COGS"], eval_df["COGS_pred"]),
            "recent_tail_revenue_mae": mean_absolute_error(
                eval_df["Revenue"].iloc[30:], eval_df["Revenue_pred"].iloc[30:]
            ) if fold_id >= 2 else np.nan
        })
    
    return pd.DataFrame(rows)

def main():
    run_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = LOGS_DIR / f"{run_time}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    print("Loading data...")
    feature_store = pd.read_csv("dataset/feature_store_main.csv", parse_dates=["Date"], low_memory=False)
    base = pd.read_csv("dataset/daily_feature_base.csv", parse_dates=["Date"], low_memory=False)
    groups = get_ablation_feature_groups(feature_store.head(1))
    
    core_features = groups["calendar"] + groups["revenue_history"] + groups["cogs_history"] + groups["promo"] + groups["promo_research"] + groups["promo_detail"]
    core_features = list(dict.fromkeys(core_features)) # Deduplicate feature names
    
    mini_families = set(groups.get("cal_eom_bom", []) + groups.get("cal_tet", []) + groups.get("cal_interact", []))
    core_base = [f for f in core_features if f not in mini_families]
    
    feature_sets = {
        "core_base": core_base,
        "core_eom": core_base + groups.get("cal_eom_bom", []),
        "core_tet": core_base + groups.get("cal_tet", []),
        "core_interact": core_base + groups.get("cal_interact", [])
    }
    
    with open("selector_v3_weights.json", "r") as f:
        selector_weights = json.load(f)
        
    cogs_preds_by_fold = get_base_cogs_predictions(feature_store, base, feature_sets)
    
    print("Starting Grid Search...")
    
    import traceback
    
    # Grid definition
    decays = [0.15, 0.20, 0.25, 0.30]
    modes = ["exp_years", "piecewise_exp"]
    promos = ["seasonal_month_day_recent_1y", "seasonal_month_day_recent_2y", "seasonal_month_day_recent_3y"]
    cals = ["core_base", "core_eom", "core_tet", "core_interact"]
    
    combinations = list(itertools.product(decays, modes, promos, cals))
    print(f"Total combinations: {len(combinations)}")
    
    all_fold_metrics = []
    summary_rows = []
    
    for idx, (decay, mode, promo, cal) in enumerate(combinations, 1):
        c_id = f"{cal}_{mode}_{int(decay*100)}_{promo.replace('seasonal_month_day_recent_', 'y')}"
        print(f"[{idx}/{len(combinations)}] Evaluating {c_id}...")
        
        try:
            fold_df = evaluate_revenue_candidate(
                c_id, feature_sets[cal], decay, mode, promo, feature_store, base, cogs_preds_by_fold
            )
            all_fold_metrics.append(fold_df)
            
            w_mae = (fold_df["combined_mae"].iloc[0] * 0.15 + fold_df["combined_mae"].iloc[1] * 0.35 + fold_df["combined_mae"].iloc[2] * 0.50)
            tail_rev = np.nanmean(fold_df["recent_tail_revenue_mae"].iloc[1:])
            cogs_oof = fold_df["cogs_mae"].mean()
            stab = fold_df["combined_mae"].std()
            
            score = (
                selector_weights["recent_weighted_combined"] * w_mae +
                selector_weights["recent_tail_revenue"] * tail_rev +
                selector_weights["cogs_oof"] * cogs_oof +
                selector_weights["stability_std"] * stab
            )
            
            summary_rows.append({
                "candidate_id": c_id,
                "proxy_score": score,
                "combined_mae_mean": fold_df["combined_mae"].mean(),
                "recent_weighted_combined_mae": w_mae,
                "recent_tail_revenue_mae": tail_rev,
                "revenue_mae_mean": fold_df["revenue_mae"].mean(),
                "cogs_mae_mean": cogs_oof,
                "combined_mae_std": stab
            })
        except Exception as e:
            with open("tb_inner.txt", "w", encoding="utf-8") as out:
                traceback.print_exc(file=out)
            break
            
    summary_df = pd.DataFrame(summary_rows).sort_values("proxy_score")
    summary_df.to_csv(run_dir / "summary.csv", index=False)
    
    pd.concat(all_fold_metrics, ignore_index=True).to_csv(run_dir / "fold_results.csv", index=False)
    print(f"Sweep complete. Ranked proxy scores saved to {run_dir / 'summary.csv'}")

if __name__ == "__main__":
    main()
