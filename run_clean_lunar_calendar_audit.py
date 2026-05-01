from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from lunar_calendar_features import add_lunar_calendar_features


DATASET_DIR = Path("dataset")
LOG_ROOT = Path("logs")
NOTES_DIR = Path("notes")
RUN_PREFIX = "clean_lunar_calendar_audit"
TRAIN_END = pd.Timestamp("2022-12-31")


WINDOWS = [
    "win_tet_pre14_1",
    "win_tet_pre7_1",
    "win_tet_0_3",
    "win_tet_0_6",
    "win_tet_post4_14",
    "win_tet_post15_35",
    "win_tet_wide",
]


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def load_sales() -> pd.DataFrame:
    sales = pd.read_csv(DATASET_DIR / "sales.csv", parse_dates=["Date"])
    sales = sales.loc[sales["Date"].le(TRAIN_END)].copy()
    sales["year"] = sales["Date"].dt.year
    sales["month"] = sales["Date"].dt.month
    sales["month_day"] = sales["Date"].dt.strftime("%m-%d")
    sales["cogs_ratio"] = sales["COGS"] / sales["Revenue"].replace(0, np.nan)
    return sales


def summarize_windows(frame: pd.DataFrame) -> pd.DataFrame:
    base = frame.copy()
    base["month_rev_avg"] = base.groupby(["year", "month"])["Revenue"].transform("mean")
    base["month_cogs_avg"] = base.groupby(["year", "month"])["COGS"].transform("mean")
    base["rev_rel_month"] = base["Revenue"] / base["month_rev_avg"].replace(0, np.nan)
    base["cogs_rel_month"] = base["COGS"] / base["month_cogs_avg"].replace(0, np.nan)
    rows: list[dict[str, object]] = []
    for window in WINDOWS:
        part = base.loc[base[window].eq(1)].copy()
        if part.empty:
            continue
        rows.append(
            {
                "window": window,
                "years": int(part["year"].nunique()),
                "days": int(len(part)),
                "rev_rel_median": float(part["rev_rel_month"].median()),
                "rev_rel_mean": float(part["rev_rel_month"].mean()),
                "cogs_rel_median": float(part["cogs_rel_month"].median()),
                "cogs_rel_mean": float(part["cogs_rel_month"].mean()),
                "cogs_ratio_median": float(part["cogs_ratio"].median()),
                "cogs_ratio_mean": float(part["cogs_ratio"].mean()),
                "revenue_total": float(part["Revenue"].sum()),
                "cogs_total": float(part["COGS"].sum()),
            }
        )
    return pd.DataFrame(rows)


def summarize_tet_dates(frame: pd.DataFrame) -> pd.DataFrame:
    cols = ["year", "tet_date"]
    out = frame[cols].drop_duplicates().sort_values("year").copy()
    out["tet_date"] = pd.to_datetime(out["tet_date"]).dt.strftime("%Y-%m-%d")
    return out


def feature_correlations(frame: pd.DataFrame) -> pd.DataFrame:
    feature_cols = [
        "lunar_day",
        "lunar_month",
        "days_from_tet",
        "days_to_tet",
        "lunar_month_sin",
        "lunar_month_cos",
        "lunar_day_sin",
        "lunar_day_cos",
        *WINDOWS,
    ]
    rows: list[dict[str, object]] = []
    for feature in feature_cols:
        series = frame[feature]
        rows.append(
            {
                "feature": feature,
                "corr_revenue_spearman": float(series.corr(frame["Revenue"], method="spearman")),
                "corr_cogs_spearman": float(series.corr(frame["COGS"], method="spearman")),
                "corr_cogs_ratio_spearman": float(series.corr(frame["cogs_ratio"], method="spearman")),
            }
        )
    result = pd.DataFrame(rows)
    return result.sort_values("corr_revenue_spearman", key=lambda s: s.abs(), ascending=False)


def write_report(run_dir: Path, tet_dates: pd.DataFrame, windows: pd.DataFrame, corr: pd.DataFrame) -> None:
    best_window = windows.sort_values("rev_rel_median", ascending=False).head(1)
    best_text = ""
    if not best_window.empty:
        row = best_window.iloc[0]
        best_text = (
            f"- Strongest median Revenue window: `{row['window']}` with "
            f"`rev_rel_median={row['rev_rel_median']:.4f}` and "
            f"`cogs_ratio_median={row['cogs_ratio_median']:.4f}`.\n"
        )
    report = f"""# Clean Lunar Calendar Audit

Run directory: `{run_dir}`

## Boundary

This audit derives lunar-calendar features deterministically from the existing `Date` column. It does not merge a holiday table, query the internet, or read external event data.

## Read

{best_text}- Historical Tet effects are measurable but should be treated as a small calendar family, not as a standalone breakthrough.
- Current broad `is_tet_month` is only a Jan/Feb approximation; exact lunar windows are cleaner and more explainable.

## Files

- `tet_dates.csv`
- `lunar_window_summary.csv`
- `lunar_feature_correlations.csv`

## Suggested Model Use

Use exact lunar features as derived calendar features:

- `lunar_month`, `lunar_day`, cyclic lunar encodings.
- `days_from_tet`, `days_to_tet`.
- Tet windows: pre-Tet, Tet core, post-Tet, and wide Tet window.

Do not use hard-coded Tet date tables in final clean code if the report claims the feature is derived only from `Date`.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    note_path = NOTES_DIR / f"clean_lunar_calendar_audit_{datetime.now():%Y-%m-%d}.md"
    note_path.write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    sales = load_sales()
    lunar = add_lunar_calendar_features(sales)
    tet_dates = summarize_tet_dates(lunar)
    windows = summarize_windows(lunar)
    corr = feature_correlations(lunar)

    tet_dates.to_csv(run_dir / "tet_dates.csv", index=False)
    windows.to_csv(run_dir / "lunar_window_summary.csv", index=False)
    corr.to_csv(run_dir / "lunar_feature_correlations.csv", index=False)
    write_report(run_dir, tet_dates, windows, corr)
    print(f"Saved lunar calendar audit to {run_dir}")


if __name__ == "__main__":
    main()
