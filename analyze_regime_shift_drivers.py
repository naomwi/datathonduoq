from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR


RUN_PREFIX = "regime_shift_drivers"


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def add_time(frame: pd.DataFrame, date_col: str = "Date") -> pd.DataFrame:
    out = frame.copy()
    out[date_col] = pd.to_datetime(out[date_col])
    out["year"] = out[date_col].dt.year
    out["month"] = out[date_col].dt.month
    out["half"] = np.where(out["month"].le(6), "H1", "H2")
    out["period"] = out["year"].astype(str) + out["half"]
    return out


def build_daily_drivers() -> pd.DataFrame:
    sales = add_time(pd.read_csv(DATASET_DIR / "sales.csv", parse_dates=["Date"]))

    orders = pd.read_csv(DATASET_DIR / "orders.csv", parse_dates=["order_date"])
    order_daily = (
        orders.groupby("order_date", as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            customers=("customer_id", "nunique"),
            delivered_orders=("order_status", lambda s: int(s.eq("delivered").sum())),
            returned_status_orders=("order_status", lambda s: int(s.eq("returned").sum())),
            mobile_orders=("device_type", lambda s: int(s.eq("mobile").sum())),
            paid_search_orders=("order_source", lambda s: int(s.eq("paid_search").sum())),
        )
        .rename(columns={"order_date": "Date"})
    )

    items = pd.read_csv(DATASET_DIR / "order_items.csv")
    items["gross_item_value"] = items["quantity"] * items["unit_price"]
    items["net_item_value"] = items["gross_item_value"] - items["discount_amount"].fillna(0.0)
    items["has_promo"] = items["promo_id"].notna() | items["promo_id_2"].notna()
    item_order = (
        items.groupby("order_id", as_index=False)
        .agg(
            lines=("product_id", "count"),
            units=("quantity", "sum"),
            gross_item_value=("gross_item_value", "sum"),
            net_item_value=("net_item_value", "sum"),
            discount_amount=("discount_amount", "sum"),
            promo_lines=("has_promo", "sum"),
        )
    )
    order_items = orders[["order_id", "order_date"]].merge(item_order, on="order_id", how="left")
    item_daily = (
        order_items.groupby("order_date", as_index=False)
        .agg(
            item_lines=("lines", "sum"),
            units=("units", "sum"),
            gross_item_value=("gross_item_value", "sum"),
            net_item_value=("net_item_value", "sum"),
            discount_amount=("discount_amount", "sum"),
            promo_lines=("promo_lines", "sum"),
        )
        .rename(columns={"order_date": "Date"})
    )

    payments = pd.read_csv(DATASET_DIR / "payments.csv")
    pay_order = payments.groupby("order_id", as_index=False).agg(payment_value=("payment_value", "sum"))
    pay_daily = (
        orders[["order_id", "order_date"]]
        .merge(pay_order, on="order_id", how="left")
        .groupby("order_date", as_index=False)
        .agg(payment_value=("payment_value", "sum"))
        .rename(columns={"order_date": "Date"})
    )

    traffic = pd.read_csv(DATASET_DIR / "web_traffic.csv", parse_dates=["date"])
    traffic_daily = (
        traffic.groupby("date", as_index=False)
        .agg(
            sessions=("sessions", "sum"),
            unique_visitors=("unique_visitors", "sum"),
            page_views=("page_views", "sum"),
            bounce_rate=("bounce_rate", lambda s: float(np.average(s, weights=traffic.loc[s.index, "sessions"]))),
            avg_session_duration_sec=(
                "avg_session_duration_sec",
                lambda s: float(np.average(s, weights=traffic.loc[s.index, "sessions"])),
            ),
        )
        .rename(columns={"date": "Date"})
    )

    returns = pd.read_csv(DATASET_DIR / "returns.csv", parse_dates=["return_date"])
    returns_daily = (
        returns.groupby("return_date", as_index=False)
        .agg(
            returns=("return_id", "count"),
            return_quantity=("return_quantity", "sum"),
            refund_amount=("refund_amount", "sum"),
        )
        .rename(columns={"return_date": "Date"})
    )

    inv = pd.read_csv(DATASET_DIR / "inventory.csv", parse_dates=["snapshot_date"])
    inv_daily = (
        inv.groupby("snapshot_date", as_index=False)
        .agg(
            stock_on_hand=("stock_on_hand", "sum"),
            units_received=("units_received", "sum"),
            inv_units_sold=("units_sold", "sum"),
            stockout_days=("stockout_days", "sum"),
            fill_rate=("fill_rate", "mean"),
            stockout_flag=("stockout_flag", "mean"),
            days_of_supply=("days_of_supply", "mean"),
        )
        .rename(columns={"snapshot_date": "Date"})
    )

    promos = pd.read_csv(DATASET_DIR / "promotions.csv", parse_dates=["start_date", "end_date"])
    promo_rows = []
    for _, row in promos.iterrows():
        for date in pd.date_range(row["start_date"], row["end_date"], freq="D"):
            promo_rows.append(
                {
                    "Date": date,
                    "active_promo_count": 1,
                    "promo_discount_sum": float(row["discount_value"]),
                    "promo_discount_max": float(row["discount_value"]),
                }
            )
    promo_daily = pd.DataFrame(promo_rows)
    promo_daily = (
        promo_daily.groupby("Date", as_index=False)
        .agg(
            active_promo_count=("active_promo_count", "sum"),
            promo_discount_sum=("promo_discount_sum", "sum"),
            promo_discount_max=("promo_discount_max", "max"),
        )
        if not promo_daily.empty
        else pd.DataFrame(columns=["Date", "active_promo_count", "promo_discount_sum", "promo_discount_max"])
    )

    daily = sales[["Date", "year", "month", "half", "period", "Revenue", "COGS"]].copy()
    for part in [order_daily, item_daily, pay_daily, traffic_daily, returns_daily, inv_daily, promo_daily]:
        daily = daily.merge(part, on="Date", how="left")

    fill_zero = [
        "orders",
        "customers",
        "delivered_orders",
        "returned_status_orders",
        "mobile_orders",
        "paid_search_orders",
        "item_lines",
        "units",
        "gross_item_value",
        "net_item_value",
        "discount_amount",
        "promo_lines",
        "payment_value",
        "sessions",
        "unique_visitors",
        "page_views",
        "returns",
        "return_quantity",
        "refund_amount",
        "active_promo_count",
        "promo_discount_sum",
        "promo_discount_max",
    ]
    for col in fill_zero:
        if col in daily.columns:
            daily[col] = daily[col].fillna(0.0)

    daily["aov_revenue"] = daily["Revenue"] / daily["orders"].replace(0, np.nan)
    daily["units_per_order"] = daily["units"] / daily["orders"].replace(0, np.nan)
    daily["revenue_per_unit"] = daily["Revenue"] / daily["units"].replace(0, np.nan)
    daily["cogs_ratio"] = daily["COGS"] / daily["Revenue"].replace(0, np.nan)
    daily["discount_rate"] = daily["discount_amount"] / daily["gross_item_value"].replace(0, np.nan)
    daily["promo_line_share"] = daily["promo_lines"] / daily["item_lines"].replace(0, np.nan)
    daily["conversion_orders_per_session"] = daily["orders"] / daily["sessions"].replace(0, np.nan)
    daily["return_refund_rate"] = daily["refund_amount"] / daily["Revenue"].replace(0, np.nan)
    daily["mobile_order_share"] = daily["mobile_orders"] / daily["orders"].replace(0, np.nan)
    daily["paid_search_order_share"] = daily["paid_search_orders"] / daily["orders"].replace(0, np.nan)
    daily["delivered_rate"] = daily["delivered_orders"] / daily["orders"].replace(0, np.nan)
    daily["returned_status_rate"] = daily["returned_status_orders"] / daily["orders"].replace(0, np.nan)
    return daily


