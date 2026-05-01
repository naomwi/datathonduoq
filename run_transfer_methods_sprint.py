from __future__ import annotations

from pathlib import Path

import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json
from run_leaderboard_sprint import build_summary, evaluate_candidate, export_final_submission
from train_recursive_forecast import ensure_inputs, get_candidate_feature_sets


RUN_PREFIX = "transfer_methods_sprint"

ANCHOR_CANDIDATE = {
    "candidate_id": "catboost_md2y_core_anchor",
    "kind": "model",
    "model_family": "catboost",
    "revenue_experiment": "curated_promo_cogs",
    "cogs_experiment": "curated_promo_cogs",
    "promo_future_policy": "seasonal_month_day_recent_2y",
    "context_future_policy": "zero",
    "price_future_policy": "zero",
    "hierarchy_future_policy": "zero",
    "cogs_postprocess_variant": "blend60_clip_q99",
}

CHALLENGER_CANDIDATES = [
    {
        "candidate_id": "catboost_md2y_core_promo_counters",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs_promo_research",
        "cogs_experiment": "curated_promo_cogs_promo_research",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "price_future_policy": "zero",
        "hierarchy_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
    },
    {
        "candidate_id": "catboost_md2y_core_targetplus",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs_target_history_plus",
        "cogs_experiment": "curated_promo_cogs_target_history_plus",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "price_future_policy": "zero",
        "hierarchy_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
    },
    {
        "candidate_id": "catboost_md2y_core_price_history",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs_price_history",
        "cogs_experiment": "curated_promo_cogs_price_history",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "price_future_policy": "seasonal_month_day_recent_2y",
        "hierarchy_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
    },
    {
        "candidate_id": "catboost_md2y_core_research_blocks",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs_research_blocks",
        "cogs_experiment": "curated_promo_cogs_research_blocks",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "price_future_policy": "seasonal_month_day_recent_2y",
        "hierarchy_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
    },
]


def _summary_by_id(summary_df: pd.DataFrame) -> dict[str, pd.Series]:
    return {str(row["candidate_id"]): row for _, row in summary_df.iterrows()}


def build_feature_inventory(feature_sets: dict[str, list[str]]) -> pd.DataFrame:
    relevant_feature_sets = [
        "curated_promo_cogs",
        "curated_promo_cogs_promo_research",
        "curated_promo_cogs_target_history_plus",
        "curated_promo_cogs_price_history",
        "curated_promo_cogs_research_blocks",
    ]
    return pd.DataFrame(
        [
            {"feature_set": name, "n_features": len(feature_sets[name])}
            for name in relevant_feature_sets
            if name in feature_sets
        ]
    )


def build_decision_frame(summary_df: pd.DataFrame) -> pd.DataFrame:
    summary_map = _summary_by_id(summary_df)
    anchor = summary_map[ANCHOR_CANDIDATE["candidate_id"]]
    rows: list[dict[str, object]] = []

    for candidate in CHALLENGER_CANDIDATES:
        row = summary_map[candidate["candidate_id"]]
        rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "revenue_experiment": row["revenue_experiment"],
                "recent_weighted_combined_mae": row["recent_weighted_combined_mae"],
                "recent_tail_revenue_mae": row["recent_tail_revenue_mae"],
                "revenue_rmse_mean": row["revenue_rmse_mean"],
                "cogs_mae_mean": row["cogs_mae_mean"],
                "delta_recent_weighted_vs_anchor": (
                    row["recent_weighted_combined_mae"] - anchor["recent_weighted_combined_mae"]
                ),
                "delta_recent_tail_revenue_vs_anchor": (
                    row["recent_tail_revenue_mae"] - anchor["recent_tail_revenue_mae"]
                ),
                "delta_revenue_rmse_vs_anchor": row["revenue_rmse_mean"] - anchor["revenue_rmse_mean"],
                "delta_cogs_mae_vs_anchor": row["cogs_mae_mean"] - anchor["cogs_mae_mean"],
                "passes_submit_gate": row["passes_submit_gate"],
                "beats_anchor": bool(row["recent_weighted_combined_mae"] < anchor["recent_weighted_combined_mae"]),
            }
        )

    return pd.DataFrame(rows).sort_values("delta_recent_weighted_vs_anchor").reset_index(drop=True)


def write_report(
    run_dir: Path,
    feature_inventory: pd.DataFrame,
    summary_df: pd.DataFrame,
    decision_df: pd.DataFrame,
) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Transfer Methods Sprint\n\n")
        f.write("## Framing\n")
        f.write("- Anchor: `catboost_md2y_core` on `curated_promo_cogs`\n")
        f.write("- Research blocks applied: promo counters, target-history robust stats, price-history features\n")
        f.write("- Goal: test Rossmann/Favorita-style transferable methods without changing the legacy anchor feature set\n\n")
        f.write("## Feature Set Sizes\n")
        f.write(feature_inventory.to_markdown(index=False))
        f.write("\n\n")
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
    logger.info("Starting transfer methods sprint in %s", run_dir)

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    feature_inventory = build_feature_inventory(feature_sets)

    candidates = [ANCHOR_CANDIDATE] + CHALLENGER_CANDIDATES
    write_json(
        run_dir / "candidates.json",
        {
            "candidates": candidates,
            "feature_set_sizes": feature_inventory.to_dict(orient="records"),
        },
    )

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

    decision_df = build_decision_frame(summary_df)
    decision_df.to_csv(run_dir / "decision_summary.csv", index=False)
    write_report(run_dir, feature_inventory, summary_df, decision_df)

    eligible = decision_df.loc[decision_df["passes_submit_gate"] & decision_df["beats_anchor"]].copy()
    if not eligible.empty:
        best_id = str(eligible.iloc[0]["candidate_id"])
        candidate_map = {str(candidate["candidate_id"]): candidate for candidate in candidates}
        dataset_path = Path("dataset") / f"submission_{best_id}.csv"
        run_path = run_dir / dataset_path.name
        export_final_submission(candidate_map[best_id], feature_store, base, feature_sets, dataset_path)
        export_final_submission(candidate_map[best_id], feature_store, base, feature_sets, run_path)
        logger.info("Exported best challenger submission to %s", dataset_path)

    if not summary_df.empty:
        logger.info("Top candidate: %s", summary_df.iloc[0]["candidate_id"])
    logger.info("Saved summary to %s", run_dir / "summary.csv")
    logger.info("Saved decision summary to %s", run_dir / "decision_summary.csv")


if __name__ == "__main__":
    main()
