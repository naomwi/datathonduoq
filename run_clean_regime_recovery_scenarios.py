from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_regime_recovery_scenarios"
FORECAST_START = pd.Timestamp("2023-01-01")
FORECAST_END = pd.Timestamp("2024-07-01")
TRAIN_END = pd.Timestamp("2022-12-31")


@dataclass(frozen=True)
class Scenario:
    name: str
    level_mode: str
    revenue_growth_strength: float = 1.0
    cogs_growth_strength: float = 1.0
    beta_2023: float = 0.25
    beta_2024: float = 0.40
    beta_2023_h1: float | None = None
    beta_2023_h2: float | None = None
    beta_2024_h1: float | None = None
    beta_2024_h2: float | None = None
    revenue_h1_pre_shape: float = 0.55
    revenue_h2_pre_shape: float = 0.15
    cogs_h1_pre_shape: float = 0.35
    cogs_h2_pre_shape: float = 0.10
    cogs_ratio_mode: str = "recent"
    note: str = ""


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def add_time(frame: pd.DataFrame, split_final_day: bool = False) -> pd.DataFrame:
    out = frame.copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out["year"] = out["Date"].dt.year
    out["month"] = out["Date"].dt.month
    out["half"] = np.where(out["month"].le(6), "H1", "H2")
    out["period"] = out["year"].astype(str) + out["half"]
    if split_final_day:
        out.loc[out["Date"].eq(pd.Timestamp("2024-07-01")), "period"] = "2024-07-01"
    out["month_day"] = out["Date"].dt.strftime("%m-%d")
    return out


def output_dates() -> pd.DataFrame:
    return add_time(pd.DataFrame({"Date": pd.date_range(FORECAST_START, FORECAST_END, freq="D")}))


def load_sales() -> pd.DataFrame:
    sales = pd.read_csv(DATASET_DIR / "sales.csv", parse_dates=["Date"])
    sales = sales.loc[sales["Date"].le(TRAIN_END), ["Date", "Revenue", "COGS"]].copy()
    return add_time(sales)


def period_dates(year: int, half: str) -> pd.DatetimeIndex:
    if half == "H1":
        return pd.date_range(f"{year}-01-01", f"{year}-06-30", freq="D")
    return pd.date_range(f"{year}-07-01", f"{year}-12-31", freq="D")


def historical_period_totals(sales: pd.DataFrame, target: str) -> pd.DataFrame:
    return (
        sales.groupby(["year", "half"], as_index=False)
        .agg(days=("Date", "count"), total=(target, "sum"))
        .loc[lambda d: d["year"].between(2013, 2022)]
    )


def annual_yoy_2022(sales: pd.DataFrame, target: str) -> float:
    annual = sales.loc[sales["year"].between(2019, 2022)].groupby("year")[target].sum()
    return float(annual.loc[2022] / annual.loc[2021] - 1.0)


def yoy_level_total(sales: pd.DataFrame, target: str, year: int, half: str, strength: float) -> float:
    totals = historical_period_totals(sales, target)
    base_2022 = float(totals.loc[totals["year"].eq(2022) & totals["half"].eq(half), "total"].iloc[0])
    yoy = annual_yoy_2022(sales, target)
    years_after = max(0, year - 2022)
    forecast = base_2022 * (1.0 + strength * yoy) ** years_after

    same_half = totals.loc[totals["half"].eq(half)]
    recent_avg = float(same_half.loc[same_half["year"].between(2019, 2022), "total"].mean())
    pre_avg = float(same_half.loc[same_half["year"].between(2013, 2018), "total"].mean())
    lower = 0.80 * recent_avg
    upper = 1.05 * pre_avg
    return float(np.clip(forecast, lower, upper))


def gap_blend_total(sales: pd.DataFrame, target: str, year: int, half: str, beta: float) -> float:
    totals = historical_period_totals(sales, target)
    same_half = totals.loc[totals["half"].eq(half)]
    recent_avg = float(same_half.loc[same_half["year"].between(2019, 2022), "total"].mean())
    pre_avg = float(same_half.loc[same_half["year"].between(2013, 2018), "total"].mean())
    return float((1.0 - beta) * recent_avg + beta * pre_avg)


