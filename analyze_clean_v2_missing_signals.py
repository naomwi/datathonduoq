from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_clean_v2_train_evidence import (
    DATASET_DIR,
    LOG_ROOT,
    NOTES_DIR,
    add_time,
    build_daily_panel,
    expand_promotions,
)


RUN_PREFIX = "clean_v2_missing_signals"


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def era_label(year: pd.Series) -> pd.Series:
    return pd.Series(
        np.select(
            [year.between(2013, 2018), year.between(2019, 2022)],
            ["pre2019_high", "recent_low"],
            default="other",
        ),
        index=year.index,
    )


def order_value_frame() -> pd.DataFrame:
    orders = pd.read_csv(DATASET_DIR / "orders.csv", parse_dates=["order_date"], dtype={"zip": str})
    items = pd.read_csv(DATASET_DIR / "order_items.csv", low_memory=False)
    products = pd.read_csv(DATASET_DIR / "products.csv")
    items = items.merge(products[["product_id", "category", "segment", "cogs"]], on="product_id", how="left")
    items["gross_item_value"] = items["quantity"] * items["unit_price"]
    items["net_item_value"] = items["gross_item_value"] - items["discount_amount"].fillna(0.0)
    items["product_cogs_value"] = items["quantity"] * items["cogs"]
    items["has_promo"] = items["promo_id"].notna() | items["promo_id_2"].notna()
    order_items = (
        items.groupby("order_id", as_index=False)
        .agg(
            units=("quantity", "sum"),
            gross_item_value=("gross_item_value", "sum"),
            net_item_value=("net_item_value", "sum"),
            product_cogs_value=("product_cogs_value", "sum"),
            discount_amount=("discount_amount", "sum"),
            promo_lines=("has_promo", "sum"),
            item_lines=("product_id", "count"),
        )
    )
    out = orders.merge(order_items, on="order_id", how="left")
    out = add_time(out, "order_date")
    out["era"] = era_label(out["year"])
    out["aov"] = out["net_item_value"] / out["order_id"].notna().astype(int).replace(0, np.nan)
    out["promo_line_share_order"] = out["promo_lines"] / out["item_lines"].replace(0, np.nan)
    return out.loc[out["year"].between(2013, 2022)].copy()


def share_shift(frame: pd.DataFrame, dim: str, value_col: str = "net_item_value") -> pd.DataFrame:
    base = frame.loc[frame["era"].ne("other")].copy()
    base[dim] = base[dim].fillna("missing").astype(str)
    grouped = (
        base.groupby(["year", "half", "era", dim], as_index=False)
        .agg(orders=("order_id", "nunique"), value=(value_col, "sum"), units=("units", "sum"))
    )
    totals = (
        grouped.groupby(["year", "half"], as_index=False)
        .agg(total_orders=("orders", "sum"), total_value=("value", "sum"), total_units=("units", "sum"))
    )
    grouped = grouped.merge(totals, on=["year", "half"], how="left")
    grouped["order_share"] = grouped["orders"] / grouped["total_orders"].replace(0, np.nan)
    grouped["value_share"] = grouped["value"] / grouped["total_value"].replace(0, np.nan)
    grouped["unit_share"] = grouped["units"] / grouped["total_units"].replace(0, np.nan)
    grouped["aov"] = grouped["value"] / grouped["orders"].replace(0, np.nan)
    era = (
        grouped.groupby(["half", "era", dim], as_index=False)
        .agg(order_share=("order_share", "mean"), value_share=("value_share", "mean"), unit_share=("unit_share", "mean"), aov=("aov", "mean"))
    )
    wide = era.pivot(index=["half", dim], columns="era", values=["order_share", "value_share", "unit_share", "aov"]).reset_index()
    wide.columns = [c if isinstance(c, str) else "_".join([x for x in c if x]) for c in wide.columns]
    wide["dimension"] = dim
    for metric in ["order_share", "value_share", "unit_share", "aov"]:
        low = f"{metric}_recent_low"
        high = f"{metric}_pre2019_high"
        if low in wide.columns and high in wide.columns:
            wide[f"{metric}_delta_recent_minus_pre"] = wide[low] - wide[high]
            wide[f"{metric}_ratio_recent_over_pre"] = wide[low] / wide[high].replace(0, np.nan)
    return wide.sort_values("value_share_delta_recent_minus_pre", key=lambda s: s.abs(), ascending=False)


