from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from feature_pipeline import CALENDAR_COLUMNS, PROMO_MODEL_COLUMNS, add_calendar_features
from logging_utils import create_run_dir, setup_logger, write_json
from train_recursive_forecast import BACKTEST_FOLDS, TRAIN_END, apply_future_promo_policy, ensure_inputs


RUN_PREFIX = "bottomup_sprint"
DATASET_DIR = Path("dataset")
FORECAST_START = pd.Timestamp("2023-01-01")
FORECAST_END = pd.Timestamp("2024-07-01")
PROMO_POLICY = "seasonal_month_day_recent_2y"

GROUP_LAGS = [1, 7, 14, 28, 56, 91, 364, 365]
GROUP_ROLLS = [7, 28, 56, 91, 364]
GLOBAL_LAGS = [1, 7, 28, 91, 364, 365]
GLOBAL_ROLLS = [7, 28, 91, 364]

GROUP_SIGNAL_SPECS = {
    "units": {"transform": "log1p"},
    "avg_unit_price": {"transform": "log1p"},
    "cogs_ratio": {"transform": "none"},
    "revenue_share": {"transform": "none"},
    "revenue": {"transform": "log1p"},
}
GLOBAL_SIGNAL_SPECS = {
    "total_units": {"transform": "log1p"},
    "total_revenue": {"transform": "log1p"},
}

TARGET_SPECS = {
    "units": {"transform": "log1p"},
    "avg_unit_price": {"transform": "log1p"},
    "cogs_ratio": {"transform": "none"},
}

VARIANT_SPECS = {
    "bottomup_category": {"group_col": "category"},
    "bottomup_segment": {"group_col": "segment"},
}

CATBOOST_PARAMS = {
    "loss_function": "RMSE",
    "iterations": 700,
    "learning_rate": 0.03,
    "depth": 6,
    "l2_leaf_reg": 4.0,
    "subsample": 0.8,
    "random_seed": 42,
    "verbose": False,
    "allow_writing_files": False,
}


