from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from feature_pipeline import TRAIN_END, get_ablation_feature_groups
from logging_utils import create_run_dir, setup_logger, write_json
from run_ablation import MODEL_PARAMS, load_training_frame


FIT_PARAMS = MODEL_PARAMS.copy()
RUN_PREFIX = "orthodox_ablation"
FOLDS = [
    ("2020-01-01", "2020-12-31"),
    ("2021-01-01", "2021-12-31"),
    ("2022-01-01", "2022-12-31"),
]
BASELINE_GROUPS = ["calendar", "revenue_history"]
CANDIDATE_GROUP_ORDER = ["promo", "cogs_history", "mix", "traffic", "returns_reviews", "order_flow", "inventory"]


def evaluate_feature_set(
    df: pd.DataFrame,
    features: list[str],
    experiment_name: str,
) -> tuple[pd.DataFrame, dict[str, float | int | str]]:
    rows: list[dict[str, object]] = []

    for fold_id, (start_date, end_date) in enumerate(FOLDS, start=1):
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        train_df = df[df["Date"] < start_ts].copy()
        valid_df = df[(df["Date"] >= start_ts) & (df["Date"] <= end_ts)].copy()

        model = xgb.XGBRegressor(**FIT_PARAMS)
        model.fit(
            train_df[features],
            train_df["Revenue"],
            eval_set=[(valid_df[features], valid_df["Revenue"])],
            verbose=False,
        )
        preds = model.predict(valid_df[features])

        rows.append(
            {
                "experiment": experiment_name,
                "fold": fold_id,
                "start_date": start_date,
                "end_date": end_date,
                "n_features": len(features),
                "mae": mean_absolute_error(valid_df["Revenue"], preds),
                "rmse": np.sqrt(mean_squared_error(valid_df["Revenue"], preds)),
                "r2": r2_score(valid_df["Revenue"], preds),
            }
        )

    fold_df = pd.DataFrame(rows)
    summary = {
        "experiment": experiment_name,
        "n_features": len(features),
        "mae_mean": float(fold_df["mae"].mean()),
        "mae_std": float(fold_df["mae"].std()),
        "rmse_mean": float(fold_df["rmse"].mean()),
        "r2_mean": float(fold_df["r2"].mean()),
    }
    return fold_df, summary


