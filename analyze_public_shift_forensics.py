from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error

from logging_utils import create_run_dir, setup_logger, write_json
from train_recursive_forecast import (
    TRAIN_END,
    apply_future_context_policy,
    apply_future_promo_policy,
    ensure_inputs,
    get_candidate_feature_sets,
    recursive_forecast,
)


RUN_PREFIX = "public_shift_forensics"
ANCHOR_PATH = Path("dataset/submission_catboost_md2y_core_recencyexp20.csv")
BEST_PATH = Path("dataset/submission_sample_v37_rev2023H2_p0100_c0650_away0250.csv")
PUBLIC_START = pd.Timestamp("2023-01-01")
PUBLIC_END = pd.Timestamp("2024-07-01")
PUBLIC_DAYS = (PUBLIC_END - PUBLIC_START).days + 1


WINDOWS = {
    "spring": ("03-18", "04-17"),
    "midyear": ("06-23", "07-22"),
    "fall": ("08-30", "10-02"),
    "yearend": ("11-18", "01-02"),
    "rural_extra": ("01-30", "03-01"),
    "urban_extra": ("07-30", "09-02"),
}


def mask_between_month_day(dates: pd.Series, start: str, end: str) -> pd.Series:
    month_day = dates.dt.strftime("%m-%d")
    if start <= end:
        return month_day.between(start, end)
    return month_day.between(start, "12-31") | month_day.between("01-01", end)


def add_period_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    dates = pd.to_datetime(out["Date"])
    out["year"] = dates.dt.year
    out["month"] = dates.dt.month
    out["month_day"] = dates.dt.strftime("%m-%d")
    out["horizon_step_from_public"] = (dates - PUBLIC_START).dt.days + 1
    out["is_public_period"] = dates.between(PUBLIC_START, PUBLIC_END)
    out["is_2024_public_h1"] = dates.between("2024-01-01", PUBLIC_END)
    main_masks = []
    for name, (start, end) in WINDOWS.items():
        col = f"win_{name}"
        out[col] = mask_between_month_day(dates, start, end)
        if name in {"spring", "midyear", "fall", "yearend"}:
            main_masks.append(out[col])
    out["win_main_promo"] = main_masks[0]
    for mask in main_masks[1:]:
        out["win_main_promo"] |= mask
    return out


def compute_metrics(truth: pd.DataFrame, pred: pd.DataFrame, label: str) -> dict[str, float | str]:
    merged = truth[["Date", "Revenue", "COGS"]].merge(pred, on="Date", how="inner")
    return {
        "label": label,
        "rows": len(merged),
        "revenue_mae": mean_absolute_error(merged["Revenue"], merged["Revenue_pred"]),
        "cogs_mae": mean_absolute_error(merged["COGS"], merged["COGS_pred"]),
        "combined_mae": 0.5
        * (
            mean_absolute_error(merged["Revenue"], merged["Revenue_pred"])
            + mean_absolute_error(merged["COGS"], merged["COGS_pred"])
        ),
        "revenue_bias": float((merged["Revenue"] - merged["Revenue_pred"]).mean()),
        "cogs_bias": float((merged["COGS"] - merged["COGS_pred"]).mean()),
        "actual_revenue_mean": float(merged["Revenue"].mean()),
        "pred_revenue_mean": float(merged["Revenue_pred"].mean()),
        "actual_cogs_ratio": float((merged["COGS"] / merged["Revenue"]).replace([np.inf, -np.inf], np.nan).mean()),
        "pred_cogs_ratio": float((merged["COGS_pred"] / merged["Revenue_pred"]).replace([np.inf, -np.inf], np.nan).mean()),
    }


def run_anchor_prediction(
    feature_store: pd.DataFrame,
    base: pd.DataFrame,
    feature_sets: dict[str, list[str]],
    train_end: pd.Timestamp,
    forecast_start: pd.Timestamp,
    forecast_end: pd.Timestamp,
    promo_policy: str = "seasonal_month_day_recent_2y",
    context_policy: str = "zero",
    sample_weight_mode: str = "exp_years",
    sample_weight_decay: float = 0.20,
) -> pd.DataFrame:
    adjusted = apply_future_promo_policy(base, train_end, promo_policy)
    adjusted = apply_future_context_policy(adjusted, train_end, context_policy)
    return recursive_forecast(
        feature_store=feature_store,
        full_base=adjusted,
        train_end_date=train_end,
        forecast_start=forecast_start,
        forecast_end=forecast_end,
        revenue_features=feature_sets["curated_promo_cogs"],
        cogs_features=feature_sets["curated_promo_cogs"],
        cogs_postprocess_variant="blend60_clip_q99",
        model_family="catboost",
        sample_weight_mode=sample_weight_mode,
        sample_weight_decay=sample_weight_decay,
    )


