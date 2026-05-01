from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from lunar_calendar_features import add_lunar_calendar_features


DATA_DIR = Path("dataset")
START_DATE = "2012-07-04"
END_DATE = "2024-07-01"
TRAIN_END = "2022-12-31"
CALENDAR_COLUMNS = [
    "year",
    "month",
    "day",
    "dayofweek",
    "weekofyear",
    "quarter",
    "dayofyear",
    "is_weekend",
    "is_month_start",
    "is_month_end",
    "is_quarter_start",
    "is_quarter_end",
    "sin_dayofyear",
    "cos_dayofyear",
    "sin_dayofyear_k2",
    "cos_dayofyear_k2",
    "sin_dayofyear_k3",
    "cos_dayofyear_k3",
    "sin_dayofweek",
    "cos_dayofweek",
    "sin_month",
    "cos_month",
    "days_to_eom",
    "days_from_bom",
    "is_tet_month",
    "month_weekday_interact",
    "lunar_month",
    "lunar_day",
    "lunar_month_sin",
    "lunar_month_cos",
    "lunar_day_sin",
    "lunar_day_cos",
    "is_lunar_new_year",
    "days_from_tet",
    "days_to_tet",
    "win_tet_pre14_1",
    "win_tet_pre7_1",
    "win_tet_0_3",
    "win_tet_0_6",
    "win_tet_post4_14",
    "win_tet_post15_35",
    "win_tet_wide",
    "lunar_year",
    "lunar_is_leap_month",
    "julian_day",
]
PROMO_BASE_COLUMNS = [
    "active_promo_count",
    "active_stackable_promo_count",
    "active_promo_discount_value_mean",
    "total_discount",
    "avg_discount_rate",
    "promo_line_share",
    "promo_2_share",
    "active_promo_stackable_share",
    "active_promo_min_order_value_mean",
    "active_promo_type_percentage_count",
    "active_promo_type_fixed_count",
    "active_promo_type_percentage_share",
    "active_promo_type_fixed_share",
    "active_promo_channel_all_channels_count",
    "active_promo_channel_email_count",
    "active_promo_channel_online_count",
    "active_promo_channel_social_media_count",
    "active_promo_channel_in_store_count",
    "active_promo_channel_all_channels_share",
    "active_promo_channel_email_share",
    "active_promo_channel_online_share",
    "active_promo_channel_social_media_share",
    "active_promo_channel_in_store_share",
    "active_promo_category_global_count",
    "active_promo_category_outdoor_count",
    "active_promo_category_streetwear_count",
    "active_promo_category_global_share",
    "active_promo_category_outdoor_share",
    "active_promo_category_streetwear_share",
    "active_promo_discount_value_percentage_mean",
    "active_promo_discount_value_fixed_mean",
]
PROMO_TARGET_ENCODING_COLUMNS = [
    "promo_type_revenue_te",
    "promo_channel_revenue_te",
    "promo_category_revenue_te",
    "promo_type_cogs_ratio_te",
    "promo_channel_cogs_ratio_te",
    "promo_category_cogs_ratio_te",
]
PROMO_MODEL_COLUMNS = PROMO_BASE_COLUMNS + PROMO_TARGET_ENCODING_COLUMNS
PROMO_SLIM_BASE_COLUMNS = [
    "total_discount",
    "avg_discount_rate",
    "promo_line_share",
    "promo_2_share",
    "active_promo_count",
    "active_stackable_promo_count",
    "active_promo_discount_value_mean",
    "active_promo_min_order_value_mean",
    "active_promo_stackable_share",
    "active_promo_type_percentage_share",
    "active_promo_type_fixed_share",
    "active_promo_discount_value_percentage_mean",
    "active_promo_discount_value_fixed_mean",
]
PROMO_RESEARCH_BASE_COLUMNS = [
    "promo_days_since_start_mean",
    "promo_days_to_end_mean",
    "promo_duration_days_mean",
    "promo_start_count",
    "promo_end_count",
]
CONTEXT_BASE_COLUMNS = [
    "new_customers",
    "shipping_fee_total",
    "shipping_fee_mean",
    "shipping_fee_per_order",
    "shipment_order_share",
    "order_to_ship_days_mean",
    "ship_to_delivery_days_mean",
    "fast_delivery_share",
    "slow_delivery_share",
    "signup_channel_share_direct",
    "signup_channel_share_email_campaign",
    "signup_channel_share_organic_search",
    "signup_channel_share_paid_search",
    "signup_channel_share_referral",
    "signup_channel_share_social_media",
    "order_region_share_central",
    "order_region_share_east",
    "order_region_share_west",
]
TARGET_LAG_PERIODS = [1, 2, 3, 4, 5, 6, 7, 14, 21, 28, 35, 42, 56, 84, 91, 182, 364, 365, 728, 730]
TARGET_ROLL_WINDOWS = [7, 14, 28, 56, 91, 182, 365, 730]
TARGET_SEASONAL_PRIOR_WINDOW_DAYS = 730
TARGET_SEASONAL_PRIOR_COLUMNS = [
    "target_seasonal_rev_md_mean_recent_2y",
    "target_seasonal_rev_mwd_mean_recent_2y",
    "target_seasonal_cogs_md_mean_recent_2y",
    "target_seasonal_cogs_mwd_mean_recent_2y",
]
TARGET_HISTORY_PLUS_PREFIXES = ("revplus_", "cogsplus_")
HIERARCHY_LITE_PREFIXES = (
    "category_rev_share_",
    "segment_rev_share_",
)
PRICE_SIGNAL_COLUMNS = [
    "avg_unit_price",
    "margin_rate",
]
PRICE_HISTORY_RESEARCH_COLUMNS = [
    "pricehist_avg_unit_price_ratio_1_7",
    "pricehist_avg_unit_price_ratio_7_28",
    "pricehist_avg_unit_price_mom_1_7",
    "pricehist_margin_rate_ratio_1_28",
    "pricehist_discount_x_price_ratio_1_7",
]
ABLATION_SIGNAL_STEMS = {
    "cogs_history": ["cogs_"],
    "order_flow": [
        "order_count",
        "unique_customers",
        "total_units",
        "cancelled_order_share",
        "returned_order_share",
        "delivered_order_share",
        "units_per_order",
        "aov_proxy",
        "conversion_proxy",
    ],
    "traffic": [
        "sessions",
        "unique_visitors",
        "page_views",
        "bounce_rate",
        "avg_session_duration_sec",
        "sessions_per_visitor",
        "pageviews_per_session",
        "traffic_share_",
    ],
    "promo": [
        "total_discount",
        "avg_discount_rate",
        "promo_line_share",
        "promo_2_share",
        "active_promo_count",
        "active_stackable_promo_count",
        "active_promo_discount_value_mean",
        "active_promo_stackable_share",
        "active_promo_min_order_value_mean",
        "active_promo_type_",
        "active_promo_channel_",
        "active_promo_category_",
        "active_promo_discount_value_percentage_mean",
        "active_promo_discount_value_fixed_mean",
        "promo_type_revenue_te",
        "promo_channel_revenue_te",
        "promo_category_revenue_te",
        "promo_type_cogs_ratio_te",
        "promo_channel_cogs_ratio_te",
        "promo_category_cogs_ratio_te",
    ],
    "promo_research": [
        "promo_days_since_start_mean",
        "promo_days_to_end_mean",
        "promo_duration_days_mean",
        "promo_start_count",
        "promo_end_count",
    ],
    "returns_reviews": [
        "return_count",
        "return_qty",
        "refund_amt",
        "review_count",
        "avg_rating",
        "refund_per_return",
    ],
    "inventory": [
        "stock_on_hand",
        "units_received",
        "units_sold",
        "stockout_days_avg",
        "days_of_supply_avg",
        "fill_rate_avg",
        "stockout_rate",
        "overstock_rate",
        "sell_through_rate_avg",
        "inv_stock_on_hand_",
        "inv_stockout_flag_",
    ],
    "mix": [
        "payment_share_",
        "device_share_",
        "order_source_share_",
        "category_rev_share_",
        "segment_rev_share_",
        "gross_margin",
        "avg_unit_price",
        "margin_rate",
    ],
    "geo_logistics": [
        "new_customers",
        "signup_channel_share_",
        "order_region_share_",
        "shipping_fee_total",
        "shipping_fee_mean",
        "shipping_fee_per_order",
        "shipment_order_share",
        "order_to_ship_days_mean",
        "ship_to_delivery_days_mean",
        "fast_delivery_share",
        "slow_delivery_share",
    ],
    "target_seasonal_priors": [
        "target_seasonal_rev_",
        "target_seasonal_cogs_",
    ],
    "target_history_plus": [
        "revplus_",
        "cogsplus_",
    ],
    "price_history": [
        "pricehist_",
    ],
}
FEATURE_GROUP_POLICIES = {
    "calendar": {"availability_type": "known_in_future", "usage_policy": "forecast_core"},
    "revenue_history": {"availability_type": "inferable_recursive", "usage_policy": "forecast_core"},
    "cogs_history": {"availability_type": "inferable_recursive", "usage_policy": "forecast_core"},
    "promo": {"availability_type": "inferable_planned_dynamic", "usage_policy": "forecast_core"},
    "promo_slim": {"availability_type": "inferable_planned_dynamic", "usage_policy": "experimental"},
    "promo_detail": {"availability_type": "inferable_planned_dynamic", "usage_policy": "experimental"},
    "promo_research": {"availability_type": "inferable_planned_dynamic", "usage_policy": "experimental"},
    "order_flow": {"availability_type": "unknown_future", "usage_policy": "analysis_rich"},
    "traffic": {"availability_type": "unknown_future", "usage_policy": "analysis_rich"},
    "returns_reviews": {"availability_type": "unknown_future", "usage_policy": "analysis_rich"},
    "inventory": {"availability_type": "unknown_future", "usage_policy": "analysis_rich"},
    "mix": {"availability_type": "unknown_future", "usage_policy": "analysis_rich"},
    "mix_light": {"availability_type": "unknown_future", "usage_policy": "experimental"},
    "hierarchy_lite": {"availability_type": "inferable_low_confidence", "usage_policy": "experimental"},
    "geo_logistics": {"availability_type": "inferable_low_confidence", "usage_policy": "experimental"},
    "target_seasonal_priors": {"availability_type": "inferable_calendar_history", "usage_policy": "experimental"},
    "target_history_plus": {"availability_type": "inferable_recursive", "usage_policy": "experimental"},
    "price_history": {"availability_type": "inferable_seasonal_history", "usage_policy": "experimental"},
    "cal_eom_bom": {"availability_type": "known_in_future", "usage_policy": "experimental"},
    "cal_tet": {"availability_type": "known_in_future", "usage_policy": "experimental"},
    "cal_interact": {"availability_type": "known_in_future", "usage_policy": "experimental"},
}


