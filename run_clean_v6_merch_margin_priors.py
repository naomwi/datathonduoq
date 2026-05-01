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


RUN_PREFIX = "clean_v6_merch_margin_priors"
TRAIN_END = pd.Timestamp("2022-12-31")
FORECAST_START = pd.Timestamp("2023-01-01")
FORECAST_END = pd.Timestamp("2024-07-01")


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    cogs_gamma: float = 0.0
    revenue_gamma: float = 0.0
    scope: str = "all"
    note: str = ""


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def slug(value: object) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("#", "").replace("-", "_")


def safe_div(num: pd.Series | float, den: pd.Series | float) -> pd.Series | float:
    if np.isscalar(num) and np.isscalar(den):
        return float(num) / float(den) if float(den) else np.nan
    return pd.Series(num, dtype=float) / pd.Series(den, dtype=float).replace(0.0, np.nan)


def add_period_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out["year"] = out["Date"].dt.year
    out["month"] = out["Date"].dt.month
    out["month_day"] = out["Date"].dt.strftime("%m-%d")
    out["half"] = np.where(out["month"].le(6), "H1", "H2")
    out["period"] = out["year"].astype(str) + out["half"]
    out.loc[out["Date"].eq(FORECAST_END), "period"] = "2024-07-01"
    return out


def robust_factor(series: pd.Series, direction: float, amplitude: float, low: float, high: float) -> pd.Series:
    values = series.astype(float).replace([np.inf, -np.inf], np.nan)
    med = float(values.median())
    q10 = float(values.quantile(0.10))
    q90 = float(values.quantile(0.90))
    scale = q90 - q10
    if not np.isfinite(scale) or scale <= 1e-12:
        return pd.Series(1.0, index=series.index)
    z = ((values - med) / scale).clip(-1.5, 1.5).fillna(0.0)
    out = (1.0 + direction * amplitude * z).clip(low, high)
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
        raise ValueError("No positive-weight factors supplied.")
    out = np.exp(log_sum / weight_sum)
    median = float(pd.Series(out).median())
    if np.isfinite(median) and median > 1e-12:
        out = out / median
    return pd.Series(out).fillna(1.0)


def build_daily_merch_features(run_dir: Path) -> pd.DataFrame:
    orders = pd.read_csv(DATASET_DIR / "orders.csv", parse_dates=["order_date"], low_memory=False)
    items = pd.read_csv(DATASET_DIR / "order_items.csv", low_memory=False)
    products = pd.read_csv(DATASET_DIR / "products.csv", low_memory=False)
    frame = (
        items.merge(orders[["order_id", "order_date"]], on="order_id", how="left")
        .merge(products[["product_id", "category", "segment", "size", "color", "cogs"]], on="product_id", how="left")
        .rename(columns={"order_date": "Date"})
    )
    frame = frame.loc[frame["Date"].le(TRAIN_END) & frame["Date"].dt.year.between(2013, 2022)].copy()
    frame["units"] = frame["quantity"].astype(float)
    frame["net_value"] = frame["quantity"] * frame["unit_price"] - frame["discount_amount"].fillna(0.0)
    frame["cogs_value"] = frame["quantity"] * frame["cogs"]
    frame["margin_value"] = frame["net_value"] - frame["cogs_value"]

    daily = (
        frame.groupby("Date", as_index=False)
        .agg(
            net_value=("net_value", "sum"),
            cogs_value=("cogs_value", "sum"),
            margin_value=("margin_value", "sum"),
            units=("units", "sum"),
            discount_amount=("discount_amount", "sum"),
        )
        .sort_values("Date")
    )
    daily["item_margin_rate_wavg"] = safe_div(daily["margin_value"], daily["net_value"])
    daily["item_cogs_ratio"] = safe_div(daily["cogs_value"], daily["net_value"])
    daily["discount_per_unit"] = safe_div(daily["discount_amount"], daily["units"])

    def pivot_margin(column: str, prefix: str) -> pd.DataFrame:
        grouped = (
            frame.groupby(["Date", column], as_index=False)
            .agg(net_value=("net_value", "sum"), margin_value=("margin_value", "sum"))
        )
        grouped["margin_rate"] = safe_div(grouped["margin_value"], grouped["net_value"])
        pivot = grouped.pivot(index="Date", columns=column, values="margin_rate")
        pivot.columns = [f"{prefix}_margin_{slug(col)}" for col in pivot.columns]
        return pivot.reset_index()

    def pivot_share(column: str, prefix: str) -> pd.DataFrame:
        grouped = frame.groupby(["Date", column], as_index=False).agg(net_value=("net_value", "sum"))
        totals = grouped.groupby("Date", as_index=False).agg(total_value=("net_value", "sum"))
        grouped = grouped.merge(totals, on="Date", how="left")
        grouped["share"] = safe_div(grouped["net_value"], grouped["total_value"])
        pivot = grouped.pivot(index="Date", columns=column, values="share")
        pivot.columns = [f"{prefix}_rev_{slug(col)}" for col in pivot.columns]
        return pivot.reset_index()

    for part in [
        pivot_margin("category", "cat"),
        pivot_margin("segment", "seg"),
        pivot_share("size", "size"),
        pivot_share("color", "color"),
    ]:
        daily = daily.merge(part, on="Date", how="left")

    daily.to_csv(run_dir / "daily_merch_features_train.csv", index=False)
    return daily