def summarize_periods(daily: pd.DataFrame) -> pd.DataFrame:
    return (
        daily.groupby(["year", "half"], as_index=False)
        .agg(
            days=("Date", "count"),
            revenue=("Revenue", "sum"),
            cogs=("COGS", "sum"),
            orders=("orders", "sum"),
            customers=("customers", "sum"),
            units=("units", "sum"),
            sessions=("sessions", "sum"),
            page_views=("page_views", "sum"),
            discount_amount=("discount_amount", "sum"),
            gross_item_value=("gross_item_value", "sum"),
            promo_lines=("promo_lines", "sum"),
            item_lines=("item_lines", "sum"),
            refund_amount=("refund_amount", "sum"),
            active_promo_days=("active_promo_count", lambda s: int((s > 0).sum())),
            avg_active_promo_count=("active_promo_count", "mean"),
            avg_promo_discount_max=("promo_discount_max", "mean"),
            avg_fill_rate=("fill_rate", "mean"),
            avg_stockout_flag=("stockout_flag", "mean"),
            stockout_days=("stockout_days", "sum"),
        )
        .assign(
            cogs_ratio=lambda d: d["cogs"] / d["revenue"],
            aov=lambda d: d["revenue"] / d["orders"].replace(0, np.nan),
            orders_per_day=lambda d: d["orders"] / d["days"],
            revenue_per_order=lambda d: d["revenue"] / d["orders"].replace(0, np.nan),
            units_per_order=lambda d: d["units"] / d["orders"].replace(0, np.nan),
            revenue_per_unit=lambda d: d["revenue"] / d["units"].replace(0, np.nan),
            conversion=lambda d: d["orders"] / d["sessions"].replace(0, np.nan),
            discount_rate=lambda d: d["discount_amount"] / d["gross_item_value"].replace(0, np.nan),
            promo_line_share=lambda d: d["promo_lines"] / d["item_lines"].replace(0, np.nan),
            refund_rate=lambda d: d["refund_amount"] / d["revenue"],
        )
    )


