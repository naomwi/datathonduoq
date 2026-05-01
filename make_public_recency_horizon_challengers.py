from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error

from logging_utils import create_run_dir, setup_logger, write_json
from run_leaderboard_sprint import FORECAST_END, FORECAST_START, SPRINT_FOLDS, forecast_baseline
from run_public_revenue_router_v1 import _rmse, predict_candidate
from train_recursive_forecast import TRAIN_END, ensure_inputs, get_candidate_feature_sets


RUN_PREFIX = "public_recency_horizon_challengers"
DATASET_DIR = Path("dataset")

PUBLIC_RECENCY_PATH = DATASET_DIR / "submission_catboost_md2y_core_recencyexp20.csv"

RECENCY_CANDIDATE = {
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
}

VARIANTS = [
    {
        "candidate_id": "public_recency_tail_ramp20",
        "mode": "tail_ramp",
        "end_weight": 0.20,
        "thesis": "blend 20% seasonal baseline by the far end of horizon.",
    },
    {
        "candidate_id": "public_recency_tail_ramp25",
        "mode": "tail_ramp",
        "end_weight": 0.25,
        "thesis": "blend 25% seasonal baseline by the far end of horizon.",
    },
    {
        "candidate_id": "public_recency_tail_ramp30",
        "mode": "tail_ramp",
        "end_weight": 0.30,
        "thesis": "blend 30% seasonal baseline by the far end of horizon.",
    },
    {
        "candidate_id": "public_recency_tail_ramp35",
        "mode": "tail_ramp",
        "end_weight": 0.35,
        "thesis": "blend 35% seasonal baseline by the far end of horizon.",
    },
    {
        "candidate_id": "public_recency_tail_ramp40",
        "mode": "tail_ramp",
        "end_weight": 0.40,
        "thesis": "blend 40% seasonal baseline by the far end of horizon.",
    },
    {
        "candidate_id": "public_recency_tail_ramp45",
        "mode": "tail_ramp",
        "end_weight": 0.45,
        "thesis": "blend 45% seasonal baseline by the far end of horizon.",
    },
    {
        "candidate_id": "public_recency_tail_ramp50",
        "mode": "tail_ramp",
        "end_weight": 0.50,
        "thesis": "blend 50% seasonal baseline by the far end of horizon.",
    },
    {
        "candidate_id": "public_recency_late_const50",
        "mode": "late_const",
        "late_start": 320,
        "late_weight": 0.50,
        "thesis": "switch 50% toward seasonal baseline only in the final 46 days.",
    },
]


def load_submission(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)


def apply_variant(
    base_df: pd.DataFrame,
    seasonal_df: pd.DataFrame,
    variant: dict[str, object],
) -> pd.DataFrame:
    merged = base_df.merge(
        seasonal_df.rename(columns={"Revenue_pred": "Revenue_pred_seasonal"})[["Date", "Revenue_pred_seasonal"]],
        on="Date",
        how="left",
    ).copy()

    mode = str(variant["mode"])
    horizon = len(merged)
    if mode == "tail_ramp":
        weights = np.linspace(0.0, float(variant["end_weight"]), horizon, dtype=float)
    elif mode == "late_const":
        weights = np.zeros(horizon, dtype=float)
        weights[int(variant["late_start"]):] = float(variant["late_weight"])
    else:
        raise ValueError(f"Unknown variant mode: {mode}")

    merged["Revenue_pred"] = (
        (1.0 - weights) * merged["Revenue_pred"] + weights * merged["Revenue_pred_seasonal"]
    ).clip(lower=0.0)
    return merged[["Date", "Revenue_pred", "COGS_pred"]].copy()


def build_summary(fold_metrics_df: pd.DataFrame) -> pd.DataFrame:
    return (
        fold_metrics_df.groupby("candidate_id", as_index=False)
        .agg(
            revenue_mae_mean=("revenue_mae", "mean"),
            revenue_rmse_mean=("revenue_rmse", "mean"),
            cogs_mae_mean=("cogs_mae", "mean"),
            combined_mae_mean=("combined_mae", "mean"),
        )
        .sort_values(["combined_mae_mean", "revenue_mae_mean"])
        .reset_index(drop=True)
    )


