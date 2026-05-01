from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from logging_utils import create_run_dir, setup_logger, write_json
from run_ablation import MODEL_PARAMS
from train_recursive_forecast import (
    BACKTEST_FOLDS,
    FIT_MODEL_PARAMS,
    build_feature_row,
    ensure_inputs,
    get_candidate_feature_sets,
    zero_unknown_promo_signals,
)


RUN_PREFIX = "cogs_postprocess_ablation"
SYSTEM_CONFIG = {
    "revenue_experiment": "curated_promo_cogs",
    "cogs_experiment": "curated_promo_cogs",
}
PROMO_COLUMNS = [
    "active_promo_count",
    "active_stackable_promo_count",
    "active_promo_discount_value_mean",
    "total_discount",
    "avg_discount_rate",
    "promo_line_share",
    "promo_2_share",
]


VARIANTS = {
    "raw": {"mode": "raw"},
    "clip_q99": {"mode": "clip", "upper_quantile": 0.99},
    "blend80": {"mode": "blend", "raw_weight": 0.8},
    "blend80_clip_q99": {"mode": "blend_clip", "raw_weight": 0.8, "upper_quantile": 0.99},
    "blend60_clip_q99": {"mode": "blend_clip", "raw_weight": 0.6, "upper_quantile": 0.99},
}


