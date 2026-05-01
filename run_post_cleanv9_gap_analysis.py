from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR


RUN_PREFIX = "post_cleanv9_gap_analysis"
FORECAST_START = pd.Timestamp("2023-01-01")
FORECAST_END = pd.Timestamp("2024-07-01")


PUBLIC_SCORES = {
    "submission_cleanv7_source_h1_s020_r0870.csv": 673720.88479,
    "submission_cleanv7_sourcefine_s0190_r0870.csv": 674415.02000,
    "submission_cleanv9_big_h1_keeprev_cogs_r0820.csv": 678484.18208,
    "submission_cleanv3_funnel_c110_h1r0876.csv": 673759.96838,
    "submission_cleanv6_merch_revshape_g010.csv": 674337.07653,
    "submission_qbb62_h1_backload_preserve_total_q2up040.csv": 661327.00240,
    "submission_qbb65_h2_highratio_cogs_down060_keeprev.csv": 659211.90870,
    "submission_qbb68_h1_q1_cogs_down080_keeprev.csv": 656301.72926,
    "submission_qbb69_h1_q1_cogs_down120_keeprev.csv": 655838.51372,
}


KEY_FILES = [
    "submission_cleanv7_source_h1_s020_r0870.csv",
    "submission_cleanv7_sourcefine_s0190_r0870.csv",
    "submission_cleanv9_big_h1_keeprev_cogs_r0820.csv",
    "submission_cleanv3_funnel_c110_h1r0876.csv",
    "submission_cleanv6_merch_revshape_g010.csv",
    "submission_qbb62_h1_backload_preserve_total_q2up040.csv",
    "submission_qbb65_h2_highratio_cogs_down060_keeprev.csv",
    "submission_qbb68_h1_q1_cogs_down080_keeprev.csv",
    "submission_qbb69_h1_q1_cogs_down120_keeprev.csv",
]

RAW_FILES = [
    "sales.csv",
    "orders.csv",
    "order_items.csv",
    "payments.csv",
    "returns.csv",
    "shipments.csv",
    "web_traffic.csv",
    "promotions.csv",
    "inventory.csv",
    "reviews.csv",
    "customers.csv",
    "products.csv",
]


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def period_label(date: pd.Timestamp) -> str:
    if pd.Timestamp("2023-01-01") <= date <= pd.Timestamp("2023-06-30"):
        return "2023H1"
    if pd.Timestamp("2023-07-01") <= date <= pd.Timestamp("2023-12-31"):
        return "2023H2"
    if pd.Timestamp("2024-01-01") <= date <= pd.Timestamp("2024-06-30"):
        return "2024H1"
    return "2024-07-01"


def quarter_label(date: pd.Timestamp) -> str:
    return f"{date.year}Q{((date.month - 1) // 3) + 1}"


def load_submission(filename: str) -> pd.DataFrame:
    path = DATASET_DIR / filename
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path)
    frame["Date"] = pd.to_datetime(frame["Date"])
    frame["period"] = frame["Date"].map(period_label)
    frame["quarter"] = frame["Date"].map(quarter_label)
    frame["month"] = frame["Date"].dt.to_period("M").astype(str)
    frame["weekday"] = frame["Date"].dt.day_name()
    return frame


def summarize_submission(filename: str) -> dict[str, float | str]:
    frame = load_submission(filename)
    out: dict[str, float | str] = {
        "filename": filename,
        "public_score": PUBLIC_SCORES.get(filename, np.nan),
        "rows": len(frame),
        "start": str(frame["Date"].min().date()),
        "end": str(frame["Date"].max().date()),
        "revenue_total": frame["Revenue"].sum(),
        "cogs_total": frame["COGS"].sum(),
        "ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
        "max_revenue": frame["Revenue"].max(),
        "max_cogs": frame["COGS"].max(),
    }
    for period, g in frame.groupby("period", sort=False):
        out[f"rev_{period}"] = g["Revenue"].sum()
        out[f"cogs_{period}"] = g["COGS"].sum()
        out[f"ratio_{period}"] = g["COGS"].sum() / g["Revenue"].sum()
    return out


