import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shap
from pathlib import Path

# Import from existing codebase
from train_recursive_forecast import (
    ensure_inputs,
    get_candidate_feature_sets,
    make_regressor,
    fit_regressor,
    TRAIN_END
)

def main():
    print("Loading data...")
    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    
    # We will analyze the revenue anchor model using baseline_plus_promo features
    # which is the core anchor used in most experiments
    features = feature_sets["baseline_plus_promo"]
    
    train_mask = feature_store["Date"] <= TRAIN_END
    train_df = feature_store.loc[train_mask].copy()
    
    X = train_df[features]
    y = train_df["Revenue"]
    
    print(f"Training CatBoost model on {len(X)} rows and {len(features)} features...")
    model = make_regressor("catboost")
    fit_regressor(model, X, y, "catboost")
    
    print("Computing SHAP values...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    
    out_dir = Path("logs/shap_analysis")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating Global SHAP Summary Plot...")
    plt.figure(figsize=(8, 5))
    shap.summary_plot(shap_values, X, show=False, max_display=10)
    plt.title("SHAP Summary: Top 10 Most Important Features (Revenue)", pad=20)
    plt.tight_layout()
    summary_path = out_dir / "shap_summary_plot_compact.png"
    plt.savefig(summary_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    # Save the mean absolute SHAP values to CSV
    mean_shap = np.abs(shap_values).mean(axis=0)
    importance_df = pd.DataFrame({
        "feature": features,
        "mean_abs_shap": mean_shap
    }).sort_values("mean_abs_shap", ascending=False)
    
    csv_path = out_dir / "shap_feature_importance.csv"
    importance_df.to_csv(csv_path, index=False)
    
    print(f"SHAP analysis complete. Outputs saved to {out_dir}")

if __name__ == "__main__":
    main()
