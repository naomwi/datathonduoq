from __future__ import annotations

from pathlib import Path

import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json
from run_leaderboard_sprint import build_summary, evaluate_candidate, export_final_submission
from train_recursive_forecast import ensure_inputs, get_candidate_feature_sets


RUN_PREFIX = "recency_weighted_sprint"
DATASET_DIR = Path("dataset")

CANDIDATES = [
    {
        "candidate_id": "catboost_md2y_core",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
    },
    {
        "candidate_id": "catboost_md2y_recent_core",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "train_window_days": 1095,
    },
    {
        "candidate_id": "catboost_md2y_core_recencyexp20",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "sample_weight_mode": "exp_years",
        "sample_weight_decay": 0.20,
    },
    {
        "candidate_id": "catboost_md2y_core_recencyexp35",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "sample_weight_mode": "exp_years",
        "sample_weight_decay": 0.35,
    },
    {
        "candidate_id": "catboost_md2y_context_recencyexp20",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_context_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "seasonal_month_day_recent_2y",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "sample_weight_mode": "exp_years",
        "sample_weight_decay": 0.20,
    },
]


def write_report(run_dir: Path, summary_df: pd.DataFrame, fold_df: pd.DataFrame, top_ids: list[str]) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Recency Weighted Sprint\n\n")
        f.write("## Framing\n")
        f.write("- Goal: test soft recency weighting instead of hard shrink or hand-tuned public blends.\n")
        f.write("- Base family: CatBoost recursive core that already transfers reasonably to public.\n")
        f.write("- New branch: exponential sample weights by years-ago, keeping the full recursive pipeline unchanged.\n")
        f.write("- Comparison anchors: unweighted core and the existing 1095-day recent-window variant.\n\n")
        f.write("## Candidate Ranking\n")
        f.write(summary_df.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Fold Metrics\n")
        f.write(fold_df.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Submission Files\n")
        for candidate_id in top_ids:
            f.write(f"- `dataset/submission_{candidate_id}.csv`\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting recency weighted sprint in %s", run_dir)
    write_json(run_dir / "config.json", {"candidates": CANDIDATES})

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))

    fold_frames = [evaluate_candidate(candidate, feature_store, base, feature_sets) for candidate in CANDIDATES]
    fold_df = pd.concat(fold_frames, ignore_index=True)
    fold_df.to_csv(run_dir / "fold_results.csv", index=False)

    summary_df = build_summary(fold_df)
    summary_df.to_csv(run_dir / "summary.csv", index=False)

    top_ids = summary_df.loc[summary_df["passes_submit_gate"], "candidate_id"].head(2).tolist()

    candidate_map = {str(candidate["candidate_id"]): candidate for candidate in CANDIDATES}
    for candidate_id in top_ids:
        dataset_path = DATASET_DIR / f"submission_{candidate_id}.csv"
        run_path = run_dir / f"submission_{candidate_id}.csv"
        export_final_submission(candidate_map[candidate_id], feature_store, base, feature_sets, dataset_path)
        export_final_submission(candidate_map[candidate_id], feature_store, base, feature_sets, run_path)
        logger.info("Exported submission for %s", candidate_id)

    write_report(run_dir, summary_df, fold_df, top_ids)
    logger.info("Saved summary to %s", run_dir / "summary.csv")
    if not summary_df.empty:
        logger.info("Top candidate: %s", summary_df.iloc[0]["candidate_id"])


if __name__ == "__main__":
    main()