def build_monthday_priors(daily_merch: pd.DataFrame, run_dir: Path) -> pd.DataFrame:
    hist = daily_merch.copy()
    hist["month_day"] = pd.to_datetime(hist["Date"]).dt.strftime("%m-%d")
    priors = hist.groupby("month_day", as_index=False).median(numeric_only=True).sort_values("month_day")

    required = [
        "discount_per_unit",
        "item_margin_rate_wavg",
        "cat_margin_streetwear",
        "seg_margin_everyday",
        "seg_margin_activewear",
        "color_rev_white",
        "color_rev_black",
        "size_rev_l",
        "size_rev_s",
    ]
    for col in required:
        if col not in priors.columns:
            priors[col] = np.nan

    priors["merch_cogs_factor"] = weighted_geomean(
        [
            (robust_factor(priors["discount_per_unit"], direction=1.0, amplitude=0.24, low=0.80, high=1.25), 0.35),
            (robust_factor(priors["item_margin_rate_wavg"], direction=-1.0, amplitude=0.26, low=0.78, high=1.25), 0.30),
            (robust_factor(priors["cat_margin_streetwear"], direction=-1.0, amplitude=0.20, low=0.82, high=1.20), 0.15),
            (robust_factor(priors["seg_margin_everyday"], direction=-1.0, amplitude=0.18, low=0.84, high=1.18), 0.10),
            (robust_factor(priors["seg_margin_activewear"], direction=-1.0, amplitude=0.16, low=0.85, high=1.16), 0.10),
        ]
    ).clip(0.82, 1.22)
    priors["merch_revenue_factor"] = weighted_geomean(
        [
            (robust_factor(priors["color_rev_white"], direction=1.0, amplitude=0.20, low=0.85, high=1.18), 0.35),
            (robust_factor(priors["size_rev_l"], direction=1.0, amplitude=0.16, low=0.88, high=1.15), 0.25),
            (robust_factor(priors["color_rev_black"], direction=-1.0, amplitude=0.14, low=0.88, high=1.14), 0.20),
            (robust_factor(priors["size_rev_s"], direction=-1.0, amplitude=0.12, low=0.90, high=1.12), 0.20),
        ]
    ).clip(0.86, 1.16)

    priors.to_csv(run_dir / "merch_monthday_priors.csv", index=False)
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