def channel_device_geo_shifts(order_values: pd.DataFrame) -> dict[str, pd.DataFrame]:
    geography = pd.read_csv(DATASET_DIR / "geography.csv", dtype={"zip": str})
    customers = pd.read_csv(DATASET_DIR / "customers.csv", parse_dates=["signup_date"], dtype={"zip": str})
    enriched = order_values.merge(geography[["zip", "region", "district"]], on="zip", how="left")
    enriched = enriched.merge(customers[["customer_id", "gender", "age_group", "acquisition_channel"]], on="customer_id", how="left")
    outputs = {}
    for dim in [
        "order_source",
        "device_type",
        "payment_method",
        "region",
        "district",
        "gender",
        "age_group",
        "acquisition_channel",
    ]:
        outputs[dim] = share_shift(enriched, dim)
    return outputs


def payment_installment_shift(order_values: pd.DataFrame) -> pd.DataFrame:
    payments = pd.read_csv(DATASET_DIR / "payments.csv")
    pay = payments.groupby("order_id", as_index=False).agg(payment_value=("payment_value", "sum"), installments=("installments", "mean"))
    joined = order_values.merge(pay, on="order_id", how="left")
    joined["installment_bin"] = pd.cut(
        joined["installments"].fillna(0),
        bins=[-0.1, 1, 3, 6, np.inf],
        labels=["1", "2-3", "4-6", "7+"],
    ).astype(str)
    return share_shift(joined, "installment_bin", value_col="payment_value")


def inventory_shift() -> pd.DataFrame:
    inv = pd.read_csv(DATASET_DIR / "inventory.csv", parse_dates=["snapshot_date"])
    inv = add_time(inv, "snapshot_date")
    inv["era"] = era_label(inv["year"])
    grouped = (
        inv.loc[inv["year"].between(2013, 2022) & inv["era"].ne("other")]
        .groupby(["year", "half", "era", "category", "segment"], as_index=False)
        .agg(
            stockout_flag=("stockout_flag", "mean"),
            fill_rate=("fill_rate", "mean"),
            days_of_supply=("days_of_supply", "mean"),
            sell_through_rate=("sell_through_rate", "mean"),
            stock_on_hand=("stock_on_hand", "sum"),
            units_sold=("units_sold", "sum"),
        )
    )
    era = (
        grouped.groupby(["half", "era", "category", "segment"], as_index=False)
        .agg(
            stockout_flag=("stockout_flag", "mean"),
            fill_rate=("fill_rate", "mean"),
            days_of_supply=("days_of_supply", "mean"),
            sell_through_rate=("sell_through_rate", "mean"),
            stock_on_hand=("stock_on_hand", "mean"),
            units_sold=("units_sold", "mean"),
        )
    )
    wide = era.pivot(index=["half", "category", "segment"], columns="era").reset_index()
    wide.columns = [c if isinstance(c, str) else "_".join([x for x in c if x]) for c in wide.columns]
    for metric in ["stockout_flag", "fill_rate", "days_of_supply", "sell_through_rate", "stock_on_hand", "units_sold"]:
        low = f"{metric}_recent_low"
        high = f"{metric}_pre2019_high"
        if low in wide.columns and high in wide.columns:
            wide[f"{metric}_delta_recent_minus_pre"] = wide[low] - wide[high]
    return wide.sort_values("stockout_flag_delta_recent_minus_pre", key=lambda s: s.abs(), ascending=False)