def _load_csv(name: str, parse_dates: list[str] | None = None) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name, parse_dates=parse_dates, low_memory=False)


def _share_table(
    df: pd.DataFrame,
    index: str,
    column: str,
    value: str,
    prefix: str,
) -> pd.DataFrame:
    table = (
        df.pivot_table(index=index, columns=column, values=value, aggfunc="count", fill_value=0)
        .sort_index(axis=1)
        .astype(float)
    )
    denom = table.sum(axis=1).replace(0, np.nan)
    shares = table.div(denom, axis=0).fillna(0.0)
    shares.columns = [f"{prefix}{_slugify(col)}" for col in shares.columns]
    return shares.reset_index()


def _value_share_table(
    df: pd.DataFrame,
    index: str,
    column: str,
    value: str,
    prefix: str,
) -> pd.DataFrame:
    table = (
        df.pivot_table(index=index, columns=column, values=value, aggfunc="sum", fill_value=0)
        .sort_index(axis=1)
        .astype(float)
    )
    denom = table.sum(axis=1).replace(0, np.nan)
    shares = table.div(denom, axis=0).fillna(0.0)
    shares.columns = [f"{prefix}{_slugify(col)}" for col in shares.columns]
    return shares.reset_index()


def _slugify(value: str) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_").replace("/", "_")


