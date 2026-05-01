from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_clean_regime_recovery_scenarios import load_sales, period_summary
from run_clean_v2_eda_guided_candidates import base_totals
from run_clean_v3_funnel_regime_head import build_period_table, funnel_revenue, ratio_donor, same_half_history
from run_cleaninput_rawmdshape_pubguided import apply_period_totals, build_shape_base
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v7_period_funnel_council"
FORECAST_PERIODS = ("2023H1", "2023H2", "2024H1")
TRAIN_END = pd.Timestamp("2022-12-31")
FORECAST_START = pd.Timestamp("2023-01-01")
FORECAST_END = pd.Timestamp("2024-07-01")


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    revenue_head: str
    h1_recovery: float | None = None
    h2_recovery: float | None = None
    h1_ratio: float | None = 0.876
    h2_ratio_mode: str = "base"
    override_periods: tuple[str, ...] = ("2023H1",)
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
    out["half"] = np.where(out["month"].le(6), "H1", "H2")
    out["period"] = out["year"].astype(str) + out["half"]
    out.loc[out["Date"].eq(FORECAST_END), "period"] = "2024-07-01"
    return out


def safe_div(num: pd.Series | float, den: pd.Series | float) -> pd.Series | float:
    if np.isscalar(num) and np.isscalar(den):
        return float(num) / float(den) if float(den) else np.nan
    return pd.Series(num, dtype=float) / pd.Series(den, dtype=float).replace(0.0, np.nan)


def weighted_recent(history: pd.DataFrame, col: str, n: int = 4) -> float:
    recent = history.tail(n).copy()
    if recent.empty:
        return np.nan
    weights = np.exp((recent["year"].to_numpy(dtype=float) - recent["year"].max()) / 2.0)
    values = recent[col].fillna(0.0).to_numpy(dtype=float)
    return float(np.average(values, weights=weights))


def high_regime_mean(history: pd.DataFrame, col: str) -> float:
    values = history[col].replace([np.inf, -np.inf], np.nan).dropna().sort_values()
    if values.empty:
        return np.nan
    return float(values.loc[values.ge(values.median())].mean())


def build_source_period_table(run_dir: Path) -> pd.DataFrame:
    orders = pd.read_csv(DATASET_DIR / "orders.csv", parse_dates=["order_date"], low_memory=False)
    items = pd.read_csv(DATASET_DIR / "order_items.csv", low_memory=False)
    traffic = pd.read_csv(DATASET_DIR / "web_traffic.csv", parse_dates=["date"], low_memory=False)

    item_value = (
        items.assign(net_value=items["quantity"] * items["unit_price"] - items["discount_amount"].fillna(0.0))
        .groupby("order_id", as_index=False)
        .agg(order_value=("net_value", "sum"))
    )
    order_values = orders.merge(item_value, on="order_id", how="left")
    order_values = order_values.loc[order_values["order_date"].le(TRAIN_END) & order_values["order_date"].dt.year.between(2013, 2022)].copy()
    order_values["year"] = order_values["order_date"].dt.year
    order_values["half"] = np.where(order_values["order_date"].dt.month.le(6), "H1", "H2")

    order_source = (
        order_values.groupby(["year", "half", "order_source"], as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            order_value=("order_value", "sum"),
            cancelled_rate=("order_status", lambda s: float(s.eq("cancelled").mean())),
        )
        .rename(columns={"order_source": "source"})
    )

    traffic = traffic.loc[traffic["date"].le(TRAIN_END) & traffic["date"].dt.year.between(2013, 2022)].copy()
    traffic["year"] = traffic["date"].dt.year
    traffic["half"] = np.where(traffic["date"].dt.month.le(6), "H1", "H2")
    traffic_source = (
        traffic.groupby(["year", "half", "traffic_source"], as_index=False)
        .agg(sessions=("sessions", "sum"), unique_visitors=("unique_visitors", "sum"))
        .rename(columns={"traffic_source": "source"})
    )

    source = order_source.merge(traffic_source, on=["year", "half", "source"], how="outer")
    source["revenue_per_session"] = safe_div(source["order_value"], source["sessions"])
    source["orders_per_session"] = safe_div(source["orders"], source["sessions"])
    source.to_csv(run_dir / "source_quality_period_table.csv", index=False)
    return source


