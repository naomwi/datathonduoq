from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


DATASET_DIR = Path("dataset")
LOG_ROOT = Path("logs")
NOTES_DIR = Path("notes")
RUN_PREFIX = "llm_council_feature_audit"
TRAIN_END = pd.Timestamp("2022-12-31")


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def safe_div(num: pd.Series | float, den: pd.Series | float) -> pd.Series | float:
    if np.isscalar(num) and np.isscalar(den):
        return float(num) / float(den) if float(den) else np.nan
    return pd.Series(num, dtype=float) / pd.Series(den, dtype=float).replace(0.0, np.nan)


def pct_change(new: float, old: float) -> float:
    return float((new - old) / old) if np.isfinite(old) and abs(old) > 1e-12 else np.nan


def feature_group(name: str) -> str:
    if name in {"order_count", "unique_customers", "new_customers", "conversion_proxy", "aov_proxy"}:
        return "funnel"
    if name.startswith(("traffic_share_", "sessions", "unique_visitors", "page_views", "bounce_rate", "avg_session")):
        return "traffic"
    if name.startswith(("order_source_share_", "device_share_", "payment_share_", "signup_channel_share_")):
        return "channel_mix"
    if name.startswith(("category_rev_share_", "segment_rev_share_")):
        return "product_mix"
    if name.startswith(("active_promo_", "promo_", "avg_discount", "total_discount")):
        return "promo"
    if name.startswith(("inv_", "stock", "units_received", "units_sold", "fill_rate", "days_of_supply", "sell_through", "overstock")):
        return "inventory"
    if name.startswith(("return_", "refund_", "review_", "avg_rating")):
        return "returns_reviews"
    if name.startswith(("shipping_", "order_to_ship", "ship_to_delivery", "fast_delivery", "slow_delivery", "shipment")):
        return "logistics"
    if name.startswith(("gross_", "margin", "avg_unit_price", "units_per_order")):
        return "price_basket"
    return "other"


def future_policy(name: str) -> str:
    group = feature_group(name)
    if group == "promo":
        return "known_or_policy_future"
    if group in {"funnel", "traffic", "channel_mix", "product_mix", "inventory", "returns_reviews", "logistics", "price_basket"}:
        return "unknown_future_use_train_prior_only"
    return "audit_before_public_use"


def load_daily_train() -> tuple[pd.DataFrame, pd.DataFrame]:
    daily = pd.read_csv(DATASET_DIR / "daily_feature_base.csv", parse_dates=["Date"], low_memory=False)
    train = daily.loc[daily["Date"].le(TRAIN_END) & daily["Date"].dt.year.between(2013, 2022)].copy()
    train["log_revenue"] = np.log1p(train["Revenue"])
    train["log_cogs"] = np.log1p(train["COGS"])
    train["cogs_ratio"] = safe_div(train["COGS"], train["Revenue"])
    train["era"] = np.where(train["Date"].dt.year.le(2018), "pre2019", "post2018")
    train["month_day"] = train["Date"].dt.strftime("%m-%d")
    return daily, train