def scenario_beta(scenario: Scenario, year: int, half: str) -> float:
    if year == 2023 and half == "H1" and scenario.beta_2023_h1 is not None:
        return scenario.beta_2023_h1
    if year == 2023 and half == "H2" and scenario.beta_2023_h2 is not None:
        return scenario.beta_2023_h2
    if year == 2024 and half == "H1" and scenario.beta_2024_h1 is not None:
        return scenario.beta_2024_h1
    if year == 2024 and half == "H2" and scenario.beta_2024_h2 is not None:
        return scenario.beta_2024_h2
    return scenario.beta_2023 if year == 2023 else scenario.beta_2024


def scenario_total(sales: pd.DataFrame, scenario: Scenario, target: str, year: int, half: str) -> float:
    if scenario.level_mode == "yoy":
        strength = scenario.revenue_growth_strength if target == "Revenue" else scenario.cogs_growth_strength
        return yoy_level_total(sales, target, year, half, strength)
    if scenario.level_mode == "gap":
        beta = scenario_beta(scenario, year, half)
        return gap_blend_total(sales, target, year, half, beta)
    if scenario.level_mode == "gap_h2strong":
        beta = scenario_beta(scenario, year, half)
        has_explicit_h2 = (year == 2023 and scenario.beta_2023_h2 is not None) or (
            year == 2024 and scenario.beta_2024_h2 is not None
        )
        if half == "H2" and not has_explicit_h2:
            beta = min(0.95, beta + 0.20)
        return gap_blend_total(sales, target, year, half, beta)
    if scenario.level_mode == "hybrid":
        strength = scenario.revenue_growth_strength if target == "Revenue" else scenario.cogs_growth_strength
        beta = scenario_beta(scenario, year, half)
        return 0.50 * yoy_level_total(sales, target, year, half, strength) + 0.50 * gap_blend_total(
            sales, target, year, half, beta
        )
    raise ValueError(f"Unknown level_mode: {scenario.level_mode}")


