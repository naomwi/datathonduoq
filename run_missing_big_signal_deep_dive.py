from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


DATASET_DIR = Path("dataset")
LOG_ROOT = Path("logs")
NOTES_DIR = Path("notes")
RUN_PREFIX = "missing_big_signal_deep_dive"

from lunar_calendar_features import tet_date_for_solar_year

TET_DATES = {y: tet_date_for_solar_year(y).strftime("%Y-%m-%d") for y in range(2012, 2026)}

SUBMISSION_FILES = [
    "sample_submission.csv",
    "submission_catboost_md2y_core_recencyexp20.csv",
    "submission_tabpfn_promo_windowmix_v1.csv",
    "submission_promo_cogsratio_bestrev_a010_clip005.csv",
    "submission_public_revenue_gate_v3_soft.csv",
    "submission_public_probe_promo_windows_rev_up8.csv",
    "submission_catboost_md2y_core_price_history.csv",
]

RAW_DATE_COLUMNS = {
    "sales.csv": ["Date"],
    "orders.csv": ["order_date"],
    "shipments.csv": ["ship_date", "delivery_date"],
    "returns.csv": ["return_date"],
    "reviews.csv": ["review_date"],
    "web_traffic.csv": ["date"],
    "inventory.csv": ["snapshot_date"],
    "promotions.csv": ["start_date", "end_date"],
    "customers.csv": ["signup_date"],
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def load_transaction_daily() -> tuple[pd.DataFrame, pd.DataFrame]:
    sales = pd.read_csv(DATASET_DIR / "sales.csv", parse_dates=["Date"])
    orders = pd.read_csv(
        DATASET_DIR / "orders.csv",
        parse_dates=["order_date"],
        low_memory=False,
    )
    items = pd.read_csv(DATASET_DIR / "order_items.csv", low_memory=False)
    products = pd.read_csv(
        DATASET_DIR / "products.csv",
        usecols=["product_id", "category", "segment", "price", "cogs"],
        low_memory=False,
    )

    details = (
        items.merge(orders[["order_id", "order_date"]], on="order_id", how="left")
        .merge(products, on="product_id", how="left")
        .copy()
    )
    details["gross_rev"] = details["quantity"] * details["unit_price"]
    details["gross_cogs"] = details["quantity"] * details["cogs"]
    details["gross_list_value"] = details["quantity"] * details["price"]
    details["year"] = details["order_date"].dt.year

    daily = (
        details.groupby("order_date", as_index=False)
        .agg(
            gross_rev=("gross_rev", "sum"),
            gross_cogs=("gross_cogs", "sum"),
            total_units=("quantity", "sum"),
            total_discount=("discount_amount", "sum"),
            gross_list_value=("gross_list_value", "sum"),
            line_count=("order_id", "size"),
            active_products=("product_id", "nunique"),
        )
        .rename(columns={"order_date": "Date"})
    )
    order_daily = (
        orders.groupby("order_date", as_index=False)
        .agg(order_count=("order_id", "nunique"))
        .rename(columns={"order_date": "Date"})
    )
    daily = sales.merge(daily, on="Date", how="left").merge(order_daily, on="Date", how="left")
    daily = daily.fillna(0.0)
    daily["gross_aov"] = daily["gross_rev"] / daily["order_count"].replace(0, np.nan)
    daily["units_per_order"] = daily["total_units"] / daily["order_count"].replace(0, np.nan)
    daily["gross_price_per_unit"] = daily["gross_rev"] / daily["total_units"].replace(0, np.nan)
    daily["gross_cogs_per_unit"] = daily["gross_cogs"] / daily["total_units"].replace(0, np.nan)
    daily["gross_cogs_ratio"] = daily["gross_cogs"] / daily["gross_rev"].replace(0, np.nan)
    daily["discount_share_gross"] = daily["total_discount"] / daily["gross_rev"].replace(0, np.nan)
    return daily, details


def date_coverage() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for filename, cols in RAW_DATE_COLUMNS.items():
        frame = pd.read_csv(DATASET_DIR / filename, usecols=lambda c, keep=set(cols): c in keep)
        for col in cols:
            values = pd.to_datetime(frame[col], errors="coerce")
            rows.append(
                {
                    "filename": filename,
                    "date_column": col,
                    "rows": len(frame),
                    "nonnull": int(values.notna().sum()),
                    "min_date": values.min(),
                    "max_date": values.max(),
                    "has_future_after_2022": bool((values > pd.Timestamp("2022-12-31")).any()),
                }
            )
    return pd.DataFrame(rows)


def target_identity(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    checks = [
        ("Revenue", "gross_rev"),
        ("COGS", "gross_cogs"),
    ]
    for target, pred in checks:
        diff = daily[target] - daily[pred]
        rows.append(
            {
                "target": target,
                "component": pred,
                "corr": daily[target].corr(daily[pred]),
                "mae": diff.abs().mean(),
                "max_abs": diff.abs().max(),
                "bias": diff.mean(),
                "component_total_ratio": daily[pred].sum() / daily[target].sum(),
            }
        )
    return pd.DataFrame(rows)


def annual_components(daily: pd.DataFrame) -> pd.DataFrame:
    frame = daily.copy()
    frame["year"] = frame["Date"].dt.year
    grouped = (
        frame.groupby("year", as_index=False)
        .agg(
            revenue_sum=("Revenue", "sum"),
            cogs_sum=("COGS", "sum"),
            order_count=("order_count", "sum"),
            total_units=("total_units", "sum"),
            active_products_mean=("active_products", "mean"),
            total_discount=("total_discount", "sum"),
            rows=("Date", "size"),
        )
        .copy()
    )
    grouped["revenue_per_day"] = grouped["revenue_sum"] / grouped["rows"]
    grouped["cogs_per_day"] = grouped["cogs_sum"] / grouped["rows"]
    grouped["orders_per_day"] = grouped["order_count"] / grouped["rows"]
    grouped["units_per_day"] = grouped["total_units"] / grouped["rows"]
    grouped["aov"] = grouped["revenue_sum"] / grouped["order_count"]
    grouped["units_per_order"] = grouped["total_units"] / grouped["order_count"]
    grouped["price_per_unit"] = grouped["revenue_sum"] / grouped["total_units"]
    grouped["cogs_per_unit"] = grouped["cogs_sum"] / grouped["total_units"]
    grouped["cogs_ratio"] = grouped["cogs_sum"] / grouped["revenue_sum"]
    grouped["discount_share_gross"] = grouped["total_discount"] / grouped["revenue_sum"]
    return grouped


def mix_trends(details: pd.DataFrame, column: str) -> pd.DataFrame:
    grouped = (
        details.groupby(["year", column], as_index=False)
        .agg(revenue=("gross_rev", "sum"), cogs=("gross_cogs", "sum"), units=("quantity", "sum"))
        .copy()
    )
    grouped["revenue_share"] = grouped["revenue"] / grouped.groupby("year")["revenue"].transform("sum")
    grouped["cogs_ratio"] = grouped["cogs"] / grouped["revenue"].replace(0, np.nan)
    return grouped


def tet_profile(daily: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    tet_map = {year: pd.Timestamp(value) for year, value in TET_DATES.items()}
    frame = daily.copy()
    frame["year"] = frame["Date"].dt.year
    frame["month"] = frame["Date"].dt.month
    frame["tet_date"] = frame["year"].map(tet_map)
    frame["tet_offset"] = (frame["Date"] - frame["tet_date"]).dt.days
    frame["rev_month_median"] = frame.groupby(["year", "month"])["Revenue"].transform("median")
    frame["cogs_month_median"] = frame.groupby(["year", "month"])["COGS"].transform("median")
    frame["ratio_month_median"] = frame.groupby(["year", "month"])["gross_cogs_ratio"].transform("median")
    frame["rev_rel_month"] = frame["Revenue"] / frame["rev_month_median"]
    frame["cogs_rel_month"] = frame["COGS"] / frame["cogs_month_median"]
    frame["ratio_delta_month"] = frame["gross_cogs_ratio"] - frame["ratio_month_median"]

    window = frame[frame["tet_offset"].between(-21, 35)].copy()
    offsets = (
        window.groupby("tet_offset", as_index=False)
        .agg(
            n=("Revenue", "size"),
            rev_rel_median=("rev_rel_month", "median"),
            rev_rel_mean=("rev_rel_month", "mean"),
            cogs_rel_median=("cogs_rel_month", "median"),
            ratio_delta_median=("ratio_delta_month", "median"),
        )
        .sort_values("tet_offset")
    )

    windows = [
        ("pre14_1", -14, -1),
        ("pre7_1", -7, -1),
        ("tet0_3", 0, 3),
        ("tet0_6", 0, 6),
        ("post4_14", 4, 14),
        ("post15_35", 15, 35),
    ]
    rows: list[dict[str, object]] = []
    for name, start, end in windows:
        part = window[window["tet_offset"].between(start, end)]
        for year, group in part.groupby("year"):
            rows.append(
                {
                    "window": name,
                    "year": year,
                    "rows": len(group),
                    "rev_rel": group["Revenue"].sum() / group["rev_month_median"].sum(),
                    "cogs_rel": group["COGS"].sum() / group["cogs_month_median"].sum(),
                    "cogs_ratio": group["COGS"].sum() / group["Revenue"].sum(),
                }
            )
    return offsets, pd.DataFrame(rows)


def compare_submissions() -> pd.DataFrame:
    available = [name for name in SUBMISSION_FILES if (DATASET_DIR / name).exists()]
    frames = {name: pd.read_csv(DATASET_DIR / name, parse_dates=["Date"]) for name in available}
    best_name = "submission_promo_cogsratio_bestrev_a010_clip005.csv"
    if best_name not in frames:
        best_name = "submission_tabpfn_promo_windowmix_v1.csv"
    best = frames[best_name]
    rows: list[dict[str, object]] = []
    for name, frame in frames.items():
        merged = best.merge(frame, on="Date", suffixes=("_best", "_candidate"))
        rows.append(
            {
                "filename": name,
                "rows": len(frame),
                "revenue_mean": frame["Revenue"].mean(),
                "cogs_mean": frame["COGS"].mean(),
                "revenue_total_ratio_vs_best": frame["Revenue"].sum() / best["Revenue"].sum(),
                "cogs_total_ratio_vs_best": frame["COGS"].sum() / best["COGS"].sum(),
                "revenue_corr_vs_best": merged["Revenue_best"].corr(merged["Revenue_candidate"]),
                "cogs_corr_vs_best": merged["COGS_best"].corr(merged["COGS_candidate"]),
                "mean_abs_revenue_diff_vs_best": (merged["Revenue_candidate"] - merged["Revenue_best"]).abs().mean(),
                "mean_abs_cogs_diff_vs_best": (merged["COGS_candidate"] - merged["COGS_best"]).abs().mean(),
            }
        )
    return pd.DataFrame(rows).sort_values("mean_abs_revenue_diff_vs_best")


def write_report(
    run_dir: Path,
    coverage: pd.DataFrame,
    identity: pd.DataFrame,
    annual: pd.DataFrame,
    category_mix: pd.DataFrame,
    segment_mix: pd.DataFrame,
    tet_offsets: pd.DataFrame,
    tet_windows: pd.DataFrame,
    submission_cmp: pd.DataFrame,
) -> None:
    report_path = run_dir / "missing_big_signal_report.md"
    latest_note = NOTES_DIR / "missing_big_signal_2026-04-21.md"
    streetwear_2022 = category_mix[(category_mix["year"] == 2022) & (category_mix["category"] == "Streetwear")]
    balanced_2022 = segment_mix[(segment_mix["year"] == 2022) & (segment_mix["segment"] == "Balanced")]
    annual_tail = annual[annual["year"].between(2018, 2022)].copy()
    tet_window_summary = (
        tet_windows.groupby("window", as_index=False)
        .agg(
            years=("year", "nunique"),
            rev_rel_median=("rev_rel", "median"),
            rev_rel_mean=("rev_rel", "mean"),
            cogs_rel_median=("cogs_rel", "median"),
            cogs_ratio_median=("cogs_ratio", "median"),
        )
        .sort_values("window")
    )

    text = f"""# Missing Big Signal Deep Dive

Run directory: `{run_dir}`

## Main Finding
The target is exactly reconstructable from item-level transactions:

{identity.to_markdown(index=False)}

This means `Revenue` is gross merchandise value, not net payment after discount, and `COGS` is the sum of `quantity * product.cogs`. The most credible gap to top teams is not TabPFN/CatBoost choice; it is whether the future is modeled as transaction components: order volume, units, unit price, product/category/segment mix, and promo/event calendars.

## Future Raw Coverage
No raw operational table has actual 2023-2024 observations:

{coverage.to_markdown(index=False)}

So any strong solution must forecast transaction structure, not read future orders/traffic/inventory.

## 2018-2022 Component Regime
{annual_tail[["year", "revenue_per_day", "orders_per_day", "units_per_day", "aov", "units_per_order", "price_per_unit", "cogs_per_unit", "cogs_ratio", "discount_share_gross"]].to_markdown(index=False)}

Important pattern: volume collapsed after 2018-2019, while `AOV`, `price_per_unit`, and `cogs_per_unit` rose sharply. Direct daily models can fit this locally while still missing the future split between level and mix.

## Product Mix Drift
- 2022 Streetwear revenue share: `{float(streetwear_2022["revenue_share"].iloc[0]) if not streetwear_2022.empty else np.nan:.4f}`.
- 2022 Balanced segment revenue share: `{float(balanced_2022["revenue_share"].iloc[0]) if not balanced_2022.empty else np.nan:.4f}`.
- Streetwear and Balanced have trended up for years; Outdoor/Activewear trended down. This is a plausible COGS-ratio and promo-window lever.

## Lunar Tet Check
Current calendar only knows Jan/Feb, not the moving lunar date. Historical Tet effect is noisy but real enough to keep as a diagnostic family:

{tet_window_summary.to_markdown(index=False)}

This is probably not a single 180k-MAE key by itself, but top solutions likely include exact Vietnamese holiday/event calendars.

## Submission Shape Check
{submission_cmp.to_markdown(index=False)}

`sample_submission.csv` is far below the current best level, so it is unlikely to be a magic 700k baseline. Its value is only as a weak shape donor after level alignment.

## Decision
The next serious direction should be `transaction-decomposition v2`, not another model swap:

- Build forecasts for `order_count`, `total_units`, `gross_price_per_unit`, and `gross_cogs_per_unit`.
- Use category/segment mix as a constrained COGS-ratio layer, not as a raw daily Revenue replacement.
- Add exact moving holiday/event features: Tet dates, 11.11, 12.12, Black Friday, month-end/payday.
- Blend component forecasts only where they explain public shift: promo windows, Tet/event windows, and COGS ratio.
- Keep the current best Revenue shape as anchor until a component forecast beats it on public-like folds.
"""
    report_path.write_text(text, encoding="utf-8")
    latest_note.write_text(text, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    daily, details = load_transaction_daily()
    coverage = date_coverage()
    identity = target_identity(daily)
    annual = annual_components(daily)
    category_mix = mix_trends(details, "category")
    segment_mix = mix_trends(details, "segment")
    tet_offsets, tet_windows = tet_profile(daily)
    submission_cmp = compare_submissions()

    coverage.to_csv(run_dir / "date_coverage.csv", index=False)
    identity.to_csv(run_dir / "target_identity.csv", index=False)
    annual.to_csv(run_dir / "annual_components.csv", index=False)
    category_mix.to_csv(run_dir / "category_mix_trends.csv", index=False)
    segment_mix.to_csv(run_dir / "segment_mix_trends.csv", index=False)
    tet_offsets.to_csv(run_dir / "tet_offset_profile.csv", index=False)
    tet_windows.to_csv(run_dir / "tet_window_by_year.csv", index=False)
    submission_cmp.to_csv(run_dir / "submission_shape_compare.csv", index=False)
    write_report(
        run_dir,
        coverage,
        identity,
        annual,
        category_mix,
        segment_mix,
        tet_offsets,
        tet_windows,
        submission_cmp,
    )
    print(run_dir)


if __name__ == "__main__":
    main()
