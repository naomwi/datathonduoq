from __future__ import annotations

from pathlib import Path

import pandas as pd

from feature_pipeline import get_ablation_feature_groups
from logging_utils import create_run_dir, setup_logger, write_json
from run_leaderboard_sprint import build_summary, evaluate_candidate, export_final_submission
from train_recursive_forecast import ensure_inputs, get_candidate_feature_sets


RUN_PREFIX = "catboost_core_plus"
VARIANCE_MULTIPLIER = 1.15

STRICT_CORE_CANDIDATE = {
    "candidate_id": "catboost_governance_strict_core",
    "kind": "model",
    "model_family": "catboost",
    "revenue_experiment": "forecast_core_strict",
    "cogs_experiment": "forecast_core_strict",
    "promo_future_policy": "seasonal_month_day_recent_2y",
    "context_future_policy": "zero",
    "cogs_postprocess_variant": "blend60_clip_q99",
}

FAMILY_CANDIDATES = [
    {
        "candidate_id": "catboost_governance_plus_promo_detail",
        "family_name": "promo_detail",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "forecast_core_plus_promo_detail",
        "cogs_experiment": "forecast_core_plus_promo_detail",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
    },
    {
        "candidate_id": "catboost_governance_plus_geo_logistics",
        "family_name": "geo_logistics",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "forecast_core_plus_geo_logistics",
        "cogs_experiment": "forecast_core_plus_geo_logistics",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
    },
    {
        "candidate_id": "catboost_governance_plus_mix_light",
        "family_name": "mix_light",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "forecast_core_plus_mix_light",
        "cogs_experiment": "forecast_core_plus_mix_light",
        "promo_future_policy": "seasonal_month_day_recent_2y",
        "context_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
    },
]

PERFORMANCE_ANCHOR_CANDIDATE = {
    "candidate_id": "catboost_md2y_core",
    "kind": "model",
    "model_family": "catboost",
    "revenue_experiment": "curated_promo_cogs",
    "cogs_experiment": "curated_promo_cogs",
    "promo_future_policy": "seasonal_month_day_recent_2y",
    "context_future_policy": "zero",
    "cogs_postprocess_variant": "blend60_clip_q99",
}


def _summary_by_id(summary_df: pd.DataFrame) -> dict[str, pd.Series]:
    return {str(row["candidate_id"]): row for _, row in summary_df.iterrows()}


def decide_family_passes(summary_df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    summary_map = _summary_by_id(summary_df)
    base = summary_map[STRICT_CORE_CANDIDATE["candidate_id"]]
    decision_rows: list[dict[str, object]] = []
    passing_families: list[str] = []

    for candidate in FAMILY_CANDIDATES:
        row = summary_map[candidate["candidate_id"]]
        recent_improves = bool(
            float(row["recent_weighted_revenue_mae"]) < float(base["recent_weighted_revenue_mae"])
            and float(row["recent_tail_revenue_mae"]) < float(base["recent_tail_revenue_mae"])
        )
        breadth_ok = bool(
            float(row["revenue_rmse_mean"]) <= float(base["revenue_rmse_mean"]) * 1.03
            and float(row["revenue_r2_mean"]) >= float(base["revenue_r2_mean"]) - 0.02
            and float(row["cogs_mae_mean"]) <= float(base["cogs_mae_mean"]) * 1.05
        )
        stability_ok = bool(float(row["revenue_mae_std"]) <= float(base["revenue_mae_std"]) * VARIANCE_MULTIPLIER)
        passes_family_gate = recent_improves and breadth_ok and stability_ok
        if passes_family_gate:
            passing_families.append(str(candidate["family_name"]))
        decision_rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "family_name": candidate["family_name"],
                "recent_improves": recent_improves,
                "breadth_ok": breadth_ok,
                "stability_ok": stability_ok,
                "passes_family_gate": passes_family_gate,
                "recent_weighted_revenue_mae": row["recent_weighted_revenue_mae"],
                "recent_tail_revenue_mae": row["recent_tail_revenue_mae"],
                "revenue_mae_std": row["revenue_mae_std"],
                "revenue_rmse_mean": row["revenue_rmse_mean"],
                "revenue_r2_mean": row["revenue_r2_mean"],
                "cogs_mae_mean": row["cogs_mae_mean"],
            }
        )

    return pd.DataFrame(decision_rows), passing_families