def recurring_promo_priors() -> tuple[pd.DataFrame, pd.DataFrame]:
    promos = pd.read_csv(DATASET_DIR / "promotions.csv", parse_dates=["start_date", "end_date"])
    daily = expand_promotions(promos)
    daily = add_time(daily, "Date")
    daily["day"] = daily["Date"].dt.day
    active_years = daily["year"].nunique()
    day_prior = (
        daily.groupby(["month", "day"], as_index=False)
        .agg(
            active_years=("year", "nunique"),
            avg_promo_count=("active_promo_count", "mean"),
            avg_discount_max=("promo_discount_max", "mean"),
            max_discount=("promo_discount_max", "max"),
            stackable_days=("stackable_promos", lambda s: int((s > 0).sum())),
        )
    )
    day_prior["active_year_share"] = day_prior["active_years"] / active_years
    day_prior["month_day"] = day_prior["month"].astype(str).str.zfill(2) + "-" + day_prior["day"].astype(str).str.zfill(2)
    day_prior = day_prior.sort_values(["active_year_share", "avg_discount_max", "max_discount"], ascending=False)
    month_prior = (
        daily.groupby(["year", "month"], as_index=False)
        .agg(active_days=("Date", "nunique"), avg_discount_max=("promo_discount_max", "mean"), max_discount=("promo_discount_max", "max"))
        .groupby("month", as_index=False)
        .agg(
            years_with_promo=("year", "nunique"),
            active_days_mean=("active_days", "mean"),
            active_days_std=("active_days", "std"),
            avg_discount_max=("avg_discount_max", "mean"),
            max_discount=("max_discount", "max"),
        )
        .sort_values(["years_with_promo", "active_days_mean", "avg_discount_max"], ascending=False)
    )
    month_prior["year_share"] = month_prior["years_with_promo"] / active_years
    return day_prior, month_prior


def period_factor_bridge(daily: pd.DataFrame) -> pd.DataFrame:
    period = (
        daily.loc[daily["year"].between(2013, 2022)]
        .groupby(["year", "half"], as_index=False)
        .agg(
            revenue=("Revenue", "sum"),
            cogs=("COGS", "sum"),
            orders=("orders", "sum"),
            sessions=("sessions", "sum"),
            units=("units", "sum"),
            discount_amount=("discount_amount", "sum"),
            gross_item_value=("gross_item_value", "sum"),
        )
    )
    period["era"] = era_label(period["year"])
    period["conversion"] = period["orders"] / period["sessions"].replace(0, np.nan)
    period["aov"] = period["revenue"] / period["orders"].replace(0, np.nan)
    period["units_per_order"] = period["units"] / period["orders"].replace(0, np.nan)
    period["revenue_per_unit"] = period["revenue"] / period["units"].replace(0, np.nan)
    period["discount_rate"] = period["discount_amount"] / period["gross_item_value"].replace(0, np.nan)
    cols = ["revenue", "cogs", "orders", "sessions", "conversion", "aov", "units_per_order", "revenue_per_unit", "discount_rate"]
    era = period.loc[period["era"].ne("other")].groupby(["half", "era"], as_index=False)[cols].mean()
    wide = era.pivot(index="half", columns="era", values=cols).reset_index()
    wide.columns = [c if isinstance(c, str) else "_".join([x for x in c if x]) for c in wide.columns]
    for col in cols:
        wide[f"{col}_ratio_recent_over_pre"] = wide[f"{col}_recent_low"] / wide[f"{col}_pre2019_high"].replace(0, np.nan)
        wide[f"{col}_gap_to_pre_pct"] = (wide[f"{col}_pre2019_high"] - wide[f"{col}_recent_low"]) / wide[f"{col}_recent_low"].replace(0, np.nan)
    return wide


def extreme_day_diagnostics(daily: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "Date",
        "year",
        "month",
        "half",
        "Revenue",
        "COGS",
        "cogs_ratio",
        "orders",
        "sessions",
        "conversion",
        "aov",
        "active_promo_count",
        "promo_discount_max",
        "promo_line_share",
        "discount_rate",
        "fill_rate",
        "stockout_flag",
    ]
    frame = daily.loc[daily["year"].between(2013, 2022), cols].copy()
    top_revenue = frame.nlargest(40, "Revenue").assign(reason="top_revenue")
    high_ratio = frame.nlargest(40, "cogs_ratio").assign(reason="high_cogs_ratio")
    low_conversion = frame.nsmallest(40, "conversion").assign(reason="low_conversion")
    return pd.concat([top_revenue, high_ratio, low_conversion], ignore_index=True).drop_duplicates(["Date", "reason"])


