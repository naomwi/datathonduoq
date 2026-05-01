from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_clean_regime_recovery_scenarios import load_sales, period_summary
from run_clean_v2_eda_guided_candidates import apply_h1_total_override, base_totals, h1_ratio_stats
from run_cleaninput_rawmdshape_pubguided import apply_period_totals, build_shape_base
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v4_operational_funnel"
TRAIN_END = pd.Timestamp("2022-12-31")
FORECAST_START = pd.Timestamp("2023-01-01")
FORECAST_END = pd.Timestamp("2024-07-01")


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    demand_gamma: float = 0.0
    ratio_gamma: float = 0.0
    scope: str = "all"
    note: str = ""


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def add_period_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out["year"] = out["Date"].dt.year
    out["month"] = out["Date"].dt.month
    out["day"] = out["Date"].dt.day
    out["month_day"] = out["Date"].dt.strftime("%m-%d")
    out["half"] = np.where(out["month"].le(6), "H1", "H2")
    out["period"] = out["year"].astype(str) + out["half"]
    out.loc[out["Date"].eq(FORECAST_END), "period"] = "2024-07-01"
    return out


def safe_div(num: pd.Series, den: pd.Series) -> pd.Series:
    return num.astype(float) / den.astype(float).replace(0.0, np.nan)


def normalise(series: pd.Series, low: float, high: float) -> pd.Series:
    values = series.astype(float).replace([np.inf, -np.inf], np.nan)
    median = float(values.median())
    if not np.isfinite(median) or abs(median) <= 1e-12:
        return pd.Series(1.0, index=series.index)
    out = (values / median).clip(low, high).fillna(1.0)
    out_median = float(out.median())
    if np.isfinite(out_median) and out_median > 1e-12:
        out = out / out_median
    return out.fillna(1.0)


def weighted_geomean(factors: list[tuple[pd.Series, float]]) -> pd.Series:
    log_sum: pd.Series | None = None
    weight_sum = 0.0
    for factor, weight in factors:
        clipped = factor.astype(float).clip(0.50, 1.80)
        term = weight * np.log(clipped)
        log_sum = term if log_sum is None else log_sum + term
        weight_sum += weight
    if log_sum is None or weight_sum <= 0:
        raise ValueError("At least one factor with positive weight is required.")
    out = np.exp(log_sum / weight_sum)
    median = float(pd.Series(out).median())
    if np.isfinite(median) and median > 1e-12:
        out = out / median
    return pd.Series(out).fillna(1.0)


