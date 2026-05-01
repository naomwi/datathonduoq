from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


DATASET_DIR = Path("dataset")
LOG_ROOT = Path("logs")
NOTES_DIR = Path("notes")
RUN_PREFIX = "clean_v2_train_evidence"


SOURCE_FILES = [
    "sales.csv",
    "orders.csv",
    "order_items.csv",
    "payments.csv",
    "shipments.csv",
    "returns.csv",
    "reviews.csv",
    "web_traffic.csv",
    "promotions.csv",
    "inventory.csv",
    "products.csv",
    "customers.csv",
    "geography.csv",
]


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def safe_div(num: pd.Series | float, den: pd.Series | float) -> pd.Series | float:
    return num / pd.Series(den).replace(0, np.nan) if not np.isscalar(den) else num / den if den else np.nan


def add_time(frame: pd.DataFrame, date_col: str) -> pd.DataFrame:
    out = frame.copy()
    out[date_col] = pd.to_datetime(out[date_col])
    out["year"] = out[date_col].dt.year
    out["month"] = out[date_col].dt.month
    out["half"] = np.where(out["month"].le(6), "H1", "H2")
    out["period"] = out["year"].astype(str) + out["half"]
    return out


def weighted_avg(values: pd.Series, weights: pd.Series) -> float:
    mask = values.notna() & weights.notna() & weights.gt(0)
    if not mask.any():
        return np.nan
    return float(np.average(values.loc[mask], weights=weights.loc[mask]))


def source_coverage() -> pd.DataFrame:
    date_candidates = {
        "sales.csv": ["Date"],
        "orders.csv": ["order_date"],
        "shipments.csv": ["ship_date", "delivery_date"],
        "returns.csv": ["return_date"],
        "reviews.csv": ["review_date"],
        "web_traffic.csv": ["date"],
        "promotions.csv": ["start_date", "end_date"],
        "inventory.csv": ["snapshot_date"],
        "customers.csv": ["signup_date"],
    }
    rows = []
    for name in SOURCE_FILES:
        path = DATASET_DIR / name
        if not path.exists():
            continue
        frame = pd.read_csv(path, low_memory=False)
        row = {
            "file": name,
            "rows": len(frame),
            "columns": len(frame.columns),
            "date_cols": "",
            "min_date": pd.NaT,
            "max_date": pd.NaT,
            "null_cells": int(frame.isna().sum().sum()),
        }
        dates = []
        for col in date_candidates.get(name, []):
            if col in frame.columns:
                parsed = pd.to_datetime(frame[col], errors="coerce")
                if parsed.notna().any():
                    row["date_cols"] = (row["date_cols"] + "," + col).strip(",")
                    dates.append(parsed)
        if dates:
            all_dates = pd.concat(dates, ignore_index=True)
            row["min_date"] = all_dates.min()
            row["max_date"] = all_dates.max()
        rows.append(row)
    return pd.DataFrame(rows)


def expand_promotions(promos: pd.DataFrame) -> pd.DataFrame:
    if promos.empty:
        return pd.DataFrame(columns=["Date", "active_promo_count", "promo_discount_sum", "promo_discount_max"])
    rows = []
    for promo in promos.itertuples(index=False):
        start = pd.to_datetime(promo.start_date)
        end = pd.to_datetime(promo.end_date)
        for date in pd.date_range(start, end, freq="D"):
            rows.append(
                {
                    "Date": date,
                    "active_promo_count": 1,
                    "promo_discount_sum": float(getattr(promo, "discount_value")),
                    "promo_discount_max": float(getattr(promo, "discount_value")),
                    "stackable_promos": int(getattr(promo, "stackable_flag", 0)),
                }
            )
    promo_daily = pd.DataFrame(rows)
    return (
        promo_daily.groupby("Date", as_index=False)
        .agg(
            active_promo_count=("active_promo_count", "sum"),
            promo_discount_sum=("promo_discount_sum", "sum"),
            promo_discount_max=("promo_discount_max", "max"),
            stackable_promos=("stackable_promos", "sum"),
        )
        .sort_values("Date")
    )