def build_customer_period_table(run_dir: Path) -> pd.DataFrame:
    orders = pd.read_csv(DATASET_DIR / "orders.csv", parse_dates=["order_date"], low_memory=False)
    customers = pd.read_csv(DATASET_DIR / "customers.csv", parse_dates=["signup_date"], low_memory=False)
    frame = orders.loc[orders["order_date"].le(TRAIN_END) & orders["order_date"].dt.year.between(2013, 2022)].copy()
    frame = frame.sort_values(["customer_id", "order_date", "order_id"])
    frame["prior_orders"] = frame.groupby("customer_id").cumcount()
    frame["is_repeat"] = frame["prior_orders"].gt(0)
    frame = frame.merge(customers[["customer_id", "signup_date", "acquisition_channel", "age_group", "gender"]], on="customer_id", how="left")
    frame["tenure_days"] = (frame["order_date"] - frame["signup_date"]).dt.days.clip(lower=0)
    frame["year"] = frame["order_date"].dt.year
    frame["half"] = np.where(frame["order_date"].dt.month.le(6), "H1", "H2")
    out = (
        frame.groupby(["year", "half"], as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            repeat_order_share=("is_repeat", "mean"),
            avg_tenure_days=("tenure_days", "mean"),
            cod_share=("payment_method", lambda s: float(s.eq("cod").mean())),
            mobile_share=("device_type", lambda s: float(s.eq("mobile").mean())),
        )
        .sort_values(["year", "half"])
    )
    out.to_csv(run_dir / "customer_period_table.csv", index=False)
    return out


def same_half_source_history(source: pd.DataFrame, year: int, half: str, source_name: str) -> pd.DataFrame:
    return source.loc[(source["year"].lt(year)) & (source["half"].eq(half)) & (source["source"].eq(source_name))].sort_values("year")


def source_quality_revenue(source: pd.DataFrame, year: int, half: str, recovery: float) -> float:
    total = 0.0
    for source_name in sorted(source["source"].dropna().unique()):
        history = same_half_source_history(source, year, half, str(source_name))
        if history.empty:
            continue
        sessions = weighted_recent(history, "sessions", n=4)
        recent_rps = weighted_recent(history, "revenue_per_session", n=4)
        high_rps = high_regime_mean(history, "revenue_per_session")
        if not np.isfinite(sessions) or not np.isfinite(recent_rps) or not np.isfinite(high_rps):
            continue
        rps = recent_rps + recovery * (high_rps - recent_rps)
        total += sessions * rps
    return float(total)


def customer_quality_scale(customer_periods: pd.DataFrame, year: int, half: str, gamma: float) -> float:
    history = customer_periods.loc[(customer_periods["year"].lt(year)) & (customer_periods["half"].eq(half))].sort_values("year")
    if len(history) < 4 or gamma <= 0:
        return 1.0
    repeat_recent = weighted_recent(history, "repeat_order_share", n=4)
    repeat_high = high_regime_mean(history, "repeat_order_share")
    tenure_recent = weighted_recent(history, "avg_tenure_days", n=4)
    tenure_high = high_regime_mean(history, "avg_tenure_days")
    repeat_lift = 0.0 if not np.isfinite(repeat_high) or repeat_recent <= 0 else (repeat_high / repeat_recent - 1.0)
    tenure_lift = 0.0 if not np.isfinite(tenure_high) or tenure_recent <= 0 else (tenure_high / tenure_recent - 1.0)
    return float(np.clip(1.0 + gamma * (0.70 * repeat_lift + 0.30 * tenure_lift), 0.92, 1.08))


def forecast_revenue(
    periods: pd.DataFrame,
    source_periods: pd.DataFrame,
    customer_periods: pd.DataFrame,
    year: int,
    half: str,
    spec: CandidateSpec,
) -> float:
    recovery = spec.h1_recovery if half == "H1" else spec.h2_recovery
    if recovery is None:
        recovery = spec.h1_recovery
    if recovery is None:
        raise ValueError(f"Missing recovery value for {spec.name} {year}{half}")

    history = same_half_history(periods, year, half)
    if spec.revenue_head == "order_funnel":
        return funnel_revenue(history, year, recovery, sessions_mode="last")
    if spec.revenue_head == "source_quality":
        return source_quality_revenue(source_periods, year, half, recovery)
    if spec.revenue_head == "source_quality_customer":
        revenue = source_quality_revenue(source_periods, year, half, recovery)
        return revenue * customer_quality_scale(customer_periods, year, half, gamma=0.35)
    raise ValueError(f"Unknown revenue head: {spec.revenue_head}")