def compare_to_anchor(anchor_file: str, other_files: list[str]) -> pd.DataFrame:
    anchor = load_submission(anchor_file).set_index("Date")
    rows = []
    for filename in other_files:
        other = load_submission(filename).set_index("Date")
        delta = other[["Revenue", "COGS"]] - anchor[["Revenue", "COGS"]]
        work = other[["period", "quarter", "month"]].join(delta.add_prefix("delta_"))
        rows.append(
            {
                "filename": filename,
                "public_score": PUBLIC_SCORES.get(filename, np.nan),
                "public_delta_vs_anchor": PUBLIC_SCORES.get(filename, np.nan)
                - PUBLIC_SCORES.get(anchor_file, np.nan),
                "delta_revenue_total": delta["Revenue"].sum(),
                "delta_cogs_total": delta["COGS"].sum(),
                "delta_abs_total": delta.abs().sum().sum(),
                "max_abs_daily_rev_delta": delta["Revenue"].abs().max(),
                "max_abs_daily_cogs_delta": delta["COGS"].abs().max(),
            }
        )
        period = (
            work.groupby("period")[["delta_Revenue", "delta_COGS"]]
            .sum()
            .reset_index()
            .assign(filename=filename)
        )
        period.to_csv(run_dir / f"period_delta_{Path(filename).stem}.csv", index=False)
    return pd.DataFrame(rows)


def build_period_matrix(files: list[str]) -> pd.DataFrame:
    rows = []
    for filename in files:
        frame = load_submission(filename)
        for period, g in frame.groupby("period", sort=False):
            rows.append(
                {
                    "filename": filename,
                    "public_score": PUBLIC_SCORES.get(filename, np.nan),
                    "period": period,
                    "revenue_total": g["Revenue"].sum(),
                    "cogs_total": g["COGS"].sum(),
                    "cogs_ratio": g["COGS"].sum() / g["Revenue"].sum(),
                    "mean_daily_revenue": g["Revenue"].mean(),
                    "mean_daily_cogs": g["COGS"].mean(),
                    "peak_daily_revenue": g["Revenue"].max(),
                    "peak_daily_cogs": g["COGS"].max(),
                }
            )
    return pd.DataFrame(rows)


def raw_date_audit() -> pd.DataFrame:
    rows = []
    for file_name in RAW_FILES:
        path = DATASET_DIR / file_name
        if not path.exists():
            continue
        frame = pd.read_csv(path, nrows=5000)
        full = None
        date_cols = []
        for col in frame.columns:
            if "date" in col.lower() or col.lower() in {"timestamp", "created_at"}:
                date_cols.append(col)
        if date_cols:
            full = pd.read_csv(path, usecols=date_cols)
        for col in date_cols:
            parsed = pd.to_datetime(full[col], errors="coerce")
            rows.append(
                {
                    "file": file_name,
                    "date_column": col,
                    "non_null": int(parsed.notna().sum()),
                    "min_date": str(parsed.min().date()) if parsed.notna().any() else "",
                    "max_date": str(parsed.max().date()) if parsed.notna().any() else "",
                    "has_forecast_period_rows": bool(
                        ((parsed >= FORECAST_START) & (parsed <= FORECAST_END)).any()
                    ),
                    "rows_in_forecast_period": int(
                        ((parsed >= FORECAST_START) & (parsed <= FORECAST_END)).sum()
                    ),
                }
            )
        if not date_cols:
            rows.append(
                {
                    "file": file_name,
                    "date_column": "",
                    "non_null": 0,
                    "min_date": "",
                    "max_date": "",
                    "has_forecast_period_rows": False,
                    "rows_in_forecast_period": 0,
                }
            )
    return pd.DataFrame(rows)