def corr_pair(frame: pd.DataFrame, feature: str, target: str) -> float:
    pair = frame[[feature, target]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(pair) < 30 or pair[feature].nunique(dropna=True) <= 1:
        return np.nan
    return float(pair[feature].corr(pair[target]))


def build_feature_audit(daily: pd.DataFrame, train: pd.DataFrame) -> pd.DataFrame:
    skip = {"Date", "Revenue", "COGS", "snapshot_date", "is_train"}
    numeric_cols = [col for col in daily.select_dtypes(include=[np.number]).columns if col not in skip]
    future = daily.loc[daily["Date"].gt(TRAIN_END)].copy()
    rows = []
    for col in numeric_cols:
        values = train[col].replace([np.inf, -np.inf], np.nan)
        pre = train.loc[train["era"].eq("pre2019"), col].replace([np.inf, -np.inf], np.nan)
        post = train.loc[train["era"].eq("post2018"), col].replace([np.inf, -np.inf], np.nan)
        monthday = train.groupby("month_day")[col].median(numeric_only=True).replace([np.inf, -np.inf], np.nan)
        pre_mean = float(pre.mean()) if pre.notna().any() else np.nan
        post_mean = float(post.mean()) if post.notna().any() else np.nan
        row = {
            "feature": col,
            "group": feature_group(col),
            "future_policy": future_policy(col),
            "train_missing_rate": float(values.isna().mean()),
            "future_missing_rate": float(future[col].isna().mean()) if col in future.columns and len(future) else np.nan,
            "train_mean": float(values.mean()) if values.notna().any() else np.nan,
            "train_std": float(values.std()) if values.notna().any() else np.nan,
            "pre2019_mean": pre_mean,
            "post2018_mean": post_mean,
            "post_vs_pre_pct": pct_change(post_mean, pre_mean),
            "monthday_cv": float(monthday.std() / abs(monthday.mean())) if monthday.notna().sum() > 5 and abs(monthday.mean()) > 1e-12 else np.nan,
            "corr_revenue": corr_pair(train, col, "Revenue"),
            "corr_cogs": corr_pair(train, col, "COGS"),
            "corr_log_revenue": corr_pair(train, col, "log_revenue"),
            "corr_cogs_ratio": corr_pair(train, col, "cogs_ratio"),
        }
        row["abs_max_corr"] = float(
            np.nanmax(
                np.abs(
                    [
                        row["corr_revenue"],
                        row["corr_cogs"],
                        row["corr_log_revenue"],
                        row["corr_cogs_ratio"],
                    ]
                )
            )
        )
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["abs_max_corr", "post_vs_pre_pct"], ascending=[False, False])


def driver_decomposition(train: pd.DataFrame) -> pd.DataFrame:
    monthly = (
        train.groupby(pd.Grouper(key="Date", freq="MS"))
        .agg(
            revenue=("Revenue", "sum"),
            cogs=("COGS", "sum"),
            sessions=("sessions", "sum"),
            orders=("order_count", "sum"),
        )
        .reset_index()
    )
    monthly["conversion"] = safe_div(monthly["orders"], monthly["sessions"])
    monthly["aov"] = safe_div(monthly["revenue"], monthly["orders"])
    monthly["cogs_ratio"] = safe_div(monthly["cogs"], monthly["revenue"])
    monthly["era"] = np.where(monthly["Date"].dt.year.le(2018), "pre2019", "post2018")
    era = monthly.groupby("era").mean(numeric_only=True)
    rows = []
    for metric in ["revenue", "cogs", "sessions", "orders", "conversion", "aov", "cogs_ratio"]:
        pre = float(era.loc["pre2019", metric])
        post = float(era.loc["post2018", metric])
        rows.append(
            {
                "metric": metric,
                "pre2019_monthly_avg": pre,
                "post2018_monthly_avg": post,
                "post_vs_pre_pct": pct_change(post, pre),
            }
        )
    return pd.DataFrame(rows)


def source_quality_by_era() -> pd.DataFrame:
    orders = pd.read_csv(DATASET_DIR / "orders.csv", parse_dates=["order_date"], low_memory=False)
    items = pd.read_csv(DATASET_DIR / "order_items.csv", low_memory=False)
    traffic = pd.read_csv(DATASET_DIR / "web_traffic.csv", parse_dates=["date"], low_memory=False)

    item_rev = items.assign(net_value=items["quantity"] * items["unit_price"] - items["discount_amount"].fillna(0.0))
    order_value = item_rev.groupby("order_id", as_index=False).agg(net_value=("net_value", "sum"))
    orders = orders.merge(order_value, on="order_id", how="left")
    orders["era"] = np.where(orders["order_date"].dt.year.le(2018), "pre2019", "post2018")
    order_source = (
        orders.loc[orders["order_date"].dt.year.between(2013, 2022)]
        .groupby(["era", "order_source"], as_index=False)
        .agg(orders=("order_id", "nunique"), order_value=("net_value", "sum"), cancelled_share=("order_status", lambda s: float(s.eq("cancelled").mean())))
        .rename(columns={"order_source": "source"})
    )
    traffic["era"] = np.where(traffic["date"].dt.year.le(2018), "pre2019", "post2018")
    traffic_source = (
        traffic.loc[traffic["date"].dt.year.between(2013, 2022)]
        .groupby(["era", "traffic_source"], as_index=False)
        .agg(sessions=("sessions", "sum"), unique_visitors=("unique_visitors", "sum"))
        .rename(columns={"traffic_source": "source"})
    )
    out = order_source.merge(traffic_source, on=["era", "source"], how="outer")
    out["orders_per_session"] = safe_div(out["orders"], out["sessions"])
    out["revenue_per_session"] = safe_div(out["order_value"], out["sessions"])
    return out.sort_values(["era", "revenue_per_session"], ascending=[True, False])