def build_operational_priors(run_dir: Path) -> pd.DataFrame:
    feature_path = DATASET_DIR / "daily_feature_base.csv"
    if not feature_path.exists():
        raise FileNotFoundError(f"Missing clean derived feature file: {feature_path}")

    base = pd.read_csv(feature_path, parse_dates=["Date"], low_memory=False)
    history = base.loc[
        base["Date"].le(TRAIN_END) & base["Date"].dt.year.between(2013, 2022) & base["Revenue"].notna() & base["COGS"].notna()
    ].copy()

    required_defaults = {
        "sessions": np.nan,
        "conversion_proxy": np.nan,
        "aov_proxy": np.nan,
        "category_rev_share_streetwear": np.nan,
        "inv_stockout_flag_streetwear": np.nan,
        "stockout_rate": np.nan,
        "payment_share_cod": 0.0,
        "cancelled_order_share": 0.0,
        "refund_amt": 0.0,
    }
    for col, default in required_defaults.items():
        if col not in history.columns:
            history[col] = default

    history["month_day"] = history["Date"].dt.strftime("%m-%d")
    history["rev_per_session"] = safe_div(history["Revenue"], history["sessions"])
    history["cogs_ratio"] = safe_div(history["COGS"], history["Revenue"])
    history["cod_cancel_index"] = history["payment_share_cod"] * (1.0 + 2.0 * history["cancelled_order_share"])
    history["return_value_rate"] = safe_div(history["refund_amt"], history["Revenue"]).clip(lower=0.0)
    history["stockout_blend"] = history[["inv_stockout_flag_streetwear", "stockout_rate"]].mean(axis=1)

    priors = (
        history.groupby("month_day", as_index=False)
        .agg(
            train_days=("Date", "count"),
            conversion_proxy=("conversion_proxy", "median"),
            rev_per_session=("rev_per_session", "median"),
            aov_proxy=("aov_proxy", "median"),
            cogs_ratio=("cogs_ratio", "median"),
            streetwear_share=("category_rev_share_streetwear", "median"),
            streetwear_stockout=("inv_stockout_flag_streetwear", "median"),
            stockout_blend=("stockout_blend", "median"),
            cod_cancel_index=("cod_cancel_index", "median"),
            return_value_rate=("return_value_rate", "median"),
        )
        .sort_values("month_day")
    )

    conv_factor = normalise(priors["conversion_proxy"], 0.75, 1.30)
    rps_factor = normalise(priors["rev_per_session"], 0.75, 1.30)
    streetwear_demand = normalise(priors["streetwear_share"], 0.85, 1.15)
    stockout_demand = normalise(priors["stockout_blend"], 0.90, 1.12)
    cod_friction = 1.0 / normalise(priors["cod_cancel_index"], 0.75, 1.35)
    return_friction = 1.0 / normalise(priors["return_value_rate"], 0.75, 1.35)

    ratio_prior = normalise(priors["cogs_ratio"], 0.80, 1.25)
    aov_ratio = 1.0 / normalise(priors["aov_proxy"], 0.75, 1.30)
    streetwear_ratio = 1.0 / normalise(priors["streetwear_share"], 0.85, 1.20)
    stockout_ratio = 1.0 / normalise(priors["stockout_blend"], 0.90, 1.15)

    priors["demand_factor"] = weighted_geomean(
        [
            (conv_factor, 0.45),
            (rps_factor, 0.25),
            (streetwear_demand, 0.10),
            (stockout_demand, 0.05),
            (cod_friction, 0.10),
            (return_friction, 0.05),
        ]
    ).clip(0.80, 1.25)
    priors["cogs_ratio_factor"] = weighted_geomean(
        [
            (ratio_prior, 0.45),
            (aov_ratio, 0.25),
            (streetwear_ratio, 0.20),
            (stockout_ratio, 0.10),
        ]
    ).clip(0.75, 1.25)
    priors["conversion_factor"] = conv_factor.clip(0.75, 1.30)
    priors["friction_factor"] = weighted_geomean([(cod_friction, 0.60), (return_friction, 0.40)]).clip(0.80, 1.20)

    priors.to_csv(run_dir / "operational_monthday_priors.csv", index=False)
    return priors


def scope_mask(frame: pd.DataFrame, scope: str) -> pd.Series:
    if scope == "all":
        return frame["period"].isin(["2023H1", "2023H2", "2024H1", "2024-07-01"])
    if scope == "h1":
        return frame["period"].isin(["2023H1", "2024H1"])
    if scope == "2023h1":
        return frame["period"].eq("2023H1")
    if scope == "2024h1":
        return frame["period"].eq("2024H1")
    if scope == "h2":
        return frame["period"].eq("2023H2")
    raise ValueError(f"Unknown scope: {scope}")


def preserve_period_totals(out: pd.DataFrame, reference: pd.DataFrame, active: pd.Series, targets: list[str]) -> pd.DataFrame:
    result = out.copy()
    reference_periods = add_period_columns(reference)
    for period, idx in result.groupby("period").groups.items():
        idx_list = list(idx)
        if not bool(active.loc[idx_list].any()):
            continue
        for target in targets:
            original_total = float(reference_periods.loc[idx_list, target].sum())
            new_total = float(result.loc[idx_list, target].sum())
            if new_total > 0:
                result.loc[idx_list, target] *= original_total / new_total
    return result