def _rmse(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def compute_ratio_stats(train_df: pd.DataFrame) -> dict[str, float]:
    ratio = (train_df["COGS"] / train_df["Revenue"]).replace([np.inf, -np.inf], np.nan).dropna()
    return {
        "median": float(ratio.median()),
        "q99": float(ratio.quantile(0.99)),
    }


def trailing_ratio(history: pd.DataFrame, fallback: float, window: int = 28) -> float:
    recent = history.tail(window).copy()
    ratio = (recent["COGS"] / recent["Revenue"]).replace([np.inf, -np.inf], np.nan).dropna()
    if ratio.empty:
        return fallback
    return float(ratio.mean())


def apply_variant(
    variant_name: str,
    pred_revenue: float,
    pred_cogs_raw: float,
    hist_ratio: float,
    ratio_stats: dict[str, float],
) -> tuple[float, float]:
    revenue = max(pred_revenue, 0.0)
    raw_cogs = max(pred_cogs_raw, 0.0)
    raw_ratio = raw_cogs / revenue if revenue > 0 else ratio_stats["median"]

    spec = VARIANTS[variant_name]
    mode = spec["mode"]
    corrected_ratio = raw_ratio

    if mode == "clip":
        corrected_ratio = min(raw_ratio, ratio_stats["q99"])
    elif mode == "blend":
        corrected_ratio = spec["raw_weight"] * raw_ratio + (1.0 - spec["raw_weight"]) * hist_ratio
    elif mode == "blend_clip":
        blended = spec["raw_weight"] * raw_ratio + (1.0 - spec["raw_weight"]) * hist_ratio
        corrected_ratio = min(blended, ratio_stats["q99"])

    corrected_cogs = revenue * max(corrected_ratio, 0.0)
    return corrected_cogs, corrected_ratio


def fit_models(train_df: pd.DataFrame, revenue_features: list[str], cogs_features: list[str]) -> tuple[xgb.XGBRegressor, xgb.XGBRegressor]:
    revenue_model = xgb.XGBRegressor(**FIT_MODEL_PARAMS)
    cogs_model = xgb.XGBRegressor(**FIT_MODEL_PARAMS)
    revenue_model.fit(train_df[revenue_features], train_df["Revenue"], verbose=False)
    cogs_model.fit(train_df[cogs_features], train_df["COGS"], verbose=False)
    return revenue_model, cogs_model


def sequential_predict_fold(
    train_df: pd.DataFrame,
    valid_df: pd.DataFrame,
    base: pd.DataFrame,
    revenue_features: list[str],
    cogs_features: list[str],
    variant_name: str,
    use_predicted_history: bool,
) -> pd.DataFrame:
    revenue_model, cogs_model = fit_models(train_df, revenue_features, cogs_features)
    ratio_stats = compute_ratio_stats(train_df)
    promo_indexed = base[["Date"] + PROMO_COLUMNS].copy().set_index("Date")
    history = train_df[["Date", "Revenue", "COGS"]].copy().set_index("Date").sort_index()
    results: list[dict[str, float | str]] = []

    for current_date in valid_df["Date"]:
        revenue_row = build_feature_row(current_date, history, promo_indexed, revenue_features)
        cogs_row = build_feature_row(current_date, history, promo_indexed, cogs_features)
        pred_revenue = float(revenue_model.predict(revenue_row)[0])
        pred_cogs_raw = float(cogs_model.predict(cogs_row)[0])
        hist_ratio = trailing_ratio(history, fallback=ratio_stats["median"])
        pred_cogs, pred_ratio = apply_variant(
            variant_name=variant_name,
            pred_revenue=pred_revenue,
            pred_cogs_raw=pred_cogs_raw,
            hist_ratio=hist_ratio,
            ratio_stats=ratio_stats,
        )
        results.append(
            {
                "Date": current_date,
                "Revenue_pred": max(pred_revenue, 0.0),
                "COGS_pred_raw": max(pred_cogs_raw, 0.0),
                "COGS_pred": pred_cogs,
                "pred_ratio": pred_ratio,
                "hist_ratio_28": hist_ratio,
                "ratio_gt_q99_flag": int(pred_ratio > ratio_stats["q99"]),
            }
        )

        if use_predicted_history:
            history.loc[current_date, ["Revenue", "COGS"]] = [max(pred_revenue, 0.0), pred_cogs]
        else:
            actual_row = valid_df.loc[valid_df["Date"] == current_date, ["Revenue", "COGS"]].iloc[0]
            history.loc[current_date, ["Revenue", "COGS"]] = [float(actual_row["Revenue"]), float(actual_row["COGS"])]

    return pd.DataFrame(results)


def run_one_step(
    feature_store: pd.DataFrame,
    base: pd.DataFrame,
    revenue_features: list[str],
    cogs_features: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    for variant_name in VARIANTS:
        for fold_id, (start_date, end_date) in enumerate(BACKTEST_FOLDS, start=1):
            start_ts = pd.Timestamp(start_date)
            end_ts = pd.Timestamp(end_date)
            train_df = feature_store[feature_store["Date"] < start_ts].copy()
            valid_df = feature_store[(feature_store["Date"] >= start_ts) & (feature_store["Date"] <= end_ts)].copy()
            adjusted_base = zero_unknown_promo_signals(base, start_ts - pd.Timedelta(days=1))
            preds = sequential_predict_fold(
                train_df=train_df,
                valid_df=valid_df,
                base=adjusted_base,
                revenue_features=revenue_features,
                cogs_features=cogs_features,
                variant_name=variant_name,
                use_predicted_history=False,
            )
            merged = valid_df[["Date", "Revenue", "COGS"]].merge(preds, on="Date", how="left")
            rows.append(
                {
                    "variant": variant_name,
                    "fold": fold_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "cogs_mae": mean_absolute_error(merged["COGS"], merged["COGS_pred"]),
                    "cogs_rmse": _rmse(merged["COGS"], merged["COGS_pred"]),
                    "cogs_r2": r2_score(merged["COGS"], merged["COGS_pred"]),
                    "violation_count_gt_actual_q99": int(merged["ratio_gt_q99_flag"].sum()),
                }
            )

    fold_df = pd.DataFrame(rows)
    summary_df = (
        fold_df.groupby("variant")
        .agg(
            cogs_mae_mean=("cogs_mae", "mean"),
            cogs_mae_std=("cogs_mae", "std"),
            cogs_rmse_mean=("cogs_rmse", "mean"),
            cogs_r2_mean=("cogs_r2", "mean"),
            q99_excess_total=("violation_count_gt_actual_q99", "sum"),
        )
        .reset_index()
        .sort_values("cogs_mae_mean")
        .reset_index(drop=True)
    )
    raw_mae = float(summary_df.loc[summary_df["variant"] == "raw", "cogs_mae_mean"].iloc[0])
    summary_df["delta_cogs_mae_vs_raw"] = summary_df["cogs_mae_mean"] - raw_mae
    return fold_df, summary_df


def run_recursive(
    feature_store: pd.DataFrame,
    base: pd.DataFrame,
    revenue_features: list[str],
    cogs_features: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    for variant_name in VARIANTS:
        for fold_id, (start_date, end_date) in enumerate(BACKTEST_FOLDS, start=1):
            start_ts = pd.Timestamp(start_date)
            end_ts = pd.Timestamp(end_date)
            cutoff = start_ts - pd.Timedelta(days=1)
            train_df = feature_store[feature_store["Date"] <= cutoff].copy()
            valid_df = feature_store[(feature_store["Date"] >= start_ts) & (feature_store["Date"] <= end_ts)].copy()
            adjusted_base = zero_unknown_promo_signals(base, cutoff)
            preds = sequential_predict_fold(
                train_df=train_df,
                valid_df=valid_df,
                base=adjusted_base,
                revenue_features=revenue_features,
                cogs_features=cogs_features,
                variant_name=variant_name,
                use_predicted_history=True,
            )
            merged = valid_df[["Date", "Revenue", "COGS"]].merge(preds, on="Date", how="left")
            rows.append(
                {
                    "variant": variant_name,
                    "fold": fold_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "revenue_mae": mean_absolute_error(merged["Revenue"], merged["Revenue_pred"]),
                    "revenue_rmse": _rmse(merged["Revenue"], merged["Revenue_pred"]),
                    "revenue_r2": r2_score(merged["Revenue"], merged["Revenue_pred"]),
                    "cogs_mae": mean_absolute_error(merged["COGS"], merged["COGS_pred"]),
                    "cogs_rmse": _rmse(merged["COGS"], merged["COGS_pred"]),
                    "cogs_r2": r2_score(merged["COGS"], merged["COGS_pred"]),
                    "combined_mae": mean_absolute_error(merged["Revenue"], merged["Revenue_pred"])
                    + mean_absolute_error(merged["COGS"], merged["COGS_pred"]),
                    "q99_excess_total": int(merged["ratio_gt_q99_flag"].sum()),
                }
            )

    fold_df = pd.DataFrame(rows)
    summary_df = (
        fold_df.groupby("variant")
        .agg(
            revenue_mae_mean=("revenue_mae", "mean"),
            revenue_rmse_mean=("revenue_rmse", "mean"),
            revenue_r2_mean=("revenue_r2", "mean"),
            cogs_mae_mean=("cogs_mae", "mean"),
            cogs_rmse_mean=("cogs_rmse", "mean"),
            cogs_r2_mean=("cogs_r2", "mean"),
            combined_mae_mean=("combined_mae", "mean"),
            q99_excess_total=("q99_excess_total", "sum"),
        )
        .reset_index()
        .sort_values("combined_mae_mean")
        .reset_index(drop=True)
    )
    raw_combined = float(summary_df.loc[summary_df["variant"] == "raw", "combined_mae_mean"].iloc[0])
    summary_df["delta_combined_mae_vs_raw"] = summary_df["combined_mae_mean"] - raw_combined
    return fold_df, summary_df


def write_report(
    run_dir: Path,
    one_step_summary: pd.DataFrame,
    one_step_folds: pd.DataFrame,
    recursive_summary: pd.DataFrame,
    recursive_folds: pd.DataFrame,
) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# COGS Postprocess Ablation\n\n")
        f.write("## Design Notes\n")
        f.write("- Track: `competition-first`\n")
        f.write("- Revenue model stays on `curated_promo_cogs`\n")
        f.write("- COGS model stays direct-level; only post-processing changes\n")
        f.write("- One-step summary is diagnostic; recursive summary is the primary ranking for this run\n\n")

        f.write("## One-Step Summary\n")
        f.write(one_step_summary.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Recursive Summary\n")
        f.write(recursive_summary.to_markdown(index=False))
        f.write("\n\n")

        f.write("## One-Step Fold Details\n")
        f.write(one_step_folds.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Recursive Fold Details\n")
        f.write(recursive_folds.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting cogs postprocess ablation in %s", run_dir)

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    revenue_features = feature_sets[SYSTEM_CONFIG["revenue_experiment"]]
    cogs_features = feature_sets[SYSTEM_CONFIG["cogs_experiment"]]

    train_stats = compute_ratio_stats(feature_store[feature_store["Date"] <= pd.Timestamp("2022-12-31")])
    write_json(
        run_dir / "config.json",
        {
            "system_config": SYSTEM_CONFIG,
            "variants": VARIANTS,
            "train_ratio_stats": train_stats,
            "primary_ranking": "recursive_combined_mae_mean",
        },
    )

    logger.info("Running one-step diagnostic...")
    one_step_folds, one_step_summary = run_one_step(feature_store, base, revenue_features, cogs_features)
    one_step_folds.to_csv(run_dir / "one_step_fold_results.csv", index=False)
    one_step_summary.to_csv(run_dir / "one_step_summary.csv", index=False)

    logger.info("Running recursive ranking...")
    recursive_folds, recursive_summary = run_recursive(feature_store, base, revenue_features, cogs_features)
    recursive_folds.to_csv(run_dir / "recursive_fold_results.csv", index=False)
    recursive_summary.to_csv(run_dir / "recursive_summary.csv", index=False)

    write_report(run_dir, one_step_summary, one_step_folds, recursive_summary, recursive_folds)
    logger.info("Finished cogs postprocess ablation. Artifacts written to %s", run_dir)


if __name__ == "__main__":
    main()
