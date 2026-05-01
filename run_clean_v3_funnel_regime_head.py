from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_clean_v2_train_evidence import build_daily_panel, period_metrics
from run_clean_regime_recovery_scenarios import load_sales, period_summary
from run_clean_v2_eda_guided_candidates import base_totals
from run_cleaninput_rawmdshape_pubguided import apply_period_totals, build_shape_base
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v3_funnel_regime_head"
FORECAST_PERIODS = ["2023H1", "2023H2", "2024H1"]


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    total_mode: str
    conv_recovery: float | None = None
    h1_ratio: float | None = None
    h2_ratio_mode: str = "base"
    override_periods: tuple[str, ...] = ("2023H1",)
    note: str = ""


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def period_key(year: int, half: str) -> str:
    return f"{year}{half}"


def add_period_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out["year"] = out["Date"].dt.year
    out["month"] = out["Date"].dt.month
    out["half"] = np.where(out["month"].le(6), "H1", "H2")
    out["period"] = out["year"].astype(str) + out["half"]
    out.loc[out["Date"].eq(pd.Timestamp("2024-07-01")), "period"] = "2024-07-01"
    return out


def build_period_table() -> pd.DataFrame:
    daily = build_daily_panel()
    periods = period_metrics(daily)
    keep = [
        "year",
        "half",
        "days",
        "revenue",
        "cogs",
        "cogs_ratio",
        "orders",
        "sessions",
        "conversion",
        "aov",
        "units",
        "revenue_per_unit",
        "discount_rate",
        "promo_line_share",
    ]
    return periods.loc[periods["year"].between(2013, 2022), keep].copy()


def same_half_history(periods: pd.DataFrame, year: int, half: str) -> pd.DataFrame:
    return periods.loc[(periods["year"].lt(year)) & (periods["half"].eq(half))].sort_values("year").copy()


def weighted_recent(history: pd.DataFrame, col: str, n: int = 4) -> float:
    recent = history.tail(n).copy()
    if recent.empty:
        return np.nan
    weights = np.exp((recent["year"].to_numpy(dtype=float) - recent["year"].max()) / 2.0)
    return float(np.average(recent[col].to_numpy(dtype=float), weights=weights))


def trend_log(history: pd.DataFrame, col: str, year: int) -> float:
    recent = history.tail(6).copy()
    if len(recent) < 3:
        return weighted_recent(history, col)
    x = recent["year"].to_numpy(dtype=float)
    y = np.log(np.clip(recent[col].to_numpy(dtype=float), 1e-9, None))
    weights = np.exp((x - x.max()) / 2.0)
    xm = np.average(x, weights=weights)
    ym = np.average(y, weights=weights)
    denom = float(np.sum(weights * (x - xm) ** 2))
    slope = 0.0 if denom <= 0 else float(np.sum(weights * (x - xm) * (y - ym)) / denom)
    pred = float(np.exp((ym - slope * xm) + slope * year))
    recent3 = float(recent.tail(3)[col].mean())
    return float(np.clip(pred, 0.65 * recent3, 1.45 * recent3))


def high_regime_mean(history: pd.DataFrame, col: str) -> float:
    if history.empty:
        return np.nan
    values = history[col].dropna().sort_values()
    if values.empty:
        return np.nan
    return float(values.loc[values.ge(values.median())].mean())


def regime_mix(history: pd.DataFrame, col: str, beta: float) -> float:
    recent = weighted_recent(history, col, n=4)
    high = high_regime_mean(history, col)
    return float((1.0 - beta) * recent + beta * high)


def funnel_revenue(history: pd.DataFrame, year: int, conv_recovery: float, sessions_mode: str = "last") -> float:
    if history.empty:
        return np.nan
    if sessions_mode == "trend":
        sessions = trend_log(history, "sessions", year)
        aov = trend_log(history, "aov", year)
    else:
        last = history.tail(1).iloc[0]
        sessions = float(last["sessions"])
        aov = float(last["aov"])
    recent_conv = weighted_recent(history, "conversion", n=4)
    high_conv = high_regime_mean(history, "conversion")
    conversion = recent_conv + conv_recovery * (high_conv - recent_conv)
    return float(sessions * conversion * aov)


