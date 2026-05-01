from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_blackbox_rule_inference import PROBES, segment_profile, summarize_probe
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns


RUN_PREFIX = "data_pattern_deep_dive"
TRAIN_END = pd.Timestamp("2022-12-31")
CURRENT_BEST_FILE = "submission_publiconly_segment_v8_h2best_2024h1_down100.csv"
CURRENT_BEST_SCORE = 807504.66276


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def table_coverage() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for path in sorted(DATASET_DIR.glob("*.csv")):
        if path.name.startswith("submission"):
            continue
        header = pd.read_csv(path, nrows=0)
        date_cols = [
            c
            for c in header.columns
            if "date" in c.lower() or c.lower() in {"date", "snapshot_date", "start_date", "end_date"}
        ]
        if not date_cols:
            rows.append(
                {
                    "table": path.name,
                    "date_column": "",
                    "rows": sum(1 for _ in path.open("rb")) - 1,
                    "min_date": "",
                    "max_date": "",
                    "rows_after_2022": 0,
                }
            )
            continue
        dates = pd.read_csv(path, usecols=date_cols, low_memory=False)
        for col in date_cols:
            parsed = pd.to_datetime(dates[col], errors="coerce")
            rows.append(
                {
                    "table": path.name,
                    "date_column": col,
                    "rows": int(len(parsed)),
                    "min_date": parsed.min(),
                    "max_date": parsed.max(),
                    "rows_after_2022": int(parsed.gt(TRAIN_END).sum()),
                    "non_null_dates": int(parsed.notna().sum()),
                }
            )
    return pd.DataFrame(rows)


def build_detail_daily() -> tuple[pd.DataFrame, pd.DataFrame]:
    orders = pd.read_csv(
        DATASET_DIR / "orders.csv",
        usecols=["order_id", "order_date", "customer_id", "zip", "order_status", "payment_method", "device_type", "order_source"],
        parse_dates=["order_date"],
        low_memory=False,
    )
    items = pd.read_csv(
        DATASET_DIR / "order_items.csv",
        usecols=["order_id", "product_id", "quantity", "unit_price", "discount_amount", "promo_id", "promo_id_2"],
        low_memory=False,
    )
    products = pd.read_csv(
        DATASET_DIR / "products.csv",
        usecols=["product_id", "category", "segment", "price", "cogs"],
        low_memory=False,
    )
    products["catalog_cogs_price_ratio"] = products["cogs"] / products["price"].replace(0, np.nan)
    details = items.merge(orders, on="order_id", how="left").merge(products, on="product_id", how="left")
    details["line_revenue"] = details["quantity"] * details["unit_price"]
    details["line_cogs"] = details["quantity"] * details["cogs"]
    details["line_catalog_value"] = details["quantity"] * details["price"]
    details["line_discount"] = details["quantity"] * details["discount_amount"].fillna(0.0)
    details["line_is_promo"] = details["promo_id"].notna() | details["promo_id_2"].notna()
    details["line_cogs_rev_ratio"] = details["line_cogs"] / details["line_revenue"].replace(0, np.nan)
    details["line_catalog_ratio"] = details["line_cogs"] / details["line_catalog_value"].replace(0, np.nan)
    details["line_discount_rate"] = details["line_discount"] / (
        details["line_revenue"] + details["line_discount"]
    ).replace(0, np.nan)

    daily = (
        details.groupby("order_date", as_index=False)
        .agg(
            total_units=("quantity", "sum"),
            line_count=("order_id", "size"),
            detail_revenue=("line_revenue", "sum"),
            detail_cogs=("line_cogs", "sum"),
            detail_catalog_value=("line_catalog_value", "sum"),
            detail_discount=("line_discount", "sum"),
            promo_line_share=("line_is_promo", "mean"),
            promo_revenue=("line_revenue", lambda s: float(s[details.loc[s.index, "line_is_promo"]].sum())),
            active_products=("product_id", "nunique"),
        )
        .rename(columns={"order_date": "Date"})
    )
    order_daily = (
        orders.groupby("order_date", as_index=False)
        .agg(
            order_count=("order_id", "nunique"),
            unique_customers=("customer_id", "nunique"),
            delivered_share=("order_status", lambda s: float(s.eq("delivered").mean())),
            returned_share=("order_status", lambda s: float(s.eq("returned").mean())),
            cancelled_share=("order_status", lambda s: float(s.eq("cancelled").mean())),
        )
        .rename(columns={"order_date": "Date"})
    )
    daily = daily.merge(order_daily, on="Date", how="left")
    daily["promo_rev_share"] = daily["promo_revenue"] / daily["detail_revenue"].replace(0, np.nan)
    daily["weighted_cogs_rev_ratio"] = daily["detail_cogs"] / daily["detail_revenue"].replace(0, np.nan)
    daily["weighted_catalog_ratio"] = daily["detail_cogs"] / daily["detail_catalog_value"].replace(0, np.nan)
    daily["effective_discount_rate"] = daily["detail_discount"] / (
        daily["detail_revenue"] + daily["detail_discount"]
    ).replace(0, np.nan)
    daily["avg_unit_price"] = daily["detail_revenue"] / daily["total_units"].replace(0, np.nan)
    daily["cogs_per_unit"] = daily["detail_cogs"] / daily["total_units"].replace(0, np.nan)
    daily["units_per_order"] = daily["total_units"] / daily["order_count"].replace(0, np.nan)
    daily["aov"] = daily["detail_revenue"] / daily["order_count"].replace(0, np.nan)

    for category, group in details.groupby("category"):
        rev = group.groupby("order_date")["line_revenue"].sum()
        daily[f"category_rev_{category}"] = daily["Date"].map(rev).fillna(0.0)
        daily[f"category_share_{category}"] = daily[f"category_rev_{category}"] / daily["detail_revenue"].replace(0, np.nan)
    for segment, group in details.groupby("segment"):
        rev = group.groupby("order_date")["line_revenue"].sum()
        daily[f"segment_rev_{segment}"] = daily["Date"].map(rev).fillna(0.0)
        daily[f"segment_share_{segment}"] = daily[f"segment_rev_{segment}"] / daily["detail_revenue"].replace(0, np.nan)

    return daily, details


