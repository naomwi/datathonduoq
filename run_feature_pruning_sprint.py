from __future__ import annotations

from pathlib import Path

import pandas as pd

from feature_pipeline import get_ablation_feature_groups
from logging_utils import create_run_dir, setup_logger, write_json
from run_leaderboard_sprint import build_summary, evaluate_candidate
from train_recursive_forecast import ensure_inputs, get_candidate_feature_sets


RUN_PREFIX = "feature_pruning_sprint"
PRUNING_MODEL_PARAMS_OVERRIDE = {
    "iterations": 1200,
    "learning_rate": 0.025,
    "depth": 5,
    "l2_leaf_reg": 8.0,
}

PERFORMANCE_ANCHOR_CANDIDATE = {
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

GOVERNANCE_ANCHOR_CANDIDATE = {
    "candidate_id": "catboost_core_strict",
    "kind": "model",
    "model_family": "catboost",
    "revenue_experiment": "forecast_core_strict",
    "cogs_experiment": "forecast_core_strict",
    "promo_future_policy": "seasonal_month_day_recent_2y",
    "context_future_policy": "zero",
    "hierarchy_future_policy": "zero",
    "cogs_postprocess_variant": "blend60_clip_q99",
    "model_params_override": PRUNING_MODEL_PARAMS_OVERRIDE,
}

PRUNING_CANDIDATES = [
    {
        "candidate_id": "catboost_promo_slim",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "forecast_core_promo_slim",
        "cogs_experiment": "forecast_core_promo_slim",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "hierarchy_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "model_params_override": PRUNING_MODEL_PARAMS_OVERRIDE,
    },
    {
        "candidate_id": "catboost_promo_slim_hierarchy_lite",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "forecast_core_promo_slim_hierarchy_lite",
        "cogs_experiment": "forecast_core_promo_slim_hierarchy_lite",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "hierarchy_future_policy": "seasonal_month_day_recent_2y",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "model_params_override": PRUNING_MODEL_PARAMS_OVERRIDE,
    },
    {
        "candidate_id": "catboost_core_strict_hierarchy_lite",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "forecast_core_strict_hierarchy_lite",
        "cogs_experiment": "forecast_core_strict_hierarchy_lite",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "hierarchy_future_policy": "seasonal_month_day_recent_2y",
        "cogs_postprocess_variant": "blend60_clip_q99",
        "model_params_override": PRUNING_MODEL_PARAMS_OVERRIDE,
    },
]


def _summary_by_id(summary_df: pd.DataFrame) -> dict[str, pd.Series]:
    return {str(row["candidate_id"]): row for _, row in summary_df.iterrows()}


def build_feature_inventory(
    feature_sets: dict[str, list[str]],
    groups: dict[str, list[str]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    feature_set_rows = [
        {"feature_set": name, "n_features": len(feature_sets[name])}
        for name in [
            "curated_promo_cogs",
            "forecast_core_strict",
            "forecast_core_promo_slim",
            "forecast_core_promo_slim_hierarchy_lite",
            "forecast_core_strict_hierarchy_lite",
        ]
        if name in feature_sets
    ]
    group_rows = [
        {"group": name, "n_features": len(groups.get(name, []))}
        for name in ["promo", "promo_slim", "hierarchy_lite"]
        if groups.get(name)
    ]
    return pd.DataFrame(feature_set_rows), pd.DataFrame(group_rows)


def build_decision_frame(summary_df: pd.DataFrame) -> pd.DataFrame:
    summary_map = _summary_by_id(summary_df)
    performance_anchor = summary_map[PERFORMANCE_ANCHOR_CANDIDATE["candidate_id"]]
    governance_anchor = summary_map[GOVERNANCE_ANCHOR_CANDIDATE["candidate_id"]]
    rows: list[dict[str, object]] = []

    for candidate in PRUNING_CANDIDATES:
        row = summary_map[candidate["candidate_id"]]
        rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "revenue_experiment": row["revenue_experiment"],
                "recent_weighted_combined_mae": row["recent_weighted_combined_mae"],
                "recent_tail_revenue_mae": row["recent_tail_revenue_mae"],
                "revenue_rmse_mean": row["revenue_rmse_mean"],
                "cogs_mae_mean": row["cogs_mae_mean"],
                "delta_recent_weighted_vs_performance_anchor": (
                    row["recent_weighted_combined_mae"] - performance_anchor["recent_weighted_combined_mae"]
                ),
                "delta_recent_weighted_vs_governance_anchor": (
                    row["recent_weighted_combined_mae"] - governance_anchor["recent_weighted_combined_mae"]
                ),
                "delta_recent_tail_revenue_vs_governance_anchor": (
                    row["recent_tail_revenue_mae"] - governance_anchor["recent_tail_revenue_mae"]
                ),
                "passes_submit_gate": row["passes_submit_gate"],
            }
        )

    return pd.DataFrame(rows)


def write_report(
    run_dir: Path,
    feature_set_inventory: pd.DataFrame,
    group_inventory: pd.DataFrame,
    summary_df: pd.DataFrame,
    decision_df: pd.DataFrame,
) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Feature Pruning Sprint\n\n")
        f.write("## Framing\n")
        f.write("- Performance anchor: `catboost_md2y_core`\n")
        f.write("- Governance anchor: `catboost_core_strict`\n")
        f.write("- Experiments: `promo_slim`, `promo_slim + hierarchy_lite`, `core_strict + hierarchy_lite`\n\n")
        f.write("## Feature Set Sizes\n")
        f.write(feature_set_inventory.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Group Sizes\n")
        f.write(group_inventory.to_markdown(index=False))
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
        f.write("## Experiment Decisions\n")
        f.write(decision_df.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting feature pruning sprint in %s", run_dir)

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    groups = get_ablation_feature_groups(feature_store.head(1))
    feature_set_inventory, group_inventory = build_feature_inventory(feature_sets, groups)

    candidates = [PERFORMANCE_ANCHOR_CANDIDATE, GOVERNANCE_ANCHOR_CANDIDATE] + PRUNING_CANDIDATES
    write_json(
        run_dir / "candidates.json",
        {
            "candidates": candidates,
            "feature_set_sizes": feature_set_inventory.to_dict(orient="records"),
            "group_sizes": group_inventory.to_dict(orient="records"),
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
    write_report(run_dir, feature_set_inventory, group_inventory, summary_df, decision_df)

    if not summary_df.empty:
        logger.info("Top candidate: %s", summary_df.iloc[0]["candidate_id"])
    logger.info("Saved summary to %s", run_dir / "summary.csv")
    logger.info("Saved decision summary to %s", run_dir / "decision_summary.csv")


if __name__ == "__main__":
    main()