def apply_merch_prior(base_frame: pd.DataFrame, priors: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    out = add_period_columns(base_frame)
    merged = out.merge(priors[["month_day", "merch_cogs_factor", "merch_revenue_factor"]], on="month_day", how="left")
    active = scope_mask(merged, spec.scope)

    if spec.revenue_gamma > 0:
        rev_factor = (1.0 + spec.revenue_gamma * (merged["merch_revenue_factor"].fillna(1.0) - 1.0)).clip(0.75, 1.25)
        out.loc[active, "Revenue"] *= rev_factor.loc[active]
        out = preserve_period_totals(out, base_frame, active, ["Revenue"])

    if spec.cogs_gamma > 0:
        cogs_factor = (1.0 + spec.cogs_gamma * (merged["merch_cogs_factor"].fillna(1.0) - 1.0)).clip(0.75, 1.25)
        out.loc[active, "COGS"] *= cogs_factor.loc[active]
        out = preserve_period_totals(out, base_frame, active, ["COGS"])

    return out[["Date", "Revenue", "COGS", "period"]]


def build_specs() -> list[CandidateSpec]:
    return [
        CandidateSpec(
            name="cleanv6_merch_base_h1b044_r0876",
            note="Sanity rebuild of current clean base; do not submit.",
        ),
        CandidateSpec(
            name="cleanv6_merch_cogs_g010",
            cogs_gamma=0.10,
            note="Gentle COGS-only merchandise economics prior from discount/unit and category/segment margin month-day priors.",
        ),
        CandidateSpec(
            name="cleanv6_merch_cogs_g020",
            cogs_gamma=0.20,
            note="Moderate COGS-only merchandise economics prior; Revenue unchanged.",
        ),
        CandidateSpec(
            name="cleanv6_merch_cogs_g035",
            cogs_gamma=0.35,
            note="Stronger COGS-only merchandise economics prior; still period-total preserving.",
        ),
        CandidateSpec(
            name="cleanv6_merch_h1_cogs_g025",
            cogs_gamma=0.25,
            scope="h1",
            note="H1-only COGS merchandise economics prior.",
        ),
        CandidateSpec(
            name="cleanv6_merch_revshape_g010",
            revenue_gamma=0.10,
            note="Revenue shape prior from train recurring color/size mix; COGS unchanged.",
        ),
        CandidateSpec(
            name="cleanv6_merch_revshape_g020",
            revenue_gamma=0.20,
            note="Stronger Revenue color/size daily-shape prior; COGS unchanged.",
        ),
        CandidateSpec(
            name="cleanv6_merch_combo_rev010_cogs020",
            revenue_gamma=0.10,
            cogs_gamma=0.20,
            note="Combined color/size Revenue shape and merchandise COGS-ratio prior.",
        ),
        CandidateSpec(
            name="cleanv6_merch_h1_combo_rev010_cogs025",
            revenue_gamma=0.10,
            cogs_gamma=0.25,
            scope="h1",
            note="H1-only combined merchandise prior.",
        ),
    ]


def sanity_check(frame: pd.DataFrame, name: str) -> None:
    if len(frame) != 548:
        raise ValueError(f"{name}: expected 548 rows, got {len(frame)}")
    dates = pd.to_datetime(frame["Date"])
    if dates.min() != FORECAST_START or dates.max() != FORECAST_END:
        raise ValueError(f"{name}: bad date range {dates.min()} - {dates.max()}")
    if frame[["Revenue", "COGS"]].isna().any().any():
        raise ValueError(f"{name}: contains NaN")
    if frame[["Revenue", "COGS"]].lt(0).any().any():
        raise ValueError(f"{name}: contains negative values")


def movement_summary(frame: pd.DataFrame, base_frame: pd.DataFrame) -> dict[str, float]:
    rev_delta = frame["Revenue"] - base_frame["Revenue"]
    cogs_delta = frame["COGS"] - base_frame["COGS"]
    return {
        "rev_abs_delta_mean": float(rev_delta.abs().mean()),
        "cogs_abs_delta_mean": float(cogs_delta.abs().mean()),
        "rev_abs_delta_max": float(rev_delta.abs().max()),
        "cogs_abs_delta_max": float(cogs_delta.abs().max()),
        "revenue_total_ratio_vs_base": float(frame["Revenue"].sum() / base_frame["Revenue"].sum()),
        "cogs_total_ratio_vs_base": float(frame["COGS"].sum() / base_frame["COGS"].sum()),
        "max_revenue": float(frame["Revenue"].max()),
        "max_cogs": float(frame["COGS"].max()),
    }


def write_report(run_dir: Path, manifest: pd.DataFrame, priors: pd.DataFrame) -> None:
    factor_profile = priors[["merch_cogs_factor", "merch_revenue_factor"]].describe(percentiles=[0.05, 0.25, 0.50, 0.75, 0.95])
    report = f"""# Clean V6 Merchandise Margin Priors

Run directory: `{run_dir}`

## Boundary

This is clean-input public-guided. It does not read `sample_submission.csv`, previous submissions, blackbox files, or test targets.

The new signal comes from train-only `orders.csv`, `order_items.csv`, and `products.csv` through `2022-12-31`:

- `discount_per_unit`
- weighted item margin rate
- category/segment margin rates
- size/color revenue shares

Future values are not used directly. They are projected by recurring train `month-day` priors, then applied as gentle period-total-preserving daily shape adjustments.

## Why This Exists

The LLM-council audit found that broad operational COGS ratio failed, but product economics by category/segment had stronger clean evidence for COGS-ratio residuals. This tests that more specific mechanism without using forbidden inputs.

## Factor Profile

{factor_profile.to_markdown()}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Suggested Submit Order

1. `submission_cleanv6_merch_cogs_g010.csv`
2. `submission_cleanv6_merch_cogs_g020.csv`
3. `submission_cleanv6_merch_revshape_g010.csv`
4. `submission_cleanv6_merch_combo_rev010_cogs020.csv`
5. `submission_cleanv6_merch_h1_cogs_g025.csv`

If `cogs_g010` fails, do not escalate `cogs_g020/g035`; pivot to the strict period-total funnel head.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v6_merch_margin_priors_2026-04-28.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    sales = load_sales()
    stats = h1_ratio_stats(sales)
    shape_base = build_shape_base()
    totals = apply_h1_total_override(sales, base_totals(sales), beta=0.44, ratio=stats["h1_recovery_stress"])
    base_frame = apply_period_totals(shape_base, totals).reset_index(drop=True)
    sanity_check(base_frame, "base_frame")

    daily_merch = build_daily_merch_features(run_dir)
    priors = build_monthday_priors(daily_merch, run_dir)

    rows: list[dict[str, object]] = []
    for priority, spec in enumerate(build_specs(), start=1):
        frame = apply_merch_prior(base_frame, priors, spec).reset_index(drop=True)
        sanity_check(frame, spec.name)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)
        prof = period_summary(frame)
        prof.to_csv(run_dir / f"{spec.name}_period_summary.csv", index=False)
        row = {
            "priority": priority,
            "filename": path.name,
            "scope": spec.scope,
            "cogs_gamma": spec.cogs_gamma,
            "revenue_gamma": spec.revenue_gamma,
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
    write_report(run_dir, manifest, priors)
    print(run_dir)
    print(manifest[["priority", "filename", "scope", "cogs_gamma", "revenue_gamma", "rev_abs_delta_mean", "cogs_abs_delta_mean"]].to_string(index=False))


if __name__ == "__main__":
    main()