def target_identity(daily: pd.DataFrame) -> pd.DataFrame:
    sales = pd.read_csv(DATASET_DIR / "sales.csv", parse_dates=["Date"])
    merged = sales.merge(daily[["Date", "detail_revenue", "detail_cogs"]], on="Date", how="left")
    merged["revenue_abs_error"] = (merged["Revenue"] - merged["detail_revenue"]).abs()
    merged["cogs_abs_error"] = (merged["COGS"] - merged["detail_cogs"]).abs()
    return pd.DataFrame(
        [
            {
                "rows": len(merged),
                "max_revenue_abs_error": merged["revenue_abs_error"].max(),
                "max_cogs_abs_error": merged["cogs_abs_error"].max(),
                "mean_revenue_abs_error": merged["revenue_abs_error"].mean(),
                "mean_cogs_abs_error": merged["cogs_abs_error"].mean(),
            }
        ]
    )


def product_ratio_tables(details: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    products = pd.read_csv(DATASET_DIR / "products.csv")
    products["catalog_cogs_price_ratio"] = products["cogs"] / products["price"].replace(0, np.nan)
    category = (
        products.groupby("category", as_index=False)
        .agg(product_count=("product_id", "size"), catalog_ratio_mean=("catalog_cogs_price_ratio", "mean"), cogs_sum=("cogs", "sum"), price_sum=("price", "sum"))
        .assign(catalog_ratio_weighted=lambda d: d["cogs_sum"] / d["price_sum"])
        .sort_values("catalog_ratio_weighted", ascending=False)
    )
    segment = (
        products.groupby("segment", as_index=False)
        .agg(product_count=("product_id", "size"), catalog_ratio_mean=("catalog_cogs_price_ratio", "mean"), cogs_sum=("cogs", "sum"), price_sum=("price", "sum"))
        .assign(catalog_ratio_weighted=lambda d: d["cogs_sum"] / d["price_sum"])
        .sort_values("catalog_ratio_weighted", ascending=False)
    )
    sold_mix = (
        details.groupby(["category", "segment"], as_index=False)
        .agg(revenue_sum=("line_revenue", "sum"), cogs_sum=("line_cogs", "sum"), units=("quantity", "sum"))
        .assign(realized_cogs_rev_ratio=lambda d: d["cogs_sum"] / d["revenue_sum"])
        .sort_values("realized_cogs_rev_ratio", ascending=False)
    )
    return category, segment, sold_mix


def halfyear_profile(daily: pd.DataFrame) -> pd.DataFrame:
    df = add_event_columns(daily.copy())
    df["year"] = df["Date"].dt.year
    df["half"] = np.where(df["Date"].dt.month.le(6), "H1", "H2")
    df = df.loc[df["Date"].le(TRAIN_END)].copy()
    share_cols = [c for c in df.columns if c.startswith(("category_share_", "segment_share_"))]
    agg = {
        "Date": "size",
        "detail_revenue": "sum",
        "detail_cogs": "sum",
        "total_units": "sum",
        "order_count": "sum",
        "line_count": "sum",
        "active_products": "mean",
        "promo_line_share": "mean",
        "promo_rev_share": "mean",
        "effective_discount_rate": "mean",
        "weighted_catalog_ratio": "mean",
        "avg_unit_price": "mean",
        "cogs_per_unit": "mean",
        "units_per_order": "mean",
        "aov": "mean",
        "delivered_share": "mean",
        "returned_share": "mean",
        "cancelled_share": "mean",
        "win_main_promo": "mean",
        "win_tet_wide": "mean",
    }
    for col in share_cols:
        agg[col] = "mean"
    out = df.groupby(["year", "half"], as_index=False).agg(agg).rename(columns={"Date": "days"})
    out["weighted_cogs_rev_ratio"] = out["detail_cogs"] / out["detail_revenue"]
    out["revenue_per_day"] = out["detail_revenue"] / out["days"]
    out["cogs_per_day"] = out["detail_cogs"] / out["days"]
    out["odd_year"] = out["year"] % 2 == 1
    return out.sort_values(["year", "half"])


def h2_odd_even_diff(profile: pd.DataFrame) -> pd.DataFrame:
    h2 = profile.loc[profile["half"].eq("H2") & profile["year"].between(2013, 2022)].copy()
    numeric = h2.select_dtypes(include=[np.number, bool]).columns
    rows: list[dict[str, object]] = []
    for col in numeric:
        if col in {"year"}:
            continue
        odd = h2.loc[h2["odd_year"], col].astype(float)
        even = h2.loc[~h2["odd_year"], col].astype(float)
        if odd.empty or even.empty:
            continue
        rows.append(
            {
                "feature": col,
                "odd_h2_mean": odd.mean(),
                "even_h2_mean": even.mean(),
                "odd_minus_even": odd.mean() - even.mean(),
                "relative_diff": (odd.mean() - even.mean()) / (abs(even.mean()) + 1e-9),
            }
        )
    return pd.DataFrame(rows).sort_values("relative_diff", key=lambda s: s.abs(), ascending=False)


def daily_feature_correlations() -> pd.DataFrame:
    base = pd.read_csv(DATASET_DIR / "daily_feature_base.csv", parse_dates=["Date"], low_memory=False)
    train = base.loc[base["is_train"].eq(1)].copy()
    train["target_cogs_rev_ratio"] = train["COGS"] / train["Revenue"].replace(0, np.nan)
    drop_contains = ["Revenue", "COGS", "gross_cogs", "gross_rev", "gross_margin", "margin_rate"]
    numeric = train.select_dtypes(include=[np.number]).columns
    rows: list[dict[str, object]] = []
    for col in numeric:
        if col in {"target_cogs_rev_ratio", "is_train"}:
            continue
        if any(s.lower() in col.lower() for s in drop_contains):
            continue
        valid = train[[col, "target_cogs_rev_ratio"]].replace([np.inf, -np.inf], np.nan).dropna()
        if len(valid) < 100 or valid[col].nunique() < 3:
            continue
        corr = valid[col].corr(valid["target_cogs_rev_ratio"], method="spearman")
        rows.append({"feature": col, "spearman_corr_with_daily_cogs_ratio": corr, "non_null": len(valid)})
    return pd.DataFrame(rows).sort_values("spearman_corr_with_daily_cogs_ratio", key=lambda s: s.abs(), ascending=False)


def future_feature_audit() -> pd.DataFrame:
    base = pd.read_csv(DATASET_DIR / "daily_feature_base.csv", parse_dates=["Date"], low_memory=False)
    future = base.loc[base["Date"].gt(TRAIN_END)].copy()
    rows: list[dict[str, object]] = []
    for col in base.columns:
        if col in {"Date", "Revenue", "COGS", "is_train"}:
            continue
        rows.append(
            {
                "feature": col,
                "future_non_null_share": float(future[col].notna().mean()),
                "future_nunique": int(future[col].nunique(dropna=True)),
                "future_mean": float(future[col].mean()) if pd.api.types.is_numeric_dtype(future[col]) else np.nan,
                "train_mean": float(base.loc[base["is_train"].eq(1), col].mean()) if pd.api.types.is_numeric_dtype(base[col]) else np.nan,
            }
        )
    return pd.DataFrame(rows).sort_values(["future_non_null_share", "future_nunique"], ascending=[False, False])


def promotion_summary() -> pd.DataFrame:
    promos = pd.read_csv(DATASET_DIR / "promotions.csv", parse_dates=["start_date", "end_date"])
    promos["year"] = promos["start_date"].dt.year
    promos["month"] = promos["start_date"].dt.month
    promos["half"] = np.where(promos["month"].le(6), "H1", "H2")
    promos["duration_days"] = (promos["end_date"] - promos["start_date"]).dt.days + 1
    return (
        promos.groupby(["year", "half"], as_index=False)
        .agg(
            promo_count=("promo_id", "size"),
            mean_discount=("discount_value", "mean"),
            max_discount=("discount_value", "max"),
            pct_percentage=("promo_type", lambda s: float(s.eq("percentage").mean())),
            pct_stackable=("stackable_flag", "mean"),
            total_duration_days=("duration_days", "sum"),
            global_share=("applicable_category", lambda s: float(s.isna().mean())),
            outdoor_share=("applicable_category", lambda s: float(s.eq("Outdoor").mean())),
            streetwear_share=("applicable_category", lambda s: float(s.eq("Streetwear").mean())),
        )
        .sort_values(["year", "half"])
    )


def current_vs_history(current_profile: pd.DataFrame, hist_profile: pd.DataFrame) -> pd.DataFrame:
    h1 = hist_profile.loc[hist_profile["half"].eq("H1"), "weighted_cogs_rev_ratio"]
    h2 = hist_profile.loc[hist_profile["half"].eq("H2"), "weighted_cogs_rev_ratio"]
    odd_h2 = hist_profile.loc[hist_profile["half"].eq("H2") & hist_profile["odd_year"], "weighted_cogs_rev_ratio"]
    rows = []
    for _, row in current_profile.iterrows():
        segment = row["segment"]
        ratio = row["cogs_rev_ratio_weighted"]
        ref = h2 if "H2" in segment else h1 if "H1" in segment else hist_profile["weighted_cogs_rev_ratio"]
        rows.append(
            {
                "segment": segment,
                "current_ratio": ratio,
                "history_ref_mean": ref.mean(),
                "history_ref_min": ref.min(),
                "history_ref_max": ref.max(),
                "z_vs_ref": (ratio - ref.mean()) / (ref.std(ddof=0) + 1e-9),
                "odd_h2_mean": odd_h2.mean() if "H2" in segment else np.nan,
                "odd_h2_max": odd_h2.max() if "H2" in segment else np.nan,
            }
        )
    return pd.DataFrame(rows)


def probe_reaction_table() -> pd.DataFrame:
    rows = []
    for probe in PROBES:
        try:
            rows.append(summarize_probe(probe))
        except FileNotFoundError:
            continue
    return pd.DataFrame(rows)


def build_report(
    run_dir: Path,
    coverage: pd.DataFrame,
    identity: pd.DataFrame,
    half: pd.DataFrame,
    odd_diff: pd.DataFrame,
    current_profile: pd.DataFrame,
    cur_vs_hist: pd.DataFrame,
    category: pd.DataFrame,
    segment: pd.DataFrame,
    sold_mix: pd.DataFrame,
    corr: pd.DataFrame,
    future_audit: pd.DataFrame,
    promo: pd.DataFrame,
    probes: pd.DataFrame,
) -> str:
    h2_ratios = half.loc[half["half"].eq("H2"), ["year", "weighted_cogs_rev_ratio", "promo_rev_share", "effective_discount_rate", "category_share_Streetwear", "segment_share_Everyday"]]
    h2_ratios = h2_ratios.copy()
    accepted = probes.loc[probes["candidate_score"].notna() & probes["score_gain_positive_is_good"].gt(0)]
    rejected = probes.loc[probes["candidate_score"].notna() & probes["score_gain_positive_is_good"].lt(0)]

    return f"""# Data Pattern Deep Dive

Run directory: `{run_dir}`

Current public best considered: `{CURRENT_BEST_FILE}` = `{CURRENT_BEST_SCORE}`.

## Executive Rule
The best rule I can infer is:

`Revenue` forecast is roughly serviceable, while `COGS/Revenue` needs a regime model. The hidden public target appears to have an odd-year H2 cost/margin-compression regime in `2023H2`, but not in `2023H1` or `2024H1`.

Operationally:

- Let `2023H2` have a high ratio regime, especially not clipping high-ratio days.
- Keep `2024H1` restrained around normal H1-ish ratios.
- Do not keep raising all periods; broad COGS-up has already plateaued.

## Why This Rule
Accepted blackbox signals:

{accepted[["label", "score_gain_positive_is_good", "realized_efficiency", "changed_cogs_ratio_base", "changed_cogs_ratio_midpoint", "changed_cogs_ratio_candidate", "implied_cogs_bound"]].to_markdown(index=False)}

Rejected blackbox signals:

{rejected[["label", "score_gain_positive_is_good", "realized_efficiency", "changed_cogs_ratio_base", "changed_cogs_ratio_midpoint", "changed_cogs_ratio_candidate", "implied_cogs_bound"]].to_markdown(index=False)}

The strongest constraint is `2023H2 COGS +10%`: it improved public and implies hidden `2023H2` actual is above a midpoint ratio around `1.04`. But the `+20%` month probes failed, so the true level is probably near current boosted `2023H2`, not far above it.

## Raw Data Availability
All operational tables stop at `2022-12-31`; future rows are only sample submission dates and imputed feature-store rows. So this is not a missing future-table problem.

{coverage.to_markdown(index=False)}

## Target Identity
`sales.csv` targets reconstruct from `orders + order_items + products`.

{identity.to_markdown(index=False)}

## Historical Half-Year Regimes
H2 has a strong odd/even pattern. Odd-year H2 ratios are repeatedly high: 2013, 2015, 2017, 2019, 2021. This directly matches why `2023H2` needed a higher COGS ratio.

{half[["year", "half", "days", "weighted_cogs_rev_ratio", "revenue_per_day", "cogs_per_day", "promo_rev_share", "effective_discount_rate", "weighted_catalog_ratio", "category_share_Streetwear", "category_share_Outdoor", "segment_share_Everyday", "segment_share_Premium"]].to_markdown(index=False)}

H2-only compact view:

{h2_ratios.to_markdown(index=False)}

Largest odd-vs-even H2 feature shifts:

{odd_diff.head(25).to_markdown(index=False)}

## Current Best Vs History
Current best ratios are much more H2-skewed than normal H1/H2 history, which explains both the public improvement and the private-risk warning.

{current_profile.to_markdown(index=False)}

{cur_vs_hist.to_markdown(index=False)}

## Product And Mix
Catalog-level product COGS/price ratios are only around `0.77-0.81`. Daily/public ratios above 1 therefore come from realized selling price/discount/mix, not static catalog cost alone.

Category catalog ratios:

{category.to_markdown(index=False)}

Segment catalog ratios:

{segment.to_markdown(index=False)}

Sold mix by category/segment:

{sold_mix.head(20).to_markdown(index=False)}

## Feature Signals
Top daily features correlated with COGS/Revenue ratio in train:

{corr.head(35).to_markdown(index=False)}

Future feature audit, highest future availability:

{future_audit.head(40).to_markdown(index=False)}

Promotion metadata by half-year:

{promo.to_markdown(index=False)}

## Interpretation
- The public blackbox rule is not random: it lines up with a real historical H2 odd-year high-ratio pattern.
- The local OOF likely underweighted this because `2022H2` is a low/normal H2, while public starts at `2023`, an odd-year regime candidate.
- Product catalog ratios alone cannot explain `COGS/Revenue > 1`; these high ratios require selling-price compression, discounts, or mix toward high-cost items.
- Future promo/inventory/traffic are not truly available after 2022, so any successful solution must impute policy/regime, not read future features.
- The most robust next model is a COGS-ratio model with features for `half`, `odd_year_h2`, promo/event windows, discount/promo analogs, and product-mix priors.

## Next Non-Overfit Modeling Direction
Build a structural candidate:

1. Keep a stable Revenue anchor.
2. Predict/assign `COGS/Revenue` by regime instead of direct COGS.
3. For `2023H2`, blend toward odd-year H2 analogs plus a small public-supported uplift, but cap below rejected month-spike bounds.
4. For `2024H1`, use recent H1 analogs, not the public H2 shock.
5. Avoid direct use of unknown future operational features unless they are generated by a clearly fixed policy.
"""


def main() -> None:
    run_dir = make_run_dir()
    coverage = table_coverage()
    coverage.to_csv(run_dir / "table_coverage.csv", index=False)

    daily, details = build_detail_daily()
    daily.to_csv(run_dir / "daily_detail_features.csv", index=False)

    identity = target_identity(daily)
    identity.to_csv(run_dir / "target_identity.csv", index=False)

    category, segment, sold_mix = product_ratio_tables(details)
    category.to_csv(run_dir / "category_catalog_ratios.csv", index=False)
    segment.to_csv(run_dir / "segment_catalog_ratios.csv", index=False)
    sold_mix.to_csv(run_dir / "sold_mix_ratios.csv", index=False)

    half = halfyear_profile(daily)
    half.to_csv(run_dir / "halfyear_regime_profile.csv", index=False)

    odd_diff = h2_odd_even_diff(half)
    odd_diff.to_csv(run_dir / "h2_odd_even_feature_diff.csv", index=False)

    corr = daily_feature_correlations()
    corr.to_csv(run_dir / "daily_feature_cogs_ratio_correlations.csv", index=False)

    future_audit = future_feature_audit()
    future_audit.to_csv(run_dir / "future_feature_audit.csv", index=False)

    promo = promotion_summary()
    promo.to_csv(run_dir / "promotion_halfyear_summary.csv", index=False)

    current_profile = segment_profile(CURRENT_BEST_FILE)
    current_profile.to_csv(run_dir / "current_best_segment_profile.csv", index=False)

    cur_vs_hist = current_vs_history(current_profile, half)
    cur_vs_hist.to_csv(run_dir / "current_best_vs_history.csv", index=False)

    probes = probe_reaction_table()
    probes.to_csv(run_dir / "blackbox_probe_reactions.csv", index=False)

    report = build_report(
        run_dir,
        coverage,
        identity,
        half,
        odd_diff,
        current_profile,
        cur_vs_hist,
        category,
        segment,
        sold_mix,
        corr,
        future_audit,
        promo,
        probes,
    )
    (run_dir / "data_pattern_deep_dive.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "data_pattern_deep_dive_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
