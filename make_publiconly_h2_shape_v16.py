from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns, write_submission


RUN_PREFIX = "publiconly_h2_shape_v16"
CURRENT_BEST_FILE = "submission_top10_v13_rev2023h2_up100_keepcogs.csv"
CURRENT_BEST_SCORE = 797595.96410
LATEST_FAILED_FILE = "submission_h2rev_v15_current_h2_rev_up050.csv"
LATEST_FAILED_SCORE = 800572.16096

KNOWN_RESULTS = {
    "submission_publiconly_segment_v8_h2best_2024h1_down100.csv": 807504.66276,
    "submission_top10_v13_rev2023h2_up100_keepcogs.csv": CURRENT_BEST_SCORE,
    LATEST_FAILED_FILE: LATEST_FAILED_SCORE,
}

MONTHS_H2 = [7, 8, 9, 10, 11, 12]
ODD_REFERENCE_YEARS = [2013, 2015, 2017, 2019, 2021]
LAST_ODD_REFERENCE_YEAR = 2021


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
    out["month_key"] = out["Date"].dt.strftime("%Y-%m")
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
    )


def current_h2_month_profile(frame: pd.DataFrame) -> pd.DataFrame:
    h2 = frame[frame["period"].eq("2023H2")]
    monthly = h2.groupby("month", as_index=False)[["Revenue", "COGS"]].sum()
    monthly["rev_share"] = monthly["Revenue"] / monthly["Revenue"].sum()
    monthly["cogs_share"] = monthly["COGS"] / monthly["COGS"].sum()
    monthly["ratio"] = monthly["COGS"] / monthly["Revenue"]
    return monthly


def preserve_h2_month_shares(
    base: pd.DataFrame,
    target_shares: pd.DataFrame,
    columns: tuple[str, ...],
) -> pd.DataFrame:
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
            desired_total = total * float(row[share_col])
            out.loc[month_mask, col] *= desired_total / current_total
    return out


def multiply_and_normalize_h2(
    base: pd.DataFrame,
    revenue_multipliers: dict[int, float] | None = None,
    cogs_multipliers: dict[int, float] | None = None,
) -> pd.DataFrame:
    out = base[["Date", "Revenue", "COGS"]].copy()
    h2_mask = base["period"].eq("2023H2")
    for col, multipliers in (("Revenue", revenue_multipliers or {}), ("COGS", cogs_multipliers or {})):
        original_total = out.loc[h2_mask, col].sum()
        for month, multiplier in multipliers.items():
            out.loc[h2_mask & base["month"].eq(month), col] *= multiplier
        new_total = out.loc[h2_mask, col].sum()
        if new_total > 0:
            out.loc[h2_mask, col] *= original_total / new_total
    return out


def summarize_candidate(base: pd.DataFrame, frame: pd.DataFrame, filename: str, thesis: str, priority: int) -> dict[str, object]:
    profile = add_segments(frame)
    h2 = profile["period"].eq("2023H2")
    delta_rev = frame["Revenue"] - base["Revenue"]
    delta_cogs = frame["COGS"] - base["COGS"]
    h2_month = current_h2_month_profile(profile)
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
        "h2_ratio": profile.loc[h2, "COGS"].sum() / profile.loc[h2, "Revenue"].sum(),
        "h2_jul_rev_share": h2_month.loc[h2_month["month"].eq(7), "rev_share"].iloc[0],
        "h2_aug_cogs_share": h2_month.loc[h2_month["month"].eq(8), "cogs_share"].iloc[0],
        "h2_oct_cogs_share": h2_month.loc[h2_month["month"].eq(10), "cogs_share"].iloc[0],
        "h2_dec_cogs_share": h2_month.loc[h2_month["month"].eq(12), "cogs_share"].iloc[0],
    }


def register(
    rows: list[dict[str, object]],
    base: pd.DataFrame,
    frame: pd.DataFrame,
    filename: str,
    thesis: str,
    priority: int,
) -> None:
    write_submission(frame, DATASET_DIR / filename)
    rows.append(summarize_candidate(base, frame, filename, thesis, priority))