def _rmse(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def _transform_target(series: pd.Series, transform: str) -> pd.Series:
    values = series.astype(float)
    if transform == "none":
        return values
    if transform == "log1p":
        return np.log1p(values.clip(lower=0.0))
    raise ValueError(f"Unknown target transform: {transform}")


def _inverse_transform(value: float, transform: str) -> float:
    if transform == "none":
        return float(value)
    if transform == "log1p":
        return float(np.expm1(value))
    raise ValueError(f"Unknown target transform: {transform}")


def _add_series_history_features(
    df: pd.DataFrame,
    column: str,
    prefix: str,
    lags: list[int],
    rolls: list[int],
) -> pd.DataFrame:
    out = df.copy()
    shifted = out[column].shift(1)
    for lag in lags:
        out[f"{prefix}_lag_{lag}"] = out[column].shift(lag)
    for window in rolls:
        rolling = shifted.rolling(window=window, min_periods=1)
        out[f"{prefix}_rollmean_{window}"] = rolling.mean()
    return out


def _load_order_details() -> pd.DataFrame:
    orders = pd.read_csv(DATASET_DIR / "orders.csv", parse_dates=["order_date"], low_memory=False)
    items = pd.read_csv(DATASET_DIR / "order_items.csv", low_memory=False)
    products = pd.read_csv(DATASET_DIR / "products.csv", low_memory=False)

    order_details = (
        items.merge(
            orders[["order_id", "order_date"]],
            on="order_id",
            how="left",
        )
        .merge(
            products[["product_id", "category", "segment", "cogs"]],
            on="product_id",
            how="left",
        )
        .copy()
    )
    order_details["gross_rev"] = order_details["quantity"] * order_details["unit_price"]
    order_details["gross_cogs"] = order_details["quantity"] * order_details["cogs"]
    return order_details[
        ["order_date", "category", "segment", "quantity", "gross_rev", "gross_cogs"]
    ].copy()


def build_group_panel(
    order_details: pd.DataFrame,
    base: pd.DataFrame,
    group_col: str,
) -> pd.DataFrame:
    groups = sorted(order_details[group_col].dropna().astype(str).unique().tolist())
    full_grid = (
        pd.MultiIndex.from_product(
            [base["Date"].sort_values().unique(), groups],
            names=["Date", "group_key"],
        )
        .to_frame(index=False)
        .sort_values(["group_key", "Date"])
        .reset_index(drop=True)
    )

    grouped = (
        order_details.assign(group_key=order_details[group_col].astype(str))
        .groupby(["order_date", "group_key"], as_index=False)
        .agg(
            units=("quantity", "sum"),
            revenue=("gross_rev", "sum"),
            cogs=("gross_cogs", "sum"),
        )
        .rename(columns={"order_date": "Date"})
    )
    grouped["avg_unit_price"] = grouped["revenue"] / grouped["units"].replace(0, np.nan)
    grouped["cogs_ratio"] = grouped["cogs"] / grouped["revenue"].replace(0, np.nan)

    panel = full_grid.merge(grouped, on=["Date", "group_key"], how="left")
    panel["is_train"] = panel["Date"] <= TRAIN_END
    train_mask = panel["is_train"]

    panel.loc[train_mask, ["units", "revenue", "cogs"]] = panel.loc[
        train_mask, ["units", "revenue", "cogs"]
    ].fillna(0.0)
    panel["avg_unit_price"] = panel["revenue"] / panel["units"].replace(0, np.nan)
    panel["cogs_ratio"] = panel["cogs"] / panel["revenue"].replace(0, np.nan)

    for column in ["avg_unit_price", "cogs_ratio"]:
        panel.loc[train_mask, column] = (
            panel.loc[train_mask]
            .groupby("group_key")[column]
            .transform(lambda s: s.ffill().bfill())
        )
        fallback = float(panel.loc[train_mask, column].median())
        panel.loc[train_mask, column] = panel.loc[train_mask, column].fillna(fallback)

    panel.loc[train_mask, "cogs_ratio"] = panel.loc[train_mask, "cogs_ratio"].clip(0.0, 0.995)

    daily_revenue = panel.loc[train_mask].groupby("Date")["revenue"].transform("sum")
    panel.loc[train_mask, "revenue_share"] = (
        panel.loc[train_mask, "revenue"] / daily_revenue.replace(0, np.nan)
    ).fillna(0.0)
    return panel


def add_training_features(panel_train: pd.DataFrame, adjusted_base: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    promo_cols = [col for col in PROMO_MODEL_COLUMNS if col in adjusted_base.columns]
    base_features = adjusted_base[["Date"] + promo_cols].copy()

    featured = panel_train.copy().sort_values(["group_key", "Date"]).reset_index(drop=True)
    featured = featured.merge(base_features, on="Date", how="left")

    daily_totals = (
        featured.groupby("Date", as_index=False)
        .agg(total_units=("units", "sum"), total_revenue=("revenue", "sum"))
        .sort_values("Date")
        .reset_index(drop=True)
    )
    for signal in GLOBAL_SIGNAL_SPECS:
        daily_totals = _add_series_history_features(
            daily_totals,
            column=signal,
            prefix=signal,
            lags=GLOBAL_LAGS,
            rolls=GLOBAL_ROLLS,
        )
    global_feature_cols = [
        col
        for col in daily_totals.columns
        if col != "Date" and col not in GLOBAL_SIGNAL_SPECS
    ]
    featured = featured.merge(daily_totals[["Date"] + global_feature_cols], on="Date", how="left")

    group_feature_cols: list[str] = []
    for signal in GROUP_SIGNAL_SPECS:
        grouped = featured.groupby("group_key")[signal]
        for lag in GROUP_LAGS:
            col_name = f"{signal}_lag_{lag}"
            featured[col_name] = grouped.shift(lag)
            group_feature_cols.append(col_name)
        for window in GROUP_ROLLS:
            col_name = f"{signal}_rollmean_{window}"
            featured[col_name] = grouped.transform(
                lambda s, w=window: s.shift(1).rolling(window=w, min_periods=1).mean()
            )
            group_feature_cols.append(col_name)

    featured = add_calendar_features(featured)

    feature_cols = ["group_key"] + [col for col in CALENDAR_COLUMNS if col in featured.columns]
    feature_cols += promo_cols
    feature_cols += sorted(set(group_feature_cols))
    feature_cols += sorted(set(global_feature_cols))
    cat_feature_cols = ["group_key"]
    return featured, feature_cols, cat_feature_cols


def fit_bottomup_models(
    train_features: pd.DataFrame,
    feature_cols: list[str],
    cat_feature_cols: list[str],
) -> dict[str, CatBoostRegressor]:
    models: dict[str, CatBoostRegressor] = {}
    X = train_features[feature_cols]
    for target, spec in TARGET_SPECS.items():
        y = _transform_target(train_features[target], str(spec["transform"]))
        model = CatBoostRegressor(**CATBOOST_PARAMS)
        model.fit(X, y, cat_features=cat_feature_cols)
        models[target] = model
    return models


def build_group_stats(train_panel: pd.DataFrame) -> dict[str, dict[str, float]]:
    stats: dict[str, dict[str, float]] = {}
    for group_key, group_df in train_panel.groupby("group_key"):
        stats[str(group_key)] = {
            "units_default": float(group_df["units"].median()),
            "avg_unit_price_default": float(group_df["avg_unit_price"].median()),
            "cogs_ratio_default": float(group_df["cogs_ratio"].median()),
            "revenue_share_default": float(group_df["revenue_share"].mean()),
            "revenue_default": float(group_df["revenue"].median()),
            "price_lower": float(group_df["avg_unit_price"].quantile(0.05)),
            "price_upper": float(group_df["avg_unit_price"].quantile(0.95)),
            "ratio_lower": float(group_df["cogs_ratio"].quantile(0.05)),
            "ratio_upper": float(group_df["cogs_ratio"].quantile(0.95)),
        }
    return stats


def make_history_maps(
    train_panel: pd.DataFrame,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    history_by_group: dict[str, pd.DataFrame] = {}
    for group_key, group_df in train_panel.groupby("group_key"):
        history_by_group[str(group_key)] = (
            group_df[["Date", "units", "avg_unit_price", "cogs_ratio", "revenue", "cogs", "revenue_share"]]
            .copy()
            .set_index("Date")
            .sort_index()
        )
    total_history = (
        train_panel.groupby("Date", as_index=True)
        .agg(total_units=("units", "sum"), total_revenue=("revenue", "sum"))
        .sort_index()
    )
    return history_by_group, total_history


def _lag_value(series: pd.Series, current_date: pd.Timestamp, lag: int, fallback: float) -> float:
    lookup_date = current_date - pd.Timedelta(days=lag)
    if lookup_date in series.index:
        value = series.loc[lookup_date]
        if pd.notna(value):
            return float(value)
    return fallback


def _roll_mean(series: pd.Series, current_date: pd.Timestamp, window: int, fallback: float) -> float:
    start = current_date - pd.Timedelta(days=window)
    end = current_date - pd.Timedelta(days=1)
    values = series.loc[(series.index >= start) & (series.index <= end)].dropna()
    if values.empty:
        return fallback
    return float(values.mean())


def build_feature_row(
    current_date: pd.Timestamp,
    group_key: str,
    known_base: pd.DataFrame,
    history_by_group: dict[str, pd.DataFrame],
    total_history: pd.DataFrame,
    group_stats: dict[str, dict[str, float]],
    feature_cols: list[str],
) -> pd.DataFrame:
    row = known_base.loc[[current_date]].copy()
    row["group_key"] = group_key

    group_history = history_by_group[group_key]
    defaults = group_stats[group_key]
    for signal in GROUP_SIGNAL_SPECS:
        signal_series = group_history[signal]
        fallback = defaults[f"{signal}_default"]
        for lag in GROUP_LAGS:
            row[f"{signal}_lag_{lag}"] = _lag_value(signal_series, current_date, lag, fallback)
        for window in GROUP_ROLLS:
            row[f"{signal}_rollmean_{window}"] = _roll_mean(signal_series, current_date, window, fallback)

    for signal in GLOBAL_SIGNAL_SPECS:
        signal_series = total_history[signal]
        fallback = float(signal_series.median()) if not signal_series.empty else 0.0
        for lag in GLOBAL_LAGS:
            row[f"{signal}_lag_{lag}"] = _lag_value(signal_series, current_date, lag, fallback)
        for window in GLOBAL_ROLLS:
            row[f"{signal}_rollmean_{window}"] = _roll_mean(signal_series, current_date, window, fallback)

    return row.reindex(columns=feature_cols)


def recursive_forecast_variant(
    panel: pd.DataFrame,
    adjusted_base: pd.DataFrame,
    forecast_start: pd.Timestamp,
    forecast_end: pd.Timestamp,
    cutoff: pd.Timestamp,
) -> pd.DataFrame:
    train_panel = panel.loc[panel["Date"] <= cutoff].copy()
    training_frame, feature_cols, cat_feature_cols = add_training_features(train_panel, adjusted_base)
    models = fit_bottomup_models(training_frame, feature_cols, cat_feature_cols)

    known_base = add_calendar_features(
        adjusted_base[["Date"] + [col for col in PROMO_MODEL_COLUMNS if col in adjusted_base.columns]].copy()
    ).set_index("Date")
    history_by_group, total_history = make_history_maps(train_panel)
    group_stats = build_group_stats(train_panel)
    group_keys = sorted(history_by_group.keys())

    results: list[dict[str, float | str]] = []
    forecast_dates = pd.date_range(start=forecast_start, end=forecast_end, freq="D")
    for current_date in forecast_dates:
        daily_rows: list[dict[str, float | str]] = []
        for group_key in group_keys:
            feature_row = build_feature_row(
                current_date=current_date,
                group_key=group_key,
                known_base=known_base,
                history_by_group=history_by_group,
                total_history=total_history,
                group_stats=group_stats,
                feature_cols=feature_cols,
            )
            pred_units = _inverse_transform(
                float(models["units"].predict(feature_row)[0]),
                str(TARGET_SPECS["units"]["transform"]),
            )
            pred_price = _inverse_transform(
                float(models["avg_unit_price"].predict(feature_row)[0]),
                str(TARGET_SPECS["avg_unit_price"]["transform"]),
            )
            pred_ratio = _inverse_transform(
                float(models["cogs_ratio"].predict(feature_row)[0]),
                str(TARGET_SPECS["cogs_ratio"]["transform"]),
            )

            stats = group_stats[group_key]
            pred_units = max(pred_units, 0.0)
            pred_price = np.clip(
                pred_price,
                a_min=max(0.0, stats["price_lower"] * 0.8),
                a_max=max(stats["price_upper"] * 1.2, stats["price_lower"] * 0.8 + 1e-9),
            )
            pred_ratio = np.clip(
                pred_ratio,
                a_min=max(0.0, stats["ratio_lower"] * 0.8),
                a_max=min(0.995, max(stats["ratio_upper"] * 1.2, 0.01)),
            )
            pred_revenue = float(pred_units * pred_price)
            pred_cogs = float(pred_revenue * pred_ratio)

            daily_rows.append(
                {
                    "Date": current_date,
                    "group_key": group_key,
                    "units": float(pred_units),
                    "avg_unit_price": float(pred_price),
                    "cogs_ratio": float(pred_ratio),
                    "revenue": pred_revenue,
                    "cogs": pred_cogs,
                }
            )

        daily_df = pd.DataFrame(daily_rows)
        total_revenue = float(daily_df["revenue"].sum())
        total_units = float(daily_df["units"].sum())
        total_history.loc[current_date, ["total_units", "total_revenue"]] = [total_units, total_revenue]

        for row in daily_rows:
            revenue_share = row["revenue"] / total_revenue if total_revenue > 0 else 0.0
            history_by_group[str(row["group_key"])].loc[current_date, :] = [
                row["units"],
                row["avg_unit_price"],
                row["cogs_ratio"],
                row["revenue"],
                row["cogs"],
                revenue_share,
            ]

        results.extend(daily_rows)

    group_preds = pd.DataFrame(results)
    return (
        group_preds.groupby("Date", as_index=False)
        .agg(Revenue_pred=("revenue", "sum"), COGS_pred=("cogs", "sum"))
        .sort_values("Date")
        .reset_index(drop=True)
    )


def evaluate_variant(
    variant_name: str,
    panel: pd.DataFrame,
    base: pd.DataFrame,
) -> tuple[list[dict[str, object]], dict[int, pd.DataFrame], pd.DataFrame]:
    fold_rows: list[dict[str, object]] = []
    fold_predictions: dict[int, pd.DataFrame] = {}

    for fold_id, (start_date, end_date) in enumerate(BACKTEST_FOLDS, start=1):
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        cutoff = start_ts - pd.Timedelta(days=1)
        adjusted_base = apply_future_promo_policy(base, cutoff, PROMO_POLICY)
        preds = recursive_forecast_variant(
            panel=panel,
            adjusted_base=adjusted_base,
            forecast_start=start_ts,
            forecast_end=end_ts,
            cutoff=cutoff,
        )
        truth = base.loc[
            (base["Date"] >= start_ts) & (base["Date"] <= end_ts),
            ["Date", "Revenue", "COGS"],
        ].copy()
        merged = truth.merge(preds, on="Date", how="left")
        fold_predictions[fold_id] = preds.copy()
        fold_predictions[fold_id]["fold"] = fold_id
        fold_rows.append(
            {
                "candidate_id": variant_name,
                "fold": fold_id,
                "start_date": start_date,
                "end_date": end_date,
                "revenue_mae": mean_absolute_error(merged["Revenue"], merged["Revenue_pred"]),
                "revenue_rmse": _rmse(merged["Revenue"], merged["Revenue_pred"]),
                "revenue_r2": r2_score(merged["Revenue"], merged["Revenue_pred"]),
                "cogs_mae": mean_absolute_error(merged["COGS"], merged["COGS_pred"]),
                "cogs_rmse": _rmse(merged["COGS"], merged["COGS_pred"]),
                "cogs_r2": r2_score(merged["COGS"], merged["COGS_pred"]),
            }
        )

    final_adjusted_base = apply_future_promo_policy(base, TRAIN_END, PROMO_POLICY)
    final_preds = recursive_forecast_variant(
        panel=panel,
        adjusted_base=final_adjusted_base,
        forecast_start=FORECAST_START,
        forecast_end=FORECAST_END,
        cutoff=TRAIN_END,
    )
    return fold_rows, fold_predictions, final_preds


def blend_predictions(pred_a: pd.DataFrame, pred_b: pd.DataFrame, weight_a: float) -> pd.DataFrame:
    merged = pred_a.merge(pred_b, on="Date", suffixes=("_a", "_b"))
    return pd.DataFrame(
        {
            "Date": merged["Date"],
            "Revenue_pred": weight_a * merged["Revenue_pred_a"] + (1.0 - weight_a) * merged["Revenue_pred_b"],
            "COGS_pred": weight_a * merged["COGS_pred_a"] + (1.0 - weight_a) * merged["COGS_pred_b"],
        }
    )


def summarize_results(fold_results: pd.DataFrame) -> pd.DataFrame:
    summary = (
        fold_results.groupby("candidate_id")
        .agg(
            revenue_mae_mean=("revenue_mae", "mean"),
            revenue_mae_std=("revenue_mae", "std"),
            revenue_rmse_mean=("revenue_rmse", "mean"),
            revenue_r2_mean=("revenue_r2", "mean"),
            cogs_mae_mean=("cogs_mae", "mean"),
            cogs_mae_std=("cogs_mae", "std"),
            cogs_rmse_mean=("cogs_rmse", "mean"),
            cogs_r2_mean=("cogs_r2", "mean"),
        )
        .reset_index()
    )
    summary["combined_mae_mean"] = 0.5 * (summary["revenue_mae_mean"] + summary["cogs_mae_mean"])
    summary["combined_mae_std_proxy"] = 0.5 * (
        summary["revenue_mae_std"].fillna(0.0) + summary["cogs_mae_std"].fillna(0.0)
    )
    return summary.sort_values(["combined_mae_mean", "cogs_mae_mean"]).reset_index(drop=True)


def write_report(run_dir: Path, summary: pd.DataFrame, fold_results: pd.DataFrame) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Bottom-Up Sprint\n\n")
        f.write("## Framing\n")
        f.write("- Structural challenger only: no near-anchor weight tuning in this sprint.\n")
        f.write("- Each bottom-up variant forecasts `units`, `avg_unit_price`, and `cogs_ratio`, then re-aggregates to total Revenue and COGS.\n")
        f.write("- Future promotions use the same seasonal policy already trusted in the recursive baseline pipeline.\n")
        f.write("- Variants: category panel, segment panel, and a 50/50 blend of both aggregate forecasts.\n\n")
        f.write("## Candidate Ranking\n")
        f.write(summary.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Fold Metrics\n")
        f.write(fold_results.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting bottom-up sprint in %s", run_dir)

    _, base = ensure_inputs()
    order_details = _load_order_details()
    panels = {
        variant_name: build_group_panel(order_details, base, spec["group_col"])
        for variant_name, spec in VARIANT_SPECS.items()
    }

    all_fold_rows: list[dict[str, object]] = []
    fold_predictions_by_variant: dict[str, dict[int, pd.DataFrame]] = {}
    final_predictions_by_variant: dict[str, pd.DataFrame] = {}

    for variant_name, panel in panels.items():
        logger.info("Evaluating %s", variant_name)
        fold_rows, fold_predictions, final_preds = evaluate_variant(variant_name, panel, base)
        all_fold_rows.extend(fold_rows)
        fold_predictions_by_variant[variant_name] = fold_predictions
        final_predictions_by_variant[variant_name] = final_preds

        submission = final_preds.rename(columns={"Revenue_pred": "Revenue", "COGS_pred": "COGS"})
        submission["Date"] = pd.to_datetime(submission["Date"]).dt.strftime("%Y-%m-%d")
        dataset_path = DATASET_DIR / f"submission_{variant_name}.csv"
        run_path = run_dir / f"submission_{variant_name}.csv"
        submission.to_csv(dataset_path, index=False)
        submission.to_csv(run_path, index=False)
        logger.info("Exported submission for %s", variant_name)

    blend_name = "bottomup_category_segment_blend50"
    for fold_id in range(1, len(BACKTEST_FOLDS) + 1):
        blended = blend_predictions(
            fold_predictions_by_variant["bottomup_category"][fold_id],
            fold_predictions_by_variant["bottomup_segment"][fold_id],
            weight_a=0.5,
        )
        truth = base.loc[
            (base["Date"] >= pd.Timestamp(BACKTEST_FOLDS[fold_id - 1][0]))
            & (base["Date"] <= pd.Timestamp(BACKTEST_FOLDS[fold_id - 1][1])),
            ["Date", "Revenue", "COGS"],
        ].copy()
        merged = truth.merge(blended, on="Date", how="left")
        all_fold_rows.append(
            {
                "candidate_id": blend_name,
                "fold": fold_id,
                "start_date": BACKTEST_FOLDS[fold_id - 1][0],
                "end_date": BACKTEST_FOLDS[fold_id - 1][1],
                "revenue_mae": mean_absolute_error(merged["Revenue"], merged["Revenue_pred"]),
                "revenue_rmse": _rmse(merged["Revenue"], merged["Revenue_pred"]),
                "revenue_r2": r2_score(merged["Revenue"], merged["Revenue_pred"]),
                "cogs_mae": mean_absolute_error(merged["COGS"], merged["COGS_pred"]),
                "cogs_rmse": _rmse(merged["COGS"], merged["COGS_pred"]),
                "cogs_r2": r2_score(merged["COGS"], merged["COGS_pred"]),
            }
        )
    final_blended = blend_predictions(
        final_predictions_by_variant["bottomup_category"],
        final_predictions_by_variant["bottomup_segment"],
        weight_a=0.5,
    )
    final_predictions_by_variant[blend_name] = final_blended
    blend_submission = final_blended.rename(columns={"Revenue_pred": "Revenue", "COGS_pred": "COGS"})
    blend_submission["Date"] = pd.to_datetime(blend_submission["Date"]).dt.strftime("%Y-%m-%d")
    blend_dataset_path = DATASET_DIR / f"submission_{blend_name}.csv"
    blend_run_path = run_dir / f"submission_{blend_name}.csv"
    blend_submission.to_csv(blend_dataset_path, index=False)
    blend_submission.to_csv(blend_run_path, index=False)
    logger.info("Exported submission for %s", blend_name)

    fold_results = pd.DataFrame(all_fold_rows).sort_values(["candidate_id", "fold"]).reset_index(drop=True)
    summary = summarize_results(fold_results)
    fold_results.to_csv(run_dir / "fold_results.csv", index=False)
    summary.to_csv(run_dir / "summary.csv", index=False)

    winner = str(summary.iloc[0]["candidate_id"])
    write_json(
        run_dir / "manifest.json",
        {
            "promo_policy": PROMO_POLICY,
            "variants": list(final_predictions_by_variant.keys()),
            "winner": winner,
        },
    )
    write_report(run_dir, summary, fold_results)
    logger.info("Saved summary to %s", run_dir / "summary.csv")
    logger.info("Top candidate: %s", winner)


if __name__ == "__main__":
    main()