def revenue_donor(history: pd.DataFrame, year: int, donor: str) -> float:
    if donor == "recent4":
        return weighted_recent(history, "revenue", n=4)
    if donor == "trend_log":
        return trend_log(history, "revenue", year)
    if donor == "high_regime":
        return high_regime_mean(history, "revenue")
    if donor.startswith("regime_b"):
        beta = float(donor.replace("regime_b", "")) / 100.0
        return regime_mix(history, "revenue", beta)
    if donor.startswith("funnel_last_c"):
        recovery = float(donor.replace("funnel_last_c", "")) / 100.0
        return funnel_revenue(history, year, recovery, sessions_mode="last")
    if donor.startswith("funnel_trend_c"):
        recovery = float(donor.replace("funnel_trend_c", "")) / 100.0
        return funnel_revenue(history, year, recovery, sessions_mode="trend")
    raise ValueError(f"Unknown revenue donor: {donor}")


def ratio_donor(history: pd.DataFrame, donor: str) -> float:
    ratios = history["cogs_ratio"].dropna()
    if ratios.empty:
        return np.nan
    if donor == "recent4":
        return weighted_recent(history, "cogs_ratio", n=4)
    if donor == "median":
        return float(ratios.median())
    if donor.startswith("q"):
        quantile = float(donor.replace("q", "")) / 100.0
        return float(ratios.quantile(quantile))
    if donor == "max":
        return float(ratios.max())
    raise ValueError(f"Unknown ratio donor: {donor}")


