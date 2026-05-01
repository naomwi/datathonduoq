from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_cleanroom_rawmd_pipeline import build_clean_anchor
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission
from train_recursive_forecast import TRAIN_END, ensure_inputs, get_candidate_feature_sets


RUN_PREFIX = "strict_legal_trainvalidated_pipeline"
VALIDATION_YEARS = range(2018, 2023)


@dataclass(frozen=True)
class TargetParams:
    target: str
    share_mode: str
    total_method: str
    alpha_h1: float
    alpha_h2: float
    level_gamma: float


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def add_time_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out["year"] = out["Date"].dt.year
    out["month"] = out["Date"].dt.month
    out["half"] = np.where(out["month"].le(6), "H1", "H2")
    out["period"] = out["year"].astype(str) + out["half"]
    out["month_day"] = out["Date"].dt.strftime("%m-%d")
    return out


def final_period(frame: pd.DataFrame) -> pd.DataFrame:
    out = add_time_columns(frame)
    out.loc[out["Date"].eq(pd.Timestamp("2024-07-01")), "period"] = "2024-07-01"
    return out


def period_dates(year: int, half: str) -> pd.DatetimeIndex:
    if half == "H1":
        return pd.date_range(f"{year}-01-01", f"{year}-06-30", freq="D")
    return pd.date_range(f"{year}-07-01", f"{year}-12-31", freq="D")


def period_total(history: pd.DataFrame, target: str, year: int, half: str, method: str) -> float:
    hist = add_time_columns(history)
    same_half = (
        hist.loc[hist["half"].eq(half) & hist["year"].lt(year)]
        .groupby("year", as_index=False)
        .agg(total=(target, "sum"))
        .sort_values("year")
    )
    same_half = same_half.loc[same_half["total"].gt(0)]
    if same_half.empty:
        return float(hist[target].dropna().tail(365).mean() * len(period_dates(year, half)))

    if method == "recent2":
        return float(same_half.tail(2)["total"].mean())
    if method == "recent3":
        return float(same_half.tail(3)["total"].mean())
    if method == "ewm":
        recent = same_half.tail(5).copy()
        w = np.exp((recent["year"].to_numpy() - recent["year"].max()) / 2.0)
        return float(np.average(recent["total"].to_numpy(), weights=w))
    if method == "trend_log":
        recent = same_half.tail(6).copy()
        x = recent["year"].to_numpy(dtype=float)
        y = np.log(recent["total"].to_numpy(dtype=float).clip(min=1.0))
        w = np.exp((x - x.max()) / 2.0)
        xm = np.average(x, weights=w)
        ym = np.average(y, weights=w)
        denom = np.sum(w * (x - xm) ** 2)
        slope = 0.0 if denom <= 0 else float(np.sum(w * (x - xm) * (y - ym)) / denom)
        intercept = ym - slope * xm
        pred = float(np.exp(intercept + slope * year))
        recent3 = float(same_half.tail(3)["total"].mean())
        return float(np.clip(pred, 0.65 * recent3, 1.45 * recent3))
    raise ValueError(f"Unknown total_method: {method}")


def build_shape_share(history: pd.DataFrame, dates: pd.DatetimeIndex, target: str, mode: str) -> pd.Series:
    hist = add_time_columns(history.loc[history[target].notna()].copy())
    future = add_time_columns(pd.DataFrame({"Date": dates}))
    max_year = int(hist["year"].max())
    if mode == "base_recent2":
        hist = hist.loc[hist["year"].ge(max_year - 1)]
        reducer = "mean"
    elif mode == "recent3":
        hist = hist.loc[hist["year"].ge(max_year - 2)]
        reducer = "mean"
    elif mode == "median":
        reducer = "median"
    else:
        reducer = "mean"

    rows = []
    for (_, half), group in hist.groupby(["year", "half"]):
        total = group[target].sum()
        if total <= 0:
            continue
        tmp = group[["month_day", "month", "half"]].copy()
        tmp["share"] = group[target].to_numpy() / total
        rows.append(tmp)
    shares = pd.concat(rows, ignore_index=True)

    md = shares.groupby(["half", "month_day"], as_index=False).agg(md_share=("share", reducer))
    month = shares.groupby(["half", "month"], as_index=False).agg(month_share=("share", reducer))

    out = pd.Series(index=future.index, dtype=float)
    for _, group in future.groupby("period"):
        idx = list(group.index)
        half = str(group["half"].iloc[0])
        tmp = group[["half", "month_day", "month"]].merge(md, how="left", on=["half", "month_day"])
        tmp = tmp.merge(month, how="left", on=["half", "month"])
        global_daily = 1.0 / len(group)
        md_values = tmp["md_share"].fillna(tmp["month_share"]).fillna(global_daily)
        month_values = tmp["month_share"].fillna(global_daily)
        if mode == "month_shrink":
            values = 0.35 * md_values + 0.65 * month_values
        else:
            values = md_values
        values = pd.Series(values.to_numpy(), index=idx).clip(lower=1e-9)
        values = values / values.sum()
        out.loc[idx] = values
    return out