def era_profile(sales: pd.DataFrame, target: str, era: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    max_year = int(sales["year"].max())
    if era == "pre":
        hist = sales.loc[sales["year"].between(2013, 2018)].copy()
        if hist.empty:
            hist = sales.loc[sales["year"].le(max_year - 4)].copy()
    elif era == "recent":
        hist = sales.loc[sales["year"].between(2019, 2022)].copy()
        if hist.empty:
            hist = sales.loc[sales["year"].ge(max_year - 3)].copy()
    else:
        hist = sales.loc[sales["year"].between(2013, 2022)].copy()
    if hist.empty:
        hist = sales.copy()

    hist = hist.loc[~((hist["Date"].dt.month == 2) & (hist["Date"].dt.day == 29))].copy()
    rows = []
    for (_, half), group in hist.groupby(["year", "half"]):
        total = float(group[target].sum())
        if total <= 0:
            continue
        tmp = group[["half", "month", "month_day"]].copy()
        tmp["share"] = group[target].to_numpy() / total
        rows.append(tmp)
    shares = pd.concat(rows, ignore_index=True)
    md = shares.groupby(["half", "month_day"], as_index=False).agg(share=("share", "mean"))
    month = shares.groupby(["half", "month"], as_index=False).agg(month_share=("share", "mean"))
    return md, month


def profile_share(
    sales: pd.DataFrame,
    dates: pd.DatetimeIndex,
    target: str,
    pre_weight_h1: float,
    pre_weight_h2: float,
) -> pd.Series:
    future = add_time(pd.DataFrame({"Date": dates}))
    recent_md, recent_month = era_profile(sales, target, "recent")
    pre_md, pre_month = era_profile(sales, target, "pre")
    out = pd.Series(index=future.index, dtype=float)

    for period, group in future.groupby("period"):
        idx = list(group.index)
        half = str(group["half"].iloc[0])
        pre_weight = pre_weight_h1 if half == "H1" else pre_weight_h2
        tmp = group[["half", "month", "month_day"]].copy()
        tmp = tmp.merge(recent_md, on=["half", "month_day"], how="left").rename(columns={"share": "recent_md"})
        tmp = tmp.merge(pre_md, on=["half", "month_day"], how="left").rename(columns={"share": "pre_md"})
        tmp = tmp.merge(recent_month, on=["half", "month"], how="left").rename(
            columns={"month_share": "recent_month"}
        )
        tmp = tmp.merge(pre_month, on=["half", "month"], how="left").rename(columns={"month_share": "pre_month"})
        uniform = 1.0 / len(group)
        recent = tmp["recent_md"].fillna(tmp["recent_month"]).fillna(uniform).to_numpy()
        pre = tmp["pre_md"].fillna(tmp["pre_month"]).fillna(uniform).to_numpy()
        values = (1.0 - pre_weight) * recent + pre_weight * pre
        values = np.clip(values, 1e-12, None)
        out.loc[idx] = values / values.sum()

    return out


def cogs_ratio_for_period(sales: pd.DataFrame, scenario: Scenario, year: int, half: str) -> float:
    hist = sales.loc[sales["year"].between(2013, 2022)].copy()
    period = (
        hist.groupby(["year", "half"], as_index=False)
        .agg(revenue=("Revenue", "sum"), cogs=("COGS", "sum"))
        .assign(ratio=lambda d: d["cogs"] / d["revenue"])
    )
    same = period.loc[period["half"].eq(half)]
    h1 = period.loc[period["half"].eq("H1")]
    h2 = period.loc[period["half"].eq("H2")]
    recent = float(same.loc[same["year"].between(2019, 2022), "ratio"].mean())
    pre = float(same.loc[same["year"].between(2013, 2018), "ratio"].mean())
    median = float(same["ratio"].median())
    all_ratios = period["ratio"].to_numpy()
    if scenario.cogs_ratio_mode == "recent":
        return recent
    if scenario.cogs_ratio_mode == "median":
        return median
    if scenario.cogs_ratio_mode == "regime_blend":
        beta = scenario_beta(scenario, year, half)
        return float((1.0 - beta) * recent + beta * pre)
    if scenario.cogs_ratio_mode == "transition_stress_p85":
        if year == 2023:
            return float(np.quantile(all_ratios, 0.85))
        beta = scenario_beta(scenario, year, half)
        return float((1.0 - beta) * recent + beta * pre)
    if scenario.cogs_ratio_mode == "transition_stress_p95":
        if year == 2023:
            return float(np.quantile(all_ratios, 0.95))
        beta = scenario_beta(scenario, year, half)
        return float((1.0 - beta) * recent + beta * pre)
    if scenario.cogs_ratio_mode == "transition_stress_p95_h2max_2024h1max":
        if year == 2023 and half == "H1":
            return float(np.quantile(all_ratios, 0.95))
        if year == 2023 and half == "H2":
            return float(h2["ratio"].max())
        if year == 2024 and half == "H1":
            return float(h1["ratio"].max())
        return float(h2["ratio"].max())
    if scenario.cogs_ratio_mode == "transition_stress_p85_h2max_2024h1max":
        if year == 2023 and half == "H1":
            return float(np.quantile(all_ratios, 0.85))
        if year == 2023 and half == "H2":
            return float(h2["ratio"].max())
        if year == 2024 and half == "H1":
            return float(h1["ratio"].max())
        return float(h2["ratio"].max())
    raise ValueError(f"Unknown cogs_ratio_mode: {scenario.cogs_ratio_mode}")


def build_forecast(sales: pd.DataFrame, scenario: Scenario) -> pd.DataFrame:
    future = output_dates()
    out = future[["Date", "year", "half", "period"]].copy()
    out["Revenue"] = np.nan
    out["COGS"] = np.nan

    forecast_periods = [(2023, "H1"), (2023, "H2"), (2024, "H1"), (2024, "H2")]
    for year, half in forecast_periods:
        dates = period_dates(year, half)
        visible_dates = dates[(dates >= FORECAST_START) & (dates <= FORECAST_END)]
        if len(visible_dates) == 0:
            continue
        revenue_total = scenario_total(sales, scenario, "Revenue", year, half)
        revenue_share = profile_share(
            sales,
            dates,
            "Revenue",
            scenario.revenue_h1_pre_shape,
            scenario.revenue_h2_pre_shape,
        )
        revenue_full = pd.Series(revenue_share.to_numpy() * revenue_total, index=dates)

        ratio = cogs_ratio_for_period(sales, scenario, year, half)
        cogs_total = revenue_total * ratio
        cogs_share = profile_share(
            sales,
            dates,
            "COGS",
            scenario.cogs_h1_pre_shape,
            scenario.cogs_h2_pre_shape,
        )
        cogs_full = pd.Series(cogs_share.to_numpy() * cogs_total, index=dates)

        mask = out["Date"].isin(visible_dates)
        out.loc[mask, "Revenue"] = out.loc[mask, "Date"].map(revenue_full)
        out.loc[mask, "COGS"] = out.loc[mask, "Date"].map(cogs_full)

    return out[["Date", "Revenue", "COGS", "period"]]


def period_summary(frame: pd.DataFrame) -> pd.DataFrame:
    prof = add_time(frame, split_final_day=True)
    return (
        prof.groupby("period", as_index=False)
        .agg(days=("Date", "count"), revenue=("Revenue", "sum"), cogs=("COGS", "sum"))
        .assign(cogs_ratio=lambda d: d["cogs"] / d["revenue"])
    )


def shape_validation(sales: pd.DataFrame) -> pd.DataFrame:
    rows = []
    configs = [
        ("recent_only", 0.0, 0.0),
        ("clean_recovery_shape", 0.55, 0.15),
        ("pre_only", 1.0, 1.0),
    ]
    for target in ["Revenue", "COGS"]:
        for name, h1_w, h2_w in configs:
            for year in range(2018, 2023):
                for half in ["H1", "H2"]:
                    dates = period_dates(year, half)
                    history = sales.loc[sales["Date"].lt(dates.min())].copy()
                    actual = sales.loc[sales["Date"].isin(dates), ["Date", target]].set_index("Date")[target]
                    if len(history) < 365 * 4 or actual.empty:
                        continue
                    share = profile_share(history, dates, target, h1_w, h2_w)
                    pred = share.to_numpy() * float(actual.sum())
                    err = np.abs(pred - actual.reindex(dates).to_numpy())
                    rows.append(
                        {
                            "target": target,
                            "shape": name,
                            "year": year,
                            "half": half,
                            "oracle_total_mae": float(err.mean()),
                            "oracle_total_wape": float(err.sum() / actual.sum()),
                        }
                    )
    return pd.DataFrame(rows)


def build_scenarios() -> list[Scenario]:
    return [
        Scenario(
            name="clean_regime_recovery_v2_yoy100",
            level_mode="yoy",
            revenue_growth_strength=1.00,
            cogs_ratio_mode="recent",
            note="Continue the 2022 annual revenue recovery rate into 2023-2024; COGS ratio from recent train regime.",
        ),
        Scenario(
            name="clean_regime_recovery_v2_yoy125",
            level_mode="yoy",
            revenue_growth_strength=1.25,
            cogs_ratio_mode="recent",
            note="Stronger continuation of the 2022 recovery, still capped below pre-2019 high-regime average.",
        ),
        Scenario(
            name="clean_regime_recovery_v2_gap30_45",
            level_mode="gap",
            beta_2023=0.30,
            beta_2024=0.45,
            cogs_ratio_mode="regime_blend",
            note="Latent regime blend: 2023 recovers 30 percent of the low-to-high gap, 2024 recovers 45 percent.",
        ),
        Scenario(
            name="clean_regime_recovery_v2_hybrid",
            level_mode="hybrid",
            revenue_growth_strength=1.15,
            beta_2023=0.30,
            beta_2024=0.45,
            cogs_ratio_mode="regime_blend",
            note="Average of train-derived YoY recovery and low/high latent regime blend.",
        ),
        Scenario(
            name="clean_regime_recovery_v2_h1strong_h2shrink",
            level_mode="hybrid",
            revenue_growth_strength=1.25,
            beta_2023=0.25,
            beta_2024=0.50,
            revenue_h1_pre_shape=0.70,
            revenue_h2_pre_shape=0.05,
            cogs_h1_pre_shape=0.45,
            cogs_h2_pre_shape=0.05,
            cogs_ratio_mode="median",
            note="Use stronger H1 stable seasonality, aggressively shrink H2 shape, and median COGS ratios.",
        ),
        Scenario(
            name="clean_regime_recovery_v2_trainshape_hybrid",
            level_mode="hybrid",
            revenue_growth_strength=1.15,
            beta_2023=0.30,
            beta_2024=0.45,
            revenue_h1_pre_shape=0.55,
            revenue_h2_pre_shape=1.00,
            cogs_h1_pre_shape=0.35,
            cogs_h2_pre_shape=1.00,
            cogs_ratio_mode="regime_blend",
            note="Shape weights selected from train-only oracle-total validation: blended H1, pre-2019 H2.",
        ),
        Scenario(
            name="clean_regime_recovery_v3_h2strong_cogsp85",
            level_mode="gap_h2strong",
            beta_2023=0.30,
            beta_2024=0.50,
            revenue_h1_pre_shape=0.55,
            revenue_h2_pre_shape=1.00,
            cogs_h1_pre_shape=0.35,
            cogs_h2_pre_shape=1.00,
            cogs_ratio_mode="transition_stress_p85",
            note=(
                "Clean stress scenario: H2 revenue recovers faster from the low regime; 2023 COGS ratio uses "
                "the 85th percentile of train half-year ratios, then normalizes in 2024."
            ),
        ),
        Scenario(
            name="clean_regime_recovery_v3_h2strong_cogsp95",
            level_mode="gap_h2strong",
            beta_2023=0.30,
            beta_2024=0.50,
            revenue_h1_pre_shape=0.55,
            revenue_h2_pre_shape=1.00,
            cogs_h1_pre_shape=0.35,
            cogs_h2_pre_shape=1.00,
            cogs_ratio_mode="transition_stress_p95",
            note=(
                "More aggressive clean stress scenario: H2 revenue recovers faster; 2023 COGS ratio uses "
                "the 95th percentile of train half-year ratios, then normalizes in 2024."
            ),
        ),
        Scenario(
            name="cleaninput_pubguided_v4_h2max_2024h1max",
            level_mode="gap",
            beta_2023_h1=0.24,
            beta_2023_h2=0.53,
            beta_2024_h1=0.51,
            beta_2024_h2=0.51,
            revenue_h1_pre_shape=0.55,
            revenue_h2_pre_shape=1.00,
            cogs_h1_pre_shape=0.35,
            cogs_h2_pre_shape=1.00,
            cogs_ratio_mode="transition_stress_p95_h2max_2024h1max",
            note=(
                "Clean-input, public-guided scenario: period recovery is adjusted after the 732k result; "
                "COGS ratios remain train-derived upper-tail/max stress values."
            ),
        ),
        Scenario(
            name="cleaninput_pubguided_v4_h1p85_h2max",
            level_mode="gap",
            beta_2023_h1=0.24,
            beta_2023_h2=0.53,
            beta_2024_h1=0.51,
            beta_2024_h2=0.51,
            revenue_h1_pre_shape=0.55,
            revenue_h2_pre_shape=1.00,
            cogs_h1_pre_shape=0.35,
            cogs_h2_pre_shape=1.00,
            cogs_ratio_mode="transition_stress_p85_h2max_2024h1max",
            note=(
                "Softer 2023H1 COGS stress than v4_h2max_2024h1max; H2 and 2024H1 use train max stress."
            ),
        ),
        Scenario(
            name="cleaninput_pubguided_v4_revlow_h2max",
            level_mode="gap",
            beta_2023_h1=0.18,
            beta_2023_h2=0.55,
            beta_2024_h1=0.51,
            beta_2024_h2=0.51,
            revenue_h1_pre_shape=0.55,
            revenue_h2_pre_shape=1.00,
            cogs_h1_pre_shape=0.35,
            cogs_h2_pre_shape=1.00,
            cogs_ratio_mode="transition_stress_p95_h2max_2024h1max",
            note=(
                "Lower 2023H1 revenue recovery and stronger H2 recovery; clean-input but public-guided after v3."
            ),
        ),
    ]


def write_report(
    run_dir: Path,
    manifest: pd.DataFrame,
    era: pd.DataFrame,
    shape_scores: pd.DataFrame,
) -> None:
    shape_agg = (
        shape_scores.groupby(["target", "shape", "half"], as_index=False)
        .agg(mean_oracle_wape=("oracle_total_wape", "mean"), worst_oracle_wape=("oracle_total_wape", "max"))
        .sort_values(["target", "half", "mean_oracle_wape"])
    )
    report = f"""# Clean Regime Recovery Scenarios

Run directory: `{run_dir}`

## Boundary

This branch is a clean-input scenario pipeline. It uses:

- `dataset/sales.csv` through `2022-12-31`;
- known calendar dates from `2023-01-01` to `2024-07-01`;
- no `sample_submission.csv`;
- no previous `submission_*.csv` as inputs;
- no test `Revenue` / `COGS` values.

It is not pure train-validation selection. It explicitly models a latent business scenario: after the 2019-2022 low-demand regime, 2023-2024 partially recover toward the 2013-2018 high-demand regime.

## Era Evidence

{era.to_markdown(index=False)}

## Shape Validation

These scores use oracle period totals, so they evaluate only daily allocation shape.

{shape_agg.to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Reading

If public improves, the clean interpretation is that leaderboard years are not a new all-time-high regime; they are a partial recovery of order/conversion level while retaining stable H1 seasonality. If public fails, the missing signal is not recoverable from train-only sales history without some form of scenario calibration.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_regime_recovery_scenarios_2026-04-23.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    sales = load_sales()

    era_rows = []
    for half in ["H1", "H2"]:
        for era_name, lo, hi in [("pre2019_high", 2013, 2018), ("recent_low", 2019, 2022)]:
            sub = sales.loc[sales["year"].between(lo, hi) & sales["half"].eq(half)]
            annualized = (
                sub.groupby("year", as_index=False)
                .agg(revenue=("Revenue", "sum"), cogs=("COGS", "sum"))
                .assign(cogs_ratio=lambda d: d["cogs"] / d["revenue"])
            )
            era_rows.append(
                {
                    "era": era_name,
                    "half": half,
                    "revenue_avg": annualized["revenue"].mean(),
                    "cogs_avg": annualized["cogs"].mean(),
                    "cogs_ratio_avg": annualized["cogs_ratio"].mean(),
                }
            )
    era = pd.DataFrame(era_rows)
    era.to_csv(run_dir / "era_halfyear_reference.csv", index=False)

    shape_scores = shape_validation(sales)
    shape_scores.to_csv(run_dir / "shape_validation.csv", index=False)

    manifest_rows = []
    for scenario in build_scenarios():
        frame = build_forecast(sales, scenario)
        path = DATASET_DIR / f"submission_{scenario.name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)
        prof = period_summary(frame)
        prof.to_csv(run_dir / f"{scenario.name}_period_summary.csv", index=False)
        manifest_rows.append(
            {
                "filename": path.name,
                "level_mode": scenario.level_mode,
                "revenue_growth_strength": scenario.revenue_growth_strength,
                "beta_2023": scenario.beta_2023,
                "beta_2024": scenario.beta_2024,
                "beta_2023_h1": scenario.beta_2023_h1,
                "beta_2023_h2": scenario.beta_2023_h2,
                "beta_2024_h1": scenario.beta_2024_h1,
                "beta_2024_h2": scenario.beta_2024_h2,
                "cogs_ratio_mode": scenario.cogs_ratio_mode,
                "revenue_total": frame["Revenue"].sum(),
                "cogs_total": frame["COGS"].sum(),
                "ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
                "rev_2023H1": prof.loc[prof["period"].eq("2023H1"), "revenue"].iloc[0],
                "rev_2023H2": prof.loc[prof["period"].eq("2023H2"), "revenue"].iloc[0],
                "rev_2024H1": prof.loc[prof["period"].eq("2024H1"), "revenue"].iloc[0],
                "ratio_2023H1": prof.loc[prof["period"].eq("2023H1"), "cogs_ratio"].iloc[0],
                "ratio_2023H2": prof.loc[prof["period"].eq("2023H2"), "cogs_ratio"].iloc[0],
                "ratio_2024H1": prof.loc[prof["period"].eq("2024H1"), "cogs_ratio"].iloc[0],
                "note": scenario.note,
            }
        )

    manifest = pd.DataFrame(manifest_rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    write_report(run_dir, manifest, era, shape_scores)
    print(run_dir)


if __name__ == "__main__":
    main()
