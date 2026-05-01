from __future__ import annotations

from pathlib import Path

import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json
from run_leaderboard_sprint import build_summary, evaluate_candidate, export_final_submission
from train_recursive_forecast import ensure_inputs, get_candidate_feature_sets


RUN_PREFIX = "breakthrough_catboost_sprint"
DATASET_DIR = Path("dataset")
ANCHOR_ID = "catboost_md2y_core_recencyexp20"


def core_candidate(candidate_id: str, **overrides: object) -> dict[str, object]:
    candidate: dict[str, object] = {
        "candidate_id": candidate_id,
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "sample_weight_mode": "exp_years",
        "sample_weight_decay": 0.20,
    }
    candidate.update(overrides)
    return candidate


CANDIDATES = [
    core_candidate(ANCHOR_ID),
    # Revenue feature decoupling: keep the proven COGS family, vary only Revenue signals.
    core_candidate("rev_baseline_plus_promo_recency20", revenue_experiment="baseline_plus_promo"),
    core_candidate("rev_forecast_core_strict_recency20", revenue_experiment="forecast_core_strict"),
    core_candidate("rev_forecast_core_promo_slim_recency20", revenue_experiment="forecast_core_promo_slim"),
    core_candidate("rev_targetplus_cogs_anchor_recency20", revenue_experiment="curated_promo_cogs_target_history_plus"),
    # Local CatBoost parameter probes around the 896k public anchor.
    core_candidate(
        "core_d4_l2_10_lr03_it900_recency20",
        model_params_override={"depth": 4, "l2_leaf_reg": 10.0, "learning_rate": 0.03, "iterations": 900},
    ),
    core_candidate(
        "core_d5_l2_6_lr025_it1200_recency20",
        model_params_override={"depth": 5, "l2_leaf_reg": 6.0, "learning_rate": 0.025, "iterations": 1200},
    ),
    core_candidate(
        "core_d4_l2_30_lr04_it1200_recency20",
        model_params_override={"depth": 4, "l2_leaf_reg": 30.0, "learning_rate": 0.04, "iterations": 1200},
    ),
    core_candidate(
        "core_d7_l2_6_lr02_it1200_recency20",
        model_params_override={"depth": 7, "l2_leaf_reg": 6.0, "learning_rate": 0.02, "iterations": 1200},
    ),
    core_candidate(
        "core_seed123_recency20",
        model_params_override={"random_seed": 123},
    ),
    core_candidate(
        "core_seed2026_recency20",
        model_params_override={"random_seed": 2026},
    ),
]


def add_anchor_deltas(summary: pd.DataFrame) -> pd.DataFrame:
    out = summary.copy()
    anchor_rows = out.loc[out["candidate_id"] == ANCHOR_ID]
    if anchor_rows.empty:
        return out
    anchor = anchor_rows.iloc[0]
    for metric in [
        "selector_score",
        "combined_mae_mean",
        "recent_weighted_combined_mae",
        "recent_tail_combined_mae",
        "revenue_mae_mean",
        "recent_weighted_revenue_mae",
        "recent_tail_revenue_mae",
        "cogs_mae_mean",
    ]:
        out[f"{metric}_delta_vs_public_anchor"] = out[metric] - float(anchor[metric])
    out["beats_public_anchor_selector"] = out["selector_score"] < float(anchor["selector_score"])
    out["beats_public_anchor_recent"] = out["recent_weighted_combined_mae"] < float(
        anchor["recent_weighted_combined_mae"]
    )
    out["beats_public_anchor_tail"] = out["recent_tail_combined_mae"] < float(anchor["recent_tail_combined_mae"])
    return out


def choose_exports(summary: pd.DataFrame) -> list[str]:
    candidates = summary.loc[
        (summary["candidate_id"] != ANCHOR_ID)
        & (
            summary.get("beats_public_anchor_selector", False)
            | summary.get("beats_public_anchor_recent", False)
        )
    ].copy()
    if candidates.empty:
        return []
    return candidates.sort_values(
        ["selector_score", "recent_weighted_combined_mae", "recent_tail_combined_mae"]
    )["candidate_id"].head(3).tolist()


def write_report(run_dir: Path, summary: pd.DataFrame, fold_df: pd.DataFrame, exported: list[str]) -> None:
    with (run_dir / "report.md").open("w", encoding="utf-8") as f:
        f.write("# Breakthrough CatBoost Sprint\n\n")
        f.write("## Framing\n")
        f.write("- Goal: quick-but-controlled probes around the 896k public anchor.\n")
        f.write("- Branches: Revenue-only feature decoupling and small CatBoost hyperparameter/seed changes.\n")
        f.write("- Export rule: only export non-anchor candidates that beat the public anchor on selector/recent/tail gates.\n\n")
        f.write("## Summary\n")
        f.write(summary.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Fold Metrics\n")
        f.write(fold_df.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Exported Candidates\n")
        if exported:
            for candidate_id in exported:
                f.write(f"- `dataset/submission_{candidate_id}.csv`\n")
        else:
            f.write("- None. No non-anchor candidate beat the public anchor gates.\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting breakthrough CatBoost sprint in %s", run_dir)
    write_json(run_dir / "config.json", {"anchor_id": ANCHOR_ID, "candidates": CANDIDATES})

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))

    fold_frames = []
    for candidate in CANDIDATES:
        logger.info("Evaluating %s", candidate["candidate_id"])
        fold_frames.append(evaluate_candidate(candidate, feature_store, base, feature_sets))

    fold_df = pd.concat(fold_frames, ignore_index=True)
    fold_df.to_csv(run_dir / "fold_results.csv", index=False)

    summary = add_anchor_deltas(build_summary(fold_df))
    summary.to_csv(run_dir / "summary.csv", index=False)

    candidate_map = {str(candidate["candidate_id"]): candidate for candidate in CANDIDATES}
    exported = choose_exports(summary)
    for candidate_id in exported:
        dataset_path = DATASET_DIR / f"submission_{candidate_id}.csv"
        run_path = run_dir / f"submission_{candidate_id}.csv"
        export_final_submission(candidate_map[candidate_id], feature_store, base, feature_sets, dataset_path)
        export_final_submission(candidate_map[candidate_id], feature_store, base, feature_sets, run_path)
        logger.info("Exported %s", candidate_id)

    write_report(run_dir, summary, fold_df, exported)
    logger.info("Exported candidates: %s", exported or "none")
    logger.info("Saved summary to %s", run_dir / "summary.csv")


if __name__ == "__main__":
    main()