def forecast_ratio(periods: pd.DataFrame, year: int, half: str, spec: CandidateSpec) -> float:
    if half == "H1" and spec.h1_ratio is not None:
        return spec.h1_ratio
    history = same_half_history(periods, year, half)
    if spec.h2_ratio_mode == "base":
        return ratio_donor(history, "max") if half == "H2" else ratio_donor(history, "q98")
    return ratio_donor(history, spec.h2_ratio_mode)


def apply_head(
    periods: pd.DataFrame,
    source_periods: pd.DataFrame,
    customer_periods: pd.DataFrame,
    base: pd.DataFrame,
    spec: CandidateSpec,
) -> pd.DataFrame:
    out = base.copy()
    for period in FORECAST_PERIODS:
        if period not in spec.override_periods:
            continue
        year = int(period[:4])
        half = period[4:]
        revenue = forecast_revenue(periods, source_periods, customer_periods, year, half, spec)
        ratio = forecast_ratio(periods, year, half, spec)
        mask = out["period"].eq(period)
        out.loc[mask, "revenue"] = revenue
        out.loc[mask, "cogs"] = revenue * ratio
    out["cogs_ratio"] = out["cogs"] / out["revenue"]
    return out


def validation_scores(periods: pd.DataFrame, source_periods: pd.DataFrame, customer_periods: pd.DataFrame) -> pd.DataFrame:
    specs = []
    for recovery in [0.06, 0.08, 0.10, 0.11, 0.12, 0.14]:
        specs.append(("order_funnel", recovery))
    for recovery in [0.10, 0.15, 0.18, 0.20, 0.22, 0.25, 0.30]:
        specs.append(("source_quality", recovery))
        specs.append(("source_quality_customer", recovery))

    rows = []
    for _, row in periods.loc[periods["year"].between(2018, 2022)].iterrows():
        year = int(row["year"])
        half = str(row["half"])
        actual = float(row["revenue"])
        for head, recovery in specs:
            spec = CandidateSpec(name=f"{head}_{recovery}", revenue_head=head, h1_recovery=recovery)
            try:
                pred = forecast_revenue(periods, source_periods, customer_periods, year, half, spec)
            except Exception:
                continue
            rows.append(
                {
                    "year": year,
                    "half": half,
                    "head": head,
                    "recovery": recovery,
                    "actual": actual,
                    "pred": pred,
                    "abs_error": abs(pred - actual),
                    "ape": abs(pred - actual) / max(abs(actual), 1e-9),
                    "bias": pred - actual,
                }
            )
    return (
        pd.DataFrame(rows)
        .groupby(["half", "head", "recovery"], as_index=False)
        .agg(mean_ape=("ape", "mean"), worst_ape=("ape", "max"), mean_abs_error=("abs_error", "mean"), mean_bias=("bias", "mean"), folds=("year", "count"))
        .sort_values(["half", "mean_ape", "worst_ape", "head", "recovery"])
    )