def _dominant_promo_key(
    df: pd.DataFrame,
    score_columns: dict[str, str],
    none_label: str = "none",
) -> pd.Series:
    score_frame = pd.DataFrame(
        {
            label: (df[column].fillna(0.0) if column in df.columns else pd.Series(0.0, index=df.index))
            for label, column in score_columns.items()
        },
        index=df.index,
    )
    dominant = score_frame.idxmax(axis=1)
    has_signal = score_frame.max(axis=1).gt(0)
    is_active = df.get("active_promo_count", pd.Series(0.0, index=df.index)).fillna(0.0).gt(0)
    return dominant.where(has_signal & is_active, none_label)


def _expanding_group_mean(
    values: pd.Series,
    groups: pd.Series,
    observed_mask: pd.Series,
) -> pd.Series:
    eligible_values = values.where(observed_mask, 0.0).fillna(0.0)
    eligible_counts = observed_mask.astype(float)
    cumulative_sum = eligible_values.groupby(groups).cumsum()
    cumulative_count = eligible_counts.groupby(groups).cumsum()
    prior_sum = cumulative_sum - eligible_values
    prior_count = cumulative_count - eligible_counts
    overall_mean = float(values.loc[observed_mask].mean()) if observed_mask.any() else 0.0
    return (prior_sum / prior_count.replace(0, np.nan)).fillna(overall_mean)


def add_promo_target_encoding_features(
    df: pd.DataFrame,
    freeze_after: pd.Timestamp | None = None,
) -> pd.DataFrame:
    out = df.sort_values("Date").reset_index(drop=True).copy()
    observed_mask = out["Revenue"].notna() & out["COGS"].notna()
    if freeze_after is not None:
        observed_mask &= out["Date"] <= pd.Timestamp(freeze_after)

    promo_type_key = _dominant_promo_key(
        out,
        {
            "percentage": "active_promo_type_percentage_share",
            "fixed": "active_promo_type_fixed_share",
        },
    )
    promo_channel_key = _dominant_promo_key(
        out,
        {
            "all_channels": "active_promo_channel_all_channels_share",
            "email": "active_promo_channel_email_share",
            "online": "active_promo_channel_online_share",
            "social_media": "active_promo_channel_social_media_share",
            "in_store": "active_promo_channel_in_store_share",
        },
    )
    promo_category_key = _dominant_promo_key(
        out,
        {
            "global": "active_promo_category_global_share",
            "outdoor": "active_promo_category_outdoor_share",
            "streetwear": "active_promo_category_streetwear_share",
        },
    )

    cogs_ratio = (out["COGS"] / out["Revenue"]).replace([np.inf, -np.inf], np.nan)
    revenue_observed_mask = observed_mask & out["Revenue"].notna()
    cogs_ratio_observed_mask = observed_mask & cogs_ratio.notna()

    out["promo_type_revenue_te"] = _expanding_group_mean(out["Revenue"], promo_type_key, revenue_observed_mask)
    out["promo_channel_revenue_te"] = _expanding_group_mean(out["Revenue"], promo_channel_key, revenue_observed_mask)
    out["promo_category_revenue_te"] = _expanding_group_mean(
        out["Revenue"], promo_category_key, revenue_observed_mask
    )
    out["promo_type_cogs_ratio_te"] = _expanding_group_mean(cogs_ratio, promo_type_key, cogs_ratio_observed_mask)
    out["promo_channel_cogs_ratio_te"] = _expanding_group_mean(
        cogs_ratio, promo_channel_key, cogs_ratio_observed_mask
    )
    out["promo_category_cogs_ratio_te"] = _expanding_group_mean(
        cogs_ratio, promo_category_key, cogs_ratio_observed_mask
    )
    return out