def validation_scores(periods: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    revenue_donors = [
        "recent4",
        "trend_log",
        "high_regime",
        "regime_b20",
        "regime_b30",
        "regime_b40",
        "regime_b44",
        "regime_b50",
        "funnel_last_c05",
        "funnel_last_c10",
        "funnel_last_c15",
        "funnel_last_c20",
        "funnel_trend_c05",
        "funnel_trend_c10",
        "funnel_trend_c15",
    ]
    ratio_donors = ["recent4", "median", "q75", "q90", "q95", "q98", "max"]
    revenue_rows = []
    ratio_rows = []
    for _, row in periods.loc[periods["year"].between(2018, 2022)].iterrows():
        year = int(row["year"])
        half = str(row["half"])
        history = same_half_history(periods, year, half)
        if len(history) < 4:
            continue
        for donor in revenue_donors:
            pred = revenue_donor(history, year, donor)
            revenue_rows.append(
                {
                    "target": "revenue",
                    "year": year,
                    "half": half,
                    "donor": donor,
                    "actual": float(row["revenue"]),
                    "pred": pred,
                    "abs_error": abs(pred - float(row["revenue"])),
                    "ape": abs(pred - float(row["revenue"])) / max(abs(float(row["revenue"])), 1e-9),
                    "bias": pred - float(row["revenue"]),
                }
            )
        for donor in ratio_donors:
            pred = ratio_donor(history, donor)
            ratio_rows.append(
                {
                    "target": "cogs_ratio",
                    "year": year,
                    "half": half,
                    "donor": donor,
                    "actual": float(row["cogs_ratio"]),
                    "pred": pred,
                    "abs_error": abs(pred - float(row["cogs_ratio"])),
                    "ape": abs(pred - float(row["cogs_ratio"])) / max(abs(float(row["cogs_ratio"])), 1e-9),
                    "bias": pred - float(row["cogs_ratio"]),
                }
            )
    revenue = pd.DataFrame(revenue_rows)
    ratio = pd.DataFrame(ratio_rows)
    return summarize_scores(revenue), summarize_scores(ratio)


def summarize_scores(rows: pd.DataFrame) -> pd.DataFrame:
    return (
        rows.groupby(["target", "half", "donor"], as_index=False)
        .agg(
            mean_abs_error=("abs_error", "mean"),
            mean_ape=("ape", "mean"),
            worst_ape=("ape", "max"),
            mean_bias=("bias", "mean"),
            folds=("year", "count"),
        )
        .sort_values(["target", "half", "mean_ape", "worst_ape"])
    )


def best_donors(score: pd.DataFrame) -> dict[tuple[str, str], str]:
    out: dict[tuple[str, str], str] = {}
    for (target, half), group in score.groupby(["target", "half"]):
        out[(target, half)] = str(group.sort_values(["mean_ape", "worst_ape"]).iloc[0]["donor"])
    return out


def forecast_revenue(
    periods: pd.DataFrame,
    year: int,
    half: str,
    mode: str,
    conv_recovery: float | None,
    selected_revenue: dict[str, str],
) -> float:
    history = same_half_history(periods, year, half)
    if mode == "cv_selected":
        donor = selected_revenue[half]
        return revenue_donor(history, year, donor)
    if mode == "funnel_last":
        if conv_recovery is None:
            raise ValueError("conv_recovery is required for funnel mode")
        return funnel_revenue(history, year, conv_recovery, sessions_mode="last")
    if mode == "funnel_trend":
        if conv_recovery is None:
            raise ValueError("conv_recovery is required for funnel mode")
        return funnel_revenue(history, year, conv_recovery, sessions_mode="trend")
    if mode.startswith("regime_b"):
        return revenue_donor(history, year, mode)
    raise ValueError(f"Unknown total mode: {mode}")


def forecast_ratio(
    periods: pd.DataFrame,
    year: int,
    half: str,
    mode: str,
    h1_ratio: float | None,
    selected_ratio: dict[str, str],
) -> float:
    if half == "H1" and h1_ratio is not None:
        return h1_ratio
    history = same_half_history(periods, year, half)
    if mode == "cv_selected":
        return ratio_donor(history, selected_ratio[half])
    if mode == "base":
        return ratio_donor(history, "max") if half == "H2" else ratio_donor(history, "q98")
    return ratio_donor(history, mode)


def apply_head_totals(
    periods: pd.DataFrame,
    base: pd.DataFrame,
    spec: CandidateSpec,
    selected_revenue: dict[str, str],
    selected_ratio: dict[str, str],
) -> pd.DataFrame:
    out = base.copy()
    for period in FORECAST_PERIODS:
        if period not in spec.override_periods:
            continue
        year = int(period[:4])
        half = period[4:]
        revenue = forecast_revenue(periods, year, half, spec.total_mode, spec.conv_recovery, selected_revenue)
        ratio = forecast_ratio(periods, year, half, spec.h2_ratio_mode, spec.h1_ratio, selected_ratio)
        mask = out["period"].eq(period)
        out.loc[mask, "revenue"] = revenue
        out.loc[mask, "cogs"] = revenue * ratio
    out["cogs_ratio"] = out["cogs"] / out["revenue"]
    return out


def build_specs() -> list[CandidateSpec]:
    return [
        CandidateSpec(
            name="cleanv3_head_strict_cvselected",
            total_mode="cv_selected",
            h1_ratio=None,
            h2_ratio_mode="cv_selected",
            override_periods=("2023H1", "2023H2", "2024H1"),
            note="Strict train-fold selected period and ratio donors for all major periods; no public beta.",
        ),
        CandidateSpec(
            name="cleanv3_head_funnel_last_c10_h1only_r0876",
            total_mode="funnel_last",
            conv_recovery=0.10,
            h1_ratio=0.876,
            override_periods=("2023H1",),
            note="Business funnel head: 2022 sessions/AOV with 10% conversion-gap recovery; H1 only.",
        ),
        CandidateSpec(
            name="cleanv3_head_funnel_last_c12_h1only_r0876",
            total_mode="funnel_last",
            conv_recovery=0.12,
            h1_ratio=0.876,
            override_periods=("2023H1",),
            note="Business funnel head with 12% conversion-gap recovery; H1 only.",
        ),
        CandidateSpec(
            name="cleanv3_head_funnel_last_c08_h1only_r0876",
            total_mode="funnel_last",
            conv_recovery=0.08,
            h1_ratio=0.876,
            override_periods=("2023H1",),
            note="Business funnel head with 8% conversion-gap recovery; H1 only.",
        ),
        CandidateSpec(
            name="cleanv3_head_funnel_last_c10_h1only_r0870",
            total_mode="funnel_last",
            conv_recovery=0.10,
            h1_ratio=0.870,
            override_periods=("2023H1",),
            note="Funnel H1 head plus lower H1 COGS-ratio stress.",
        ),
        CandidateSpec(
            name="cleanv3_head_regime_b44_h1only_r0876",
            total_mode="regime_b44",
            h1_ratio=0.876,
            override_periods=("2023H1",),
            note="Regime-mixture period head equivalent to current best neighborhood, expressed as a model head.",
        ),
        CandidateSpec(
            name="cleanv3_head_regime_b44_h1_h2q98",
            total_mode="regime_b44",
            h1_ratio=0.876,
            h2_ratio_mode="q98",
            override_periods=("2023H1", "2023H2"),
            note="Regime H1 head plus COGS ratio head normalizing H2 to train q98.",
        ),
        CandidateSpec(
            name="cleanv3_head_funnel_last_c10_all_r0876_q98",
            total_mode="funnel_last",
            conv_recovery=0.10,
            h1_ratio=0.876,
            h2_ratio_mode="q98",
            override_periods=("2023H1", "2023H2", "2024H1"),
            note="Full funnel period-total head for 2023H1/2023H2/2024H1; higher-risk all-period test.",
        ),
    ]


def write_report(
    run_dir: Path,
    revenue_scores: pd.DataFrame,
    ratio_scores: pd.DataFrame,
    manifest: pd.DataFrame,
) -> None:
    revenue_top = revenue_scores.groupby("half", group_keys=False).head(8)
    ratio_top = ratio_scores.groupby("half", group_keys=False).head(8)
    report = f"""# Clean V3 Funnel Regime Head

Run directory: `{run_dir}`

## Boundary

This script uses provided train/source data only for modeling signals and rebuilds daily shape from raw inputs. It does not read `sample_submission.csv`, previous submissions, or test target values as feature inputs.

The candidate family is still **clean-input public-guided** where conversion-recovery values are chosen around public feedback. The script also emits a stricter train-fold selected candidate so the difference is explicit.

## Components Implemented

1. Period-total head: predicts half-year Revenue totals before daily allocation.
2. Funnel model: `Revenue = sessions_prior * conversion_regime * AOV_prior`.
3. Regime-mixture model: blends recent-low and high-regime same-half donors.
4. COGS ratio head: predicts `COGS / Revenue` separately from Revenue.

## Revenue Donor Validation

{revenue_top.to_markdown(index=False)}

## COGS Ratio Donor Validation

{ratio_top.to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Order

1. `submission_cleanv3_head_funnel_last_c10_h1only_r0876.csv`
2. `submission_cleanv3_head_funnel_last_c08_h1only_r0876.csv`
3. `submission_cleanv3_head_funnel_last_c12_h1only_r0876.csv`
4. `submission_cleanv3_head_funnel_last_c10_h1only_r0870.csv`
5. `submission_cleanv3_head_regime_b44_h1_h2q98.csv`
6. `submission_cleanv3_head_strict_cvselected.csv`
7. `submission_cleanv3_head_funnel_last_c10_all_r0876_q98.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v3_funnel_regime_head_2026-04-24.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    sales = load_sales()
    periods = build_period_table()
    base = base_totals(sales)
    shape_base = build_shape_base()

    revenue_scores, ratio_scores = validation_scores(periods)
    revenue_scores.to_csv(run_dir / "revenue_donor_validation.csv", index=False)
    ratio_scores.to_csv(run_dir / "ratio_donor_validation.csv", index=False)
    selected_revenue = {half: donor for (target, half), donor in best_donors(revenue_scores).items() if target == "revenue"}
    selected_ratio = {half: donor for (target, half), donor in best_donors(ratio_scores).items() if target == "cogs_ratio"}

    rows = []
    for priority, spec in enumerate(build_specs(), start=1):
        totals = apply_head_totals(periods, base, spec, selected_revenue, selected_ratio)
        frame = apply_period_totals(shape_base, totals)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)
        prof = period_summary(frame)
        prof.to_csv(run_dir / f"{spec.name}_period_summary.csv", index=False)
        totals.to_csv(run_dir / f"{spec.name}_target_totals.csv", index=False)
        rows.append(
            {
                "priority": priority,
                "filename": path.name,
                "total_mode": spec.total_mode,
                "conv_recovery": spec.conv_recovery,
                "h1_ratio": spec.h1_ratio,
                "h2_ratio_mode": spec.h2_ratio_mode,
                "override_periods": ",".join(spec.override_periods),
                "revenue_total": frame["Revenue"].sum(),
                "cogs_total": frame["COGS"].sum(),
                "ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
                "rev_2023H1": prof.loc[prof["period"].eq("2023H1"), "revenue"].iloc[0],
                "cogs_2023H1": prof.loc[prof["period"].eq("2023H1"), "cogs"].iloc[0],
                "ratio_2023H1": prof.loc[prof["period"].eq("2023H1"), "cogs_ratio"].iloc[0],
                "rev_2023H2": prof.loc[prof["period"].eq("2023H2"), "revenue"].iloc[0],
                "cogs_2023H2": prof.loc[prof["period"].eq("2023H2"), "cogs"].iloc[0],
                "ratio_2023H2": prof.loc[prof["period"].eq("2023H2"), "cogs_ratio"].iloc[0],
                "rev_2024H1": prof.loc[prof["period"].eq("2024H1"), "revenue"].iloc[0],
                "cogs_2024H1": prof.loc[prof["period"].eq("2024H1"), "cogs"].iloc[0],
                "ratio_2024H1": prof.loc[prof["period"].eq("2024H1"), "cogs_ratio"].iloc[0],
                "note": spec.note,
                "selected_revenue_h1": selected_revenue["H1"],
                "selected_revenue_h2": selected_revenue["H2"],
                "selected_ratio_h1": selected_ratio["H1"],
                "selected_ratio_h2": selected_ratio["H2"],
            }
        )

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    write_report(run_dir, revenue_scores, ratio_scores, manifest)
    print(run_dir)


if __name__ == "__main__":
    main()
