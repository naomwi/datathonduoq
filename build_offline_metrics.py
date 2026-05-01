import pandas as pd
from pathlib import Path

def main():
    logs_dir = Path("logs")
    summary_files = list(logs_dir.rglob("summary.csv"))
    
    rows = {}
    
    for f in summary_files:
        try:
            df = pd.read_csv(f)
        except Exception:
            continue
            
        # Differentiate between standard leaderboard scripts and the direct_horizon script
        for _, row in df.iterrows():
            c_id = None
            if "candidate_id" in row:
                c_id = row["candidate_id"]
            
            if not c_id:
                continue
                
            metrics = {"candidate_id": c_id}
            
            if "combined_mae_mean" in row:
                metrics["combined_oof"] = row["combined_mae_mean"]
                metrics["recent_weighted_combined"] = row.get("recent_weighted_combined_mae", np.nan if "np" not in globals() else None)
                metrics["recent_tail_revenue"] = row.get("recent_tail_revenue_mae", None)
                metrics["cogs_oof"] = row.get("cogs_mae_mean", None)
                metrics["revenue_oof"] = row.get("revenue_mae_mean", None)
                metrics["stability_std"] = row.get("combined_mae_std", row.get("revenue_mae_std", None))
            elif "c_combined_oof" in row: # Direct Horizon v1 format
                metrics["combined_oof"] = row["c_combined_oof"]
                metrics["recent_weighted_combined"] = row["c_recent_weighted"]
                metrics["recent_tail_revenue"] = row["c_late_rev"]
                metrics["cogs_oof"] = None # Direct horizon didn't log cogs alone in summary
                metrics["revenue_oof"] = None
                metrics["stability_std"] = None
                
            if c_id not in rows:
                rows[c_id] = metrics
            else:
                # Update if new values are not null
                for k, v in metrics.items():
                    if v is not None and not pd.isna(v):
                        rows[c_id][k] = v
                        
    out_df = pd.DataFrame(list(rows.values()))
    # Deduplicate and clean
    out_df = out_df.drop_duplicates(subset=["candidate_id"]).sort_values("candidate_id")
    out_df["Public_MAE"] = "" # Empty column for user mapping
    
    out_path = Path("candidate_offline_public_mapping.csv")
    out_df.to_csv(out_path, index=False)
    print(f"Dumped {len(out_df)} candidates to {out_path}.")

if __name__ == "__main__":
    import numpy as np
    main()