def forecast_one_period(
    history: pd.DataFrame,
    year: int,
    half: str,
    params: TargetParams,
) -> pd.Series:
    dates = period_dates(year, half)
    base_total = period_total(history, params.target, year, half, "recent2")
    model_total = period_total(history, params.target, year, half, params.total_method)
    total = (1.0 - params.level_gamma) * base_total + params.level_gamma * model_total

    base_share = build_shape_share(history, dates, params.target, "base_recent2")
    donor_share = build_shape_share(history, dates, params.target, params.share_mode)
    alpha = params.alpha_h1 if half == "H1" else params.alpha_h2
    share = (1.0 - alpha) * base_share + alpha * donor_share
    share = share / share.sum()
    return pd.Series(share.to_numpy() * total, index=dates)


def evaluate_params(sales: pd.DataFrame, params: TargetParams) -> dict[str, float]:
    rows = []
    for year in VALIDATION_YEARS:
        for half in ("H1", "H2"):
            dates = period_dates(year, half)
            history = sales.loc[sales["Date"].lt(dates.min())].copy()
            actual = sales.loc[sales["Date"].isin(dates), ["Date", params.target]].set_index("Date")[params.target]
            if len(history) < 365 * 3 or actual.empty:
                continue
            pred = forecast_one_period(history, year, half, params)
            aligned = actual.reindex(pred.index)
            err = (pred - aligned).abs()
            rows.append(
                {
                    "year": year,
                    "half": half,
                    "mae": float(err.mean()),
                    "wape": float(err.sum() / aligned.abs().sum()),
                    "bias": float((pred - aligned).mean()),
                }
            )
    metrics = pd.DataFrame(rows)
    return {
        "avg_mae": float(metrics["mae"].mean()),
        "worst_mae": float(metrics["mae"].max()),
        "avg_wape": float(metrics["wape"].mean()),
        "worst_wape": float(metrics["wape"].max()),
        "mean_bias": float(metrics["bias"].mean()),
    }


def tune_target(sales: pd.DataFrame, target: str) -> tuple[TargetParams, pd.DataFrame]:
    # Keep this grid intentionally compact. The goal is a defensible train-only
    # calibration, not an exhaustive public-score optimizer.
    share_modes = ["recent3", "month_shrink"]
    total_methods = ["recent2", "ewm", "trend_log"]
    alpha_h1_grid = [0.0, 0.50, 1.0]
    alpha_h2_grid = [0.0, 0.25, 0.50]
    gamma_grid = [0.0, 0.50, 1.0]

    rows = []
    for share_mode in share_modes:
        for total_method in total_methods:
            for alpha_h1 in alpha_h1_grid:
                for alpha_h2 in alpha_h2_grid:
                    for gamma in gamma_grid:
                        params = TargetParams(target, share_mode, total_method, alpha_h1, alpha_h2, gamma)
                        metrics = evaluate_params(sales, params)
                        rows.append({**params.__dict__, **metrics})
    table = pd.DataFrame(rows).sort_values(["avg_mae", "worst_mae"]).reset_index(drop=True)
    best = table.iloc[0]
    params = TargetParams(
        target=target,
        share_mode=str(best["share_mode"]),
        total_method=str(best["total_method"]),
        alpha_h1=float(best["alpha_h1"]),
        alpha_h2=float(best["alpha_h2"]),
        level_gamma=float(best["level_gamma"]),
    )
    return params, table


def apply_target_params(anchor: pd.DataFrame, sales: pd.DataFrame, params: TargetParams) -> pd.Series:
    future = final_period(anchor)
    out = pd.Series(index=future.index, dtype=float)
    for period, group in future.groupby("period"):
        idx = list(group.index)
        if period == "2024-07-01":
            out.loc[idx] = anchor.loc[idx, params.target].to_numpy()
            continue
        year = int(group["year"].iloc[0])
        half = str(group["half"].iloc[0])
        anchor_total = float(anchor.loc[idx, params.target].sum())
        model_total = period_total(sales, params.target, year, half, params.total_method)
        total = (1.0 - params.level_gamma) * anchor_total + params.level_gamma * model_total
        anchor_share = anchor.loc[idx, params.target].to_numpy() / max(anchor_total, 1e-9)
        donor_share = build_shape_share(sales, pd.DatetimeIndex(group["Date"]), params.target, params.share_mode)
        alpha = params.alpha_h1 if half == "H1" else params.alpha_h2
        share = (1.0 - alpha) * anchor_share + alpha * donor_share.to_numpy()
        share = np.clip(share, 1e-9, None)
        share = share / share.sum()
        out.loc[idx] = share * total
    return out


def make_candidate(anchor: pd.DataFrame, sales: pd.DataFrame, rev_params: TargetParams, cogs_params: TargetParams) -> pd.DataFrame:
    out = final_period(anchor)[["Date", "Revenue", "COGS", "period"]].copy()
    out["Revenue"] = apply_target_params(anchor, sales, rev_params).to_numpy()
    out["COGS"] = apply_target_params(anchor, sales, cogs_params).to_numpy()
    return out