def write_report(run_dir: Path, summary_df: pd.DataFrame, fold_df: pd.DataFrame) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Public Recency Horizon Challengers\n\n")
        f.write("## Framing\n")
        f.write("- Base public anchor: `submission_catboost_md2y_core_recencyexp20.csv`\n")
        f.write("- Adjustment scope: Revenue only\n")
        f.write("- Structural thesis: correct long-horizon recursive drift by blending toward a seasonal baseline later in the horizon\n")
        f.write("- COGS stays frozen from `recencyexp20`\n\n")
        f.write("## OOF Ranking\n")
        f.write(summary_df.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Fold Metrics\n")
        f.write(fold_df.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting public recency horizon challengers in %s", run_dir)

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    write_json(run_dir / "config.json", {"variants": VARIANTS, "recency_candidate": RECENCY_CANDIDATE})

    fold_rows: list[dict[str, object]] = []
    for fold_id, (start_date, end_date) in enumerate(SPRINT_FOLDS, start=1):
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        cutoff = start_ts - pd.Timedelta(days=1)

        recency_preds = predict_candidate(RECENCY_CANDIDATE, feature_store, base, feature_sets, start_ts, end_ts, cutoff)
        history_df = feature_store.loc[feature_store["Date"] <= cutoff, ["Date", "Revenue", "COGS"]].copy()
        seasonal_preds = forecast_baseline("seasonal_md2y", history_df, start_ts, end_ts)
        truth_df = base.loc[(base["Date"] >= start_ts) & (base["Date"] <= end_ts), ["Date", "Revenue", "COGS"]].copy()

        merged_base = truth_df.merge(recency_preds, on="Date", how="left")
        fold_rows.append(
            {
                "candidate_id": "recencyexp20",
                "fold": fold_id,
                "start_date": start_date,
                "end_date": end_date,
                "revenue_mae": mean_absolute_error(merged_base["Revenue"], merged_base["Revenue_pred"]),
                "revenue_rmse": _rmse(merged_base["Revenue"], merged_base["Revenue_pred"]),
                "cogs_mae": mean_absolute_error(merged_base["COGS"], merged_base["COGS_pred"]),
                "combined_mae": 0.5
                * (
                    mean_absolute_error(merged_base["Revenue"], merged_base["Revenue_pred"])
                    + mean_absolute_error(merged_base["COGS"], merged_base["COGS_pred"])
                ),
            }
        )

        for variant in VARIANTS:
            adjusted_preds = apply_variant(recency_preds, seasonal_preds, variant)
            merged = truth_df.merge(adjusted_preds, on="Date", how="left")
            fold_rows.append(
                {
                    "candidate_id": variant["candidate_id"],
                    "fold": fold_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "revenue_mae": mean_absolute_error(merged["Revenue"], merged["Revenue_pred"]),
                    "revenue_rmse": _rmse(merged["Revenue"], merged["Revenue_pred"]),
                    "cogs_mae": mean_absolute_error(merged["COGS"], merged["COGS_pred"]),
                    "combined_mae": 0.5
                    * (
                        mean_absolute_error(merged["Revenue"], merged["Revenue_pred"])
                        + mean_absolute_error(merged["COGS"], merged["COGS_pred"])
                    ),
                }
            )

    fold_df = pd.DataFrame(fold_rows).sort_values(["candidate_id", "fold"]).reset_index(drop=True)
    fold_df.to_csv(run_dir / "fold_metrics.csv", index=False)
    summary_df = build_summary(fold_df)
    summary_df.to_csv(run_dir / "summary.csv", index=False)

    logger.info("Generating final public seasonal baseline")
    public_recency = load_submission(PUBLIC_RECENCY_PATH)
    history_df = feature_store.loc[feature_store["Date"] <= TRAIN_END, ["Date", "Revenue", "COGS"]].copy()
    seasonal_public = forecast_baseline("seasonal_md2y", history_df, FORECAST_START, FORECAST_END)

    for variant in VARIANTS:
        adjusted_public = apply_variant(
            public_recency.rename(columns={"Revenue": "Revenue_pred", "COGS": "COGS_pred"})[
                ["Date", "Revenue_pred", "COGS_pred"]
            ],
            seasonal_public,
            variant,
        )
        submission = pd.DataFrame(
            {
                "Date": pd.to_datetime(adjusted_public["Date"]).dt.strftime("%Y-%m-%d"),
                "Revenue": adjusted_public["Revenue_pred"],
                "COGS": adjusted_public["COGS_pred"],
            }
        )
        output_name = f"submission_{variant['candidate_id']}.csv"
        dataset_path = DATASET_DIR / output_name
        run_path = run_dir / output_name
        submission.to_csv(dataset_path, index=False)
        submission.to_csv(run_path, index=False)
        logger.info("Exported %s", output_name)

    write_report(run_dir, summary_df, fold_df)
    logger.info("Saved summary to %s", run_dir / "summary.csv")
    if not summary_df.empty:
        logger.info("Top OOF candidate: %s", summary_df.iloc[0]["candidate_id"])


if __name__ == "__main__":
    main()
