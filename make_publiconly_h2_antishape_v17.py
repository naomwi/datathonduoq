from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns, write_submission


RUN_PREFIX = "publiconly_h2_antishape_v17"
CURRENT_BEST_FILE = "submission_top10_v13_rev2023h2_up100_keepcogs.csv"
CURRENT_BEST_SCORE = 797595.96410
FAILED_ODDMEAN_FILE = "submission_h2shape_v16_cogs_oddmean_preserve.csv"
FAILED_ODDMEAN_SCORE = 802116.33879
FAILED_REVENUE_UP_FILE = "submission_h2rev_v15_current_h2_rev_up050.csv"
FAILED_REVENUE_UP_SCORE = 800572.16096

MONTHS_H2 = [7, 8, 9, 10, 11, 12]
ODD_REFERENCE_YEARS = [2013, 2015, 2017, 2019, 2021]


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def add_segments(frame: pd.DataFrame) -> pd.DataFrame:
    out = add_event_columns(frame).reset_index(drop=True)
    out["period"] = "other"
    out.loc[out["Date"].dt.year.eq(2023) & out["Date"].dt.month.le(6), "period"] = "2023H1"
    out.loc[out["Date"].dt.year.eq(2023) & out["Date"].dt.month.ge(7), "period"] = "2023H2"
    out.loc[out["Date"].dt.year.eq(2024) & out["Date"].dt.month.le(6), "period"] = "2024H1"
    out["month"] = out["Date"].dt.month
    return out


def build_historical_daily() -> pd.DataFrame:
    orders = pd.read_csv(DATASET_DIR / "orders.csv", parse_dates=["order_date"])
    items = pd.read_csv(DATASET_DIR / "order_items.csv", low_memory=False)
    products = pd.read_csv(DATASET_DIR / "products.csv")
    frame = (
        items.merge(orders[["order_id", "order_date"]], on="order_id", how="left")
        .merge(products[["product_id", "cogs"]], on="product_id", how="left")
    )
    frame["Revenue"] = frame["quantity"] * frame["unit_price"]
    frame["COGS"] = frame["quantity"] * frame["cogs"]
    daily = (
        frame.groupby("order_date", as_index=False)[["Revenue", "COGS"]]
        .sum()
        .rename(columns={"order_date": "Date"})
    )
    daily["year"] = daily["Date"].dt.year
    daily["month"] = daily["Date"].dt.month
    return daily