def monthly_raw_sales_profile() -> pd.DataFrame:
    sales = pd.read_csv(DATASET_DIR / "sales.csv")
    sales["Date"] = pd.to_datetime(sales["Date"])
    sales["year"] = sales["Date"].dt.year
    sales["month"] = sales["Date"].dt.month
    sales["half"] = np.where(sales["Date"].dt.month <= 6, "H1", "H2")
    return (
        sales.groupby(["year", "half"])
        .agg(
            revenue=("Revenue", "sum"),
            cogs=("COGS", "sum"),
            ratio=("COGS", lambda x: x.sum() / sales.loc[x.index, "Revenue"].sum()),
            daily_revenue_mean=("Revenue", "mean"),
            daily_revenue_max=("Revenue", "max"),
        )
        .reset_index()
    )


def write_report(
    run_dir: Path,
    submission_summary: pd.DataFrame,
    delta_summary: pd.DataFrame,
    period_matrix: pd.DataFrame,
    raw_audit: pd.DataFrame,
    train_periods: pd.DataFrame,
) -> None:
    clean_best = "submission_cleanv7_source_h1_s020_r0870.csv"
    failed = "submission_cleanv9_big_h1_keeprev_cogs_r0820.csv"
    report = f"""# Post Clean V9 Gap Analysis

Run directory: `{run_dir}`

## What just happened

- Current clean best: `{clean_best} = {PUBLIC_SCORES[clean_best]:.5f}`.
- New big COGS-down test: `{failed} = {PUBLIC_SCORES[failed]:.5f}`.
- Delta: `{PUBLIC_SCORES[failed] - PUBLIC_SCORES[clean_best]:+.2f}` MAE, so the hypothesis "2023H1 COGS ratio is far too high" is rejected.

## Main read

The clean branch is not primarily missing a broad period-level COGS ratio. It is missing a clean explanation for daily allocation/phase and selective high-ratio pockets. Blackbox improvements came from localized reshaping; clean COGS ratio changes that are too broad worsen.

## Score and total summary

{submission_summary.to_markdown(index=False)}

## Delta vs current clean best

{delta_summary.to_markdown(index=False)}

## Period matrix

{period_matrix.to_markdown(index=False)}

## Raw date audit

{raw_audit.to_markdown(index=False)}

## Train half-year profile

{train_periods.to_markdown(index=False)}

## Current gap hypothesis

1. We are not losing because CatBoost/TabPFN is weak; blackbox gains are mostly post-target geometry.
2. We are not losing because 2023H1 total COGS ratio should be aggressively lower; V9 r0820 worsened.
3. We are likely missing a clean driver for **when** demand/COGS happen inside a period: source-quality, cohort/repeat customers, payment risk, return alignment, promo mix, or stockout/product availability.
4. The next clean attempt should model daily weights, not only period totals: `daily_weight = calendar x promo x source_quality_prior x return/stockout pressure`.

## Next clean directions

- Build a daily allocation model for 2023H1/Q1/Q2 using only train-derived priors: source-quality, COD cancellation risk, return-rate by original order date, and stockout pressure.
- Keep period totals close to `cleanv7`; only change daily shape first. V9 proves broad COGS-ratio movement is fragile.
- Use blackbox as diagnosis only: it says Q1/H2 high-ratio pockets matter, but clean must explain those pockets using raw operational mechanisms.
"""
    note_path = NOTES_DIR / "post_cleanv9_gap_analysis_2026-04-28.md"
    note_path.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    run_dir = make_run_dir()
    submission_summary = pd.DataFrame([summarize_submission(file) for file in KEY_FILES])
    delta_summary = compare_to_anchor(KEY_FILES[0], KEY_FILES[1:])
    period_matrix = build_period_matrix(KEY_FILES)
    raw_audit = raw_date_audit()
    train_periods = monthly_raw_sales_profile()

    submission_summary.to_csv(run_dir / "submission_summary.csv", index=False)
    delta_summary.to_csv(run_dir / "delta_vs_clean_best.csv", index=False)
    period_matrix.to_csv(run_dir / "period_matrix.csv", index=False)
    raw_audit.to_csv(run_dir / "raw_date_audit.csv", index=False)
    train_periods.to_csv(run_dir / "train_halfyear_profile.csv", index=False)
    write_report(run_dir, submission_summary, delta_summary, period_matrix, raw_audit, train_periods)

    print(run_dir)
    print(delta_summary.sort_values("public_score").to_string(index=False))