def build_daily_base(end_date: str = END_DATE) -> pd.DataFrame:
    timeline = pd.DataFrame({"Date": pd.date_range(start=START_DATE, end=end_date, freq="D")})

    sales = _load_csv("sales.csv", parse_dates=["Date"])
    orders = _load_csv("orders.csv", parse_dates=["order_date"])
    items = _load_csv("order_items.csv")
    products = _load_csv("products.csv")
    customers = _load_csv("customers.csv", parse_dates=["signup_date"])
    promotions = _load_csv("promotions.csv", parse_dates=["start_date", "end_date"])
    geography = _load_csv("geography.csv")
    shipments = _load_csv("shipments.csv", parse_dates=["ship_date", "delivery_date"])
    returns = _load_csv("returns.csv", parse_dates=["return_date"])
    reviews = _load_csv("reviews.csv", parse_dates=["review_date"])
    traffic = _load_csv("web_traffic.csv", parse_dates=["date"])
    inventory = _load_csv("inventory.csv", parse_dates=["snapshot_date"])

    base = timeline.merge(sales, on="Date", how="left")

    orders_daily = (
        orders.groupby("order_date")
        .agg(
            order_count=("order_id", "count"),
            unique_customers=("customer_id", "nunique"),
            cancelled_order_share=("order_status", lambda s: (s == "cancelled").mean()),
            returned_order_share=("order_status", lambda s: (s == "returned").mean()),
            delivered_order_share=("order_status", lambda s: (s == "delivered").mean()),
        )
        .reset_index()
        .rename(columns={"order_date": "Date"})
    )

    orders_payment_share = _share_table(
        orders, index="order_date", column="payment_method", value="order_id", prefix="payment_share_"
    ).rename(columns={"order_date": "Date"})
    orders_device_share = _share_table(
        orders, index="order_date", column="device_type", value="order_id", prefix="device_share_"
    ).rename(columns={"order_date": "Date"})
    orders_source_share = _share_table(
        orders, index="order_date", column="order_source", value="order_id", prefix="order_source_share_"
    ).rename(columns={"order_date": "Date"})
    customer_signup_daily = (
        customers.groupby("signup_date")
        .agg(new_customers=("customer_id", "count"))
        .reset_index()
        .rename(columns={"signup_date": "Date"})
    )
    signup_channel_share = _share_table(
        customers,
        index="signup_date",
        column="acquisition_channel",
        value="customer_id",
        prefix="signup_channel_share_",
    ).rename(columns={"signup_date": "Date"})
    orders_with_geo = orders.merge(geography[["zip", "region"]], on="zip", how="left")
    orders_region_share = _share_table(
        orders_with_geo,
        index="order_date",
        column="region",
        value="order_id",
        prefix="order_region_share_",
    ).rename(columns={"order_date": "Date"})

    order_details = items.merge(
        orders[
            [
                "order_id",
                "order_date",
                "customer_id",
                "zip",
                "order_status",
                "payment_method",
                "device_type",
                "order_source",
            ]
        ],
        on="order_id",
        how="left",
    ).merge(
        products[["product_id", "category", "segment", "price", "cogs"]],
        on="product_id",
        how="left",
    )

    order_details["gross_rev"] = order_details["quantity"] * order_details["unit_price"]
    order_details["gross_cogs"] = order_details["quantity"] * order_details["cogs"]
    order_details["gross_margin"] = order_details["gross_rev"] - order_details["gross_cogs"]
    order_details["gross_list_value"] = order_details["quantity"] * order_details["price"]
    order_details["discount_rate"] = (
        order_details["discount_amount"] / order_details["gross_list_value"].replace(0, np.nan)
    )
    order_details["has_promo"] = order_details["promo_id"].notna().astype(int)
    order_details["has_promo_2"] = order_details["promo_id_2"].notna().astype(int)

    items_daily = (
        order_details.groupby("order_date")
        .agg(
            total_units=("quantity", "sum"),
            gross_rev_reconstructed=("gross_rev", "sum"),
            gross_cogs_reconstructed=("gross_cogs", "sum"),
            gross_margin=("gross_margin", "sum"),
            avg_unit_price=("unit_price", "mean"),
            total_discount=("discount_amount", "sum"),
            avg_discount_rate=("discount_rate", "mean"),
            promo_line_share=("has_promo", "mean"),
            promo_2_share=("has_promo_2", "mean"),
        )
        .reset_index()
        .rename(columns={"order_date": "Date"})
    )

    category_share = _value_share_table(
        order_details,
        index="order_date",
        column="category",
        value="gross_rev",
        prefix="category_rev_share_",
    ).rename(columns={"order_date": "Date"})

    segment_share = _value_share_table(
        order_details,
        index="order_date",
        column="segment",
        value="gross_rev",
        prefix="segment_rev_share_",
    ).rename(columns={"order_date": "Date"})

    returns_daily = (
        returns.groupby("return_date")
        .agg(
            return_count=("return_id", "count"),
            return_qty=("return_quantity", "sum"),
            refund_amt=("refund_amount", "sum"),
        )
        .reset_index()
        .rename(columns={"return_date": "Date"})
    )
    shipment_details = shipments.merge(
        orders[["order_id", "order_date"]],
        on="order_id",
        how="left",
    )
    shipment_details["order_to_ship_days"] = (
        shipment_details["ship_date"] - shipment_details["order_date"]
    ).dt.days
    shipment_details["ship_to_delivery_days"] = (
        shipment_details["delivery_date"] - shipment_details["ship_date"]
    ).dt.days
    shipment_details["fast_delivery_flag"] = (shipment_details["ship_to_delivery_days"] <= 3).astype(int)
    shipment_details["slow_delivery_flag"] = (shipment_details["ship_to_delivery_days"] >= 6).astype(int)
    shipments_daily = (
        shipment_details.groupby("order_date")
        .agg(
            shipment_count=("order_id", "count"),
            shipping_fee_total=("shipping_fee", "sum"),
            shipping_fee_mean=("shipping_fee", "mean"),
            order_to_ship_days_mean=("order_to_ship_days", "mean"),
            ship_to_delivery_days_mean=("ship_to_delivery_days", "mean"),
            fast_delivery_share=("fast_delivery_flag", "mean"),
            slow_delivery_share=("slow_delivery_flag", "mean"),
        )
        .reset_index()
        .rename(columns={"order_date": "Date"})
    )

    reviews_daily = (
        reviews.groupby("review_date")
        .agg(review_count=("review_id", "count"), avg_rating=("rating", "mean"))
        .reset_index()
        .rename(columns={"review_date": "Date"})
    )

    traffic_daily = (
        traffic.groupby("date")
        .agg(
            sessions=("sessions", "sum"),
            unique_visitors=("unique_visitors", "sum"),
            page_views=("page_views", "sum"),
            bounce_rate=("bounce_rate", "mean"),
            avg_session_duration_sec=("avg_session_duration_sec", "mean"),
        )
        .reset_index()
        .rename(columns={"date": "Date"})
    )

    traffic_source_share = _value_share_table(
        traffic,
        index="date",
        column="traffic_source",
        value="sessions",
        prefix="traffic_share_",
    ).rename(columns={"date": "Date"})

    promo_calendar_rows: list[dict[str, object]] = []
    for row in promotions.itertuples(index=False):
        date_range = pd.date_range(row.start_date, row.end_date, freq="D")
        promo_type = _slugify(row.promo_type)
        promo_channel = _slugify(row.promo_channel)
        promo_category = _slugify(row.applicable_category) if pd.notna(row.applicable_category) else "global"
        for date in date_range:
            promo_days_since_start = int((date - row.start_date).days)
            promo_days_to_end = int((row.end_date - date).days)
            promo_duration_days = int((row.end_date - row.start_date).days) + 1
            record = {
                "Date": date,
                "active_promo_count": 1,
                "active_stackable_promo_count": int(row.stackable_flag),
                "active_promo_discount_value": row.discount_value,
                "active_promo_min_order_value": row.min_order_value,
                "active_promo_stackable_flag": int(row.stackable_flag),
                "promo_days_since_start_mean": promo_days_since_start,
                "promo_days_to_end_mean": promo_days_to_end,
                "promo_duration_days_mean": promo_duration_days,
                "promo_start_count": int(date == row.start_date),
                "promo_end_count": int(date == row.end_date),
                f"active_promo_type_{promo_type}_count": 1,
                f"active_promo_channel_{promo_channel}_count": 1,
                f"active_promo_category_{promo_category}_count": 1,
            }
            if promo_type == "percentage":
                record["active_promo_discount_value_percentage"] = row.discount_value
            elif promo_type == "fixed":
                record["active_promo_discount_value_fixed"] = row.discount_value
            promo_calendar_rows.append(record)
    promo_calendar = pd.DataFrame(promo_calendar_rows)
    if promo_calendar.empty:
        promo_daily = pd.DataFrame(columns=["Date"])
    else:
        count_columns = sorted([col for col in promo_calendar.columns if col.endswith("_count")])
        agg_spec: dict[str, str | tuple[str, str]] = {
            "active_promo_count": "sum",
            "active_stackable_promo_count": "sum",
            "active_promo_discount_value": "mean",
            "active_promo_min_order_value": "mean",
            "active_promo_stackable_flag": "mean",
            "promo_days_since_start_mean": "mean",
            "promo_days_to_end_mean": "mean",
            "promo_duration_days_mean": "mean",
            "promo_start_count": "sum",
            "promo_end_count": "sum",
        }
        for col in count_columns:
            agg_spec[col] = "sum"
        if "active_promo_discount_value_percentage" in promo_calendar.columns:
            agg_spec["active_promo_discount_value_percentage"] = "mean"
        if "active_promo_discount_value_fixed" in promo_calendar.columns:
            agg_spec["active_promo_discount_value_fixed"] = "mean"

        promo_daily = promo_calendar.groupby("Date").agg(agg_spec).reset_index()
        promo_daily = promo_daily.rename(
            columns={
                "active_promo_discount_value": "active_promo_discount_value_mean",
                "active_promo_min_order_value": "active_promo_min_order_value_mean",
                "active_promo_stackable_flag": "active_promo_stackable_share",
                "active_promo_discount_value_percentage": "active_promo_discount_value_percentage_mean",
                "active_promo_discount_value_fixed": "active_promo_discount_value_fixed_mean",
            }
        )

        if "active_promo_count" in promo_daily.columns:
            denom = promo_daily["active_promo_count"].replace(0, np.nan)
            share_count_columns = [
                col
                for col in promo_daily.columns
                if col.endswith("_count")
                and col
                not in {"active_promo_count", "active_stackable_promo_count"}
            ]
            for col in share_count_columns:
                promo_daily[col.replace("_count", "_share")] = promo_daily[col] / denom
            promo_daily["active_promo_type_percentage_share"] = (
                promo_daily.get("active_promo_type_percentage_count", 0.0) / denom
            )
            promo_daily["active_promo_type_fixed_share"] = (
                promo_daily.get("active_promo_type_fixed_count", 0.0) / denom
            )

    inventory_daily = (
        inventory.groupby("snapshot_date")
        .agg(
            stock_on_hand=("stock_on_hand", "sum"),
            units_received=("units_received", "sum"),
            units_sold=("units_sold", "sum"),
            stockout_days_avg=("stockout_days", "mean"),
            days_of_supply_avg=("days_of_supply", "mean"),
            fill_rate_avg=("fill_rate", "mean"),
            stockout_rate=("stockout_flag", "mean"),
            overstock_rate=("overstock_flag", "mean"),
            sell_through_rate_avg=("sell_through_rate", "mean"),
        )
        .reset_index()
        .rename(columns={"snapshot_date": "snapshot_date"})
        .sort_values("snapshot_date")
    )

    inventory_category = (
        inventory.pivot_table(
            index="snapshot_date",
            columns="category",
            values=["stock_on_hand", "stockout_flag"],
            aggfunc={"stock_on_hand": "sum", "stockout_flag": "mean"},
            fill_value=0,
        )
        .sort_index(axis=1)
        .reset_index()
    )
    inventory_category.columns = [
        "snapshot_date"
        if col == ("snapshot_date", "")
        else f"inv_{col[0]}_{_slugify(col[1])}"
        for col in inventory_category.columns
    ]

    for frame in [
        orders_daily,
        orders_payment_share,
        orders_device_share,
        orders_source_share,
        customer_signup_daily,
        signup_channel_share,
        orders_region_share,
        items_daily,
        category_share,
        segment_share,
        shipments_daily,
        returns_daily,
        reviews_daily,
        traffic_daily,
        traffic_source_share,
        promo_daily,
    ]:
        base = base.merge(frame, on="Date", how="left")

    inventory_merged = inventory_daily.merge(inventory_category, on="snapshot_date", how="left")
    base = pd.merge_asof(
        base.sort_values("Date"),
        inventory_merged.sort_values("snapshot_date"),
        left_on="Date",
        right_on="snapshot_date",
        direction="backward",
    )

    zero_fill_columns = [
        "order_count",
        "unique_customers",
        "cancelled_order_share",
        "returned_order_share",
        "delivered_order_share",
        "total_units",
        "gross_rev_reconstructed",
        "gross_cogs_reconstructed",
        "gross_margin",
        "avg_unit_price",
        "total_discount",
        "avg_discount_rate",
        "promo_line_share",
        "promo_2_share",
        "return_count",
        "return_qty",
        "refund_amt",
        "review_count",
    ]
    zero_fill_columns += [
        col
        for col in base.columns
        if col in PROMO_BASE_COLUMNS or col in PROMO_RESEARCH_BASE_COLUMNS or col.startswith("active_promo_")
    ]
    zero_fill_columns += [col for col in base.columns if col in CONTEXT_BASE_COLUMNS]
    zero_fill_columns += [col for col in base.columns if col.startswith(("payment_share_", "device_share_"))]
    zero_fill_columns += [col for col in base.columns if col.startswith(("order_source_share_", "traffic_share_"))]
    zero_fill_columns += [col for col in base.columns if col.startswith(("signup_channel_share_", "order_region_share_"))]
    zero_fill_columns += [col for col in base.columns if col.startswith(("category_rev_share_", "segment_rev_share_"))]

    for col in zero_fill_columns:
        if col in base.columns:
            base[col] = base[col].fillna(0.0)

    if "avg_rating" in base.columns:
        base["avg_rating"] = base["avg_rating"].ffill()
        if base["avg_rating"].isna().any():
            base["avg_rating"] = base["avg_rating"].fillna(base["avg_rating"].median())

    traffic_fill_cols = ["sessions", "unique_visitors", "page_views", "bounce_rate", "avg_session_duration_sec"]
    for col in traffic_fill_cols:
        if col in base.columns:
            observed_mask = base["Date"] <= pd.Timestamp(TRAIN_END)
            base.loc[observed_mask, col] = base.loc[observed_mask, col].ffill().bfill()

    base["units_per_order"] = base["total_units"] / base["order_count"].replace(0, np.nan)
    base["aov_proxy"] = base["gross_rev_reconstructed"] / base["order_count"].replace(0, np.nan)
    base["margin_rate"] = base["gross_margin"] / base["gross_rev_reconstructed"].replace(0, np.nan)
    base["refund_per_return"] = base["refund_amt"] / base["return_qty"].replace(0, np.nan)
    base["sessions_per_visitor"] = base["sessions"] / base["unique_visitors"].replace(0, np.nan)
    base["pageviews_per_session"] = base["page_views"] / base["sessions"].replace(0, np.nan)
    base["conversion_proxy"] = base["order_count"] / base["sessions"].replace(0, np.nan)
    base["shipping_fee_per_order"] = base["shipping_fee_total"] / base["order_count"].replace(0, np.nan)
    base["shipment_order_share"] = base["shipment_count"] / base["order_count"].replace(0, np.nan)
    if "shipment_count" in base.columns:
        base = base.drop(columns=["shipment_count"])

    ratio_cols = [
        "units_per_order",
        "aov_proxy",
        "margin_rate",
        "refund_per_return",
        "sessions_per_visitor",
        "pageviews_per_session",
        "conversion_proxy",
        "shipping_fee_per_order",
        "shipment_order_share",
    ]
    for col in ratio_cols:
        if col in base.columns:
            observed_mask = base["Date"] <= pd.Timestamp(TRAIN_END)
            base.loc[observed_mask, col] = base.loc[observed_mask, col].fillna(0.0)

    base = add_promo_target_encoding_features(base)
    base["is_train"] = (base["Date"] <= pd.Timestamp(TRAIN_END)).astype(int)
    return base.sort_values("Date").reset_index(drop=True)


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    iso = out["Date"].dt.isocalendar()

    out["year"] = out["Date"].dt.year
    out["month"] = out["Date"].dt.month
    out["day"] = out["Date"].dt.day
    out["dayofweek"] = out["Date"].dt.dayofweek
    out["weekofyear"] = iso.week.astype(int)
    out["quarter"] = out["Date"].dt.quarter
    out["dayofyear"] = out["Date"].dt.dayofyear
    out["is_weekend"] = out["dayofweek"].isin([5, 6]).astype(int)
    out["is_month_start"] = out["Date"].dt.is_month_start.astype(int)
    out["is_month_end"] = out["Date"].dt.is_month_end.astype(int)
    out["is_quarter_start"] = out["Date"].dt.is_quarter_start.astype(int)
    out["is_quarter_end"] = out["Date"].dt.is_quarter_end.astype(int)

    out["sin_dayofyear"] = np.sin(2 * np.pi * out["dayofyear"] / 365.25)
    out["cos_dayofyear"] = np.cos(2 * np.pi * out["dayofyear"] / 365.25)
    out["sin_dayofyear_k2"] = np.sin(4 * np.pi * out["dayofyear"] / 365.25)
    out["cos_dayofyear_k2"] = np.cos(4 * np.pi * out["dayofyear"] / 365.25)
    out["sin_dayofyear_k3"] = np.sin(6 * np.pi * out["dayofyear"] / 365.25)
    out["cos_dayofyear_k3"] = np.cos(6 * np.pi * out["dayofyear"] / 365.25)
    out["sin_dayofweek"] = np.sin(2 * np.pi * out["dayofweek"] / 7.0)
    out["cos_dayofweek"] = np.cos(2 * np.pi * out["dayofweek"] / 7.0)
    out["sin_month"] = np.sin(2 * np.pi * out["month"] / 12.0)
    out["cos_month"] = np.cos(2 * np.pi * out["month"] / 12.0)
    
    # EOM/BOM Mini-family
    out["days_to_eom"] = out["Date"].dt.days_in_month - out["day"]
    out["days_from_bom"] = out["day"] - 1
    
    # Holiday/Tet Mini-family (Approximation: active during Jan/Feb)
    out["is_tet_month"] = out["month"].isin([1, 2]).astype(int)
    
    # Calendar Interactions Mini-family
    out["month_weekday_interact"] = out["month"] * 10 + out["dayofweek"]
    
    out = add_lunar_calendar_features(out)
    return out


