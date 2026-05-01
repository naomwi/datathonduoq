from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from logging_utils import create_run_dir, setup_logger, write_json
from run_ablation import MODEL_PARAMS, load_training_frame
from train_recursive_forecast import (
    BACKTEST_FOLDS,
    FIT_MODEL_PARAMS,
    build_feature_row,
    ensure_inputs,
    get_candidate_feature_sets,
    zero_unknown_promo_signals,
)


RUN_PREFIX = "cogs_rate_protocol"
REVENUE_EXPERIMENT = "curated_promo_cogs"
COGS_FEATURE_EXPERIMENT = "curated_promo_cogs"
CONTROL_NAME = "direct_cogs_level"

RATE_SPECS = {
    "cogs_ratio": {
        "target_col": "cogs_ratio",
    },
    "gross_margin_rate": {
        "target_col": "gross_margin_rate",
    },
}


def _rmse(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def add_rate_targets(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    revenue = out["Revenue"].replace(0, np.nan)
    out["cogs_ratio"] = (out["COGS"] / revenue).clip(lower=0.0, upper=1.0).fillna(0.0)
    out["gross_margin_rate"] = ((out["Revenue"] - out["COGS"]) / revenue).clip(lower=0.0, upper=1.0).fillna(0.0)
    return out


def to_cogs_from_rate(rate_name: str, revenue_pred: np.ndarray, raw_rate_pred: np.ndarray) -> np.ndarray:
    revenue_pred = np.clip(revenue_pred, a_min=0.0, a_max=None)
    rate_pred = np.clip(raw_rate_pred, a_min=0.0, a_max=1.0)
    if rate_name == "cogs_ratio":
        cogs_pred = revenue_pred * rate_pred
    elif rate_name == "gross_margin_rate":
        cogs_pred = revenue_pred * (1.0 - rate_pred)
    else:
        raise KeyError(f"Unsupported rate target: {rate_name}")
    return np.clip(cogs_pred, a_min=0.0, a_max=revenue_pred)


def fit_one_step_models(
    train_df: pd.DataFrame,
    valid_df: pd.DataFrame,
    revenue_features: list[str],
    cogs_features: list[str],
) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    revenue_model = xgb.XGBRegressor(**MODEL_PARAMS)
    revenue_model.fit(
        train_df[revenue_features],
        train_df["Revenue"],
        eval_set=[(valid_df[revenue_features], valid_df["Revenue"])],
        verbose=False,
    )
    revenue_pred = np.clip(revenue_model.predict(valid_df[revenue_features]), a_min=0.0, a_max=None)

    direct_cogs_model = xgb.XGBRegressor(**MODEL_PARAMS)
    direct_cogs_model.fit(
        train_df[cogs_features],
        train_df["COGS"],
        eval_set=[(valid_df[cogs_features], valid_df["COGS"])],
        verbose=False,
    )
    direct_cogs_pred = np.clip(direct_cogs_model.predict(valid_df[cogs_features]), a_min=0.0, a_max=None)

    rate_preds: dict[str, np.ndarray] = {}
    for rate_name, spec in RATE_SPECS.items():
        rate_model = xgb.XGBRegressor(**MODEL_PARAMS)
        rate_model.fit(
            train_df[cogs_features],
            train_df[spec["target_col"]],
            eval_set=[(valid_df[cogs_features], valid_df[spec["target_col"]])],
            verbose=False,
        )
        raw_rate_pred = rate_model.predict(valid_df[cogs_features])
        rate_preds[rate_name] = to_cogs_from_rate(rate_name, revenue_pred, raw_rate_pred)

    return revenue_pred, direct_cogs_pred, rate_preds


def run_one_step_gate(
    feature_sets: dict[str, list[str]],
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    df = add_rate_targets(load_training_frame())
    revenue_features = feature_sets[REVENUE_EXPERIMENT]
    cogs_features = feature_sets[COGS_FEATURE_EXPERIMENT]

    rows: list[dict[str, object]] = []
    for fold_id, (start_date, end_date) in enumerate(BACKTEST_FOLDS, start=1):
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        train_df = df[df["Date"] < start_ts].copy()
        valid_df = df[(df["Date"] >= start_ts) & (df["Date"] <= end_ts)].copy()

        revenue_pred, direct_cogs_pred, rate_preds = fit_one_step_models(
            train_df=train_df,
            valid_df=valid_df,
            revenue_features=revenue_features,
            cogs_features=cogs_features,
        )

        rows.append(
            {
                "variant": CONTROL_NAME,
                "fold": fold_id,
                "start_date": start_date,
                "end_date": end_date,
                "cogs_mae": mean_absolute_error(valid_df["COGS"], direct_cogs_pred),
                "cogs_rmse": _rmse(valid_df["COGS"], direct_cogs_pred),
                "cogs_r2": r2_score(valid_df["COGS"], direct_cogs_pred),
                "violation_count": int((direct_cogs_pred > revenue_pred).sum()),
            }
        )

        for rate_name, cogs_pred in rate_preds.items():
            rows.append(
                {
                    "variant": rate_name,
                    "fold": fold_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "cogs_mae": mean_absolute_error(valid_df["COGS"], cogs_pred),
                    "cogs_rmse": _rmse(valid_df["COGS"], cogs_pred),
                    "cogs_r2": r2_score(valid_df["COGS"], cogs_pred),
                    "violation_count": int((cogs_pred > revenue_pred).sum()),
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
            violation_total=("violation_count", "sum"),
        )
        .reset_index()
        .sort_values("cogs_mae_mean")
        .reset_index(drop=True)
    )
    control_mae = float(summary_df.loc[summary_df["variant"] == CONTROL_NAME, "cogs_mae_mean"].iloc[0])
    summary_df["delta_cogs_mae_vs_control"] = summary_df["cogs_mae_mean"] - control_mae
    accepted = [
        variant
        for variant in summary_df["variant"].tolist()
        if variant != CONTROL_NAME
        and float(summary_df.loc[summary_df["variant"] == variant, "cogs_mae_mean"].iloc[0]) < control_mae
    ]
    return fold_df, summary_df, accepted


def fit_recursive_models(
    train_df: pd.DataFrame,
    revenue_features: list[str],
    cogs_features: list[str],
    variant: str,
) -> tuple[xgb.XGBRegressor, xgb.XGBRegressor | None]:
    revenue_model = xgb.XGBRegressor(**FIT_MODEL_PARAMS)
    revenue_model.fit(train_df[revenue_features], train_df["Revenue"], verbose=False)

    if variant == CONTROL_NAME:
        cogs_model = xgb.XGBRegressor(**FIT_MODEL_PARAMS)
        cogs_model.fit(train_df[cogs_features], train_df["COGS"], verbose=False)
        return revenue_model, cogs_model

    train_with_rates = add_rate_targets(train_df)
    cogs_model = xgb.XGBRegressor(**FIT_MODEL_PARAMS)
    cogs_model.fit(train_with_rates[cogs_features], train_with_rates[variant], verbose=False)
    return revenue_model, cogs_model


def recursive_forecast_variant(
    feature_store: pd.DataFrame,
    full_base: pd.DataFrame,
    train_end_date: pd.Timestamp,
    forecast_start: pd.Timestamp,
    forecast_end: pd.Timestamp,
    revenue_features: list[str],
    cogs_features: list[str],
    variant: str,
) -> pd.DataFrame:
    train_mask = feature_store["Date"] <= train_end_date
    forecast_mask = (full_base["Date"] >= forecast_start) & (full_base["Date"] <= forecast_end)

    train_df = feature_store.loc[train_mask].copy()
    promo_indexed = full_base[
        [
            "Date",
            "active_promo_count",
            "active_stackable_promo_count",
            "active_promo_discount_value_mean",
            "total_discount",
            "avg_discount_rate",
            "promo_line_share",
            "promo_2_share",
        ]
    ].copy().set_index("Date")

    revenue_model, cogs_model = fit_recursive_models(
        train_df=train_df,
        revenue_features=revenue_features,
        cogs_features=cogs_features,
        variant=variant,
    )

    history = train_df[["Date", "Revenue", "COGS"]].copy().set_index("Date").sort_index()
    results: list[dict[str, float | str]] = []

    for current_date in full_base.loc[forecast_mask, "Date"]:
        revenue_row = build_feature_row(current_date, history, promo_indexed, revenue_features)
        cogs_row = build_feature_row(current_date, history, promo_indexed, cogs_features)

        pred_revenue = float(revenue_model.predict(revenue_row)[0])
        pred_revenue = max(pred_revenue, 0.0)

        if variant == CONTROL_NAME:
            pred_cogs = float(cogs_model.predict(cogs_row)[0])
            pred_cogs = max(pred_cogs, 0.0)
        else:
            raw_rate_pred = float(cogs_model.predict(cogs_row)[0])
            pred_cogs = float(to_cogs_from_rate(variant, np.array([pred_revenue]), np.array([raw_rate_pred]))[0])

        history.loc[current_date, ["Revenue", "COGS"]] = [pred_revenue, pred_cogs]
        results.append(
            {
                "Date": current_date,
                "Revenue_pred": pred_revenue,
                "COGS_pred": pred_cogs,
                "violation_flag": int(pred_cogs > pred_revenue),
            }
        )

    return pd.DataFrame(results)


def run_recursive_stage(
    feature_sets: dict[str, list[str]],
    accepted_variants: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    feature_store, base = ensure_inputs()
    revenue_features = feature_sets[REVENUE_EXPERIMENT]
    cogs_features = feature_sets[COGS_FEATURE_EXPERIMENT]
    variants = [CONTROL_NAME] + accepted_variants
    rows: list[dict[str, object]] = []

    for variant in variants:
        for fold_id, (start_date, end_date) in enumerate(BACKTEST_FOLDS, start=1):
            start_ts = pd.Timestamp(start_date)
            end_ts = pd.Timestamp(end_date)
            cutoff = start_ts - pd.Timedelta(days=1)
            adjusted_base = zero_unknown_promo_signals(base, cutoff)
            preds = recursive_forecast_variant(
                feature_store=feature_store,
                full_base=adjusted_base,
                train_end_date=cutoff,
                forecast_start=start_ts,
                forecast_end=end_ts,
                revenue_features=revenue_features,
                cogs_features=cogs_features,
                variant=variant,
            )

            truth = feature_store.loc[
                (feature_store["Date"] >= start_ts) & (feature_store["Date"] <= end_ts),
                ["Date", "Revenue", "COGS"],
            ].copy()
            merged = truth.merge(preds, on="Date", how="left")
            rows.append(
                {
                    "variant": variant,
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
                    "violation_count": int(merged["violation_flag"].sum()),
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
            violation_total=("violation_count", "sum"),
        )
        .reset_index()
        .sort_values("combined_mae_mean")
        .reset_index(drop=True)
    )
    control_combined = float(summary_df.loc[summary_df["variant"] == CONTROL_NAME, "combined_mae_mean"].iloc[0])
    summary_df["delta_combined_mae_vs_control"] = summary_df["combined_mae_mean"] - control_combined
    return fold_df, summary_df


def write_report(
    run_dir: Path,
    one_step_summary: pd.DataFrame,
    one_step_folds: pd.DataFrame,
    accepted_variants: list[str],
    recursive_summary: pd.DataFrame | None,
    recursive_folds: pd.DataFrame | None,
) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# COGS Rate Protocol\n\n")
        f.write("## Design Notes\n")
        f.write("- Governance: two-track, but this run targets the competition-side COGS formulation\n")
        f.write(f"- Revenue feature set fixed to `{REVENUE_EXPERIMENT}`\n")
        f.write(f"- COGS feature set fixed to `{COGS_FEATURE_EXPERIMENT}`\n")
        f.write("- One-step gate compares COGS MAE only, using the same one-step revenue predictions for all variants\n")
        f.write("- Recursive stage compares full-system `combined_mae = revenue_mae + cogs_mae`\n\n")

        f.write("## One-Step Summary\n")
        f.write(one_step_summary.to_markdown(index=False))
        f.write("\n\n")
        f.write(f"Accepted one-step challengers: `{accepted_variants}`\n\n")

        if recursive_summary is not None and recursive_folds is not None:
            f.write("## Recursive Summary\n")
            f.write(recursive_summary.to_markdown(index=False))
            f.write("\n\n")
            f.write("## Recursive Fold Details\n")
            f.write(recursive_folds.to_markdown(index=False))
            f.write("\n\n")
        else:
            f.write("## Recursive Stage\n")
            f.write("- Skipped because no challenger passed the one-step gate.\n\n")

        f.write("## One-Step Fold Details\n")
        f.write(one_step_folds.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting cogs rate protocol in %s", run_dir)

    feature_store, _ = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    write_json(
        run_dir / "config.json",
        {
            "revenue_experiment": REVENUE_EXPERIMENT,
            "cogs_feature_experiment": COGS_FEATURE_EXPERIMENT,
            "control_variant": CONTROL_NAME,
            "rate_variants": list(RATE_SPECS.keys()),
            "recursive_selection_metric": "combined_mae_mean",
        },
    )

    logger.info("Running one-step gate...")
    one_step_folds, one_step_summary, accepted_variants = run_one_step_gate(feature_sets)
    one_step_folds.to_csv(run_dir / "one_step_fold_results.csv", index=False)
    one_step_summary.to_csv(run_dir / "one_step_summary.csv", index=False)
    write_json(run_dir / "one_step_decision.json", {"accepted_variants": accepted_variants})

    recursive_folds: pd.DataFrame | None = None
    recursive_summary: pd.DataFrame | None = None

    if accepted_variants:
        logger.info("Running recursive stage for accepted variants: %s", accepted_variants)
        recursive_folds, recursive_summary = run_recursive_stage(feature_sets, accepted_variants)
        recursive_folds.to_csv(run_dir / "recursive_fold_results.csv", index=False)
        recursive_summary.to_csv(run_dir / "recursive_summary.csv", index=False)
    else:
        logger.info("Skipping recursive stage because no challenger passed one-step gate.")

    write_report(
        run_dir=run_dir,
        one_step_summary=one_step_summary,
        one_step_folds=one_step_folds,
        accepted_variants=accepted_variants,
        recursive_summary=recursive_summary,
        recursive_folds=recursive_folds,
    )
    logger.info("Finished cogs rate protocol. Artifacts written to %s", run_dir)


if __name__ == "__main__":
    main()