def h2_month_shares(daily: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    h2 = daily[daily["year"].isin(years) & daily["month"].isin(MONTHS_H2)].copy()
    monthly = h2.groupby(["year", "month"], as_index=False)[["Revenue", "COGS"]].sum()
    monthly["rev_share"] = monthly["Revenue"] / monthly.groupby("year")["Revenue"].transform("sum")
    monthly["cogs_share"] = monthly["COGS"] / monthly.groupby("year")["COGS"].transform("sum")
    return (
        monthly.groupby("month", as_index=False)[["rev_share", "cogs_share"]]
        .mean()
        .sort_values("month")
        .reset_index(drop=True)
    )


def current_h2_month_profile(frame: pd.DataFrame) -> pd.DataFrame:
    h2 = frame[frame["period"].eq("2023H2")]
    monthly = h2.groupby("month", as_index=False)[["Revenue", "COGS"]].sum()
    monthly["rev_share"] = monthly["Revenue"] / monthly["Revenue"].sum()
    monthly["cogs_share"] = monthly["COGS"] / monthly["COGS"].sum()
    monthly["ratio"] = monthly["COGS"] / monthly["Revenue"]
    return monthly


def anti_target_shares(current_profile: pd.DataFrame, reference_shares: pd.DataFrame, alpha: float) -> pd.DataFrame:
    merged = current_profile[["month", "rev_share", "cogs_share"]].merge(
        reference_shares,
        on="month",
        suffixes=("_current", "_ref"),
    )
    out = pd.DataFrame({"month": merged["month"]})
    for col in ("rev_share", "cogs_share"):
        current = merged[f"{col}_current"]
        ref = merged[f"{col}_ref"]
        target = current + alpha * (current - ref)
        # Keep the vector sane; the tested move was already large.
        target = target.clip(lower=0.05)
        out[col] = target / target.sum()
    return out


def preserve_h2_month_shares(base: pd.DataFrame, target_shares: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    out = base[["Date", "Revenue", "COGS"]].copy()
    h2_mask = base["period"].eq("2023H2")
    for col in columns:
        total = out.loc[h2_mask, col].sum()
        share_col = "rev_share" if col == "Revenue" else "cogs_share"
        for _, row in target_shares.iterrows():
            month = int(row["month"])
            month_mask = h2_mask & base["month"].eq(month)
            current_total = out.loc[month_mask, col].sum()
            if current_total <= 0:
                continue
            out.loc[month_mask, col] *= (total * float(row[share_col])) / current_total
    return out


def month_multiplier_shape(base: pd.DataFrame, cogs_multipliers: dict[int, float]) -> pd.DataFrame:
    out = base[["Date", "Revenue", "COGS"]].copy()
    h2_mask = base["period"].eq("2023H2")
    total = out.loc[h2_mask, "COGS"].sum()
    for month, multiplier in cogs_multipliers.items():
        out.loc[h2_mask & base["month"].eq(month), "COGS"] *= multiplier
    new_total = out.loc[h2_mask, "COGS"].sum()
    out.loc[h2_mask, "COGS"] *= total / new_total
    return out


def summarize(base: pd.DataFrame, frame: pd.DataFrame, filename: str, thesis: str, priority: int) -> dict[str, object]:
    prof = add_segments(frame)
    h2 = prof["period"].eq("2023H2")
    delta_rev = frame["Revenue"] - base["Revenue"]
    delta_cogs = frame["COGS"] - base["COGS"]
    h2_month = current_h2_month_profile(prof)
    return {
        "priority": priority,
        "filename": filename,
        "path": str(DATASET_DIR / filename),
        "thesis": thesis,
        "rev_rows_changed": int(delta_rev.abs().gt(1e-6).sum()),
        "cogs_rows_changed": int(delta_cogs.abs().gt(1e-6).sum()),
        "mean_abs_rev_delta": delta_rev.abs().mean(),
        "mean_abs_cogs_delta": delta_cogs.abs().mean(),
        "directional_best_case_gain": 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
        "h2_revenue_total_ratio_vs_current": frame.loc[h2, "Revenue"].sum() / base.loc[h2, "Revenue"].sum(),
        "h2_cogs_total_ratio_vs_current": frame.loc[h2, "COGS"].sum() / base.loc[h2, "COGS"].sum(),
        "h2_ratio": prof.loc[h2, "COGS"].sum() / prof.loc[h2, "Revenue"].sum(),
        "jul_cogs_share": h2_month.loc[h2_month["month"].eq(7), "cogs_share"].iloc[0],
        "aug_cogs_share": h2_month.loc[h2_month["month"].eq(8), "cogs_share"].iloc[0],
        "oct_cogs_share": h2_month.loc[h2_month["month"].eq(10), "cogs_share"].iloc[0],
        "nov_cogs_share": h2_month.loc[h2_month["month"].eq(11), "cogs_share"].iloc[0],
        "dec_cogs_share": h2_month.loc[h2_month["month"].eq(12), "cogs_share"].iloc[0],
    }


def register(rows: list[dict[str, object]], base: pd.DataFrame, frame: pd.DataFrame, filename: str, thesis: str, priority: int) -> None:
    write_submission(frame, DATASET_DIR / filename)
    rows.append(summarize(base, frame, filename, thesis, priority))


def main() -> None:
    run_dir = make_run_dir()
    current = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    hist = build_historical_daily()
    odd_mean = h2_month_shares(hist, ODD_REFERENCE_YEARS)
    current_profile = current_h2_month_profile(current)

    anti_025 = anti_target_shares(current_profile, odd_mean, alpha=0.25)
    anti_050 = anti_target_shares(current_profile, odd_mean, alpha=0.50)
    anti_100 = anti_target_shares(current_profile, odd_mean, alpha=1.00)

    rows: list[dict[str, object]] = []
    specs = [
        (
            "submission_h2antishape_v17_cogs_antiodd025_preserve.csv",
            preserve_h2_month_shares(current, anti_025, ("COGS",)),
            "opposite of failed odd-year COGS-shape vector, 25% strength, preserve H2 COGS total",
            1,
        ),
        (
            "submission_h2antishape_v17_cogs_antiodd050_preserve.csv",
            preserve_h2_month_shares(current, anti_050, ("COGS",)),
            "opposite of failed odd-year COGS-shape vector, 50% strength, preserve H2 COGS total",
            2,
        ),
        (
            "submission_h2antishape_v17_cogs_antiodd100_preserve.csv",
            preserve_h2_month_shares(current, anti_100, ("COGS",)),
            "opposite of failed odd-year COGS-shape vector, full strength, preserve H2 COGS total",
            3,
        ),
        (
            "submission_h2antishape_v17_cogs_octnov_up_preserve.csv",
            month_multiplier_shape(current, {10: 1.10, 11: 1.10, 8: 0.94, 12: 0.97}),
            "manual anti-shape: move H2 COGS from Aug/Dec into Oct/Nov, preserve total",
            4,
        ),
        (
            "submission_h2antishape_v17_cogs_aug_down_preserve.csv",
            month_multiplier_shape(current, {8: 0.88, 10: 1.06, 11: 1.06}),
            "manual anti-shape: reduce August COGS spike and redistribute to Oct/Nov",
            5,
        ),
        (
            "submission_h2antishape_v17_revcogs_antiodd025_preserve.csv",
            preserve_h2_month_shares(current, anti_025, ("Revenue", "COGS")),
            "opposite of odd-year shape on both Revenue and COGS, 25% strength, preserve H2 totals",
            6,
        ),
    ]

    for filename, frame, thesis, priority in specs:
        register(rows, current, frame, filename, thesis, priority)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    current_profile.to_csv(run_dir / "current_best_h2_month_profile.csv", index=False)
    odd_mean.to_csv(run_dir / "failed_oddmean_reference_shares.csv", index=False)
    anti_025.to_csv(run_dir / "antiodd025_target_shares.csv", index=False)
    anti_050.to_csv(run_dir / "antiodd050_target_shares.csv", index=False)
    anti_100.to_csv(run_dir / "antiodd100_target_shares.csv", index=False)

    report = f"""# Public-Only H2 Anti-Shape V17

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Failed scale probe: `{FAILED_REVENUE_UP_FILE}` scored `{FAILED_REVENUE_UP_SCORE}`.

Failed shape probe: `{FAILED_ODDMEAN_FILE}` scored `{FAILED_ODDMEAN_SCORE}`.

Interpretation:

- Extra broad H2 Revenue worsened, and quadratic interpolation puts the H2 Revenue optimum essentially at the current best.
- Odd-year COGS shape also worsened, so do not submit the more aggressive `revcogs_oddmean` candidate.
- V17 tests the opposite of the failed COGS-shape vector while preserving total H2 COGS. This is a blackbox-gradient probe, not a historical prior.

Current H2 month profile:

{current_profile.to_markdown(index=False)}

Failed odd-year reference shares:

{odd_mean.to_markdown(index=False)}

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_h2antishape_v17_cogs_antiodd025_preserve.csv`
2. If it improves: `submission_h2antishape_v17_cogs_antiodd050_preserve.csv`
3. If antiodd025 is neutral/slightly bad: `submission_h2antishape_v17_cogs_octnov_up_preserve.csv`
4. Do not test full antiodd unless half strength improves.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_h2_antishape_v17_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