def payment_cancellation() -> pd.DataFrame:
    orders = pd.read_csv(DATASET_DIR / "orders.csv", parse_dates=["order_date"], low_memory=False)
    frame = orders.loc[orders["order_date"].dt.year.between(2013, 2022)].copy()
    out = (
        frame.groupby("payment_method", as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            cancelled=("order_status", lambda s: int(s.eq("cancelled").sum())),
            returned_status=("order_status", lambda s: int(s.eq("returned").sum())),
        )
        .sort_values("orders", ascending=False)
    )
    out["cancel_rate"] = safe_div(out["cancelled"], out["orders"])
    out["returned_status_rate"] = safe_div(out["returned_status"], out["orders"])
    return out


def return_reason_summary() -> pd.DataFrame:
    returns = pd.read_csv(DATASET_DIR / "returns.csv", parse_dates=["return_date"], low_memory=False)
    products = pd.read_csv(DATASET_DIR / "products.csv", low_memory=False)
    frame = returns.merge(products[["product_id", "category", "segment", "size", "color"]], on="product_id", how="left")
    return (
        frame.loc[frame["return_date"].dt.year.between(2013, 2022)]
        .groupby(["return_reason", "category"], as_index=False)
        .agg(return_records=("return_id", "count"), return_qty=("return_quantity", "sum"), refund_amount=("refund_amount", "sum"))
        .sort_values("refund_amount", ascending=False)
    )


def inventory_category_summary() -> pd.DataFrame:
    inventory = pd.read_csv(DATASET_DIR / "inventory.csv", parse_dates=["snapshot_date"], low_memory=False)
    frame = inventory.loc[inventory["snapshot_date"].dt.year.between(2013, 2022)].copy()
    return (
        frame.groupby("category", as_index=False)
        .agg(
            stockout_days=("stockout_days", "sum"),
            fill_rate=("fill_rate", "mean"),
            sell_through_rate=("sell_through_rate", "mean"),
            days_of_supply=("days_of_supply", "mean"),
            stockout_flag=("stockout_flag", "mean"),
        )
        .sort_values("stockout_days", ascending=False)
    )


def customer_cohort_summary() -> pd.DataFrame:
    orders = pd.read_csv(DATASET_DIR / "orders.csv", parse_dates=["order_date"], low_memory=False)
    customers = pd.read_csv(DATASET_DIR / "customers.csv", parse_dates=["signup_date"], low_memory=False)
    frame = orders.loc[orders["order_date"].dt.year.between(2013, 2022)].copy()
    frame = frame.sort_values(["customer_id", "order_date", "order_id"])
    frame["prior_orders"] = frame.groupby("customer_id").cumcount()
    frame["is_repeat_customer"] = frame["prior_orders"].gt(0)
    frame = frame.merge(customers[["customer_id", "signup_date", "gender", "age_group", "acquisition_channel"]], on="customer_id", how="left")
    frame["tenure_days"] = (frame["order_date"] - frame["signup_date"]).dt.days.clip(lower=0)
    frame["era"] = np.where(frame["order_date"].dt.year.le(2018), "pre2019", "post2018")
    return (
        frame.groupby("era", as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            unique_customers=("customer_id", "nunique"),
            repeat_order_share=("is_repeat_customer", "mean"),
            avg_customer_tenure_days=("tenure_days", "mean"),
            mobile_order_share=("device_type", lambda s: float(s.eq("mobile").mean())),
            cod_order_share=("payment_method", lambda s: float(s.eq("cod").mean())),
        )
    )