def period_summary(frame: pd.DataFrame) -> pd.DataFrame:
    prof = final_period(frame)
    return (
        prof.groupby("period", as_index=False)
        .agg(days=("Date", "count"), revenue=("Revenue", "sum"), cogs=("COGS", "sum"))
        .assign(cogs_ratio=lambda d: d["cogs"] / d["revenue"])
    )


def write_report(
    run_dir: Path,
    rev_params: TargetParams,
    cogs_params: TargetParams,
    rev_table: pd.DataFrame,
    cogs_table: pd.DataFrame,
    manifest: pd.DataFrame,
) -> None:
    report = f"""# Strict Legal Train-Validated Pipeline

Run directory: `{run_dir}`

## Audit Boundary

This branch is intended for clean explanation. It does **not** use public leaderboard scores, `sample_submission.csv`, `sales_test` target values, or previous `submission_*.csv` files as inputs.

Signals used:

- CatBoost anchor rebuilt from provided raw/feature tables;
- historical `sales.csv` through `2022-12-31`;
- train-only rolling validation on `2018-2022`;
- known future calendar dates only.

## Selected Revenue Params

{pd.DataFrame([rev_params.__dict__]).to_markdown(index=False)}

Top revenue validation rows:

{rev_table.head(10).to_markdown(index=False)}

## Selected COGS Params

{pd.DataFrame([cogs_params.__dict__]).to_markdown(index=False)}

Top COGS validation rows:

{cogs_table.head(10).to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Recommendation

Submit `submission_strictlegal_tv_selected.csv` only if the priority is defensibility. It may score worse than public-calibrated files, but its parameters have a clean provenance story.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "strict_legal_trainvalidated_pipeline_2026-04-23.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    sales = add_time_columns(pd.read_csv(DATASET_DIR / "sales.csv", parse_dates=["Date"]))
    sales = sales.loc[sales["Date"].le(TRAIN_END)].copy()

    rev_params, rev_table = tune_target(sales, "Revenue")
    cogs_params, cogs_table = tune_target(sales, "COGS")
    rev_table.head(50).to_csv(run_dir / "revenue_validation_top50.csv", index=False)
    cogs_table.head(50).to_csv(run_dir / "cogs_validation_top50.csv", index=False)

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    anchor = build_clean_anchor(feature_store, base, feature_sets)

    candidates = [
        (
            "strictlegal_tv_selected",
            rev_params,
            cogs_params,
            "Fully train-validated shape and period-level model.",
        ),
        (
            "strictlegal_tv_shapeonly",
            replace(rev_params, level_gamma=0.0),
            replace(cogs_params, level_gamma=0.0),
            "Same selected shape parameters, no period-level total correction.",
        ),
        (
            "strictlegal_tv_levelonly",
            replace(rev_params, alpha_h1=0.0, alpha_h2=0.0),
            replace(cogs_params, alpha_h1=0.0, alpha_h2=0.0),
            "Only train-validated period-level correction; keep anchor daily shape.",
        ),
        (
            "strictlegal_tv_conservative",
            replace(
                rev_params,
                alpha_h1=0.5 * rev_params.alpha_h1,
                alpha_h2=0.5 * rev_params.alpha_h2,
                level_gamma=0.5 * rev_params.level_gamma,
            ),
            replace(
                cogs_params,
                alpha_h1=0.5 * cogs_params.alpha_h1,
                alpha_h2=0.5 * cogs_params.alpha_h2,
                level_gamma=0.5 * cogs_params.level_gamma,
            ),
            "Half-strength version for lower variance.",
        ),
    ]

    rows = []
    for priority, (name, rp, cp, note) in enumerate(candidates, start=1):
        frame = make_candidate(anchor, sales, rp, cp)
        path = DATASET_DIR / f"submission_{name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)
        prof = period_summary(frame)
        prof.to_csv(run_dir / f"{name}_period_summary.csv", index=False)
        rows.append(
            {
                "priority": priority,
                "filename": path.name,
                "note": note,
                "rev_share_mode": rp.share_mode,
                "rev_total_method": rp.total_method,
                "rev_alpha_h1": rp.alpha_h1,
                "rev_alpha_h2": rp.alpha_h2,
                "rev_level_gamma": rp.level_gamma,
                "cogs_share_mode": cp.share_mode,
                "cogs_total_method": cp.total_method,
                "cogs_alpha_h1": cp.alpha_h1,
                "cogs_alpha_h2": cp.alpha_h2,
                "cogs_level_gamma": cp.level_gamma,
                "revenue_total": frame["Revenue"].sum(),
                "cogs_total": frame["COGS"].sum(),
                "ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
                "ratio_2023H1": prof.loc[prof["period"].eq("2023H1"), "cogs_ratio"].iloc[0],
                "ratio_2023H2": prof.loc[prof["period"].eq("2023H2"), "cogs_ratio"].iloc[0],
                "ratio_2024H1": prof.loc[prof["period"].eq("2024H1"), "cogs_ratio"].iloc[0],
            }
        )

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(anchor).to_csv(run_dir / "clean_anchor_period_summary.csv", index=False)
    write_report(run_dir, rev_params, cogs_params, rev_table, cogs_table, manifest)
    print(run_dir)


if __name__ == "__main__":
    main()
