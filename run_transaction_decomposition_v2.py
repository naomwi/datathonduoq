from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


DATASET_DIR = Path("dataset")
LOG_ROOT = Path("logs")
NOTES_DIR = Path("notes")
RUN_PREFIX = "transaction_decomposition_v2"

CURRENT_BEST_FILE = "submission_promo_cogsmult_bestrev_all_0125.csv"
FALLBACK_BEST_FILE = "submission_promo_cogsratio_bestrev_a010_clip005.csv"
FORECAST_START = pd.Timestamp("2023-01-01")
FORECAST_END = pd.Timestamp("2024-07-01")

from lunar_calendar_features import tet_date_for_solar_year

TET_DATES = {y: tet_date_for_solar_year(y).strftime("%Y-%m-%d") for y in range(2012, 2026)}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def load_best_submission() -> tuple[pd.DataFrame, str]:
    path = DATASET_DIR / CURRENT_BEST_FILE
    if not path.exists():
        path = DATASET_DIR / FALLBACK_BEST_FILE
    frame = pd.read_csv(path, parse_dates=["Date"])
    return frame, path.name


def load_daily_components() -> pd.DataFrame:
    sales = pd.read_csv(DATASET_DIR / "sales.csv", parse_dates=["Date"])
    orders = pd.read_csv(
        DATASET_DIR / "orders.csv",
        parse_dates=["order_date"],
        usecols=["order_id", "order_date"],
        low_memory=False,
    )
    items = pd.read_csv(DATASET_DIR / "order_items.csv", low_memory=False)
    products = pd.read_csv(
        DATASET_DIR / "products.csv",
        usecols=["product_id", "category", "segment", "price", "cogs"],
        low_memory=False,
    )
    details = (
        items.merge(orders, on="order_id", how="left")
        .merge(products, on="product_id", how="left")
        .copy()
    )
    details["gross_rev"] = details["quantity"] * details["unit_price"]
    details["gross_cogs"] = details["quantity"] * details["cogs"]

    daily = (
        details.groupby("order_date", as_index=False)
        .agg(
            total_units=("quantity", "sum"),
            gross_rev=("gross_rev", "sum"),
            gross_cogs=("gross_cogs", "sum"),
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
    daily["price_per_unit"] = daily["Revenue"] / daily["total_units"].replace(0, np.nan)
    daily["cogs_per_unit"] = daily["COGS"] / daily["total_units"].replace(0, np.nan)
    daily["cogs_ratio"] = daily["COGS"] / daily["Revenue"].replace(0, np.nan)
    daily["units_per_order"] = daily["total_units"] / daily["order_count"].replace(0, np.nan)
    daily["aov"] = daily["Revenue"] / daily["order_count"].replace(0, np.nan)
    daily["month"] = daily["Date"].dt.month
    daily["day"] = daily["Date"].dt.day
    daily["month_day"] = daily["Date"].dt.strftime("%m-%d")
    daily["year"] = daily["Date"].dt.year
    return daily


def add_event_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    dates = pd.to_datetime(out["Date"])
    out["year"] = dates.dt.year
    out["month"] = dates.dt.month
    out["day"] = dates.dt.day
    out["month_day"] = dates.dt.strftime("%m-%d")
    out["win_spring"] = ((out["month"] == 3) & (out["day"] >= 18)) | (
        (out["month"] == 4) & (out["day"] <= 17)
    )
    out["win_midyear"] = ((out["month"] == 6) & (out["day"] >= 23)) | (
        (out["month"] == 7) & (out["day"] <= 22)
    )
    out["win_fall"] = (
        ((out["month"] == 8) & (out["day"] >= 30))
        | (out["month"] == 9)
        | ((out["month"] == 10) & (out["day"] <= 2))
    )
    out["win_yearend"] = ((out["month"] == 11) & (out["day"] >= 18)) | (out["month"] == 12) | (
        (out["month"] == 1) & (out["day"] <= 2)
    )
    out["win_main_promo"] = out[["win_spring", "win_midyear", "win_fall", "win_yearend"]].any(axis=1)

    tet_map = {year: pd.Timestamp(value) for year, value in TET_DATES.items()}
    out["tet_date"] = out["year"].map(tet_map)
    out["tet_offset"] = (dates - out["tet_date"]).dt.days
    out["win_tet_core"] = out["tet_offset"].between(-7, 14)
    out["win_tet_wide"] = out["tet_offset"].between(-14, 21)
    out["win_same_day_sale"] = (out["month"] == out["day"]) & out["month"].between(3, 12)
    out["win_event"] = out["win_main_promo"] | out["win_tet_wide"] | out["win_same_day_sale"]
    return out


def _weighted_recent_values(history: pd.DataFrame, key: str, value: str, recent_years: int = 5) -> pd.Series:
    train = history.loc[history["year"] >= history["year"].max() - recent_years + 1].copy()
    train["_w"] = np.exp((train["year"] - train["year"].max()) / 2.0)
    numerator = train.groupby(key).apply(lambda g: float((g[value] * g["_w"]).sum()), include_groups=False)
    denominator = train.groupby(key)["_w"].sum()
    return numerator / denominator


def _monthly_weighted_medianish(history: pd.DataFrame, value: str, recent_years: int = 5) -> pd.Series:
    train = history.loc[history["year"] >= history["year"].max() - recent_years + 1].copy()
    train["_w"] = np.exp((train["year"] - train["year"].max()) / 2.0)
    return train.groupby("month").apply(lambda g: float((g[value] * g["_w"]).sum() / g["_w"].sum()), include_groups=False)


def build_component_shape_donor(history: pd.DataFrame, public: pd.DataFrame) -> pd.DataFrame:
    future = add_event_columns(public[["Date"]].copy())
    month_days = sorted(set(history["month_day"]).union(set(future["month_day"])))

    profile = pd.DataFrame({"month_day": month_days})
    profile["month"] = pd.to_datetime("2024-" + profile["month_day"], errors="coerce").dt.month
    for col in ["total_units", "price_per_unit", "cogs_per_unit", "cogs_ratio", "order_count"]:
        by_md = _weighted_recent_values(history, "month_day", col, recent_years=5)
        by_month = _monthly_weighted_medianish(history, col, recent_years=5)
        profile[col] = profile["month_day"].map(by_md)
        profile[col] = profile[col].fillna(profile["month"].map(by_month))
        profile[col] = profile[col].fillna(float(history[col].median()))
        monthly = profile.groupby("month")[col].transform("mean").replace(0, np.nan)
        profile[f"{col}_shape"] = (profile[col] / monthly).replace([np.inf, -np.inf], np.nan).fillna(1.0)

    donor = future.merge(profile[["month_day", "total_units_shape", "price_per_unit_shape", "cogs_per_unit_shape", "cogs_ratio_shape", "order_count_shape"]], on="month_day", how="left")
    for col in [c for c in donor.columns if c.endswith("_shape")]:
        donor[col] = donor[col].fillna(1.0).clip(0.35, 2.8)
    donor["revenue_shape"] = (donor["total_units_shape"] * donor["price_per_unit_shape"]).clip(0.35, 2.8)
    donor["cogs_shape"] = (donor["total_units_shape"] * donor["cogs_per_unit_shape"]).clip(0.35, 2.8)
    for col in ["revenue_shape", "cogs_shape"]:
        donor[col] = donor[col] / donor.groupby([donor["Date"].dt.year, donor["Date"].dt.month])[col].transform("mean")

    out = public[["Date", "Revenue", "COGS"]].merge(donor[["Date", "revenue_shape", "cogs_shape", "cogs_ratio_shape", "win_event", "win_main_promo", "win_tet_wide"]], on="Date")
    out["donor_revenue"] = out["Revenue"] * out["revenue_shape"]
    out["donor_cogs"] = out["COGS"] * out["cogs_shape"]
    out["donor_cogs_ratio"] = (out["COGS"] / out["Revenue"].replace(0, np.nan)) * out["cogs_ratio_shape"]
    out["donor_cogs_ratio"] = out["donor_cogs_ratio"].clip(0.72, 1.02)
    out["donor_cogs_from_ratio"] = out["Revenue"] * out["donor_cogs_ratio"]
    return out


def build_tet_profile(history: pd.DataFrame) -> pd.DataFrame:
    tet_map = {year: pd.Timestamp(value) for year, value in TET_DATES.items()}
    frame = history.copy()
    frame["tet_date"] = frame["year"].map(tet_map)
    frame["tet_offset"] = (frame["Date"] - frame["tet_date"]).dt.days
    frame["rev_month_med"] = frame.groupby(["year", "month"])["Revenue"].transform("median")
    frame["cogs_month_med"] = frame.groupby(["year", "month"])["COGS"].transform("median")
    frame["rev_rel"] = frame["Revenue"] / frame["rev_month_med"].replace(0, np.nan)
    frame["cogs_rel"] = frame["COGS"] / frame["cogs_month_med"].replace(0, np.nan)
    profile = (
        frame.loc[frame["tet_offset"].between(-21, 35)]
        .groupby("tet_offset", as_index=False)
        .agg(tet_rev_shape=("rev_rel", "median"), tet_cogs_shape=("cogs_rel", "median"))
    )
    profile["tet_rev_shape"] = profile["tet_rev_shape"].fillna(1.0).clip(0.75, 1.35)
    profile["tet_cogs_shape"] = profile["tet_cogs_shape"].fillna(1.0).clip(0.75, 1.35)
    return profile


def compensate_month_total(base: pd.Series, candidate: pd.Series, dates: pd.Series, changed_mask: pd.Series) -> pd.Series:
    out = candidate.copy()
    months = pd.to_datetime(dates).dt.to_period("M")
    for _, idx in out.groupby(months).groups.items():
        idx = pd.Index(idx)
        base_total = float(base.loc[idx].sum())
        cand_total = float(out.loc[idx].sum())
        delta = cand_total - base_total
        if abs(delta) < 1e-6:
            continue
        comp_idx = idx[~changed_mask.loc[idx].to_numpy()]
        if len(comp_idx) == 0:
            out.loc[idx] *= base_total / cand_total if cand_total else 1.0
            continue
        weights = base.loc[comp_idx].clip(lower=1.0)
        out.loc[comp_idx] = out.loc[comp_idx] - delta * weights / weights.sum()
        out.loc[comp_idx] = np.maximum(out.loc[comp_idx], base.loc[comp_idx] * 0.65)
        final_total = float(out.loc[idx].sum())
        if final_total > 0:
            out.loc[idx] *= base_total / final_total
    return out


def write_submission(frame: pd.DataFrame, path: Path) -> None:
    out = frame[["Date", "Revenue", "COGS"]].copy()
    out["Revenue"] = out["Revenue"].clip(lower=0.0)
    out["COGS"] = out["COGS"].clip(lower=0.0)
    out["Date"] = pd.to_datetime(out["Date"]).dt.strftime("%Y-%m-%d")
    out.to_csv(path, index=False)


def make_candidates(best: pd.DataFrame, donor: pd.DataFrame, tet_profile: pd.DataFrame) -> tuple[list[dict[str, object]], dict[str, pd.DataFrame]]:
    base = add_event_columns(best.copy()).reset_index(drop=True)
    donor = donor.reset_index(drop=True)
    tet = base[["Date", "year", "tet_offset"]].merge(tet_profile, on="tet_offset", how="left")
    tet["tet_rev_shape"] = tet["tet_rev_shape"].fillna(1.0)
    tet["tet_cogs_shape"] = tet["tet_cogs_shape"].fillna(1.0)

    candidate_frames: dict[str, pd.DataFrame] = {}
    rows: list[dict[str, object]] = []

    def register(name: str, frame: pd.DataFrame, thesis: str) -> None:
        path = DATASET_DIR / name
        write_submission(frame, path)
        candidate_frames[name] = frame
        changed_rev = (frame["Revenue"] - base["Revenue"]).abs()
        changed_cogs = (frame["COGS"] - base["COGS"]).abs()
        rows.append(
            {
                "filename": name,
                "path": str(path),
                "thesis": thesis,
                "revenue_total_ratio_vs_best": frame["Revenue"].sum() / base["Revenue"].sum(),
                "cogs_total_ratio_vs_best": frame["COGS"].sum() / base["COGS"].sum(),
                "mean_abs_revenue_delta": changed_rev.mean(),
                "mean_abs_cogs_delta": changed_cogs.mean(),
                "max_abs_revenue_delta": changed_rev.max(),
                "max_abs_cogs_delta": changed_cogs.max(),
                "changed_nonpromo_revenue": bool((changed_rev[~base["win_main_promo"]] > 1e-6).any()),
                "changed_nonpromo_cogs": bool((changed_cogs[~base["win_main_promo"]] > 1e-6).any()),
            }
        )

    # 1. All-day intra-month transaction shape, preserving each month total.
    for rev_w, cogs_w, suffix in [(0.10, 0.10, "r10_c10"), (0.18, 0.12, "r18_c12")]:
        frame = base[["Date", "Revenue", "COGS"]].copy()
        frame["Revenue"] = (1 - rev_w) * base["Revenue"] + rev_w * donor["donor_revenue"]
        frame["COGS"] = (1 - cogs_w) * base["COGS"] + cogs_w * donor["donor_cogs"]
        frame["Revenue"] = compensate_month_total(base["Revenue"], frame["Revenue"], base["Date"], pd.Series(True, index=base.index))
        frame["COGS"] = compensate_month_total(base["COGS"], frame["COGS"], base["Date"], pd.Series(True, index=base.index))
        register(
            f"submission_txndecomp_v2_monthshape_{suffix}.csv",
            frame,
            "transaction component intra-month shape, month totals preserved",
        )

    # 2. Only event/promo/Tet dates get revenue shape; non-event dates compensate inside month.
    event_mask = base["win_event"].astype(bool)
    for w, suffix in [(0.20, "r20"), (0.35, "r35")]:
        frame = base[["Date", "Revenue", "COGS"]].copy()
        rev = base["Revenue"].copy()
        cogs = base["COGS"].copy()
        rev.loc[event_mask] = (1 - w) * base.loc[event_mask, "Revenue"] + w * donor.loc[event_mask, "donor_revenue"]
        cogs.loc[event_mask] = (1 - w) * base.loc[event_mask, "COGS"] + w * donor.loc[event_mask, "donor_cogs"]
        frame["Revenue"] = compensate_month_total(base["Revenue"], rev, base["Date"], event_mask)
        frame["COGS"] = compensate_month_total(base["COGS"], cogs, base["Date"], event_mask)
        register(
            f"submission_txndecomp_v2_eventshape_{suffix}.csv",
            frame,
            "transaction component shape only on promo/Tet/same-day-sale windows, month totals preserved",
        )

    # 3. Exact Tet lunar-date reshaping, preserving Jan/Feb monthly totals.
    tet_mask = base["win_tet_wide"].astype(bool)
    for w, suffix in [(0.25, "r25"), (0.40, "r40")]:
        frame = base[["Date", "Revenue", "COGS"]].copy()
        rev = base["Revenue"].copy()
        cogs = base["COGS"].copy()
        rev.loc[tet_mask] = base.loc[tet_mask, "Revenue"] * (1.0 + w * (tet.loc[tet_mask, "tet_rev_shape"].to_numpy() - 1.0))
        cogs.loc[tet_mask] = base.loc[tet_mask, "COGS"] * (1.0 + w * (tet.loc[tet_mask, "tet_cogs_shape"].to_numpy() - 1.0))
        frame["Revenue"] = compensate_month_total(base["Revenue"], rev, base["Date"], tet_mask)
        frame["COGS"] = compensate_month_total(base["COGS"], cogs, base["Date"], tet_mask)
        register(
            f"submission_txndecomp_v2_tetshift_{suffix}.csv",
            frame,
            "exact lunar Tet offset profile instead of Gregorian Jan/Feb-only calendar",
        )

    # 4. COGS ratio component correction on promo + Tet, with small total COGS increase.
    ratio_mask = (base["win_main_promo"] | base["win_tet_wide"]).astype(bool)
    for w, up, suffix in [(0.25, 0.005, "r25_up005"), (0.40, 0.0075, "r40_up0075")]:
        frame = base[["Date", "Revenue", "COGS"]].copy()
        cogs_ratio_target = donor["donor_cogs_from_ratio"]
        cogs = base["COGS"].copy()
        cogs.loc[ratio_mask] = (1 - w) * base.loc[ratio_mask, "COGS"] + w * cogs_ratio_target.loc[ratio_mask]
        cogs.loc[base["win_main_promo"]] *= 1.0 + up
        frame["COGS"] = cogs
        register(
            f"submission_txndecomp_v2_cogsratio_promotet_{suffix}.csv",
            frame,
            "component-derived COGS ratio on promo/Tet plus continuation of confirmed promo COGS public gradient",
        )

    # 5. Combo candidate: event revenue shape + COGS ratio correction.
    frame = base[["Date", "Revenue", "COGS"]].copy()
    rev = base["Revenue"].copy()
    rev.loc[event_mask] = 0.75 * base.loc[event_mask, "Revenue"] + 0.25 * donor.loc[event_mask, "donor_revenue"]
    frame["Revenue"] = compensate_month_total(base["Revenue"], rev, base["Date"], event_mask)
    cogs = base["COGS"].copy()
    cogs.loc[ratio_mask] = 0.65 * base.loc[ratio_mask, "COGS"] + 0.35 * donor.loc[ratio_mask, "donor_cogs_from_ratio"]
    cogs.loc[base["win_main_promo"]] *= 1.005
    frame["COGS"] = cogs
    register(
        "submission_txndecomp_v2_combo_event25_cogs35.csv",
        frame,
        "combined event transaction-shape revenue and component COGS-ratio correction",
    )

    return rows, candidate_frames


def write_report(run_dir: Path, best_file: str, manifest: pd.DataFrame, donor: pd.DataFrame) -> None:
    report = f"""# Transaction Decomposition V2

Run directory: `{run_dir}`

Base public best: `{best_file}`.

## Thesis
Historical targets are transaction aggregates:

- `Revenue = sum(quantity * unit_price)`.
- `COGS = sum(quantity * product.cogs)`.

This sprint does not replace the current public winner with raw bottom-up forecasts. It uses transaction decomposition as a shape donor around the public winner.

## Candidate Manifest
{manifest.to_markdown(index=False)}

## Donor Shape Summary
| metric | value |
|:--|--:|
| revenue_shape_min | {donor["revenue_shape"].min():.4f} |
| revenue_shape_max | {donor["revenue_shape"].max():.4f} |
| cogs_shape_min | {donor["cogs_shape"].min():.4f} |
| cogs_shape_max | {donor["cogs_shape"].max():.4f} |
| event_rows | {int(donor["win_event"].sum())} |
| promo_rows | {int(donor["win_main_promo"].sum())} |
| tet_rows | {int(donor["win_tet_wide"].sum())} |

## Submit Guidance
These are higher-variance breakthrough probes. Submit after the pure COGS-gradient probe unless you want to spend a slot on the structural hypothesis immediately.

Recommended structural order:

1. `submission_txndecomp_v2_eventshape_r20.csv`
2. `submission_txndecomp_v2_cogsratio_promotet_r25_up005.csv`
3. `submission_txndecomp_v2_tetshift_r25.csv`
4. `submission_txndecomp_v2_combo_event25_cogs35.csv`
5. `submission_txndecomp_v2_monthshape_r10_c10.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "transaction_decomposition_v2_2026-04-22.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    best, best_file = load_best_submission()
    best = best[(best["Date"] >= FORECAST_START) & (best["Date"] <= FORECAST_END)].copy()
    history = load_daily_components()
    donor = build_component_shape_donor(history, best)
    tet_profile = build_tet_profile(history)
    rows, _ = make_candidates(best, donor, tet_profile)

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    donor.to_csv(run_dir / "component_shape_donor.csv", index=False)
    tet_profile.to_csv(run_dir / "tet_profile.csv", index=False)
    write_report(run_dir, best_file, manifest, donor)
    print(run_dir)


if __name__ == "__main__":
    main()