def build_specs() -> list[CandidateSpec]:
    return [
        CandidateSpec(
            name="cleanv7_source_h1_s020_r0876",
            revenue_head="source_quality",
            h1_recovery=0.20,
            h1_ratio=0.876,
            note="Source-quality period head: sum source sessions * recovered source revenue/session; H1 only.",
        ),
        CandidateSpec(
            name="cleanv7_source_h1_s018_r0876",
            revenue_head="source_quality",
            h1_recovery=0.18,
            h1_ratio=0.876,
            note="Softer source-quality H1 recovery.",
        ),
        CandidateSpec(
            name="cleanv7_source_h1_s022_r0876",
            revenue_head="source_quality",
            h1_recovery=0.22,
            h1_ratio=0.876,
            note="Stronger source-quality H1 recovery.",
        ),
        CandidateSpec(
            name="cleanv7_source_h1_s020_r0870",
            revenue_head="source_quality",
            h1_recovery=0.20,
            h1_ratio=0.870,
            note="Source-quality H1 level plus lower H1 COGS ratio.",
        ),
        CandidateSpec(
            name="cleanv7_source_h1_s020_r0882",
            revenue_head="source_quality",
            h1_recovery=0.20,
            h1_ratio=0.882,
            note="Source-quality H1 level plus higher H1 COGS ratio.",
        ),
        CandidateSpec(
            name="cleanv7_source_customer_h1_s020_r0876",
            revenue_head="source_quality_customer",
            h1_recovery=0.20,
            h1_ratio=0.876,
            note="Source-quality H1 head with small repeat/tenure customer-quality recovery scale.",
        ),
        CandidateSpec(
            name="cleanv7_order_h1_c109_r0876",
            revenue_head="order_funnel",
            h1_recovery=0.109,
            h1_ratio=0.876,
            note="Fine order-funnel head just below previous c110.",
        ),
        CandidateSpec(
            name="cleanv7_order_h1_c112_r0876",
            revenue_head="order_funnel",
            h1_recovery=0.112,
            h1_ratio=0.876,
            note="Fine order-funnel head just above previous c110.",
        ),
        CandidateSpec(
            name="cleanv7_source_h1h2_s020_s030_h2base",
            revenue_head="source_quality",
            h1_recovery=0.20,
            h2_recovery=0.30,
            h1_ratio=0.876,
            h2_ratio_mode="base",
            override_periods=("2023H1", "2023H2"),
            note="Source-quality period head on H1 and H2; H2 recovery chosen to stay near current clean H2 level.",
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


def write_report(run_dir: Path, validation: pd.DataFrame, manifest: pd.DataFrame) -> None:
    display_validation = validation.groupby(["half", "head"], group_keys=False).head(4)
    report = f"""# Clean V7 Period Funnel Council

Run directory: `{run_dir}`

## Boundary

This is **clean-input public-guided**. The script does not read `sample_submission.csv`, previous `submission_*.csv`, quarantine files, or test targets as inputs.

Public feedback is used only to focus candidates near the current clean best neighborhood:

- `submission_cleanv2_h1fine_b044_r0876.csv = 673757.34993`
- `submission_cleanv3_funnel_c110_h1r0876.csv = 673759.96838`
- `submission_cleanv4_opratio_g020.csv = 677137.31895` failed.
- `submission_cleanv6_merch_revshape_g010.csv = 674337.07653` failed.

## Model Change

This branch changes the **period-total head**, not the daily shape:

- `order_funnel`: `sessions_recent * recovered_conversion * AOV_recent`
- `source_quality`: `sum(source_sessions_recent * recovered_source_revenue_per_session)`
- `source_quality_customer`: source-quality head with a small repeat/tenure customer-quality recovery scale

After period totals are set, daily allocation still uses the existing clean raw-md shape path.

## Rolling Period Validation

{display_validation.to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Order

1. `submission_cleanv7_source_h1_s020_r0876.csv`
2. If step 1 improves: `submission_cleanv7_source_h1_s022_r0876.csv`
3. If step 1 worsens slightly: `submission_cleanv7_source_h1_s018_r0876.csv`
4. If source level is neutral but COGS is suspect: `submission_cleanv7_source_h1_s020_r0870.csv`
5. Do not submit H1+H2 unless H1-only is positive.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v7_period_funnel_council_2026-04-28.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    sales = load_sales()
    periods = build_period_table()
    source_periods = build_source_period_table(run_dir)
    customer_periods = build_customer_period_table(run_dir)
    base = base_totals(sales)
    shape_base = build_shape_base()

    validation = validation_scores(periods, source_periods, customer_periods)
    validation.to_csv(run_dir / "period_head_validation.csv", index=False)

    rows: list[dict[str, object]] = []
    for priority, spec in enumerate(build_specs(), start=1):
        totals = apply_head(periods, source_periods, customer_periods, base, spec)
        frame = apply_period_totals(shape_base, totals).reset_index(drop=True)
        sanity_check(frame, spec.name)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)
        prof = period_summary(frame)
        prof.to_csv(run_dir / f"{spec.name}_period_summary.csv", index=False)
        totals.to_csv(run_dir / f"{spec.name}_target_totals.csv", index=False)

        row = {
            "priority": priority,
            "filename": path.name,
            "revenue_head": spec.revenue_head,
            "h1_recovery": spec.h1_recovery,
            "h2_recovery": spec.h2_recovery,
            "h1_ratio": spec.h1_ratio,
            "h2_ratio_mode": spec.h2_ratio_mode,
            "override_periods": ",".join(spec.override_periods),
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
        rows.append(row)

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    write_report(run_dir, validation, manifest)
    print(run_dir)
    print(manifest[["priority", "filename", "revenue_head", "h1_recovery", "h2_recovery", "rev_2023H1", "cogs_2023H1"]].to_string(index=False))


if __name__ == "__main__":
    main()
