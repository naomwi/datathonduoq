from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_clean_regime_recovery_scenarios import load_sales
from run_clean_v10_h1_regime_shape import (
    add_period_columns,
    apply_h1_regime_shape,
    build_current_clean_frame,
    sanity_check,
)
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v11_trainselected_regime_shape"
VALID_YEARS = tuple(range(2018, 2023))


@dataclass(frozen=True)
class RegimeSpec:
    name: str
    revenue_mode: str
    ratio_mode: str
    alpha: float


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def r2_score(actual: np.ndarray, pred: np.ndarray) -> float:
    denom = float(np.sum((actual - actual.mean()) ** 2))
    if denom <= 0:
        return np.nan
    return float(1.0 - np.sum((actual - pred) ** 2) / denom)


def choose_history(history: pd.DataFrame, mode: str, target_year: int | None = None) -> pd.DataFrame:
    if history.empty:
        return history
    if mode == "all_median":
        return history
    if mode == "recent4":
        return history.sort_values("year").tail(4)
    if mode == "pre2019":
        out = history.loc[history["year"].le(2018)]
        return out if not out.empty else history
    if mode == "recovery_141617":
        out = history.loc[history["year"].isin([2014, 2016, 2017])]
        return out if not out.empty else history
    if mode == "low_q1":
        rows = []
        for year, group in history.groupby("year"):
            h1 = group.loc[group["month"].le(6)]
            q1_share = h1.loc[h1["month"].le(3), "Revenue"].sum() / h1["Revenue"].sum()
            rows.append((year, q1_share))
        years = [year for year, _ in sorted(rows, key=lambda item: item[1])[: max(2, min(4, len(rows)))]]
        return history.loc[history["year"].isin(years)]
    if mode == "ratio_low_mae_proxy":
        # Train-only proxy for low-ratio recovery years: select years whose
        # monthly H1 ratio is closest to the historical median profile.
        profiles = []
        for year, group in history.groupby("year"):
            h1 = group.loc[group["month"].le(6)]
            ratio = h1.groupby("month")["COGS"].sum() / h1.groupby("month")["Revenue"].sum()
            profiles.append((year, ratio))
        matrix = pd.concat([p.rename(year) for year, p in profiles], axis=1)
        median = matrix.median(axis=1)
        distances = ((matrix.sub(median, axis=0)).abs().mean()).sort_values()
        years = list(distances.head(max(2, min(4, len(distances)))).index)
        return history.loc[history["year"].isin(years)]
    raise ValueError(f"Unknown mode: {mode}")


def train_priors_for_year(sales: pd.DataFrame, target_year: int, revenue_mode: str, ratio_mode: str) -> tuple[pd.Series, pd.Series]:
    hist = add_period_columns(sales)
    history = hist.loc[hist["year"].lt(target_year) & hist["year"].ge(2013) & hist["half"].eq("H1")].copy()
    rev_history = choose_history(history, revenue_mode, target_year)
    ratio_history = choose_history(history, ratio_mode, target_year)

    rev_profiles = []
    for _, group in rev_history.groupby("year"):
        monthly = group.groupby("month")["Revenue"].sum().reindex(range(1, 7)).fillna(0.0)
        if monthly.sum() > 0:
            rev_profiles.append(monthly / monthly.sum())
    if not rev_profiles:
        raise ValueError(f"No revenue profiles for {target_year} {revenue_mode}")
    revenue_share = pd.concat(rev_profiles, axis=1).median(axis=1)
    revenue_share = revenue_share / revenue_share.sum()

    ratio_profiles = []
    for _, group in ratio_history.groupby("year"):
        monthly_rev = group.groupby("month")["Revenue"].sum().reindex(range(1, 7))
        monthly_cogs = group.groupby("month")["COGS"].sum().reindex(range(1, 7))
        ratio_profiles.append(monthly_cogs / monthly_rev.replace(0, np.nan))
    if not ratio_profiles:
        raise ValueError(f"No ratio profiles for {target_year} {ratio_mode}")
    cogs_ratio = pd.concat(ratio_profiles, axis=1).median(axis=1).ffill().bfill()
    return revenue_share.astype(float), cogs_ratio.astype(float)