def product_size_color_gap() -> pd.DataFrame:
    orders = pd.read_csv(DATASET_DIR / "orders.csv", parse_dates=["order_date"], low_memory=False)
    items = pd.read_csv(DATASET_DIR / "order_items.csv", low_memory=False)
    products = pd.read_csv(DATASET_DIR / "products.csv", low_memory=False)
    frame = items.merge(orders[["order_id", "order_date"]], on="order_id", how="left").merge(
        products[["product_id", "category", "segment", "size", "color", "cogs"]], on="product_id", how="left"
    )
    frame = frame.loc[frame["order_date"].dt.year.between(2013, 2022)].copy()
    frame["net_value"] = frame["quantity"] * frame["unit_price"] - frame["discount_amount"].fillna(0.0)
    frame["era"] = np.where(frame["order_date"].dt.year.le(2018), "pre2019", "post2018")
    by_size = (
        frame.groupby(["era", "category", "size"], as_index=False)
        .agg(net_value=("net_value", "sum"), units=("quantity", "sum"))
        .sort_values("net_value", ascending=False)
    )
    totals = by_size.groupby("era", as_index=False).agg(total_value=("net_value", "sum"))
    by_size = by_size.merge(totals, on="era", how="left")
    by_size["value_share"] = safe_div(by_size["net_value"], by_size["total_value"])
    return by_size.sort_values(["era", "value_share"], ascending=[True, False])