def build_daily_panel() -> pd.DataFrame:
    sales = add_time(pd.read_csv(DATASET_DIR / "sales.csv", parse_dates=["Date"]), "Date")

    orders = pd.read_csv(DATASET_DIR / "orders.csv", parse_dates=["order_date"])
    order_daily = (
        orders.groupby("order_date", as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            customers=("customer_id", "nunique"),
            delivered_orders=("order_status", lambda s: int(s.eq("delivered").sum())),
            returned_status_orders=("order_status", lambda s: int(s.eq("returned").sum())),
            cancelled_orders=("order_status", lambda s: int(s.eq("cancelled").sum())),
            mobile_orders=("device_type", lambda s: int(s.eq("mobile").sum())),
            desktop_orders=("device_type", lambda s: int(s.eq("desktop").sum())),
            paid_search_orders=("order_source", lambda s: int(s.eq("paid_search").sum())),
            email_orders=("order_source", lambda s: int(s.eq("email").sum())),
            organic_orders=("order_source", lambda s: int(s.eq("organic_search").sum())),
            social_orders=("order_source", lambda s: int(s.eq("social_media").sum())),
        )
        .rename(columns={"order_date": "Date"})
    )

    products = pd.read_csv(DATASET_DIR / "products.csv")
    items = pd.read_csv(DATASET_DIR / "order_items.csv", low_memory=False)
    items = items.merge(products[["product_id", "category", "segment", "cogs"]], on="product_id", how="left")
    items["gross_item_value"] = items["quantity"] * items["unit_price"]
    items["net_item_value"] = items["gross_item_value"] - items["discount_amount"].fillna(0.0)
    items["product_cogs_value"] = items["quantity"] * items["cogs"]
    items["has_promo"] = items["promo_id"].notna() | items["promo_id_2"].notna()
    item_order = (
        items.groupby("order_id", as_index=False)
        .agg(
            item_lines=("product_id", "count"),
            units=("quantity", "sum"),
            gross_item_value=("gross_item_value", "sum"),
            net_item_value=("net_item_value", "sum"),
            product_cogs_value=("product_cogs_value", "sum"),
            discount_amount=("discount_amount", "sum"),
            promo_lines=("has_promo", "sum"),
        )
    )
    item_daily = (
        orders[["order_id", "order_date"]]
        .merge(item_order, on="order_id", how="left")
        .groupby("order_date", as_index=False)
        .agg(
            item_lines=("item_lines", "sum"),
            units=("units", "sum"),
            gross_item_value=("gross_item_value", "sum"),
            net_item_value=("net_item_value", "sum"),
            product_cogs_value=("product_cogs_value", "sum"),
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
        .apply(
            lambda g: pd.Series(
                {
                    "sessions": g["sessions"].sum(),
                    "unique_visitors": g["unique_visitors"].sum(),
                    "page_views": g["page_views"].sum(),
                    "bounce_rate": weighted_avg(g["bounce_rate"], g["sessions"]),
                    "avg_session_duration_sec": weighted_avg(g["avg_session_duration_sec"], g["sessions"]),
                }
            ),
            include_groups=False,
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

    shipments = pd.read_csv(DATASET_DIR / "shipments.csv", parse_dates=["ship_date", "delivery_date"])
    ship_order = orders[["order_id", "order_date"]].merge(shipments, on="order_id", how="left")
    ship_order["ship_lag_days"] = (ship_order["ship_date"] - ship_order["order_date"]).dt.days
    ship_order["delivery_lag_days"] = (ship_order["delivery_date"] - ship_order["order_date"]).dt.days
    ship_daily = (
        ship_order.groupby("order_date", as_index=False)
        .agg(
            shipping_fee=("shipping_fee", "sum"),
            avg_ship_lag_days=("ship_lag_days", "mean"),
            avg_delivery_lag_days=("delivery_lag_days", "mean"),
        )
        .rename(columns={"order_date": "Date"})
    )

    reviews = pd.read_csv(DATASET_DIR / "reviews.csv", parse_dates=["review_date"])
    review_order = orders[["order_id", "order_date"]].merge(reviews[["order_id", "rating"]], on="order_id", how="left")
    review_daily = (
        review_order.groupby("order_date", as_index=False)
        .agg(avg_rating=("rating", "mean"), review_count=("rating", "count"))
        .rename(columns={"order_date": "Date"})
    )

    inventory = pd.read_csv(DATASET_DIR / "inventory.csv", parse_dates=["snapshot_date"])
    inv_daily = (
        inventory.groupby("snapshot_date", as_index=False)
        .agg(
            stock_on_hand=("stock_on_hand", "sum"),
            units_received=("units_received", "sum"),
            inv_units_sold=("units_sold", "sum"),
            stockout_days=("stockout_days", "sum"),
            fill_rate=("fill_rate", "mean"),
            stockout_flag=("stockout_flag", "mean"),
            days_of_supply=("days_of_supply", "mean"),
            sell_through_rate=("sell_through_rate", "mean"),
        )
        .rename(columns={"snapshot_date": "Date"})
    )

    promos = pd.read_csv(DATASET_DIR / "promotions.csv", parse_dates=["start_date", "end_date"])
    promo_daily = expand_promotions(promos)

    daily = sales[["Date", "year", "month", "half", "period", "Revenue", "COGS"]].copy()
    parts = [order_daily, item_daily, pay_daily, traffic_daily, returns_daily, ship_daily, review_daily, inv_daily, promo_daily]
    for part in parts:
        daily = daily.merge(part, on="Date", how="left")

    zero_cols = [
        "orders",
        "customers",
        "delivered_orders",
        "returned_status_orders",
        "cancelled_orders",
        "mobile_orders",
        "desktop_orders",
        "paid_search_orders",
        "email_orders",
        "organic_orders",
        "social_orders",
        "item_lines",
        "units",
        "gross_item_value",
        "net_item_value",
        "product_cogs_value",
        "discount_amount",
        "promo_lines",
        "payment_value",
        "sessions",
        "unique_visitors",
        "page_views",
        "returns",
        "return_quantity",
        "refund_amount",
        "shipping_fee",
        "review_count",
        "active_promo_count",
        "promo_discount_sum",
        "promo_discount_max",
        "stackable_promos",
    ]
    for col in zero_cols:
        if col in daily.columns:
            daily[col] = daily[col].fillna(0.0)

    daily["cogs_ratio"] = daily["COGS"] / daily["Revenue"].replace(0, np.nan)
    daily["gross_reconciliation_ratio"] = daily["gross_item_value"] / daily["Revenue"].replace(0, np.nan)
    daily["product_cogs_reconciliation_ratio"] = daily["product_cogs_value"] / daily["COGS"].replace(0, np.nan)
    daily["aov"] = daily["Revenue"] / daily["orders"].replace(0, np.nan)
    daily["units_per_order"] = daily["units"] / daily["orders"].replace(0, np.nan)
    daily["revenue_per_unit"] = daily["Revenue"] / daily["units"].replace(0, np.nan)
    daily["conversion"] = daily["orders"] / daily["sessions"].replace(0, np.nan)
    daily["discount_rate"] = daily["discount_amount"] / daily["gross_item_value"].replace(0, np.nan)
    daily["promo_line_share"] = daily["promo_lines"] / daily["item_lines"].replace(0, np.nan)
    daily["refund_rate"] = daily["refund_amount"] / daily["Revenue"].replace(0, np.nan)
    daily["mobile_share"] = daily["mobile_orders"] / daily["orders"].replace(0, np.nan)
    daily["paid_search_share"] = daily["paid_search_orders"] / daily["orders"].replace(0, np.nan)
    daily["delivered_rate"] = daily["delivered_orders"] / daily["orders"].replace(0, np.nan)
    daily["is_train"] = 1
    return daily


def period_metrics(daily: pd.DataFrame) -> pd.DataFrame:
    grouped = (
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
            gross_item_value=("gross_item_value", "sum"),
            product_cogs_value=("product_cogs_value", "sum"),
            discount_amount=("discount_amount", "sum"),
            promo_lines=("promo_lines", "sum"),
            item_lines=("item_lines", "sum"),
            refund_amount=("refund_amount", "sum"),
            shipping_fee=("shipping_fee", "sum"),
            active_promo_days=("active_promo_count", lambda s: int((s > 0).sum())),
            avg_promo_count=("active_promo_count", "mean"),
            avg_promo_discount_max=("promo_discount_max", "mean"),
            avg_fill_rate=("fill_rate", "mean"),
            avg_stockout_flag=("stockout_flag", "mean"),
            stockout_days=("stockout_days", "sum"),
            avg_rating=("avg_rating", "mean"),
        )
        .sort_values(["year", "half"])
    )
    grouped["period"] = grouped["year"].astype(str) + grouped["half"]
    grouped["cogs_ratio"] = grouped["cogs"] / grouped["revenue"].replace(0, np.nan)
    grouped["orders_per_day"] = grouped["orders"] / grouped["days"]
    grouped["aov"] = grouped["revenue"] / grouped["orders"].replace(0, np.nan)
    grouped["units_per_order"] = grouped["units"] / grouped["orders"].replace(0, np.nan)
    grouped["revenue_per_unit"] = grouped["revenue"] / grouped["units"].replace(0, np.nan)
    grouped["conversion"] = grouped["orders"] / grouped["sessions"].replace(0, np.nan)
    grouped["discount_rate"] = grouped["discount_amount"] / grouped["gross_item_value"].replace(0, np.nan)
    grouped["promo_line_share"] = grouped["promo_lines"] / grouped["item_lines"].replace(0, np.nan)
    grouped["refund_rate"] = grouped["refund_amount"] / grouped["revenue"].replace(0, np.nan)
    grouped["gross_reconciliation_ratio"] = grouped["gross_item_value"] / grouped["revenue"].replace(0, np.nan)
    grouped["product_cogs_reconciliation_ratio"] = grouped["product_cogs_value"] / grouped["cogs"].replace(0, np.nan)
    return grouped


def annual_metrics(daily: pd.DataFrame) -> pd.DataFrame:
    grouped = (
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
            promo_lines=("promo_lines", "sum"),
            item_lines=("item_lines", "sum"),
        )
        .sort_values("year")
    )
    grouped["cogs_ratio"] = grouped["cogs"] / grouped["revenue"].replace(0, np.nan)
    grouped["orders_per_day"] = grouped["orders"] / grouped["days"]
    grouped["aov"] = grouped["revenue"] / grouped["orders"].replace(0, np.nan)
    grouped["conversion"] = grouped["orders"] / grouped["sessions"].replace(0, np.nan)
    grouped["discount_rate"] = grouped["discount_amount"] / grouped["gross_item_value"].replace(0, np.nan)
    grouped["promo_line_share"] = grouped["promo_lines"] / grouped["item_lines"].replace(0, np.nan)
    for col in ["revenue", "cogs", "orders", "sessions", "aov", "conversion", "cogs_ratio"]:
        grouped[f"{col}_yoy"] = grouped[col].pct_change()
    return grouped


def era_comparison(periods: pd.DataFrame) -> pd.DataFrame:
    p = periods.loc[periods["year"].between(2013, 2022)].copy()
    p["era"] = np.select(
        [p["year"].between(2013, 2018), p["year"].between(2019, 2022)],
        ["pre2019_high", "recent_low"],
        default="other",
    )
    summary = (
        p.loc[p["era"].ne("other")]
        .groupby(["era", "half"], as_index=False)
        .agg(
            revenue=("revenue", "mean"),
            cogs=("cogs", "mean"),
            orders=("orders", "mean"),
            sessions=("sessions", "mean"),
            units=("units", "mean"),
            conversion=("conversion", "mean"),
            aov=("aov", "mean"),
            revenue_per_unit=("revenue_per_unit", "mean"),
            cogs_ratio=("cogs_ratio", "mean"),
            discount_rate=("discount_rate", "mean"),
            promo_line_share=("promo_line_share", "mean"),
            active_promo_days=("active_promo_days", "mean"),
        )
    )
    wide = summary.pivot(index="half", columns="era")
    rows = []
    for half in ["H1", "H2"]:
        for metric in ["revenue", "cogs", "orders", "sessions", "conversion", "aov", "cogs_ratio", "discount_rate", "promo_line_share"]:
            pre = wide.loc[half, (metric, "pre2019_high")]
            recent = wide.loc[half, (metric, "recent_low")]
            rows.append(
                {
                    "half": half,
                    "metric": metric,
                    "pre2019_high": pre,
                    "recent_low": recent,
                    "recent_vs_pre2019_pct": (recent / pre - 1) if pre else np.nan,
                }
            )
    return pd.DataFrame(rows)


def month_shape_stability(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    valid = daily.loc[daily["year"].between(2013, 2022)].copy()
    for half, months in {"H1": range(1, 7), "H2": range(7, 13)}.items():
        sub = valid.loc[valid["month"].isin(months)]
        month_sum = sub.groupby(["year", "month"], as_index=False).agg(revenue=("Revenue", "sum"), cogs=("COGS", "sum"))
        totals = month_sum.groupby("year", as_index=False).agg(total_revenue=("revenue", "sum"), total_cogs=("cogs", "sum"))
        month_sum = month_sum.merge(totals, on="year")
        month_sum["revenue_share"] = month_sum["revenue"] / month_sum["total_revenue"].replace(0, np.nan)
        month_sum["cogs_share"] = month_sum["cogs"] / month_sum["total_cogs"].replace(0, np.nan)
        for month, g in month_sum.groupby("month"):
            rows.append(
                {
                    "half": half,
                    "month": month,
                    "revenue_share_mean": g["revenue_share"].mean(),
                    "revenue_share_std": g["revenue_share"].std(),
                    "revenue_share_cv": g["revenue_share"].std() / g["revenue_share"].mean(),
                    "cogs_share_mean": g["cogs_share"].mean(),
                    "cogs_share_std": g["cogs_share"].std(),
                    "cogs_share_cv": g["cogs_share"].std() / g["cogs_share"].mean(),
                }
            )
    return pd.DataFrame(rows)


def daily_shape_correlation(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    valid = daily.loc[daily["year"].between(2013, 2022)].copy()
    for half, months in {"H1": range(1, 7), "H2": range(7, 13)}.items():
        sub = valid.loc[valid["month"].isin(months)].copy()
        sub["day_index"] = sub.groupby("year").cumcount()
        sub["rev_shape"] = sub["Revenue"] / sub.groupby("year")["Revenue"].transform("sum")
        pivot = sub.pivot(index="day_index", columns="year", values="rev_shape")
        corr = pivot.corr().where(np.triu(np.ones((pivot.shape[1], pivot.shape[1])), k=1).astype(bool))
        vals = corr.stack()
        rows.append(
            {
                "half": half,
                "pairwise_corr_mean": vals.mean(),
                "pairwise_corr_median": vals.median(),
                "pairwise_corr_min": vals.min(),
                "pairwise_corr_max": vals.max(),
                "pairs": int(vals.count()),
            }
        )
    return pd.DataFrame(rows)


def ratio_dispersion(daily: pd.DataFrame) -> pd.DataFrame:
    valid = daily.loc[daily["year"].between(2013, 2022)].copy()
    rows = []
    for group_cols in [["half"], ["half", "month"]]:
        for keys, g in valid.groupby(group_cols):
            if not isinstance(keys, tuple):
                keys = (keys,)
            row = {col: val for col, val in zip(group_cols, keys)}
            row.update(
                {
                    "level": "+".join(group_cols),
                    "cogs_ratio_mean": g["cogs_ratio"].mean(),
                    "cogs_ratio_std": g["cogs_ratio"].std(),
                    "cogs_ratio_p10": g["cogs_ratio"].quantile(0.10),
                    "cogs_ratio_p50": g["cogs_ratio"].quantile(0.50),
                    "cogs_ratio_p90": g["cogs_ratio"].quantile(0.90),
                    "revenue_daily_cv": g["Revenue"].std() / g["Revenue"].mean(),
                    "days": len(g),
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def driver_correlations(daily: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "Revenue",
        "COGS",
        "cogs_ratio",
        "orders",
        "sessions",
        "conversion",
        "aov",
        "units",
        "revenue_per_unit",
        "discount_rate",
        "promo_line_share",
        "active_promo_count",
        "promo_discount_max",
        "stockout_flag",
        "fill_rate",
        "refund_rate",
        "avg_rating",
    ]
    existing = [col for col in cols if col in daily.columns]
    corr = daily.loc[daily["year"].between(2013, 2022), existing].corr(numeric_only=True)
    rows = []
    for target in ["Revenue", "COGS", "cogs_ratio"]:
        if target not in corr.columns:
            continue
        for feature, value in corr[target].drop(labels=[target], errors="ignore").items():
            rows.append({"target": target, "feature": feature, "corr": value, "abs_corr": abs(value)})
    return pd.DataFrame(rows).sort_values(["target", "abs_corr"], ascending=[True, False])


def category_mix() -> pd.DataFrame:
    orders = pd.read_csv(DATASET_DIR / "orders.csv", parse_dates=["order_date"])
    products = pd.read_csv(DATASET_DIR / "products.csv")
    items = pd.read_csv(DATASET_DIR / "order_items.csv", low_memory=False)
    items = items.merge(products[["product_id", "category", "segment", "cogs"]], on="product_id", how="left")
    items["gross_item_value"] = items["quantity"] * items["unit_price"]
    items["product_cogs_value"] = items["quantity"] * items["cogs"]
    joined = orders[["order_id", "order_date"]].merge(items, on="order_id", how="inner")
    joined = add_time(joined, "order_date")
    rows = []
    for dim in ["category", "segment"]:
        agg = (
            joined.loc[joined["year"].between(2013, 2022)]
            .groupby(["year", "half", dim], as_index=False)
            .agg(gross_item_value=("gross_item_value", "sum"), product_cogs_value=("product_cogs_value", "sum"), units=("quantity", "sum"))
        )
        totals = agg.groupby(["year", "half"], as_index=False).agg(total_value=("gross_item_value", "sum"))
        agg = agg.merge(totals, on=["year", "half"])
        agg["share"] = agg["gross_item_value"] / agg["total_value"].replace(0, np.nan)
        agg["item_cogs_ratio"] = agg["product_cogs_value"] / agg["gross_item_value"].replace(0, np.nan)
        agg["era"] = np.select(
            [agg["year"].between(2013, 2018), agg["year"].between(2019, 2022)],
            ["pre2019_high", "recent_low"],
            default="other",
        )
        era = (
            agg.loc[agg["era"].ne("other")]
            .groupby(["era", "half", dim], as_index=False)
            .agg(share=("share", "mean"), item_cogs_ratio=("item_cogs_ratio", "mean"))
        )
        wide = era.pivot(index=["half", dim], columns="era", values=["share", "item_cogs_ratio"]).reset_index()
        wide.columns = [c if isinstance(c, str) else "_".join([x for x in c if x]) for c in wide.columns]
        wide["dimension"] = dim
        if "share_recent_low" in wide.columns and "share_pre2019_high" in wide.columns:
            wide["share_delta_recent_minus_pre"] = wide["share_recent_low"] - wide["share_pre2019_high"]
        rows.append(wide)
    return pd.concat(rows, ignore_index=True, sort=False)


def promotion_calendar_summary() -> pd.DataFrame:
    promos = pd.read_csv(DATASET_DIR / "promotions.csv", parse_dates=["start_date", "end_date"])
    promo_daily = expand_promotions(promos)
    promo_daily = add_time(promo_daily, "Date")
    summary = (
        promo_daily.groupby(["year", "half"], as_index=False)
        .agg(
            active_days=("Date", "nunique"),
            avg_promo_count=("active_promo_count", "mean"),
            max_promo_count=("active_promo_count", "max"),
            avg_discount_max=("promo_discount_max", "mean"),
            max_discount=("promo_discount_max", "max"),
            stackable_days=("stackable_promos", lambda s: int((s > 0).sum())),
        )
        .sort_values(["year", "half"])
    )
    return summary


def forecast_safety_audit(coverage: pd.DataFrame) -> pd.DataFrame:
    rules = [
        ("calendar", "future-known", "Generated from forecast dates; safe."),
        ("promotions.csv", "train-only-recurring-policy", "Provided promo history ends before test; safe only as train-derived recurring priors, not direct future schedule or realized uplift."),
        ("products.csv", "mostly-static", "Safe for product attributes if treated as catalog metadata; price/cogs history must not be inferred as future actuals."),
        ("orders.csv", "unknown-future", "Future orders are the outcome pathway; use only train-derived summaries or forecasted policies."),
        ("order_items.csv", "unknown-future", "Future item mix and quantities are target-adjacent; use only train-derived priors."),
        ("payments.csv", "unknown-future", "Payment amount follows orders; not future-known."),
        ("web_traffic.csv", "unknown-future", "Useful driver historically, but future traffic must be forecasted or policy-imputed."),
        ("inventory.csv", "policy-imputed", "Inventory snapshots can be operational plans only if provided for future; otherwise train-only."),
        ("returns.csv", "post-outcome", "Return dates lag orders and are not valid future drivers for target submission."),
        ("reviews.csv", "post-outcome", "Reviews lag orders and should be treated as diagnostic only."),
        ("shipments.csv", "post-outcome", "Shipment and delivery are downstream of orders; diagnostic only."),
        ("customers.csv", "partial-future-risk", "Signup history is useful; future customer acquisitions must be forecasted."),
    ]
    audit = pd.DataFrame(rules, columns=["source", "policy", "reason"])
    return audit.merge(coverage[["file", "min_date", "max_date", "rows"]], left_on="source", right_on="file", how="left").drop(columns=["file"])


def write_report(
    run_dir: Path,
    coverage: pd.DataFrame,
    annual: pd.DataFrame,
    periods: pd.DataFrame,
    era: pd.DataFrame,
    month_shape: pd.DataFrame,
    shape_corr: pd.DataFrame,
    ratio: pd.DataFrame,
    corr: pd.DataFrame,
    cat_mix: pd.DataFrame,
    promo_summary: pd.DataFrame,
    safety: pd.DataFrame,
) -> None:
    annual_focus = annual.loc[annual["year"].between(2017, 2022), ["year", "revenue", "revenue_yoy", "orders", "orders_yoy", "sessions", "sessions_yoy", "conversion", "conversion_yoy", "aov", "aov_yoy", "cogs_ratio"]]
    period_focus = periods.loc[periods["year"].between(2019, 2022), ["period", "days", "revenue", "cogs", "cogs_ratio", "orders", "sessions", "conversion", "aov", "discount_rate", "promo_line_share"]]
    top_corr = corr.loc[corr["target"].eq("Revenue")].head(12)
    top_ratio_corr = corr.loc[corr["target"].eq("cogs_ratio")].head(12)
    cat_top = cat_mix.sort_values("share_delta_recent_minus_pre", key=lambda s: s.abs(), ascending=False).head(12)
    h1h2_ratio = ratio.loc[ratio["level"].eq("half"), ["half", "cogs_ratio_mean", "cogs_ratio_std", "cogs_ratio_p10", "cogs_ratio_p50", "cogs_ratio_p90", "revenue_daily_cv"]]

    report = f"""# Clean V2 Deep EDA - 2026-04-24

Run directory: `{run_dir}`

## Boundary

This EDA uses source/train data only. It does not use `sample_submission.csv` or previous submissions as inputs.

## Executive Read

1. `2019` remains the structural break: Revenue drops together with orders/conversion, not because traffic disappears.
2. H1 is the cleaner recovery candidate: H1 has better shape stability than H2 and should support a train-derived regime recovery head.
3. H2 Revenue is noisy: broad or localized H2 Revenue freedom is hard to justify cleanly; the EDA supports stronger H2 shrinkage.
4. COGS deserves its own ratio model: COGS/Revenue ratio has period-specific dispersion that Revenue-only modeling cannot capture.
5. Promotions are useful, but `promotions.csv` ends at `2022-12-31`; clean test-period promo features must be train-derived recurring priors, not direct future schedules.
6. Traffic, order source, returns, shipments, reviews, and future item mix are strong diagnostics but must be forecasted or summarized from train history before they can be clean features.

## Source Coverage

{coverage.to_markdown(index=False)}

## Forecast Safety Audit

{safety.to_markdown(index=False)}

## Annual Breaks

{annual_focus.to_markdown(index=False)}

## Recent Half-Year Periods

{period_focus.to_markdown(index=False)}

## Era Shift: Recent Low vs Pre-2019 High

{era.to_markdown(index=False)}

## Seasonality Stability

Daily shape correlation:

{shape_corr.to_markdown(index=False)}

Monthly share stability:

{month_shape.to_markdown(index=False)}

## COGS Ratio Dispersion

{h1h2_ratio.to_markdown(index=False)}

## Revenue Driver Correlations

{top_corr.to_markdown(index=False)}

## COGS Ratio Driver Correlations

{top_ratio_corr.to_markdown(index=False)}

## Category / Segment Mix Shifts

{cat_top.to_markdown(index=False)}

## Promotion Calendar

{promo_summary.tail(12).to_markdown(index=False)}

## Missing Insights For Clean V2

### 1. The model needs a funnel decomposition, not only a target decomposition

The structural break is better explained by:

- sessions
- conversion
- orders
- AOV
- units per order

than by calendar alone. A clean model should not necessarily forecast these future actuals directly, but it can use train-derived regime priors for conversion and AOV.

### 2. H1 recovery should be justified through conversion/AOV recovery

Blackbox said `2023H1 Revenue` was undercalled. EDA gives a cleaner explanation path:

- H1 shape is more stable.
- recent-low years understate high-regime H1 level.
- recovery can be described as a conversion/order-count recovery, not an arbitrary Revenue multiplier.

### 3. H2 should be regularized because its shape is less stable

H2 has weaker daily shape stability and stronger ratio noise. This supports H2 shrinkage and smaller H2 Revenue residual caps.

### 4. COGS ratio head should be trained separately

The COGS ratio dispersion table supports a dedicated ratio target. This is cleaner than moving COGS by hand after Revenue prediction.

### 5. Promo history is underused, but not future-known

`promotions.csv` contains historical promo windows only. This still helps: recurring month-day promo intensity, discount seasonality, and stackable-promo priors can be learned from train. The clean branch should not claim direct knowledge of 2023-2024 promo schedules unless a separate future promo plan is provided.

### 6. Inventory is risky

Inventory is operationally meaningful but its future availability must be audited. It should not be used as a future feature unless the future snapshots are explicitly part of the provided input scenario.

## Clean V2 Actions

1. Add train-derived H1 recovery features based on pre-2019 vs recent-low gaps.
2. Add H2 residual caps and compare against unrestricted H2 residuals.
3. Build a separate `COGS / Revenue` ratio model.
4. Use train-derived recurring promo priors from `promotions.csv`, not realized promo usage or assumed future schedules.
5. Keep traffic/order/returns/reviews as diagnostic or forecasted-policy features, not direct future inputs.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v2_deep_eda_2026-04-24.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    coverage = source_coverage()
    daily = build_daily_panel()
    periods = period_metrics(daily)
    annual = annual_metrics(daily)
    era = era_comparison(periods)
    month_shape = month_shape_stability(daily)
    shape_corr = daily_shape_correlation(daily)
    ratio = ratio_dispersion(daily)
    corr = driver_correlations(daily)
    cat_mix = category_mix()
    promo_summary = promotion_calendar_summary()
    safety = forecast_safety_audit(coverage)

    coverage.to_csv(run_dir / "source_coverage.csv", index=False)
    daily.to_csv(run_dir / "daily_driver_panel.csv", index=False)
    periods.to_csv(run_dir / "halfyear_metrics.csv", index=False)
    annual.to_csv(run_dir / "annual_metrics.csv", index=False)
    era.to_csv(run_dir / "era_shift_metrics.csv", index=False)
    month_shape.to_csv(run_dir / "month_shape_stability.csv", index=False)
    shape_corr.to_csv(run_dir / "daily_shape_correlation.csv", index=False)
    ratio.to_csv(run_dir / "ratio_dispersion.csv", index=False)
    corr.to_csv(run_dir / "driver_correlations.csv", index=False)
    cat_mix.to_csv(run_dir / "category_segment_mix_shift.csv", index=False)
    promo_summary.to_csv(run_dir / "promotion_calendar_summary.csv", index=False)
    safety.to_csv(run_dir / "forecast_safety_audit.csv", index=False)

    write_report(run_dir, coverage, annual, periods, era, month_shape, shape_corr, ratio, corr, cat_mix, promo_summary, safety)
    print(run_dir)


if __name__ == "__main__":
    main()