def write_report(
    run_dir: Path,
    family_summary: pd.DataFrame,
    family_decisions: pd.DataFrame,
    final_summary: pd.DataFrame,
    passing_families: list[str],
) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# CatBoost Core Plus Search\n\n")
        f.write("## Framing\n")
        f.write("- Governance base: `forecast_core_strict`\n")
        f.write("- Performance anchor: `catboost_md2y_core`\n")
        f.write("- Family re-introduction policy: add by family, keep only families that improve recent metrics without failing breadth or stability\n\n")
        f.write("## Family Summary\n")
        f.write(family_summary.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Family Decisions\n")
        f.write(family_decisions.to_markdown(index=False))
        f.write("\n\n")
        f.write(f"## Passing Families\n- `{', '.join(passing_families) if passing_families else 'none'}`\n\n")
        f.write("## Final Comparison\n")
        f.write(final_summary.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting CatBoost core-plus search in %s", run_dir)

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    groups = get_ablation_feature_groups(feature_store.head(1))

    family_candidates = [STRICT_CORE_CANDIDATE] + FAMILY_CANDIDATES
    write_json(run_dir / "family_candidates.json", {"candidates": family_candidates})

    family_fold_frames = [
        evaluate_candidate(candidate, feature_store, base, feature_sets) for candidate in family_candidates
    ]
    family_fold_df = pd.concat(family_fold_frames, ignore_index=True)
    family_fold_df.to_csv(run_dir / "family_fold_results.csv", index=False)
    family_summary = build_summary(family_fold_df)
    family_summary.to_csv(run_dir / "family_summary.csv", index=False)

    family_decisions, passing_families = decide_family_passes(family_summary)
    family_decisions.to_csv(run_dir / "family_decisions.csv", index=False)
    logger.info("Passing families: %s", ", ".join(passing_families) if passing_families else "none")

    core_plus_features = set(feature_sets["forecast_core_strict"])
    for family_name in passing_families:
        core_plus_features.update(groups.get(family_name, []))
    feature_sets["forecast_core_plus"] = sorted(core_plus_features)

    final_candidates = [
        STRICT_CORE_CANDIDATE,
        PERFORMANCE_ANCHOR_CANDIDATE,
        {
            "candidate_id": "catboost_core_plus",
            "kind": "model",
            "model_family": "catboost",
            "revenue_experiment": "forecast_core_plus",
            "cogs_experiment": "forecast_core_plus",
            "promo_future_policy": "seasonal_month_day_recent_2y",
            "context_future_policy": "zero",
            "cogs_postprocess_variant": "blend60_clip_q99",
        },
    ]
    write_json(run_dir / "final_candidates.json", {"candidates": final_candidates, "passing_families": passing_families})

    final_fold_frames = [
        evaluate_candidate(candidate, feature_store, base, feature_sets) for candidate in final_candidates
    ]
    final_fold_df = pd.concat(final_fold_frames, ignore_index=True)
    final_fold_df.to_csv(run_dir / "final_fold_results.csv", index=False)
    final_summary = build_summary(final_fold_df)
    final_summary.to_csv(run_dir / "final_summary.csv", index=False)

    candidate_map = {str(candidate["candidate_id"]): candidate for candidate in final_candidates}
    for candidate_id in final_summary["candidate_id"].tolist():
        if candidate_id == "catboost_core_plus":
            export_final_submission(
                candidate_map[candidate_id],
                feature_store,
                base,
                feature_sets,
                Path("dataset") / "submission_catboost_core_plus.csv",
            )
            export_final_submission(
                candidate_map[candidate_id],
                feature_store,
                base,
                feature_sets,
                run_dir / "submission_catboost_core_plus.csv",
            )
            logger.info("Exported submission for %s", candidate_id)

    write_report(run_dir, family_summary, family_decisions, final_summary, passing_families)
    logger.info("Saved family summary to %s", run_dir / "family_summary.csv")
    logger.info("Saved final summary to %s", run_dir / "final_summary.csv")
    if not final_summary.empty:
        logger.info("Top final candidate: %s", final_summary.iloc[0]["candidate_id"])


if __name__ == "__main__":
    main()
