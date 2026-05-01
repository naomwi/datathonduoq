from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json
from train_recursive_forecast import (
    CONTEXT_POLICY_COLUMNS,
    PRICE_SIGNAL_COLUMNS,
    PROMO_POLICY_COLUMNS,
    TRAIN_END,
    apply_future_context_policy,
    apply_future_price_policy,
    apply_future_promo_policy,
    ensure_inputs,
)


RUN_PREFIX = "future_policy_shift"
PUBLIC_START = pd.Timestamp("2023-01-01")
PUBLIC_END = pd.Timestamp("2024-07-01")
POLICIES = ["seasonal_month_day_recent_1y", "seasonal_month_day_recent_2y", "seasonal_month_day_recent_3y", "seasonal_month_day_recent_2y_median"]


def mask_between_month_day(dates: pd.Series, start: str, end: str) -> pd.Series:
    md = dates.dt.strftime("%m-%d")
    if start <= end:
        return md.between(start, end)
    return md.between(start, "12-31") | md.between("01-01", end)


def add_windows(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    dates = pd.to_datetime(out["Date"])
    out["year"] = dates.dt.year
    out["month"] = dates.dt.month
    out["win_spring"] = mask_between_month_day(dates, "03-18", "04-17")
    out["win_midyear"] = mask_between_month_day(dates, "06-23", "07-22")
    out["win_fall"] = mask_between_month_day(dates, "08-30", "10-02")
    out["win_yearend"] = mask_between_month_day(dates, "11-18", "01-02")
    out["win_rural"] = mask_between_month_day(dates, "01-30", "03-01")
    out["win_urban"] = mask_between_month_day(dates, "07-30", "09-02")
    out["win_main"] = out["win_spring"] | out["win_midyear"] | out["win_fall"] | out["win_yearend"]
    return out


def summarize_frame(frame: pd.DataFrame, label: str) -> list[dict[str, object]]:
    frame = add_windows(frame)
    groups = [
        ("all", frame["Date"].notna()),
        ("2023", frame["year"] == 2023),
        ("2024_h1", frame["Date"].between("2024-01-01", PUBLIC_END)),
        ("main", frame["win_main"]),
        ("nonmain", ~frame["win_main"]),
        ("spring", frame["win_spring"]),
        ("midyear", frame["win_midyear"]),
        ("fall", frame["win_fall"]),
        ("yearend", frame["win_yearend"]),
        ("rural", frame["win_rural"]),
        ("urban", frame["win_urban"]),
    ]
    rows = []
    for group, mask in groups:
        sub = frame.loc[mask]
        if sub.empty:
            continue
        row = {
            "label": label,
            "group": group,
            "rows": len(sub),
            "active_promo_count": float(sub.get("active_promo_count", pd.Series(dtype=float)).mean()),
            "active_stackable_promo_count": float(sub.get("active_stackable_promo_count", pd.Series(dtype=float)).mean()),
            "active_promo_discount_value_mean": float(sub.get("active_promo_discount_value_mean", pd.Series(dtype=float)).mean()),
            "promo_line_share": float(sub.get("promo_line_share", pd.Series(dtype=float)).mean()),
            "avg_discount_rate": float(sub.get("avg_discount_rate", pd.Series(dtype=float)).mean()),
            "total_discount": float(sub.get("total_discount", pd.Series(dtype=float)).mean()),
            "active_promo_category_global_count": float(sub.get("active_promo_category_global_count", pd.Series(dtype=float)).mean()),
            "active_promo_category_outdoor_count": float(sub.get("active_promo_category_outdoor_count", pd.Series(dtype=float)).mean()),
            "active_promo_category_streetwear_count": float(sub.get("active_promo_category_streetwear_count", pd.Series(dtype=float)).mean()),
            "sessions": float(sub.get("sessions", pd.Series(dtype=float)).mean()),
            "avg_unit_price": float(sub.get("avg_unit_price", pd.Series(dtype=float)).mean()),
            "margin_rate": float(sub.get("margin_rate", pd.Series(dtype=float)).mean()),
        }
        rows.append(row)
    return rows


def train_window_summaries(base: pd.DataFrame) -> pd.DataFrame:
    base = add_windows(base)
    train = base.loc[base["Date"] <= TRAIN_END].copy()
    rows = []
    for year in range(2018, 2023):
        rows.extend(summarize_frame(train.loc[train["year"] == year], f"actual_{year}"))
    rows.extend(summarize_frame(train.loc[train["Date"] >= pd.Timestamp("2021-01-01")], "actual_recent_2y"))
    rows.extend(summarize_frame(train.loc[train["Date"] >= pd.Timestamp("2020-01-01")], "actual_recent_3y"))
    return pd.DataFrame(rows)


def public_policy_summaries(base: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for policy in POLICIES:
        adjusted = apply_future_promo_policy(base, TRAIN_END, policy)
        public = adjusted.loc[adjusted["Date"].between(PUBLIC_START, PUBLIC_END)].copy()
        rows.extend(summarize_frame(public, f"promo_policy_{policy}"))

    # Context and price are separate because many public-toxic candidates came from these groups.
    adjusted_context = apply_future_context_policy(base, TRAIN_END, "seasonal_month_day_recent_2y")
    rows.extend(
        summarize_frame(
            adjusted_context.loc[adjusted_context["Date"].between(PUBLIC_START, PUBLIC_END)].copy(),
            "context_policy_seasonal_month_day_recent_2y",
        )
    )
    adjusted_price = apply_future_price_policy(base, TRAIN_END, "seasonal_month_day_recent_2y")
    rows.extend(
        summarize_frame(
            adjusted_price.loc[adjusted_price["Date"].between(PUBLIC_START, PUBLIC_END)].copy(),
            "price_policy_seasonal_month_day_recent_2y",
        )
    )
    return pd.DataFrame(rows)


def compare_policy_to_actual(summary: pd.DataFrame) -> pd.DataFrame:
    actual = summary.loc[summary["label"] == "actual_recent_2y"].set_index("group")
    rows = []
    for _, row in summary.loc[summary["label"].str.startswith(("promo_policy", "context_policy", "price_policy"))].iterrows():
        group = row["group"]
        if group not in actual.index:
            continue
        ref = actual.loc[group]
        out = {"label": row["label"], "group": group, "rows": row["rows"]}
        for col in [
            "active_promo_count",
            "active_promo_discount_value_mean",
            "promo_line_share",
            "avg_discount_rate",
            "total_discount",
            "sessions",
            "avg_unit_price",
            "margin_rate",
        ]:
            out[f"{col}_delta_vs_recent2y"] = float(row[col] - ref[col])
            denom = abs(float(ref[col])) if abs(float(ref[col])) > 1e-9 else np.nan
            out[f"{col}_ratio_vs_recent2y"] = float(row[col] / denom) if pd.notna(denom) else np.nan
        rows.append(out)
    return pd.DataFrame(rows)


def write_report(run_dir: Path, summary: pd.DataFrame, compare: pd.DataFrame) -> None:
    with (run_dir / "report.md").open("w", encoding="utf-8") as f:
        f.write("# Future Policy Shift\n\n")
        f.write("Compares actual train features with generated future policy features for 2023-2024.\n\n")
        f.write("## Key Summary Rows\n")
        labels = [
            "actual_2020",
            "actual_2021",
            "actual_2022",
            "actual_recent_2y",
            "promo_policy_seasonal_month_day_recent_2y",
            "promo_policy_seasonal_month_day_recent_1y",
            "context_policy_seasonal_month_day_recent_2y",
            "price_policy_seasonal_month_day_recent_2y",
        ]
        key = summary.loc[summary["label"].isin(labels) & summary["group"].isin(["all", "main", "nonmain", "urban", "rural"])]
        f.write(key.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Generated Policy vs Actual Recent 2Y\n")
        f.write(compare.loc[compare["group"].isin(["all", "main", "nonmain", "urban", "rural"])].to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    _, base = ensure_inputs()
    train_summary = train_window_summaries(base)
    public_summary = public_policy_summaries(base)
    summary = pd.concat([train_summary, public_summary], ignore_index=True)
    compare = compare_policy_to_actual(summary)
    summary.to_csv(run_dir / "future_policy_summary.csv", index=False)
    compare.to_csv(run_dir / "future_policy_vs_recent2y.csv", index=False)
    write_json(
        run_dir / "config.json",
        {
            "public_period": [str(PUBLIC_START.date()), str(PUBLIC_END.date())],
            "policies": POLICIES,
        },
    )
    write_report(run_dir, summary, compare)
    logger.info("Saved future policy shift analysis to %s", run_dir)
    print(summary.loc[summary["label"].isin(["actual_2021", "actual_2022", "actual_recent_2y", "promo_policy_seasonal_month_day_recent_2y", "context_policy_seasonal_month_day_recent_2y", "price_policy_seasonal_month_day_recent_2y"]) & summary["group"].isin(["all", "main", "nonmain", "urban", "rural"])].to_string(index=False))
    print(compare.loc[compare["group"].isin(["all", "main", "nonmain", "urban", "rural"])].to_string(index=False))


if __name__ == "__main__":
    main()