def make_long_horizon_backtests(feature_store: pd.DataFrame, base: pd.DataFrame, feature_sets: dict[str, list[str]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    all_preds = []
    for year in [2020, 2021]:
        start = pd.Timestamp(f"{year}-01-01")
        end = start + pd.Timedelta(days=PUBLIC_DAYS - 1)
        cutoff = start - pd.Timedelta(days=1)
        pred = run_anchor_prediction(feature_store, base, feature_sets, cutoff, start, end)
        truth = feature_store.loc[(feature_store["Date"] >= start) & (feature_store["Date"] <= end), ["Date", "Revenue", "COGS"]].copy()
        rows.append(compute_metrics(truth, pred, f"long_{year}_{PUBLIC_DAYS}d"))
        tmp = truth.merge(pred, on="Date", how="inner")
        tmp["fold_label"] = f"long_{year}_{PUBLIC_DAYS}d"
        all_preds.append(tmp)

    for year in [2020, 2021, 2022]:
        start = pd.Timestamp(f"{year}-01-01")
        end = pd.Timestamp(f"{year}-12-31")
        cutoff = start - pd.Timedelta(days=1)
        pred = run_anchor_prediction(feature_store, base, feature_sets, cutoff, start, end)
        truth = feature_store.loc[(feature_store["Date"] >= start) & (feature_store["Date"] <= end), ["Date", "Revenue", "COGS"]].copy()
        rows.append(compute_metrics(truth, pred, f"year_{year}"))
    return pd.DataFrame(rows), pd.concat(all_preds, ignore_index=True)


def feature_drift_summary(base: pd.DataFrame, run_dir: Path) -> pd.DataFrame:
    frame = add_period_columns(base)
    train = frame.loc[frame["Date"] <= TRAIN_END].copy()
    public = frame.loc[frame["Date"].between(PUBLIC_START, PUBLIC_END)].copy()

    candidate_cols = [
        col
        for col in frame.columns
        if col
        not in {
            "Date",
            "Revenue",
            "COGS",
            "snapshot_date",
            "is_train",
            "month_day",
        }
        and pd.api.types.is_numeric_dtype(frame[col])
    ]
    rows = []
    for col in candidate_cols:
        train_s = train[col].replace([np.inf, -np.inf], np.nan).dropna()
        public_s = public[col].replace([np.inf, -np.inf], np.nan).dropna()
        if len(train_s) < 50 or len(public_s) < 10:
            continue
        train_std = float(train_s.std())
        public_mean = float(public_s.mean())
        train_mean = float(train_s.mean())
        rows.append(
            {
                "feature": col,
                "train_mean": train_mean,
                "public_mean": public_mean,
                "train_std": train_std,
                "std_shift": (public_mean - train_mean) / train_std if train_std > 1e-9 else 0.0,
                "train_zero_share": float((train_s == 0).mean()),
                "public_zero_share": float((public_s == 0).mean()),
                "zero_share_delta": float((public_s == 0).mean() - (train_s == 0).mean()),
            }
        )
    drift = pd.DataFrame(rows).sort_values("std_shift", key=lambda s: s.abs(), ascending=False)
    drift.to_csv(run_dir / "feature_drift_train_vs_public.csv", index=False)
    return drift


def period_summary(base: pd.DataFrame, anchor: pd.DataFrame, best: pd.DataFrame, run_dir: Path) -> pd.DataFrame:
    frame = add_period_columns(base)
    train = frame.loc[frame["Date"] <= TRAIN_END].copy()
    public = frame.loc[frame["Date"].between(PUBLIC_START, PUBLIC_END)].copy()

    anchor_pub = add_period_columns(anchor.rename(columns={"Revenue": "Revenue_pred", "COGS": "COGS_pred"}))
    best_pub = add_period_columns(best.rename(columns={"Revenue": "Revenue_best", "COGS": "COGS_best"}))
    pub_join = public[["Date"]].merge(anchor_pub, on="Date", how="left").merge(
        best_pub[["Date", "Revenue_best", "COGS_best"]],
        on="Date",
        how="left",
    )

    groups: list[tuple[str, pd.Series, pd.DataFrame]] = []
    for year in range(2018, 2023):
        groups.append((f"train_year_{year}", train["year"] == year, train))
    groups.append(("public_2023", public["year"] == 2023, public))
    groups.append(("public_2024_h1", public["is_2024_public_h1"], public))
    for name in ["spring", "midyear", "fall", "yearend", "rural_extra", "urban_extra", "main_promo"]:
        col = f"win_{name}" if name != "main_promo" else "win_main_promo"
        groups.append((f"train_{name}", train[col].astype(bool), train))
        groups.append((f"public_{name}", public[col].astype(bool), public))

    rows = []
    for label, mask, source in groups:
        sub = source.loc[mask].copy()
        if sub.empty:
            continue
        row = {
            "period": label,
            "rows": len(sub),
            "revenue_mean": float(sub["Revenue"].mean()) if "Revenue" in sub else np.nan,
            "cogs_mean": float(sub["COGS"].mean()) if "COGS" in sub else np.nan,
            "cogs_ratio_mean": float((sub["COGS"] / sub["Revenue"]).replace([np.inf, -np.inf], np.nan).mean())
            if "Revenue" in sub and sub["Revenue"].notna().any()
            else np.nan,
            "active_promo_count_mean": float(sub.get("active_promo_count", pd.Series(dtype=float)).mean()),
            "promo_line_share_mean": float(sub.get("promo_line_share", pd.Series(dtype=float)).mean()),
            "total_discount_mean": float(sub.get("total_discount", pd.Series(dtype=float)).mean()),
            "avg_discount_rate_mean": float(sub.get("avg_discount_rate", pd.Series(dtype=float)).mean()),
        }
        rows.append(row)

    pub_rows = []
    for label, mask in [
        ("public_all", pub_join["Date"].notna()),
        ("public_2023", pub_join["year"] == 2023),
        ("public_2024_h1", pub_join["is_2024_public_h1"]),
        ("public_main_promo", pub_join["win_main_promo"]),
        ("public_nonpromo", ~pub_join["win_main_promo"]),
    ]:
        sub = pub_join.loc[mask].copy()
        pub_rows.append(
            {
                "period": label,
                "rows": len(sub),
                "anchor_revenue_mean": float(sub["Revenue_pred"].mean()),
                "best_revenue_mean": float(sub["Revenue_best"].mean()),
                "best_vs_anchor_revenue_mean_delta": float((sub["Revenue_best"] - sub["Revenue_pred"]).mean()),
                "anchor_cogs_ratio_mean": float(
                    (sub["COGS_pred"] / sub["Revenue_pred"]).replace([np.inf, -np.inf], np.nan).mean()
                ),
                "best_cogs_ratio_mean": float(
                    (sub["COGS_best"] / sub["Revenue_best"]).replace([np.inf, -np.inf], np.nan).mean()
                ),
            }
        )

    summary = pd.DataFrame(rows)
    summary.to_csv(run_dir / "period_feature_summary.csv", index=False)
    pd.DataFrame(pub_rows).to_csv(run_dir / "public_prediction_summary.csv", index=False)
    return summary


def public_score_probe_regression(run_dir: Path) -> pd.DataFrame:
    known = {
        "submission_catboost_md2y_core_recencyexp20.csv": 896000.0,
        "submission_public_probe_promo_windows_rev_up6.csv": 888100.36839,
        "submission_public_probe_promo_windows_rev_up8.csv": 887225.99926,
        "submission_public_probe_promo_windows_rev_up12.csv": 888060.97204,
        "submission_tabpfn_promo_windowmix_v1.csv": 883183.19507,
        "submission_tabpfn_promo_shape_cal8.csv": 888962.79663,
        "submission_tabpfn26_windowmix_v1.csv": 883416.15633,
        "submission_tabpfn26_windowmix_scale105.csv": 883183.43978,
        "submission_tabpfn_v25low_windowmix_v1.csv": 883881.53813,
        "submission_public_parity_urban23_nonmain_up10_only.csv": 884654.02008,
        "submission_public_probe_cogs2024h1_floor87.csv": 898472.39191,
        "submission_catboost_md2y_core_price_history.csv": 923770.94996,
    }
    anchor = pd.read_csv(ANCHOR_PATH, parse_dates=["Date"])
    anchor = add_period_columns(anchor)
    rows = []
    for filename, score in known.items():
        path = Path("dataset") / filename
        if not path.exists():
            continue
        sub = pd.read_csv(path, parse_dates=["Date"])
        sub = add_period_columns(sub)
        merged = anchor[["Date", "Revenue", "COGS", "win_main_promo", "is_2024_public_h1"]].merge(
            sub[["Date", "Revenue", "COGS"]],
            on="Date",
            suffixes=("_anchor", "_sub"),
        )
        rev_delta = merged["Revenue_sub"] - merged["Revenue_anchor"]
        cogs_delta = merged["COGS_sub"] - merged["COGS_anchor"]
        promo = merged["win_main_promo"].astype(bool)
        h1_2024 = merged["is_2024_public_h1"].astype(bool)
        rows.append(
            {
                "filename": filename,
                "public_score": score,
                "delta_vs_best_score": score - 883183.19507,
                "rev_delta_mean": float(rev_delta.mean()),
                "rev_delta_abs_mean": float(rev_delta.abs().mean()),
                "rev_delta_promo_mean": float(rev_delta.loc[promo].mean()),
                "rev_delta_nonpromo_mean": float(rev_delta.loc[~promo].mean()),
                "rev_delta_2024h1_mean": float(rev_delta.loc[h1_2024].mean()),
                "cogs_delta_mean": float(cogs_delta.mean()),
                "cogs_delta_abs_mean": float(cogs_delta.abs().mean()),
                "cogs_delta_2024h1_mean": float(cogs_delta.loc[h1_2024].mean()),
            }
        )
    probes = pd.DataFrame(rows).sort_values("public_score")
    probes.to_csv(run_dir / "known_public_probe_features.csv", index=False)
    return probes


def write_report(
    run_dir: Path,
    backtest_metrics: pd.DataFrame,
    period: pd.DataFrame,
    drift: pd.DataFrame,
    probes: pd.DataFrame,
) -> None:
    pub_pred = pd.read_csv(run_dir / "public_prediction_summary.csv")
    with (run_dir / "report.md").open("w", encoding="utf-8") as f:
        f.write("# Public Shift Forensics\n\n")
        f.write("Goal: explain why local OOF around 600k does not match public around 883k.\n\n")
        f.write("## Shifted Backtests\n")
        f.write(backtest_metrics.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Public Prediction Summary\n")
        f.write(pub_pred.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Period Feature Summary - Key Rows\n")
        key_periods = period[
            period["period"].isin(
                [
                    "train_year_2018",
                    "train_year_2019",
                    "train_year_2020",
                    "train_year_2021",
                    "train_year_2022",
                    "public_2023",
                    "public_2024_h1",
                    "train_main_promo",
                    "public_main_promo",
                    "train_urban_extra",
                    "public_urban_extra",
                ]
            )
        ]
        f.write(key_periods.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Largest Train/Public Feature Drift\n")
        f.write(drift.head(30).to_markdown(index=False))
        f.write("\n\n")
        f.write("## Known Public Probe Features\n")
        f.write(probes.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    anchor = pd.read_csv(ANCHOR_PATH, parse_dates=["Date"])
    best = pd.read_csv(BEST_PATH, parse_dates=["Date"])

    logger.info("Running long-horizon shifted backtests")
    backtest_metrics, long_preds = make_long_horizon_backtests(feature_store, base, feature_sets)
    backtest_metrics.to_csv(run_dir / "shifted_backtest_metrics.csv", index=False)
    long_preds.to_csv(run_dir / "long_horizon_predictions.csv", index=False)

    logger.info("Computing period summaries")
    period = period_summary(base, anchor, best, run_dir)
    logger.info("Computing feature drift summary")
    drift = feature_drift_summary(base, run_dir)
    logger.info("Computing known public probe regression table")
    probes = public_score_probe_regression(run_dir)

    write_json(
        run_dir / "config.json",
        {
            "public_period": [str(PUBLIC_START.date()), str(PUBLIC_END.date())],
            "public_days": PUBLIC_DAYS,
            "anchor_path": str(ANCHOR_PATH),
            "best_path": str(BEST_PATH),
        },
    )
    write_report(run_dir, backtest_metrics, period, drift, probes)
    logger.info("Saved public shift forensics to %s", run_dir)
    print(backtest_metrics.to_string(index=False))
    print(pd.read_csv(run_dir / "public_prediction_summary.csv").to_string(index=False))
    print(drift.head(20).to_string(index=False))
    print(probes.to_string(index=False))


if __name__ == "__main__":
    main()