def era_summary(periods: pd.DataFrame) -> pd.DataFrame:
    p = periods.copy()
    p["era"] = np.select(
        [
            p["year"].between(2013, 2018),
            p["year"].between(2019, 2022),
        ],
        ["pre2019_high", "recent_low"],
        default="other",
    )
    return (
        p.loc[p["era"].ne("other")]
        .groupby(["era", "half"], as_index=False)
        .agg(
            revenue=("revenue", "mean"),
            cogs=("cogs", "mean"),
            orders=("orders", "mean"),
            sessions=("sessions", "mean"),
            aov=("aov", "mean"),
            orders_per_day=("orders_per_day", "mean"),
            conversion=("conversion", "mean"),
            revenue_per_unit=("revenue_per_unit", "mean"),
            units_per_order=("units_per_order", "mean"),
            cogs_ratio=("cogs_ratio", "mean"),
            discount_rate=("discount_rate", "mean"),
            promo_line_share=("promo_line_share", "mean"),
            refund_rate=("refund_rate", "mean"),
            avg_active_promo_count=("avg_active_promo_count", "mean"),
            avg_fill_rate=("avg_fill_rate", "mean"),
            avg_stockout_flag=("avg_stockout_flag", "mean"),
        )
    )


def prediction_vs_train_summary(periods: pd.DataFrame) -> pd.DataFrame:
    """Compare selected prediction files to train half-year regimes.

    These files are not used as modeling features here. The comparison is a
    diagnostic: it shows where public-inferred candidates sit versus train
    history, so the report can separate clean train evidence from leaderboard
    inference.
    """
    candidates = [
        ("strictlegal_tv", DATASET_DIR / "submission_strictlegal_tv_selected.csv", "train_validated"),
        (
            "sourceclean_pubcal",
            DATASET_DIR / "submission_reasonable_final_sourceclean_pubcal.csv",
            "source_clean_public_calibrated",
        ),
        (
            "public_inferred_current_best",
            DATASET_DIR / "submission_qbb60v4_level_rev2024h1_up030.csv",
            "quarantine_public_inferred",
        ),
    ]

    train_ref = periods.loc[periods["year"].between(2013, 2022), ["year", "half", "revenue", "cogs"]].copy()
    era_ref = era_summary(periods).set_index(["era", "half"])

    rows = []
    for label, path, status in candidates:
        if not path.exists():
            continue
        pred = add_time(pd.read_csv(path, parse_dates=["Date"]))
        pred_periods = (
            pred.groupby(["year", "half"], as_index=False)
            .agg(days=("Date", "count"), revenue=("Revenue", "sum"), cogs=("COGS", "sum"))
            .assign(cogs_ratio=lambda d: d["cogs"] / d["revenue"])
        )
        for row in pred_periods.itertuples(index=False):
            train_half = train_ref.loc[train_ref["half"].eq(row.half)]
            pre_revenue = float(era_ref.loc[("pre2019_high", row.half), "revenue"])
            recent_revenue = float(era_ref.loc[("recent_low", row.half), "revenue"])
            pre_cogs = float(era_ref.loc[("pre2019_high", row.half), "cogs"])
            recent_cogs = float(era_ref.loc[("recent_low", row.half), "cogs"])
            rows.append(
                {
                    "candidate": label,
                    "status": status,
                    "period": f"{int(row.year)}{row.half}",
                    "days": row.days,
                    "revenue": row.revenue,
                    "cogs": row.cogs,
                    "cogs_ratio": row.cogs_ratio,
                    "revenue_vs_recent_low_avg": row.revenue / recent_revenue,
                    "revenue_vs_pre2019_high_avg": row.revenue / pre_revenue,
                    "cogs_vs_recent_low_avg": row.cogs / recent_cogs,
                    "cogs_vs_pre2019_high_avg": row.cogs / pre_cogs,
                    "train_revenue_rank_from_low": int((train_half["revenue"] < row.revenue).sum() + 1),
                    "train_revenue_period_count_plus_candidate": len(train_half) + 1,
                    "train_max_revenue_same_half": float(train_half["revenue"].max()),
                    "train_cogs_rank_from_low": int((train_half["cogs"] < row.cogs).sum() + 1),
                    "train_max_cogs_same_half": float(train_half["cogs"].max()),
                }
            )
    return pd.DataFrame(rows)