def build_feature_gap_candidates(
    driver: pd.DataFrame,
    source_quality: pd.DataFrame,
    payments: pd.DataFrame,
    returns: pd.DataFrame,
    inventory: pd.DataFrame,
    cohorts: pd.DataFrame,
) -> pd.DataFrame:
    changes = driver.set_index("metric")["post_vs_pre_pct"].to_dict()
    cod = payments.loc[payments["payment_method"].eq("cod")]
    non_cod_cancel = payments.loc[~payments["payment_method"].eq("cod"), "cancelled"].sum()
    non_cod_orders = payments.loc[~payments["payment_method"].eq("cod"), "orders"].sum()
    cod_text = "COD missing"
    if not cod.empty:
        cod_cancel = float(cod["cancel_rate"].iloc[0])
        other_cancel = safe_div(non_cod_cancel, non_cod_orders)
        cod_text = f"COD cancel {cod_cancel:.1%} vs non-COD {other_cancel:.1%}"
    top_return = returns.head(1)
    return_text = "returns missing"
    if not top_return.empty:
        row = top_return.iloc[0]
        return_text = f"top refund reason/category: {row['return_reason']} / {row['category']} = {row['refund_amount']:,.0f}"
    top_inventory = inventory.head(1)
    inventory_text = "inventory missing"
    if not top_inventory.empty:
        row = top_inventory.iloc[0]
        inventory_text = f"{row['category']} stockout_days={row['stockout_days']:,.0f}, fill_rate={row['fill_rate']:.2%}"
    cohort_text = "cohort missing"
    if set(cohorts["era"]) >= {"pre2019", "post2018"}:
        pre = cohorts.set_index("era").loc["pre2019"]
        post = cohorts.set_index("era").loc["post2018"]
        cohort_text = f"repeat_order_share {pre['repeat_order_share']:.1%}->{post['repeat_order_share']:.1%}, tenure {pre['avg_customer_tenure_days']:.0f}->{post['avg_customer_tenure_days']:.0f} days"

    social = source_quality.loc[source_quality["source"].eq("social_media")]
    organic = source_quality.loc[source_quality["source"].eq("organic_search")]
    source_text = "source quality table generated"
    if not social.empty and not organic.empty:
        latest_social = social.loc[social["era"].eq("post2018")]
        latest_organic = organic.loc[organic["era"].eq("post2018")]
        if not latest_social.empty and not latest_organic.empty:
            source_text = (
                f"post2018 rev/session social={latest_social['revenue_per_session'].iloc[0]:.2f}, "
                f"organic={latest_organic['revenue_per_session'].iloc[0]:.2f}"
            )

    rows = [
        {
            "rank": 1,
            "hypothesis": "period_total_funnel_head_v1",
            "missing_mechanism": "The clean winner tunes period totals, but not through an explicit sessions x conversion x AOV decomposition.",
            "evidence": f"sessions {changes.get('sessions', np.nan):+.1%}, orders {changes.get('orders', np.nan):+.1%}, conversion {changes.get('conversion', np.nan):+.1%}, AOV {changes.get('aov', np.nan):+.1%} post2018 vs pre2019",
            "raw_sources": "web_traffic.csv, orders.csv, order_items.csv, sales.csv",
            "model_layer": "period-total head",
            "clean_status": "strict clean if weights selected by rolling folds; clean-input public-guided if using public to choose regime weights",
            "next_experiment": "Train/validate period totals for Revenue and COGS via sessions_prior, conversion_regime, AOV_regime; daily shape stays raw-md/calendar.",
        },
        {
            "rank": 2,
            "hypothesis": "source_quality_conversion_head_v1",
            "missing_mechanism": "Traffic volume is not equal to buying intent; source-specific conversion/revenue per session may explain regime shift.",
            "evidence": source_text,
            "raw_sources": "web_traffic.csv, orders.csv, order_items.csv",
            "model_layer": "period-total/funnel head, not daily postprocess",
            "clean_status": "strict clean if future source mix is month/era prior; no future actual source shares",
            "next_experiment": "Forecast effective_sessions = sum(source_sessions_prior * source_revenue_per_session_regime), then blend into period totals.",
        },
        {
            "rank": 3,
            "hypothesis": "customer_cohort_repeat_head_v1",
            "missing_mechanism": "Feature pipeline has new/customers counts but not repeat-customer share, tenure, age/gender/acquisition mix as a regime driver.",
            "evidence": cohort_text,
            "raw_sources": "orders.csv, customers.csv",
            "model_layer": "period-total head and validation segmentation",
            "clean_status": "strict clean with historical cohort priors; future actual customers/orders are not allowed",
            "next_experiment": "Build repeat/tenure monthly priors and test if they explain conversion collapse on rolling folds.",
        },
        {
            "rank": 4,
            "hypothesis": "orderdate_return_leakage_head_v1",
            "missing_mechanism": "Current return features are by return_date; revenue leakage is more naturally attached to original order_date/category/size.",
            "evidence": return_text,
            "raw_sources": "returns.csv, orders.csv, order_items.csv, products.csv",
            "model_layer": "COGS/Revenue netting or COGS-ratio head",
            "clean_status": "strict clean using train return-rate priors by category/size/month; no future return actuals",
            "next_experiment": "Re-align refunds to order_date and create expected_refund_rate prior; test period-level net revenue/COGS adjustment.",
        },
        {
            "rank": 5,
            "hypothesis": "sku_size_stockout_pressure_v1",
            "missing_mechanism": "Existing inventory features are category-level; PDF says stockouts are concentrated in high-demand Streetwear SKUs/sizes.",
            "evidence": inventory_text,
            "raw_sources": "inventory.csv, products.csv, order_items.csv",
            "model_layer": "period-total head or product-mix constraint",
            "clean_status": "strict clean only as historical stockout-pressure prior; do not use future actual inventory",
            "next_experiment": "Build SKU/size/color stockout_pressure x historical demand share; test if it improves COGS ratio or level folds.",
        },
        {
            "rank": 6,
            "hypothesis": "cod_effective_order_quality_v1",
            "missing_mechanism": "COD can inflate gross order intent while producing cancellations; better modeled as effective_orders.",
            "evidence": cod_text,
            "raw_sources": "orders.csv, payments.csv",
            "model_layer": "funnel conversion head",
            "clean_status": "strict clean with train COD risk priors by month/source/region",
            "next_experiment": "orders_effective = orders_prior * (1 - cod_share_prior * excess_cod_cancel_rate); validate on post2018 folds.",
        },
    ]
    return pd.DataFrame(rows)