def add_target_history_features(df: pd.DataFrame, column: str, prefix: str) -> pd.DataFrame:
    out = df.copy()
    features: dict[str, pd.Series] = {}
    shifted = out[column].shift(1)
    plus_prefix = f"{prefix}plus"
    zero_indicator = shifted.eq(0).where(shifted.notna(), np.nan)

    for lag in TARGET_LAG_PERIODS:
        features[f"{prefix}_lag_{lag}"] = out[column].shift(lag)

    for window in TARGET_ROLL_WINDOWS:
        rolling = shifted.rolling(window=window, min_periods=1)
        features[f"{prefix}_rollmean_{window}"] = rolling.mean()
        features[f"{prefix}_rollstd_{window}"] = rolling.std()
        features[f"{prefix}_rollmin_{window}"] = rolling.min()
        features[f"{prefix}_rollmax_{window}"] = rolling.max()
        features[f"{prefix}_ewm_{window}"] = shifted.ewm(span=window, adjust=False).mean()
        features[f"{plus_prefix}_rollmedian_{window}"] = rolling.median()
        features[f"{plus_prefix}_zero_share_{window}"] = (
            zero_indicator.rolling(window=window, min_periods=1).mean()
        )

    features[f"{prefix}_mom_1_7"] = features[f"{prefix}_lag_1"] - features[f"{prefix}_lag_7"]
    features[f"{prefix}_mom_7_28"] = features[f"{prefix}_lag_7"] - features[f"{prefix}_lag_28"]
    features[f"{prefix}_mom_28_364"] = features[f"{prefix}_lag_28"] - features[f"{prefix}_lag_364"]
    features[f"{prefix}_ratio_1_7"] = features[f"{prefix}_lag_1"] / features[f"{prefix}_rollmean_7"].replace(0, np.nan)
    features[f"{prefix}_ratio_7_28"] = features[f"{prefix}_lag_7"] / features[f"{prefix}_rollmean_28"].replace(0, np.nan)
    features[f"{prefix}_yoy_ratio"] = features[f"{prefix}_lag_7"] / features[f"{prefix}_lag_364"].replace(0, np.nan)

    feature_frame = pd.DataFrame(features, index=out.index)
    return pd.concat([out, feature_frame], axis=1)