def baseline_shape_for_year(sales: pd.DataFrame, target_year: int) -> pd.DataFrame:
    hist = add_period_columns(sales)
    target = hist.loc[hist["year"].eq(target_year) & hist["half"].eq("H1"), ["Date", "Revenue", "COGS"]].copy()
    history = hist.loc[hist["year"].lt(target_year) & hist["year"].ge(2013) & hist["half"].eq("H1")].copy()
    history["month_day"] = history["Date"].dt.strftime("%m-%d")
    target["month_day"] = target["Date"].dt.strftime("%m-%d")

    daily = (
        history.groupby("month_day")
        .agg(revenue_prior=("Revenue", "median"), cogs_prior=("COGS", "median"))
        .reset_index()
    )
    out = target[["Date", "month_day"]].merge(daily, on="month_day", how="left")
    for col in ["revenue_prior", "cogs_prior"]:
        out[col] = out[col].fillna(out[col].median())
    out["Revenue"] = out["revenue_prior"] / out["revenue_prior"].sum() * target["Revenue"].sum()
    out["COGS"] = out["cogs_prior"] / out["cogs_prior"].sum() * target["COGS"].sum()
    return out[["Date", "Revenue", "COGS"]]


def apply_train_regime_to_history(
    sales: pd.DataFrame,
    target_year: int,
    revenue_mode: str,
    ratio_mode: str,
    alpha: float,
) -> pd.DataFrame:
    base = baseline_shape_for_year(sales, target_year)
    revenue_share, cogs_ratio = train_priors_for_year(sales, target_year, revenue_mode, ratio_mode)
    work = add_period_columns(base)
    target = work.copy()
    total_revenue = target["Revenue"].sum()

    for month in range(1, 7):
        idx = target.index[target["month"].eq(month)]
        current = float(target.loc[idx, "Revenue"].sum())
        desired = total_revenue * float(revenue_share.loc[month])
        if current > 0:
            target.loc[idx, "Revenue"] *= desired / current
        target.loc[idx, "COGS"] = target.loc[idx, "Revenue"] * float(cogs_ratio.loc[month])

    work["Revenue"] = (1.0 - alpha) * work["Revenue"].to_numpy(dtype=float) + alpha * target["Revenue"].to_numpy(dtype=float)
    work["COGS"] = (1.0 - alpha) * work["COGS"].to_numpy(dtype=float) + alpha * target["COGS"].to_numpy(dtype=float)
    return work[["Date", "Revenue", "COGS"]]