def apply_operational_adjustments(base_frame: pd.DataFrame, priors: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    out = add_period_columns(base_frame)
    merged = out.merge(priors[["month_day", "demand_factor", "cogs_ratio_factor"]], on="month_day", how="left")
    active = scope_mask(merged, spec.scope)

    if spec.demand_gamma > 0:
        demand = (1.0 + spec.demand_gamma * (merged["demand_factor"].fillna(1.0) - 1.0)).clip(0.70, 1.35)
        out.loc[active, ["Revenue", "COGS"]] = out.loc[active, ["Revenue", "COGS"]].mul(demand.loc[active], axis=0)
        out = preserve_period_totals(out, base_frame, active, ["Revenue", "COGS"])

    if spec.ratio_gamma > 0:
        ratio = (1.0 + spec.ratio_gamma * (merged["cogs_ratio_factor"].fillna(1.0) - 1.0)).clip(0.70, 1.35)
        out.loc[active, "COGS"] *= ratio.loc[active]
        out = preserve_period_totals(out, base_frame, active, ["COGS"])

    return out[["Date", "Revenue", "COGS", "period"]]


def build_specs() -> list[CandidateSpec]:
    return [
        CandidateSpec(
            name="cleanv4_base_h1b044_r0876",
            note="Sanity rebuild of the current clean H1 b044/r0876 neighborhood; do not submit unless needed for reproducibility.",
        ),
        CandidateSpec(
            name="cleanv4_opratio_g020",
            ratio_gamma=0.20,
            note="Gentle COGS-ratio operational head; avoids double-counting raw month-day Revenue shape.",
        ),
        CandidateSpec(
            name="cleanv4_opratio_g035",
            ratio_gamma=0.35,
            note="Moderate COGS-ratio operational head; still keeps Revenue unchanged and preserves period COGS totals.",
        ),
        CandidateSpec(
            name="cleanv4_opdemand_g010",
            demand_gamma=0.10,
            note="Very small operational demand daily allocation; tests whether funnel priors add signal without overpowering raw-md seasonality.",
        ),
        CandidateSpec(
            name="cleanv4_opcombo_g010_r020",
            demand_gamma=0.10,
            ratio_gamma=0.20,
            note="Gentle demand plus COGS-ratio head; primary low-risk operational-funnel probe.",
        ),
        CandidateSpec(
            name="cleanv4_h1_opratio_g035",
            ratio_gamma=0.35,
            scope="h1",
            note="H1-only COGS-ratio operational head, aligned with the current clean H1 gain.",
        ),
        CandidateSpec(
            name="cleanv4_h1_opcombo_g015_r030",
            demand_gamma=0.15,
            ratio_gamma=0.30,
            scope="h1",
            note="Gentle H1-only operational combo; avoids touching 2023H2 and the final day.",
        ),
        CandidateSpec(
            name="cleanv4_opdemand_g030",
            demand_gamma=0.30,
            note="Redistribute daily Revenue/COGS by train month-day conversion, revenue-per-session, Streetwear stockout, COD, and return-risk priors; preserve every period total.",
        ),
        CandidateSpec(
            name="cleanv4_opdemand_g050",
            demand_gamma=0.50,
            note="Stronger version of operational demand daily allocation; still period-total preserving.",
        ),
        CandidateSpec(
            name="cleanv4_opratio_g060",
            ratio_gamma=0.60,
            note="Keep Revenue unchanged; reshape daily COGS ratio using train cogs-ratio, AOV, Streetwear share, and stockout priors.",
        ),
        CandidateSpec(
            name="cleanv4_opcombo_g030_r060",
            demand_gamma=0.30,
            ratio_gamma=0.60,
            note="Operational demand shape plus separate COGS-ratio head; tests whether the analyst report's funnel/stockout story helps daily allocation.",
        ),
        CandidateSpec(
            name="cleanv4_h1_opcombo_g040_r070",
            demand_gamma=0.40,
            ratio_gamma=0.70,
            scope="h1",
            note="Apply operational shape only to H1 periods, where current clean public signal is strongest.",
        ),
        CandidateSpec(
            name="cleanv4_2024h1_opcombo_g050_r080",
            demand_gamma=0.50,
            ratio_gamma=0.80,
            scope="2024h1",
            note="Isolate 2024H1 operational manifold without touching 2023; useful if H1 pattern is real but 2023 already saturated.",
        ),
    ]


def sanity_check(frame: pd.DataFrame, name: str) -> None:
    if len(frame) != 548:
        raise ValueError(f"{name}: expected 548 rows, got {len(frame)}")
    dates = pd.to_datetime(frame["Date"])
    if dates.min() != FORECAST_START or dates.max() != FORECAST_END:
        raise ValueError(f"{name}: bad date range {dates.min()} - {dates.max()}")
    if frame[["Revenue", "COGS"]].isna().any().any():
        raise ValueError(f"{name}: contains NaN target values")
    if frame[["Revenue", "COGS"]].lt(0).any().any():
        raise ValueError(f"{name}: contains negative target values")


def movement_summary(frame: pd.DataFrame, base_frame: pd.DataFrame) -> dict[str, float]:
    delta_rev = frame["Revenue"] - base_frame["Revenue"]
    delta_cogs = frame["COGS"] - base_frame["COGS"]
    return {
        "rev_abs_delta_mean": float(delta_rev.abs().mean()),
        "cogs_abs_delta_mean": float(delta_cogs.abs().mean()),
        "rev_abs_delta_max": float(delta_rev.abs().max()),
        "cogs_abs_delta_max": float(delta_cogs.abs().max()),
        "revenue_total_ratio_vs_base": float(frame["Revenue"].sum() / base_frame["Revenue"].sum()),
        "cogs_total_ratio_vs_base": float(frame["COGS"].sum() / base_frame["COGS"].sum()),
        "max_revenue": float(frame["Revenue"].max()),
        "max_cogs": float(frame["COGS"].max()),
    }


def feature_provenance() -> pd.DataFrame:
    rows = [
        ("conversion_proxy", "dataset/daily_feature_base.csv <= 2022-12-31", "order_count / sessions proxy", "month-day median prior"),
        ("rev_per_session", "Revenue and sessions <= 2022-12-31", "funnel realized value per traffic", "month-day median prior"),
        ("category_rev_share_streetwear", "provided order/product-derived train feature", "dominant segment demand mix", "month-day median prior"),
        ("inv_stockout_flag_streetwear", "provided inventory-derived train feature", "Streetwear stockout exposure", "month-day median prior"),
        ("payment_share_cod + cancelled_order_share", "provided orders/payments train features", "COD cancellation friction", "month-day median prior"),
        ("refund_amt / Revenue", "provided returns + sales train features", "returns friction", "month-day median prior"),
        ("COGS / Revenue and AOV", "sales/order-derived train features", "COGS-ratio head", "month-day median prior"),
    ]
    return pd.DataFrame(rows, columns=["feature", "source", "role", "future_policy"])


def write_report(run_dir: Path, manifest: pd.DataFrame, provenance: pd.DataFrame, priors: pd.DataFrame) -> None:
    factor_profile = priors[["demand_factor", "cogs_ratio_factor", "conversion_factor", "friction_factor"]].describe(
        percentiles=[0.05, 0.25, 0.50, 0.75, 0.95]
    )
    report = f"""# Clean V4 Operational Funnel

Run directory: `{run_dir}`

## Boundary

This is **clean-input public-guided**, not quarantine blackbox.

The script does not read `sample_submission.csv`, previous submission files, test targets, or public-blackbox donor files as inputs. It rebuilds the base forecast from existing clean code, then uses only train-period raw/derived features through `dataset/daily_feature_base.csv` up to `2022-12-31`.

The analyst PDF is used only as qualitative EDA motivation: conversion/funnel friction, Streetwear stockout exposure, COD cancellation, and return friction are treated as plausible business mechanisms. Numeric factors are computed from train data only and projected to 2023-2024 by recurring `month-day` priors.

## Method

- Base level: current clean neighborhood `2023H1 beta = 0.44`, `2023H1 COGS ratio = 0.876`.
- Demand head: month-day prior from conversion proxy, revenue/session, Streetwear mix/stockout, COD friction, and return friction.
- COGS-ratio head: month-day prior from train COGS/Revenue, AOV, Streetwear mix, and stockout.
- Every candidate preserves period totals after daily reshaping; this tests shape quality rather than another hidden level squeeze.

## Feature Provenance

{provenance.to_markdown(index=False)}

## Factor Profile

{factor_profile.to_markdown()}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Suggested Submit Order

1. `submission_cleanv4_opcombo_g010_r020.csv`
2. `submission_cleanv4_opratio_g020.csv`
3. `submission_cleanv4_h1_opratio_g035.csv`
4. `submission_cleanv4_opdemand_g010.csv`
5. `submission_cleanv4_opratio_g035.csv`

Readout: if combo improves, the clean story is that operational/funnel daily allocation matters beyond period totals. If only ratio improves, keep Revenue shape and develop the COGS-ratio head. If all fail, operational report features explain the business but do not improve this leaderboard target at daily resolution.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v4_operational_funnel_2026-04-28.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    sales = load_sales()
    stats = h1_ratio_stats(sales)
    shape_base = build_shape_base()
    totals = apply_h1_total_override(sales, base_totals(sales), beta=0.44, ratio=stats["h1_recovery_stress"])
    base_frame = apply_period_totals(shape_base, totals).reset_index(drop=True)
    sanity_check(base_frame, "base_frame")

    priors = build_operational_priors(run_dir)
    provenance = feature_provenance()
    provenance.to_csv(run_dir / "feature_provenance.csv", index=False)

    rows: list[dict[str, object]] = []
    for priority, spec in enumerate(build_specs(), start=1):
        frame = apply_operational_adjustments(base_frame, priors, spec).reset_index(drop=True)
        sanity_check(frame, spec.name)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)

        prof = period_summary(frame)
        prof.to_csv(run_dir / f"{spec.name}_period_summary.csv", index=False)
        monthly = add_period_columns(frame).groupby(["year", "month"], as_index=False).agg(revenue=("Revenue", "sum"), cogs=("COGS", "sum"))
        monthly["cogs_ratio"] = monthly["cogs"] / monthly["revenue"]
        monthly.to_csv(run_dir / f"{spec.name}_month_summary.csv", index=False)

        row = {
            "priority": priority,
            "filename": path.name,
            "scope": spec.scope,
            "demand_gamma": spec.demand_gamma,
            "ratio_gamma": spec.ratio_gamma,
            "revenue_total": float(frame["Revenue"].sum()),
            "cogs_total": float(frame["COGS"].sum()),
            "ratio_total": float(frame["COGS"].sum() / frame["Revenue"].sum()),
            "note": spec.note,
        }
        for _, period_row in prof.iterrows():
            period = str(period_row["period"])
            row[f"rev_{period}"] = float(period_row["revenue"])
            row[f"cogs_{period}"] = float(period_row["cogs"])
            row[f"ratio_{period}"] = float(period_row["cogs_ratio"])
        row.update(movement_summary(frame, base_frame))
        rows.append(row)

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    totals.to_csv(run_dir / "base_period_totals.csv", index=False)
    period_summary(base_frame).to_csv(run_dir / "base_period_summary.csv", index=False)
    write_report(run_dir, manifest, provenance, priors)
    print(run_dir)


if __name__ == "__main__":
    main()