def write_report(
    run_dir: Path,
    factor_bridge: pd.DataFrame,
    channel_source: pd.DataFrame,
    device_shift: pd.DataFrame,
    payment_shift: pd.DataFrame,
    region_shift: pd.DataFrame,
    inventory: pd.DataFrame,
    promo_day: pd.DataFrame,
    promo_month: pd.DataFrame,
    extreme_days: pd.DataFrame,
) -> None:
    channel_top = channel_source.head(12)
    device_top = device_shift.head(12)
    payment_top = payment_shift.head(12)
    region_top = region_shift.head(12)
    inventory_top = inventory.head(12)
    promo_day_top = promo_day.head(20)
    promo_month_top = promo_month.head(12)
    extreme_top = extreme_days.head(25)
    report = f"""# Clean V2 Missing Signals EDA - 2026-04-24

Run directory: `{run_dir}`

## Boundary

This pass uses provided train/source data only. It does not read `sample_submission.csv`, previous submissions, public scores, or test targets.

## New Read

1. The clean path should model a business funnel: `sessions -> conversion -> orders -> AOV -> Revenue`, then a separate promo-sensitive `COGS / Revenue` ratio.
2. Mix shift is real, but strongest in product/segment and region; source/device/channel shares are mostly stable, so AOV recovery is not just a channel-mix artifact.
3. Promo history is not future-known, but recurring promo intensity by month-day is a legal train-derived prior.
4. Inventory/returns/reviews are diagnostic, not direct future inputs; they can explain why recent-low years may understate recovery.
5. A cleaner model improvement should come from period-aware priors and caps, not another generic regressor.

## Period Factor Bridge

{factor_bridge.to_markdown(index=False)}

## Order Source Shift

{channel_top.to_markdown(index=False)}

## Device Shift

{device_top.to_markdown(index=False)}

## Payment Installment Shift

{payment_top.to_markdown(index=False)}

## Region Shift

{region_top.to_markdown(index=False)}

## Inventory Shift

{inventory_top.to_markdown(index=False)}

## Recurring Promo Day Priors

{promo_day_top.to_markdown(index=False)}

## Recurring Promo Month Priors

{promo_month_top.to_markdown(index=False)}

## Extreme Day Diagnostics

{extreme_top.to_markdown(index=False)}

## Model Implications

1. Add a train-derived H1 regime recovery prior through `conversion` and `AOV`, not a raw Revenue multiplier.
2. Keep H2 Revenue shrunk, especially around unstable August-like shape regions.
3. Build `COGS / Revenue` as a separate ratio target using month, half, promo-prior intensity, discount-prior intensity, and AOV/revenue-per-unit priors.
4. Add source/device/payment/channel only as low-weight diagnostics. They are stable enough to explain AOV recovery, but not strong enough to be the main breakthrough feature.
5. Add product/category/segment mix priors only as train-derived long-run regime priors; do not use future item mix.
6. Treat inventory, returns, reviews, and shipments as explanation/validation diagnostics unless a future operational plan is explicitly provided.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v2_missing_signals_eda_2026-04-24.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    daily = build_daily_panel()
    order_values = order_value_frame()
    shifts = channel_device_geo_shifts(order_values)
    payment = payment_installment_shift(order_values)
    inventory = inventory_shift()
    promo_day, promo_month = recurring_promo_priors()
    factor_bridge = period_factor_bridge(daily)
    extremes = extreme_day_diagnostics(daily)

    factor_bridge.to_csv(run_dir / "period_factor_bridge.csv", index=False)
    payment.to_csv(run_dir / "payment_installment_shift.csv", index=False)
    inventory.to_csv(run_dir / "inventory_shift.csv", index=False)
    promo_day.to_csv(run_dir / "recurring_promo_day_priors.csv", index=False)
    promo_month.to_csv(run_dir / "recurring_promo_month_priors.csv", index=False)
    extremes.to_csv(run_dir / "extreme_day_diagnostics.csv", index=False)
    for name, table in shifts.items():
        table.to_csv(run_dir / f"{name}_shift.csv", index=False)

    write_report(
        run_dir=run_dir,
        factor_bridge=factor_bridge,
        channel_source=shifts["order_source"],
        device_shift=shifts["device_type"],
        payment_shift=payment,
        region_shift=shifts["region"],
        inventory=inventory,
        promo_day=promo_day,
        promo_month=promo_month,
        extreme_days=extremes,
    )
    print(run_dir)


if __name__ == "__main__":
    main()
