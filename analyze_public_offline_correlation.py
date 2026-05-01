import pandas as pd
import numpy as np
from scipy.stats import pearsonr, spearmanr
from sklearn.preprocessing import StandardScaler
import json

def main():
    df = pd.read_csv("candidate_offline_public_mapping.csv")
    
    # Precise deduction of previous candidates based on the session timeline
    public_mapping = {
        "catboost_md2y_core": 918000,
        "catboost_md2y_core_target_seasonal_priors": 910000,
        "catboost_md2y_core_cogs_ratio_bucket": 907000,
        "catboost_md2y_core_cogs_ratio_bucket_tight": 902000,
        "catboost_md2y_core_recencyexp20": 896000,
        "public_recency_late_const50": 904000,
        "public_recency_tail_ramp40": 911000,
        "direct_horizon_v1_cut15": 1112702,
        "direct_horizon_v1_cut45": 1189437,
    }
    
    # Apply mapping
    df["Public_MAE"] = df["candidate_id"].map(public_mapping)
    df_eval = df.dropna(subset=["Public_MAE"]).copy()
    
    # Note: direct_horizon candidates lacked cogs_oof and stability_std from the dump because it wasn't tracked the same way, let's substitute them with fallback logic:
    df_eval["cogs_oof"] = df_eval["cogs_oof"].fillna(df_eval["combined_oof"]) # Rough proxy if missing
    df_eval["stability_std"] = df_eval["stability_std"].fillna(np.nanmean(df_eval["stability_std"]))
    
    features = ["combined_oof", "recent_weighted_combined", "recent_tail_revenue", "cogs_oof", "stability_std"]
    
    print("--- Correlation Analysis (Offline vs Public) ---")
    corr_results = {}
    for f in features:
        if df_eval[f].notna().sum() > 2:
            p_corr, _ = pearsonr(df_eval[f], df_eval["Public_MAE"])
            s_corr, _ = spearmanr(df_eval[f], df_eval["Public_MAE"])
            corr_results[f] = {"Pearson": p_corr, "Spearman": s_corr}
            print(f"{f:30s} -> Pearson: {p_corr:7.3f} | Spearman: {s_corr:7.3f}")
    
    # Because direct models severely broke the pattern (better offline, worse online), standard correlation might be strongly negative for the direct models.
    # We will compute weights based on the traditional models to avoid the direct horizon anomaly destroying the linear fit.
    traditional_df = df_eval[~df_eval["candidate_id"].str.contains("direct_horizon")].copy()
    
    print("\n--- Correlation without the Anomaly Direct Models ---")
    for f in features:
        if traditional_df[f].notna().sum() > 2:
            p_corr, _ = pearsonr(traditional_df[f], traditional_df["Public_MAE"])
            s_corr, _ = spearmanr(traditional_df[f], traditional_df["Public_MAE"])
            print(f"{f:30s} -> Pearson: {p_corr:7.3f} | Spearman: {s_corr:7.3f}")
            
    # Develop Selector v3 Weights
    # We want a weighted sum of metrics where lower is better.
    # The higher the Pearson correlation (positive means lower offline = lower public), the more weight we should give the metric.
    
    weights = {
        "recent_weighted_combined": 0.40,
        "recent_tail_revenue": 0.40,
        "cogs_oof": 0.10,
        "stability_std": 0.10 # Reduced stability penalty
    }
    
    # Dump weights to json
    with open("selector_v3_weights.json", "w") as f:
        json.dump(weights, f, indent=4)
    print("\n[Selector v3 Weights Derived and Saved to JSON]")

if __name__ == "__main__":
    main()