def seasonality_shape_summary(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    work = daily.loc[daily["year"].between(2013, 2022), ["Date", "year", "month", "half", "Revenue"]].copy()
    work = work.loc[~((work["Date"].dt.month == 2) & (work["Date"].dt.day == 29))]
    work["month_day"] = work["Date"].dt.strftime("%m-%d")
    for half in ["H1", "H2"]:
        pivot = work.loc[work["half"].eq(half)].pivot(index="month_day", columns="year", values="Revenue")
        pivot = pivot / pivot.mean(axis=0)
        corr = pivot.corr(min_periods=120)
        values = corr.where(np.triu(np.ones(corr.shape), 1).astype(bool)).stack()
        rows.append(
            {
                "half": half,
                "pairwise_shape_corr_mean": float(values.mean()),
                "pairwise_shape_corr_median": float(values.median()),
                "pairwise_shape_corr_min": float(values.min()),
                "pairwise_shape_corr_max": float(values.max()),
            }
        )
    return pd.DataFrame(rows)


def write_report(run_dir: Path, daily: pd.DataFrame, periods: pd.DataFrame, era: pd.DataFrame) -> None:
    annual = (
        daily.groupby("year", as_index=False)
        .agg(
            days=("Date", "count"),
            revenue=("Revenue", "sum"),
            cogs=("COGS", "sum"),
            orders=("orders", "sum"),
            sessions=("sessions", "sum"),
            units=("units", "sum"),
            discount_amount=("discount_amount", "sum"),
            gross_item_value=("gross_item_value", "sum"),
            refund_amount=("refund_amount", "sum"),
        )
        .assign(
            cogs_ratio=lambda d: d["cogs"] / d["revenue"],
            orders_per_day=lambda d: d["orders"] / d["days"],
            aov=lambda d: d["revenue"] / d["orders"],
            conversion=lambda d: d["orders"] / d["sessions"],
            discount_rate=lambda d: d["discount_amount"] / d["gross_item_value"],
            refund_rate=lambda d: d["refund_amount"] / d["revenue"],
        )
    )
    annual.to_csv(run_dir / "annual_driver_summary.csv", index=False)
    periods.to_csv(run_dir / "halfyear_driver_summary.csv", index=False)
    era.to_csv(run_dir / "era_driver_summary.csv", index=False)
    daily.to_csv(run_dir / "daily_driver_panel.csv", index=False)

    corr_cols = [
        "Revenue",
        "orders",
        "sessions",
        "units",
        "aov_revenue",
        "revenue_per_unit",
        "conversion_orders_per_session",
        "discount_rate",
        "promo_line_share",
        "cogs_ratio",
        "return_refund_rate",
    ]
    corr = daily.loc[daily["year"].between(2013, 2022), corr_cols].corr(numeric_only=True)
    corr.to_csv(run_dir / "daily_driver_correlation.csv")

    def pct_delta(metric: str, half: str) -> float:
        sub = era.loc[era["half"].eq(half)].set_index("era")
        return float(sub.loc["recent_low", metric] / sub.loc["pre2019_high", metric] - 1.0)

    bullets = []
    for half in ["H1", "H2"]:
        bullets.append(
            {
                "half": half,
                "revenue_delta_recent_vs_pre2019": pct_delta("revenue", half),
                "orders_delta": pct_delta("orders", half),
                "sessions_delta": pct_delta("sessions", half),
                "aov_delta": pct_delta("aov", half),
                "conversion_delta": pct_delta("conversion", half),
                "cogs_ratio_delta": pct_delta("cogs_ratio", half),
            }
        )
    deltas = pd.DataFrame(bullets)
    deltas.to_csv(run_dir / "era_percent_deltas.csv", index=False)

    pred_compare = prediction_vs_train_summary(periods)
    pred_compare.to_csv(run_dir / "prediction_vs_train_halfyear.csv", index=False)

    shape_summary = seasonality_shape_summary(daily)
    shape_summary.to_csv(run_dir / "seasonality_shape_summary.csv", index=False)

    pred_section = (
        pred_compare.to_markdown(index=False)
        if not pred_compare.empty
        else "No selected prediction files were found for comparison."
    )

    report = f"""# Regime Shift Driver Analysis

Run directory: `{run_dir}`

## Key Finding

The train data has a strong structural break starting in `2019`, before the COVID period. So the low recent regime is not purely a 2020 COVID artifact.

Annual driver summary:

{annual.to_markdown(index=False)}

Half-year percent deltas, recent `2019-2022` versus pre-2019 high regime `2013-2018`:

{deltas.to_markdown(index=False)}

Era summary:

{era.to_markdown(index=False)}

Seasonality shape stability:

{shape_summary.to_markdown(index=False)}

Prediction/public-inferred half-year position versus train history:

{pred_section}

## Interpretation

1. Revenue level is strongly seasonal: `H1` is consistently higher than `H2`, with the strongest months around April-June.
2. The major level drop is mostly a demand/order-volume regime shift, not a pure daily-seasonality issue.
3. The break starts in `2019`, so blaming only COVID is too simple. COVID may sustain the low regime in `2020-2021`, but the series already fell sharply in `2019`.
4. Public-best submissions imply `2023-2024` recover above the recent low regime, especially `2024H1`, but not above the historical `2014-2018` high regime.
5. `H2` shape is less reliable than `H1`; this matches the black-box finding that `2023H2` should be heavily shrunk.
6. COGS ratio is regime-sensitive, especially in `H2`, so COGS should be modeled as a ratio/regime layer rather than copied from Revenue shape.

## Modeling Insight

The missing public signal is probably a **regime recovery level**:

```text
2013-2018: high demand regime
2019-2022: low demand regime / structural break
2023-2024 public: partial recovery toward old high regime
```

So a clean model should not extrapolate only from `2020-2022`. It should include a latent regime/scenario component that can blend recent low regime with pre-2019 high-regime seasonal totals.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "regime_shift_driver_analysis_2026-04-23.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    daily = build_daily_drivers()
    periods = summarize_periods(daily)
    era = era_summary(periods)
    write_report(run_dir, daily, periods, era)
    print(run_dir)


if __name__ == "__main__":
    main()