def write_report(
    run_dir: Path,
    group_sizes: pd.DataFrame,
    stepwise_results: pd.DataFrame,
    final_summary: pd.DataFrame,
    accepted_groups: list[str],
) -> None:
    report_path = run_dir / "selection_report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Orthodox Ablation Report\n\n")
        f.write("## Accepted Groups\n")
        for group in accepted_groups:
            f.write(f"- `{group}`\n")
        f.write("\n")

        f.write("## Group Sizes\n")
        f.write(group_sizes.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Stepwise Decisions\n")
        f.write(stepwise_results.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Final Candidate Summary\n")
        f.write(final_summary.sort_values("mae_mean").to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting orthodox ablation run in %s", run_dir)

    df = load_training_frame()
    groups = get_ablation_feature_groups(df)
    candidate_groups = [group for group in CANDIDATE_GROUP_ORDER if groups.get(group)]
    group_sizes = pd.DataFrame(
        [{"group": group, "n_columns": len(groups[group])} for group in BASELINE_GROUPS + candidate_groups]
    )
    group_sizes.to_csv(run_dir / "group_sizes.csv", index=False)

    write_json(
        run_dir / "config.json",
        {
            "train_end": TRAIN_END,
            "folds": FOLDS,
            "baseline_groups": BASELINE_GROUPS,
            "candidate_group_order": candidate_groups,
            "model_params": FIT_PARAMS,
        },
    )

    accepted_groups = BASELINE_GROUPS.copy()
    accepted_features = sorted(set().union(*(groups[group] for group in accepted_groups)))
    logger.info("Baseline groups: %s", accepted_groups)
    baseline_fold_df, baseline_summary = evaluate_feature_set(df, accepted_features, "baseline")
    logger.info("Baseline mean MAE: %.3f with %s features", baseline_summary["mae_mean"], baseline_summary["n_features"])

    all_fold_results = [baseline_fold_df]
    all_summaries = [baseline_summary]
    stepwise_rows: list[dict[str, object]] = []
    current_best_mae = float(baseline_summary["mae_mean"])

    remaining = candidate_groups.copy()
    round_idx = 1
    while remaining:
        logger.info("Round %s starting. Accepted groups: %s", round_idx, accepted_groups)
        round_summaries: list[dict[str, object]] = []
        best_candidate_name: str | None = None
        best_candidate_mae = current_best_mae

        for group in remaining:
            trial_groups = accepted_groups + [group]
            trial_features = sorted(set().union(*(groups[name] for name in trial_groups)))
            experiment_name = f"round_{round_idx}_plus_{group}"
            logger.info("Evaluating %s with groups %s", experiment_name, trial_groups)
            fold_df, summary = evaluate_feature_set(df, trial_features, experiment_name)
            summary["trial_group"] = group
            summary["trial_groups"] = ",".join(trial_groups)
            summary["delta_mae_vs_current"] = float(summary["mae_mean"]) - current_best_mae
            round_summaries.append(summary)
            all_fold_results.append(fold_df)
            all_summaries.append(summary)

            logger.info(
                "Result %s | mean MAE %.3f | delta vs current %.3f",
                experiment_name,
                summary["mae_mean"],
                summary["delta_mae_vs_current"],
            )
            if float(summary["mae_mean"]) < best_candidate_mae:
                best_candidate_mae = float(summary["mae_mean"])
                best_candidate_name = group

        round_df = pd.DataFrame(round_summaries).sort_values("mae_mean").reset_index(drop=True)
        round_df.to_csv(run_dir / f"round_{round_idx}_summary.csv", index=False)

        chosen = best_candidate_name if best_candidate_name is not None else "STOP"
        improvement = best_candidate_mae - current_best_mae if best_candidate_name is not None else 0.0
        stepwise_rows.append(
            {
                "round": round_idx,
                "accepted_before": ",".join(accepted_groups),
                "best_trial": chosen,
                "best_trial_mae": best_candidate_mae if best_candidate_name is not None else current_best_mae,
                "improvement_vs_current": improvement,
                "decision": "accept" if best_candidate_name is not None else "stop",
            }
        )

        if best_candidate_name is None:
            logger.info("No candidate improved baseline in round %s. Stopping.", round_idx)
            break

        accepted_groups.append(best_candidate_name)
        accepted_features = sorted(set().union(*(groups[group] for group in accepted_groups)))
        current_best_mae = best_candidate_mae
        remaining.remove(best_candidate_name)
        logger.info(
            "Accepted group %s in round %s. New mean MAE %.3f",
            best_candidate_name,
            round_idx,
            current_best_mae,
        )
        round_idx += 1

    fold_results_df = pd.concat(all_fold_results, ignore_index=True)
    fold_results_df.to_csv(run_dir / "experiment_fold_results.csv", index=False)

    summary_df = pd.DataFrame(all_summaries)
    summary_df.to_csv(run_dir / "experiment_summary.csv", index=False)

    stepwise_df = pd.DataFrame(stepwise_rows)
    stepwise_df.to_csv(run_dir / "stepwise_decisions.csv", index=False)

    write_json(
        run_dir / "selected_groups.json",
        {
            "accepted_groups": accepted_groups,
            "accepted_feature_count": len(accepted_features),
            "final_mae_mean": current_best_mae,
        },
    )
    write_report(run_dir, group_sizes, stepwise_df, summary_df, accepted_groups)
    logger.info("Finished orthodox ablation. Accepted groups: %s", accepted_groups)
    logger.info("Artifacts written to %s", run_dir)


if __name__ == "__main__":
    main()
