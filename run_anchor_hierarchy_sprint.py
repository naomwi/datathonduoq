from __future__ import annotations

from pathlib import Path

import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json
from run_leaderboard_sprint import build_summary, evaluate_candidate, export_final_submission
from train_recursive_forecast import ensure_inputs, get_candidate_feature_sets


RUN_PREFIX = "anchor_hierarchy_sprint"
OUTPUT_SUBMISSION_PATH = Path("dataset") / "submission_catboost_md2y_core_hierarchy_lite.csv"

ANCHOR_CANDIDATE = {
    "candidate_id": "catboost_md2y_core",
    "kind": "model",
    "model_family": "catboost",
    "revenue_experiment": "curated_promo_cogs",
    "cogs_experiment": "curated_promo_cogs",
    "promo_future_policy": "seasonal_month_day_recent_2y",
    "context_future_policy": "zero",
    "hierarchy_future_policy": "zero",
    "cogs_postprocess_variant": "blend60_clip_q99",
}

CHALLENGER_CANDIDATE = {
    "candidate_id": "catboost_md2y_core_hierarchy_lite",
    "kind": "model",
    "model_family": "catboost",
    "revenue_experiment": "curated_promo_cogs_hierarchy_lite",
    "cogs_experiment": "curated_promo_cogs_hierarchy_lite",
    "promo_future_policy": "seasonal_month_day_recent_2y",
    "context_future_policy": "zero",
    "hierarchy_future_policy": "seasonal_month_day_recent_2y",
    "cogs_postprocess_variant": "blend60_clip_q99",
}


def build_decision_summary(summary_df: pd.DataFrame) -> pd.DataFrame:
    summary_map = {str(row["candidate_id"]): row for _, row in summary_df.iterrows()}
    anchor = summary_map[ANCHOR_CANDIDATE["candidate_id"]]
    challenger = summary_map[CHALLENGER_CANDIDATE["candidate_id"]]
    return pd.DataFrame(
        [
            {
                "anchor_candidate_id": anchor["candidate_id"],
                "challenger_candidate_id": challenger["candidate_id"],
                "anchor_recent_weighted_combined_mae": anchor["recent_weighted_combined_mae"],
                "challenger_recent_weighted_combined_mae": challenger["recent_weighted_combined_mae"],
                "delta_recent_weighted_combined_mae": (
                    challenger["recent_weighted_combined_mae"] - anchor["recent_weighted_combined_mae"]
                ),
                "anchor_recent_tail_revenue_mae": anchor["recent_tail_revenue_mae"],
                "challenger_recent_tail_revenue_mae": challenger["recent_tail_revenue_mae"],
                "delta_recent_tail_revenue_mae": (
                    challenger["recent_tail_revenue_mae"] - anchor["recent_tail_revenue_mae"]
                ),
                "anchor_revenue_rmse_mean": anchor["revenue_rmse_mean"],
                "challenger_revenue_rmse_mean": challenger["revenue_rmse_mean"],
                "delta_revenue_rmse_mean": challenger["revenue_rmse_mean"] - anchor["revenue_rmse_mean"],
                "anchor_cogs_mae_mean": anchor["cogs_mae_mean"],
                "challenger_cogs_mae_mean": challenger["cogs_mae_mean"],
                "delta_cogs_mae_mean": challenger["cogs_mae_mean"] - anchor["cogs_mae_mean"],
                "challenger_passes_submit_gate": challenger["passes_submit_gate"],
                "challenger_beats_anchor": bool(
                    challenger["recent_weighted_combined_mae"] < anchor["recent_weighted_combined_mae"]
                ),
            }
        ]
    )


def write_report(run_dir: Path, summary_df: pd.DataFrame, decision_df: pd.DataFrame) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Anchor Hierarchy Sprint\n\n")
        f.write("## Framing\n")
        f.write("- Anchor: `catboost_md2y_core`\n")
        f.write("- Challenger: `catboost_md2y_core_hierarchy_lite`\n")
        f.write("- Question: does `hierarchy_lite` improve the current full-promo anchor?\n\n")
        f.write("## Candidate Summary\n")
        f.write(
            summary_df[
                [
                    "candidate_id",
                    "revenue_experiment",
                    "revenue_n_features",
                    "cogs_n_features",
                    "recent_weighted_combined_mae",
                    "recent_tail_revenue_mae",
                    "revenue_rmse_mean",
                    "cogs_mae_mean",
                    "passes_submit_gate",
                ]
            ].to_markdown(index=False)
        )
        f.write("\n\n")
        f.write("## Decision\n")
        f.write(decision_df.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting anchor hierarchy sprint in %s", run_dir)

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    candidates = [ANCHOR_CANDIDATE, CHALLENGER_CANDIDATE]
    write_json(run_dir / "candidates.json", {"candidates": candidates})

    fold_frames = [evaluate_candidate(candidate, feature_store, base, feature_sets) for candidate in candidates]
    fold_df = pd.concat(fold_frames, ignore_index=True)
    fold_df.to_csv(run_dir / "fold_results.csv", index=False)

    summary_df = build_summary(fold_df)
    feature_meta = pd.DataFrame(
        [
            {
                "candidate_id": candidate["candidate_id"],
                "revenue_n_features": len(feature_sets[str(candidate["revenue_experiment"])]),
                "cogs_n_features": len(feature_sets[str(candidate["cogs_experiment"])]),
            }
            for candidate in candidates
        ]
    )
    summary_df = summary_df.merge(feature_meta, on="candidate_id", how="left")
    summary_df.to_csv(run_dir / "summary.csv", index=False)

    decision_df = build_decision_summary(summary_df)
    decision_df.to_csv(run_dir / "decision_summary.csv", index=False)
    write_report(run_dir, summary_df, decision_df)

    challenger_row = decision_df.iloc[0]
    if bool(challenger_row["challenger_passes_submit_gate"]) and bool(challenger_row["challenger_beats_anchor"]):
        export_final_submission(
            CHALLENGER_CANDIDATE,
            feature_store,
            base,
            feature_sets,
            OUTPUT_SUBMISSION_PATH,
        )
        export_final_submission(
            CHALLENGER_CANDIDATE,
            feature_store,
            base,
            feature_sets,
            run_dir / OUTPUT_SUBMISSION_PATH.name,
        )
        logger.info("Exported challenger submission to %s", OUTPUT_SUBMISSION_PATH)

    logger.info("Saved summary to %s", run_dir / "summary.csv")
    logger.info("Saved decision summary to %s", run_dir / "decision_summary.csv")
    if not summary_df.empty:
        logger.info("Top candidate: %s", summary_df.iloc[0]["candidate_id"])


if __name__ == "__main__":
    main()