def validate_specs(sales: pd.DataFrame, specs: list[RegimeSpec]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    fold_rows = []
    actual_full = add_period_columns(sales)
    actual_full = actual_full.loc[actual_full["year"].isin(VALID_YEARS) & actual_full["half"].eq("H1")]

    for spec in specs:
        preds = []
        actuals = []
        for year in VALID_YEARS:
            pred = apply_train_regime_to_history(sales, year, spec.revenue_mode, spec.ratio_mode, spec.alpha)
            actual = actual_full.loc[actual_full["year"].eq(year), ["Date", "Revenue", "COGS"]].copy()
            merged = actual.merge(pred, on="Date", suffixes=("_actual", "_pred"))
            y_true = merged[["Revenue_actual", "COGS_actual"]].to_numpy(dtype=float).ravel()
            y_pred = merged[["Revenue_pred", "COGS_pred"]].to_numpy(dtype=float).ravel()
            mae = float(np.mean(np.abs(y_true - y_pred)))
            rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
            r2 = r2_score(y_true, y_pred)
            fold_rows.append(
                {
                    "name": spec.name,
                    "year": year,
                    "revenue_mode": spec.revenue_mode,
                    "ratio_mode": spec.ratio_mode,
                    "alpha": spec.alpha,
                    "mae": mae,
                    "rmse": rmse,
                    "r2": r2,
                }
            )
            actuals.append(y_true)
            preds.append(y_pred)
        y_true_all = np.concatenate(actuals)
        y_pred_all = np.concatenate(preds)
        rows.append(
            {
                "name": spec.name,
                "revenue_mode": spec.revenue_mode,
                "ratio_mode": spec.ratio_mode,
                "alpha": spec.alpha,
                "mae": float(np.mean(np.abs(y_true_all - y_pred_all))),
                "rmse": float(np.sqrt(np.mean((y_true_all - y_pred_all) ** 2))),
                "r2": r2_score(y_true_all, y_pred_all),
            }
        )
    summary = pd.DataFrame(rows).sort_values(["mae", "rmse", "r2"], ascending=[True, True, False])
    folds = pd.DataFrame(fold_rows)
    return summary, folds


def build_specs() -> list[RegimeSpec]:
    revenue_modes = ["recent4", "all_median", "pre2019", "low_q1", "recovery_141617"]
    ratio_modes = ["recent4", "all_median", "pre2019", "ratio_low_mae_proxy", "recovery_141617"]
    alphas = [0.0, 0.25, 0.50, 0.75, 1.0]
    specs = []
    for revenue_mode in revenue_modes:
        for ratio_mode in ratio_modes:
            for alpha in alphas:
                specs.append(
                    RegimeSpec(
                        name=f"rev-{revenue_mode}__ratio-{ratio_mode}__a{int(alpha * 100):03d}",
                        revenue_mode=revenue_mode,
                        ratio_mode=ratio_mode,
                        alpha=alpha,
                    )
                )
    return specs


def apply_selected_to_forecast(
    base_frame: pd.DataFrame,
    sales: pd.DataFrame,
    spec: RegimeSpec,
) -> pd.DataFrame:
    revenue_share, cogs_ratio = train_priors_for_year(sales, 2023, spec.revenue_mode, spec.ratio_mode)
    candidate = type(
        "CandidateSpec",
        (),
        {
            "name": spec.name,
            "alpha": spec.alpha,
            "use_revenue_shape": True,
            "note": f"Train-selected {spec.name}",
        },
    )()
    return apply_h1_regime_shape(base_frame, revenue_share, cogs_ratio, candidate)


def write_report(run_dir: Path, summary: pd.DataFrame, folds: pd.DataFrame, selected: pd.DataFrame) -> None:
    report = f"""# Clean V11 Train-Selected Regime Shape

Run directory: `{run_dir}`

## Boundary

This run selects the H1 regime-shape calibration by rolling validation on train years only (`2018-2022` H1). It does not use public leaderboard scores, `sample_submission.csv`, prior submissions, quarantine files, or test targets to select parameters.

The generated submission still builds on the existing clean-input forecast base, but the post-processing choice is train-selected rather than leaderboard-selected.

## Selected Candidate

{selected.to_markdown(index=False)}

## Top Validation Rows

{summary.head(20).to_markdown(index=False)}

## Fold Metrics For Selected

{folds.loc[folds["name"].eq(selected["name"].iloc[0])].to_markdown(index=False)}

## Test Metrics Caveat

Only public leaderboard MAE is observable from Kaggle. Test RMSE and R2 cannot be known without hidden labels or an official leaderboard that reports those metrics.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v11_trainselected_regime_shape_2026-04-28.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    run_dir = make_run_dir()
    sales = load_sales()
    summary, folds = validate_specs(sales, build_specs())
    summary.to_csv(run_dir / "validation_summary.csv", index=False)
    folds.to_csv(run_dir / "validation_folds.csv", index=False)

    selected = summary.head(1).copy()
    selected_spec = RegimeSpec(
        name=str(selected["name"].iloc[0]),
        revenue_mode=str(selected["revenue_mode"].iloc[0]),
        ratio_mode=str(selected["ratio_mode"].iloc[0]),
        alpha=float(selected["alpha"].iloc[0]),
    )
    base_frame = build_current_clean_frame(run_dir)
    frame = apply_selected_to_forecast(base_frame, sales, selected_spec)
    sanity_check(frame, selected_spec.name)
    filename = f"submission_cleanv11_trainselected_{selected_spec.name.replace('-', '').replace('__', '_')}.csv"
    path = DATASET_DIR / filename
    write_submission(frame, path)
    selected["filename"] = filename
    selected.to_csv(run_dir / "selected_candidate.csv", index=False)
    write_report(run_dir, summary, folds, selected)

    print(run_dir)
    print(selected.to_string(index=False))
    print(summary.head(10).to_string(index=False))