def _build_recent_key_mean_feature(
    dates: pd.Series,
    keys: pd.Series,
    values: pd.Series,
    window_days: int,
) -> pd.Series:
    from collections import defaultdict, deque

    per_key_queue: dict[object, deque[tuple[pd.Timestamp, float]]] = defaultdict(deque)
    per_key_sum: dict[object, float] = defaultdict(float)
    per_key_count: dict[object, int] = defaultdict(int)
    priors: list[float] = []

    for current_date, key, value in zip(dates, keys, values, strict=False):
        cutoff = current_date - pd.Timedelta(days=window_days)
        queue = per_key_queue[key]
        while queue and queue[0][0] <= cutoff:
            _, old_value = queue.popleft()
            per_key_sum[key] -= old_value
            per_key_count[key] -= 1

        if per_key_count[key] > 0:
            priors.append(per_key_sum[key] / per_key_count[key])
        else:
            priors.append(np.nan)

        if pd.notna(value):
            float_value = float(value)
            queue.append((current_date, float_value))
            per_key_sum[key] += float_value
            per_key_count[key] += 1

    return pd.Series(priors, index=dates.index)


def add_target_seasonal_prior_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    dates = pd.to_datetime(out["Date"])
    month_day_keys = pd.Series(list(zip(dates.dt.month, dates.dt.day, strict=False)), index=out.index)
    month_weekday_keys = pd.Series(list(zip(dates.dt.month, dates.dt.dayofweek, strict=False)), index=out.index)

    out["target_seasonal_rev_md_mean_recent_2y"] = _build_recent_key_mean_feature(
        dates=dates,
        keys=month_day_keys,
        values=out["Revenue"],
        window_days=TARGET_SEASONAL_PRIOR_WINDOW_DAYS,
    )
    out["target_seasonal_rev_mwd_mean_recent_2y"] = _build_recent_key_mean_feature(
        dates=dates,
        keys=month_weekday_keys,
        values=out["Revenue"],
        window_days=TARGET_SEASONAL_PRIOR_WINDOW_DAYS,
    )
    out["target_seasonal_cogs_md_mean_recent_2y"] = _build_recent_key_mean_feature(
        dates=dates,
        keys=month_day_keys,
        values=out["COGS"],
        window_days=TARGET_SEASONAL_PRIOR_WINDOW_DAYS,
    )
    out["target_seasonal_cogs_mwd_mean_recent_2y"] = _build_recent_key_mean_feature(
        dates=dates,
        keys=month_weekday_keys,
        values=out["COGS"],
        window_days=TARGET_SEASONAL_PRIOR_WINDOW_DAYS,
    )
    return out