def write_report(
    run_dir: Path,
    driver: pd.DataFrame,
    top_features: pd.DataFrame,
    candidates: pd.DataFrame,
    source_quality: pd.DataFrame,
    payments: pd.DataFrame,
    cohorts: pd.DataFrame,
) -> None:
    report = f"""# LLM Council Feature Audit

Run directory: `{run_dir}`

## Boundary

This is a clean-feature discovery audit. It does not use `sample_submission.csv`, previous submissions, public-blackbox files, or test target values as inputs.

The method follows a practical LLM-council style:

- Business analyst: convert the PDF into business mechanisms.
- Data scientist: quantify train evidence and regime shifts.
- ML engineer: map mechanisms to model layers.
- Checker: classify clean legality and leakage risk.

## Current Clean Status

- Current clean best public: `submission_cleanv2_h1fine_b044_r0876.csv = 673757.34993`.
- Latest operational COGS-ratio probe failed: `submission_cleanv4_opratio_g020.csv = 677137.31895`.
- Interpretation: daily operational COGS-ratio priors are not the missing clean signal; focus should move back to period-total/funnel features.

## Driver Decomposition

{driver.to_markdown(index=False)}

## Top Raw-Derived Feature Signals

{top_features.to_markdown(index=False)}

## Council Candidate Backlog

{candidates.to_markdown(index=False)}

## Source Quality Snapshot

{source_quality.head(12).to_markdown(index=False)}

## Payment Cancellation Snapshot

{payments.to_markdown(index=False)}

## Customer Cohort Snapshot

{cohorts.to_markdown(index=False)}

## Council Decision

The highest-value clean route is not another daily shape or COGS-ratio tweak. The missing layer is an explicit period-total funnel model:

`period Revenue = sessions_prior x conversion_regime x AOV_regime`

The next clean implementation should build this head first, then add source-quality and cohort/repeat-customer priors only if rolling folds show they improve MAE without hurting RMSE/R2.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "llm_council_feature_audit_2026-04-28.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    daily, train = load_daily_train()
    feature_audit = build_feature_audit(daily, train)
    driver = driver_decomposition(train)
    source_quality = source_quality_by_era()
    payments = payment_cancellation()
    returns = return_reason_summary()
    inventory = inventory_category_summary()
    cohorts = customer_cohort_summary()
    product_size = product_size_color_gap()
    candidates = build_feature_gap_candidates(driver, source_quality, payments, returns, inventory, cohorts)

    feature_audit.to_csv(run_dir / "feature_audit.csv", index=False)
    driver.to_csv(run_dir / "driver_decomposition.csv", index=False)
    source_quality.to_csv(run_dir / "source_quality_by_era.csv", index=False)
    payments.to_csv(run_dir / "payment_cancellation.csv", index=False)
    returns.to_csv(run_dir / "return_reason_summary.csv", index=False)
    inventory.to_csv(run_dir / "inventory_category_summary.csv", index=False)
    cohorts.to_csv(run_dir / "customer_cohort_summary.csv", index=False)
    product_size.to_csv(run_dir / "product_size_color_gap.csv", index=False)
    candidates.to_csv(run_dir / "feature_gap_candidates.csv", index=False)

    top_features = feature_audit[
        [
            "feature",
            "group",
            "future_policy",
            "abs_max_corr",
            "corr_revenue",
            "corr_cogs",
            "corr_cogs_ratio",
            "post_vs_pre_pct",
            "monthday_cv",
        ]
    ].head(25)
    write_report(run_dir, driver, top_features, candidates, source_quality, payments, cohorts)
    print(run_dir)
    print(candidates[["rank", "hypothesis", "model_layer", "clean_status"]].to_string(index=False))


if __name__ == "__main__":
    main()