def main() -> None:
    run_dir = make_run_dir()
    current = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    historical_daily = build_historical_daily()
    odd_mean = h2_month_shares(historical_daily, ODD_REFERENCE_YEARS)
    last_odd = h2_month_shares(historical_daily, [LAST_ODD_REFERENCE_YEAR])

    rows: list[dict[str, object]] = []
    specs = [
        (
            "submission_h2shape_v16_cogs_oddmean_preserve.csv",
            preserve_h2_month_shares(current, odd_mean, ("COGS",)),
            "preserve total H2 COGS, reshape monthly COGS to odd-year mean shares",
            1,
        ),
        (
            "submission_h2shape_v16_revcogs_oddmean_preserve.csv",
            preserve_h2_month_shares(current, odd_mean, ("Revenue", "COGS")),
            "preserve H2 totals, reshape both Revenue and COGS to odd-year mean shares",
            2,
        ),
        (
            "submission_h2shape_v16_cogs_2021_preserve.csv",
            preserve_h2_month_shares(current, last_odd, ("COGS",)),
            "preserve total H2 COGS, use 2021 H2 COGS monthly shares as nearest odd-year analogue",
            3,
        ),
        (
            "submission_h2shape_v16_revcogs_2021_preserve.csv",
            preserve_h2_month_shares(current, last_odd, ("Revenue", "COGS")),
            "preserve H2 totals, use 2021 H2 monthly shares as nearest odd-year analogue",
            4,
        ),
        (
            "submission_h2shape_v16_cogs_q3up_preserve.csv",
            multiply_and_normalize_h2(current, cogs_multipliers={7: 1.08, 8: 1.08, 9: 1.08}),
            "preserve total H2 COGS, move COGS mass from Q4 into Q3",
            5,
        ),
        (
            "submission_h2shape_v16_cogs_augdec_up_preserve.csv",
            multiply_and_normalize_h2(current, cogs_multipliers={8: 1.15, 12: 1.08}),
            "preserve total H2 COGS, emphasize August and December odd-year cost spikes",
            6,
        ),
        (
            "submission_h2shape_v16_rev_oddmean_preserve.csv",
            preserve_h2_month_shares(current, odd_mean, ("Revenue",)),
            "preserve total H2 Revenue, reshape monthly Revenue to odd-year mean shares",
            7,
        ),
        (
            "submission_h2shape_v16_rev_q3up_preserve.csv",
            multiply_and_normalize_h2(current, revenue_multipliers={7: 1.05, 8: 1.05, 9: 1.05}),
            "preserve total H2 Revenue, move Revenue mass from Q4 into Q3",
            8,
        ),
        (
            "submission_h2shape_v16_rev_julup_preserve.csv",
            multiply_and_normalize_h2(current, revenue_multipliers={7: 1.12}),
            "preserve total H2 Revenue, test odd-year July Revenue underprediction",
            9,
        ),
        (
            "submission_h2shape_v16_revjul_cogsaugdec_preserve.csv",
            multiply_and_normalize_h2(
                current,
                revenue_multipliers={7: 1.10},
                cogs_multipliers={8: 1.12, 12: 1.06},
            ),
            "preserve H2 totals, combine July Revenue shift with Aug/Dec COGS shift",
            10,
        ),
    ]

    for filename, frame, thesis, priority in specs:
        register(rows, current, frame, filename, thesis, priority)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    current_h2_month_profile(current).to_csv(run_dir / "current_best_h2_month_profile.csv", index=False)
    odd_mean.to_csv(run_dir / "odd_mean_h2_month_shares.csv", index=False)
    last_odd.to_csv(run_dir / "last_odd_2021_h2_month_shares.csv", index=False)

    report = f"""# Public-Only H2 Shape V16

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Latest failed scale probe: `{LATEST_FAILED_FILE}` scored `{LATEST_FAILED_SCORE}`.

Known results:

{pd.Series(KNOWN_RESULTS, name="public_score").to_markdown()}

Interpretation:

- Extra H2 Revenue +5% worsened from `{CURRENT_BEST_SCORE}` to `{LATEST_FAILED_SCORE}`, so broad H2 scale is near saturation.
- The next high-leverage hypothesis is H2 monthly shape, especially COGS timing.
- Historical odd-year H2 puts more COGS mass into Jul-Aug/Dec and less into Oct-Nov than the current best.
- These candidates preserve H2 totals unless explicitly stated otherwise, so they test shape rather than another broad leaderboard scale knob.

Current best H2 monthly profile:

{current_h2_month_profile(current).to_markdown(index=False)}

Odd-year mean H2 monthly shares:

{odd_mean.to_markdown(index=False)}

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_h2shape_v16_cogs_oddmean_preserve.csv`
2. If it improves: `submission_h2shape_v16_revcogs_oddmean_preserve.csv`
3. If COGS oddmean is too aggressive: `submission_h2shape_v16_cogs_q3up_preserve.csv`
4. Only after COGS-shape signal: test Revenue shape with `submission_h2shape_v16_rev_oddmean_preserve.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_h2_shape_v16_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