def add_exogenous_history_features(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    features: dict[str, pd.Series] = {}
    lag_periods = [1, 7, 14, 28]
    roll_windows = [7, 28, 91]

    for col in columns:
        shifted = out[col].shift(1)
        for lag in lag_periods:
            features[f"{col}_lag_{lag}"] = out[col].shift(lag)
        for window in roll_windows:
            rolling = shifted.rolling(window=window, min_periods=1)
            features[f"{col}_rollmean_{window}"] = rolling.mean()
            features[f"{col}_rollstd_{window}"] = rolling.std()

    feature_frame = pd.DataFrame(features, index=out.index)
    price_features = pd.DataFrame(index=out.index)

    if {"avg_unit_price_lag_1", "avg_unit_price_rollmean_7"}.issubset(feature_frame.columns):
        price_features["pricehist_avg_unit_price_ratio_1_7"] = (
            feature_frame["avg_unit_price_lag_1"] / feature_frame["avg_unit_price_rollmean_7"].replace(0, np.nan)
        )
    if {"avg_unit_price_lag_7", "avg_unit_price_rollmean_28"}.issubset(feature_frame.columns):
        price_features["pricehist_avg_unit_price_ratio_7_28"] = (
            feature_frame["avg_unit_price_lag_7"] / feature_frame["avg_unit_price_rollmean_28"].replace(0, np.nan)
        )
    if {"avg_unit_price_lag_1", "avg_unit_price_lag_7"}.issubset(feature_frame.columns):
        price_features["pricehist_avg_unit_price_mom_1_7"] = (
            feature_frame["avg_unit_price_lag_1"] - feature_frame["avg_unit_price_lag_7"]
        )
    if {"margin_rate_lag_1", "margin_rate_rollmean_28"}.issubset(feature_frame.columns):
        price_features["pricehist_margin_rate_ratio_1_28"] = (
            feature_frame["margin_rate_lag_1"] / feature_frame["margin_rate_rollmean_28"].replace(0, np.nan)
        )
    if {
        "avg_discount_rate_rollmean_7",
        "pricehist_avg_unit_price_ratio_1_7",
    }.issubset(price_features.columns.union(feature_frame.columns)):
        price_features["pricehist_discount_x_price_ratio_1_7"] = (
            feature_frame["avg_discount_rate_rollmean_7"] * price_features["pricehist_avg_unit_price_ratio_1_7"]
        )

    return pd.concat([out, feature_frame, price_features], axis=1)


def get_model_signal_columns(df: pd.DataFrame) -> list[str]:
    blocked = {"Date", "Revenue", "COGS", "snapshot_date", "is_train", "gross_rev_reconstructed", "gross_cogs_reconstructed", "tet_date"}
    return [col for col in df.columns if col not in blocked]


def _history_columns_for_stems(columns: list[str], stems: list[str]) -> list[str]:
    matched: list[str] = []
    for col in columns:
        for stem in stems:
            if stem.endswith("_"):
                if col.startswith(stem):
                    matched.append(col)
                    break
            else:
                if col.startswith(f"{stem}_"):
                    matched.append(col)
                    break
    return sorted(set(matched))


def _columns_with_history(columns: list[str], base_columns: list[str]) -> list[str]:
    base_set = set(base_columns)
    return sorted(
        set(
            col
            for col in columns
            if col in base_set or any(col.startswith(f"{base_col}_") for base_col in base_columns)
        )
    )


def get_hierarchy_lite_raw_columns(columns: list[str] | pd.Index) -> list[str]:
    return sorted(
        col for col in columns if any(col.startswith(prefix) for prefix in HIERARCHY_LITE_PREFIXES)
    )


def get_ablation_feature_groups(df: pd.DataFrame) -> dict[str, list[str]]:
    columns = df.columns.tolist()
    groups = {
        "calendar": [col for col in CALENDAR_COLUMNS if col in columns],
        "revenue_history": sorted([col for col in columns if col.startswith("rev_")]),
    }
    for name, stems in ABLATION_SIGNAL_STEMS.items():
        matched = _history_columns_for_stems(columns, stems)
        if name == "promo":
            matched = sorted(set(matched).union(col for col in PROMO_MODEL_COLUMNS if col in columns))
        groups[name] = matched
    groups["promo_slim"] = _columns_with_history(
        columns,
        [col for col in PROMO_SLIM_BASE_COLUMNS if col in columns],
    )
    groups["promo_detail"] = sorted(
        col
        for col in groups.get("promo", [])
        if any(col == stem or col.startswith(f"{stem}_") for stem in PROMO_TARGET_ENCODING_COLUMNS)
    )
    mix_light_stems = ["payment_share_", "device_share_", "order_source_share_"]
    groups["mix_light"] = sorted(
        col for col in columns if any(col.startswith(stem) for stem in mix_light_stems)
    )
    hierarchy_raw_columns = get_hierarchy_lite_raw_columns(columns)
    groups["hierarchy_lite"] = _columns_with_history(columns, hierarchy_raw_columns)
    
    # Expose Mini-Families
    groups["cal_eom_bom"] = [c for c in columns if c in ["days_to_eom", "days_from_bom"]]
    groups["cal_tet"] = [c for c in columns if c in ["is_tet_month"]]
    groups["cal_interact"] = [c for c in columns if c in ["month_weekday_interact"]]
    
    return groups


def get_feature_group_policies() -> dict[str, dict[str, str]]:
    return {name: values.copy() for name, values in FEATURE_GROUP_POLICIES.items()}
