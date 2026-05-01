from __future__ import annotations

from pathlib import Path

import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json
from run_leaderboard_sprint import build_summary, evaluate_candidate, export_final_submission
from train_recursive_forecast import ensure_inputs, get_candidate_feature_sets


RUN_PREFIX = "target_seasonal_prior_sprint"

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
        "candidate_id": "catboost_md2y_core_target_seasonal_priors",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs_target_seasonal",
        "cogs_experiment": "curated_promo_cogs_target_seasonal",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
    },
]


def write_report(run_dir: Path, summary_df: pd.DataFrame, fold_df: pd.DataFrame) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Target Seasonal Prior Sprint\n\n")
        f.write("## Framing\n")
        f.write("- Compare the current CatBoost core anchor against a narrow challenger only\n")
        f.write("- Challenger adds forecast-safe target seasonal priors, not a post-hoc seasonal blend\n")
        f.write("- Added features: month/day and month/weekday Revenue/COGS priors computed from the trailing 730 days of history\n\n")
        f.write("## Candidate Ranking\n")
        f.write(summary_df.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Fold Metrics\n")
        f.write(fold_df.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting target seasonal prior sprint in %s", run_dir)
    write_json(run_dir / "config.json", {"candidates": CANDIDATES})

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))

    fold_frames = [evaluate_candidate(candidate, feature_store, base, feature_sets) for candidate in CANDIDATES]
    fold_df = pd.concat(fold_frames, ignore_index=True)
    fold_df.to_csv(run_dir / "fold_results.csv", index=False)

    summary_df = build_summary(fold_df)
    summary_df.to_csv(run_dir / "summary.csv", index=False)
    write_report(run_dir, summary_df, fold_df)

    candidate_map = {str(candidate["candidate_id"]): candidate for candidate in CANDIDATES}
    challenger_id = "catboost_md2y_core_target_seasonal_priors"
    export_final_submission(
        candidate_map[challenger_id],
        feature_store,
        base,
        feature_sets,
        Path("dataset") / f"submission_{challenger_id}.csv",
    )
    export_final_submission(
        candidate_map[challenger_id],
        feature_store,
        base,
        feature_sets,
        run_dir / f"submission_{challenger_id}.csv",
    )
    logger.info("Exported submission for %s", challenger_id)
    logger.info("Top candidate: %s", summary_df.iloc[0]["candidate_id"])


if __name__ == "__main__":
    main()
