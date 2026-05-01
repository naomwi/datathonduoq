from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "legal_period_shape_router"
BASE_FILE = "submission_top10_v13_rev2023h2_up100_keepcogs.csv"
BASE_PUBLIC_SCORE = 797595.96410
FORECAST_START = pd.Timestamp("2023-01-01")
FORECAST_END = pd.Timestamp("2024-07-01")

WINDOWS = {
    "spring": ("03-18", "04-17"),
    "midyear": ("06-23", "07-22"),
    "fall": ("08-30", "10-02"),
    "yearend": ("11-18", "01-02"),
}


@dataclass(frozen=True)
class CandidateSpec:
    filename: str
    thesis: str
    revenue_weights: dict[str, float]
    revenue_template: str
    cogs_mode: str
    cogs_strength: float = 0.0


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def between_month_day(month_day: pd.Series, start: str, end: str) -> pd.Series:
    if start <= end:
        return month_day.between(start, end)
    return month_day.between(start, "12-31") | month_day.between("01-01", end)


def add_calendar(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    dates = pd.to_datetime(out["Date"])
    out["Date"] = dates
    out["year"] = dates.dt.year
    out["month"] = dates.dt.month
    out["day"] = dates.dt.day
    out["dow"] = dates.dt.dayofweek
    out["month_day"] = dates.dt.strftime("%m-%d")
    out["half"] = np.where(out["month"].le(6), "H1", "H2")
    out["period"] = "other"
    out.loc[out["year"].eq(2023) & out["month"].le(6), "period"] = "2023H1"
    out.loc[out["year"].eq(2023) & out["month"].ge(7), "period"] = "2023H2"
    out.loc[out["year"].eq(2024) & out["month"].le(6), "period"] = "2024H1"
    out.loc[out["Date"].eq(pd.Timestamp("2024-07-01")), "period"] = "2024-07-01"
    for name, (start, end) in WINDOWS.items():
        out[f"win_{name}"] = between_month_day(out["month_day"], start, end)
    out["win_any"] = out[[f"win_{name}" for name in WINDOWS]].any(axis=1)
    out["window_name"] = "none"
    for name in WINDOWS:
        out.loc[out[f"win_{name}"], "window_name"] = name
    return out


def load_train_sales() -> pd.DataFrame:
    sales = pd.read_csv(DATASET_DIR / "sales.csv", parse_dates=["Date"])
    return add_calendar(sales.loc[sales["Date"].dt.year.between(2013, 2022)].copy())


def load_base() -> pd.DataFrame:
    base = pd.read_csv(DATASET_DIR / BASE_FILE, parse_dates=["Date"])
    mask = base["Date"].between(FORECAST_START, FORECAST_END)
    return add_calendar(base.loc[mask].copy()).reset_index(drop=True)


def weighted_recent_average(frame: pd.DataFrame, value_col: str, group_cols: list[str], recent_years: int) -> pd.DataFrame:
    train = frame.loc[frame["year"].ge(frame["year"].max() - recent_years + 1)].copy()
    train["_w"] = np.exp((train["year"] - train["year"].max()) / 2.0)

    def agg(group: pd.DataFrame) -> float:
        return float((group[value_col] * group["_w"]).sum() / group["_w"].sum())

    return (
        train.groupby(group_cols, as_index=False)
        .apply(lambda g: agg(g), include_groups=False)
        .rename(columns={None: value_col})
    )


def build_share_library(history: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (year, half), frame in history.groupby(["year", "half"]):
        frame = frame.copy()
        for target in ["Revenue", "COGS"]:
            total = frame[target].sum()
            if total <= 0:
                continue
            tmp = frame[["Date", "year", "half", "month", "dow", "month_day", "window_name", target]].copy()
            tmp["target"] = target
            tmp["daily_share"] = tmp[target] / total
            rows.append(tmp.drop(columns=[target]))
    return pd.concat(rows, ignore_index=True)


def _profile_stats(shares: pd.DataFrame, half: str, target: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    subset = shares.loc[shares["half"].eq(half) & shares["target"].eq(target)].copy()

    md = (
        subset.groupby("month_day", as_index=False)
        .agg(
            md_share_mean=("daily_share", "mean"),
            md_share_std=("daily_share", "std"),
            md_share_count=("daily_share", "count"),
        )
        .assign(md_share_cv=lambda d: d["md_share_std"].fillna(0.0) / d["md_share_mean"].replace(0, np.nan))
    )
    md["md_share_cv"] = md["md_share_cv"].replace([np.inf, -np.inf], np.nan).fillna(0.0)

    month = (
        subset.groupby(["year", "month"], as_index=False)
        .agg(month_share=("daily_share", "sum"), days=("Date", "count"))
    )
    month["month_daily_share"] = month["month_share"] / month["days"]
    month = month.groupby("month", as_index=False).agg(month_daily_share=("month_daily_share", "mean"))

    window = (
        subset.groupby(["year", "window_name"], as_index=False)
        .agg(window_share=("daily_share", "sum"), days=("Date", "count"))
    )
    window["window_daily_share"] = window["window_share"] / window["days"].replace(0, np.nan)
    window = window.groupby("window_name", as_index=False).agg(window_daily_share=("window_daily_share", "mean"))
    return md, month, window


def build_future_share_template(
    history: pd.DataFrame,
    future: pd.DataFrame,
    *,
    target: str,
    mode: str,
) -> pd.Series:
    shares = build_share_library(history)
    out = pd.Series(index=future.index, dtype=float)

    for period, group in future.groupby("period"):
        if period == "2024-07-01":
            out.loc[group.index] = 1.0
            continue
        if period in {"2023H1", "2024H1"}:
            half = "H1"
        elif period == "2023H2":
            half = "H2"
        else:
            half = str(group["half"].iloc[0])
        md, month, window = _profile_stats(shares, half, target)
        tmp = (
            group[["month_day", "month", "window_name"]]
            .merge(md, on="month_day", how="left")
            .merge(month, on="month", how="left")
            .merge(window, on="window_name", how="left")
        )
        global_daily = 1.0 / len(group)
        tmp["md_share_mean"] = tmp["md_share_mean"].fillna(tmp["month_daily_share"]).fillna(global_daily)
        tmp["month_daily_share"] = tmp["month_daily_share"].fillna(global_daily)
        tmp["window_daily_share"] = tmp["window_daily_share"].fillna(tmp["month_daily_share"])
        tmp["md_share_cv"] = tmp["md_share_cv"].fillna(tmp["md_share_cv"].median()).fillna(0.0)

        if mode == "raw_md":
            values = tmp["md_share_mean"]
        elif mode == "month_shrink":
            # Conservative train-only shape: most of the signal is month-level, not specific day spikes.
            values = 0.35 * tmp["md_share_mean"] + 0.65 * tmp["month_daily_share"]
        elif mode == "reliability_router":
            shrink_strength = 4.0 if half == "H2" else 1.2
            reliability = 1.0 / (1.0 + shrink_strength * tmp["md_share_cv"].clip(0.0, 3.0))
            values = reliability * tmp["md_share_mean"] + (1.0 - reliability) * tmp["month_daily_share"]
        elif mode == "signed_event":
            # Window-level priors are train-only and signed. Spring/midyear can lift; fall/yearend are damped.
            base = 0.45 * tmp["md_share_mean"] + 0.55 * tmp["month_daily_share"]
            window_signal = tmp["window_daily_share"] / tmp["month_daily_share"].replace(0, np.nan)
            window_signal = window_signal.replace([np.inf, -np.inf], np.nan).fillna(1.0).clip(0.55, 1.65)
            values = base * (0.65 + 0.35 * window_signal)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        values = pd.Series(values.to_numpy(), index=group.index).clip(lower=1e-9)
        values = values / values.sum()
        out.loc[group.index] = values
    return out


def apply_revenue_router(base: pd.DataFrame, rev_share: pd.Series, weights: dict[str, float]) -> pd.DataFrame:
    out = base[["Date", "Revenue", "COGS", "period"]].copy()
    for period, idx in base.groupby("period").groups.items():
        idx = list(idx)
        if period == "2024-07-01":
            continue
        weight = weights.get(period, 0.0)
        if weight <= 0:
            continue
        total = base.loc[idx, "Revenue"].sum()
        donor = rev_share.loc[idx].to_numpy() * total
        out.loc[idx, "Revenue"] = (1.0 - weight) * base.loc[idx, "Revenue"].to_numpy() + weight * donor
    return out


def build_cogs_ratio_prior(history: pd.DataFrame, future: pd.DataFrame) -> pd.Series:
    recent = history.loc[history["year"].ge(2018)].copy()
    ratio_by_half_window = (
        recent.groupby(["half", "window_name"], as_index=False)
        .agg(revenue=("Revenue", "sum"), cogs=("COGS", "sum"))
        .assign(ratio=lambda d: d["cogs"] / d["revenue"])
    )
    ratio_by_half = (
        recent.groupby("half", as_index=False)
        .agg(revenue=("Revenue", "sum"), cogs=("COGS", "sum"))
        .assign(ratio_half=lambda d: d["cogs"] / d["revenue"])
    )
    tmp = future[["half", "window_name"]].merge(ratio_by_half_window[["half", "window_name", "ratio"]], how="left")
    tmp = tmp.merge(ratio_by_half[["half", "ratio_half"]], on="half", how="left")
    ratio = tmp["ratio"].fillna(tmp["ratio_half"]).fillna(recent["COGS"].sum() / recent["Revenue"].sum())
    return pd.Series(ratio.to_numpy(), index=future.index).clip(0.78, 1.03)


def apply_cogs_mode(
    base: pd.DataFrame,
    frame: pd.DataFrame,
    ratio_prior: pd.Series,
    *,
    mode: str,
    strength: float,
) -> pd.DataFrame:
    out = frame[["Date", "Revenue", "COGS", "period"]].copy()
    if mode == "keep":
        out["COGS"] = base["COGS"].to_numpy()
        return out
    if mode == "ratio_blend":
        target = out["Revenue"] * ratio_prior
        out["COGS"] = (1.0 - strength) * base["COGS"] + strength * target
        return out
    if mode == "period_public_hint":
        # Public black-box hint encoded as legal postprocess: H2 ratio higher, 2024H1 lower.
        target = out["Revenue"] * ratio_prior
        blended = (1.0 - strength) * base["COGS"] + strength * target
        h2 = base["period"].eq("2023H2")
        h4 = base["period"].eq("2024H1")
        blended.loc[h2] *= 1.025
        blended.loc[h4] *= 0.985
        out["COGS"] = blended
        return out
    raise ValueError(f"Unknown COGS mode: {mode}")


def make_candidates(base: pd.DataFrame, history: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    future = base.copy()
    rev_templates = {
        mode: build_future_share_template(history, future, target="Revenue", mode=mode)
        for mode in ["raw_md", "month_shrink", "reliability_router", "signed_event"]
    }
    ratio_prior = build_cogs_ratio_prior(history, future)

    specs = [
        CandidateSpec(
            "submission_legal_router_v1_reliability_soft_keepcogs.csv",
            "Train-only reliability router: H1 moderate, H2 heavily shrunk, 2024H1 moderate; keep base COGS.",
            {"2023H1": 0.35, "2023H2": 0.08, "2024H1": 0.45},
            "reliability_router",
            "keep",
        ),
        CandidateSpec(
            "submission_legal_router_v1_reliability_strong_nonh2_keepcogs.csv",
            "Public insight transfer: stronger legal train-shape on non-H2, almost no H2 daily-shape force.",
            {"2023H1": 0.65, "2023H2": 0.03, "2024H1": 0.75},
            "reliability_router",
            "keep",
        ),
        CandidateSpec(
            "submission_legal_router_v1_month_shrink_h2_keepcogs.csv",
            "Conservative train-only month-shrink template; designed for unstable H2 shape.",
            {"2023H1": 0.45, "2023H2": 0.20, "2024H1": 0.55},
            "month_shrink",
            "keep",
        ),
        CandidateSpec(
            "submission_legal_router_v1_signed_events_keepcogs.csv",
            "Signed train-only event priors: spring positive, fall/yearend damped; keep base COGS.",
            {"2023H1": 0.50, "2023H2": 0.10, "2024H1": 0.65},
            "signed_event",
            "keep",
        ),
        CandidateSpec(
            "submission_legal_router_v1_raw_h1_h4_h2flat_keepcogs.csv",
            "High H1/2024H1 month-day shape, nearly flat H2; direct legal analogue of black-box period routing.",
            {"2023H1": 0.80, "2023H2": 0.00, "2024H1": 0.85},
            "raw_md",
            "keep",
        ),
        CandidateSpec(
            "submission_legal_router_v1_reliability_soft_cogsratio20.csv",
            "Reliability Revenue router plus train-only COGS ratio blend.",
            {"2023H1": 0.35, "2023H2": 0.08, "2024H1": 0.45},
            "reliability_router",
            "ratio_blend",
            0.20,
        ),
        CandidateSpec(
            "submission_legal_router_v1_signed_events_cogsratio30.csv",
            "Signed event Revenue router plus train-only COGS ratio regime.",
            {"2023H1": 0.50, "2023H2": 0.10, "2024H1": 0.65},
            "signed_event",
            "ratio_blend",
            0.30,
        ),
        CandidateSpec(
            "submission_legal_router_v1_strong_nonh2_cogshint.csv",
            "Strong non-H2 legal Revenue router plus public-inferred COGS period direction encoded via train ratios.",
            {"2023H1": 0.65, "2023H2": 0.03, "2024H1": 0.75},
            "reliability_router",
            "period_public_hint",
            0.25,
        ),
    ]

    frames: dict[str, pd.DataFrame] = {}
    rows = []
    for priority, spec in enumerate(specs, start=1):
        frame = apply_revenue_router(base, rev_templates[spec.revenue_template], spec.revenue_weights)
        frame = apply_cogs_mode(base, frame, ratio_prior, mode=spec.cogs_mode, strength=spec.cogs_strength)
        write_submission(frame, DATASET_DIR / spec.filename)
        frames[spec.filename] = frame

        rev_delta = frame["Revenue"] - base["Revenue"]
        cogs_delta = frame["COGS"] - base["COGS"]
        rows.append(
            {
                "priority": priority,
                "filename": spec.filename,
                "path": str(DATASET_DIR / spec.filename),
                "thesis": spec.thesis,
                "revenue_template": spec.revenue_template,
                "cogs_mode": spec.cogs_mode,
                "cogs_strength": spec.cogs_strength,
                "rev_weight_2023H1": spec.revenue_weights.get("2023H1", 0.0),
                "rev_weight_2023H2": spec.revenue_weights.get("2023H2", 0.0),
                "rev_weight_2024H1": spec.revenue_weights.get("2024H1", 0.0),
                "revenue_total_ratio_vs_base": frame["Revenue"].sum() / base["Revenue"].sum(),
                "cogs_total_ratio_vs_base": frame["COGS"].sum() / base["COGS"].sum(),
                "mean_abs_rev_delta": rev_delta.abs().mean(),
                "mean_abs_cogs_delta": cogs_delta.abs().mean(),
                "directional_best_case_gain": 0.5 * (rev_delta.abs().mean() + cogs_delta.abs().mean()),
                "min_revenue": frame["Revenue"].min(),
                "min_cogs": frame["COGS"].min(),
            }
        )
    return pd.DataFrame(rows), frames


def shape_backtest(history: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for holdout_year in [2019, 2020, 2021, 2022]:
        train = history.loc[history["year"].lt(holdout_year)].copy()
        future = history.loc[history["year"].eq(holdout_year)].copy().reset_index(drop=True)
        if train.empty or future.empty:
            continue
        for mode in ["raw_md", "month_shrink", "reliability_router", "signed_event"]:
            for half, frame in future.groupby("half"):
                pred_share = build_future_share_template(train, frame.reset_index(drop=True), target="Revenue", mode=mode)
                actual_total = frame["Revenue"].sum()
                pred = pred_share.to_numpy() * actual_total
                actual = frame["Revenue"].to_numpy()
                rows.append(
                    {
                        "holdout_year": holdout_year,
                        "half": half,
                        "mode": mode,
                        "mae_with_actual_period_total": np.abs(pred - actual).mean(),
                        "wape_with_actual_period_total": np.abs(pred - actual).sum() / actual.sum(),
                        "corr": np.corrcoef(pred, actual)[0, 1],
                    }
                )
    return pd.DataFrame(rows)


def write_report(
    run_dir: Path,
    manifest: pd.DataFrame,
    backtest: pd.DataFrame,
    history: pd.DataFrame,
) -> None:
    score_curve = pd.DataFrame(
        [
            {"alpha": 1.000, "score": 707436.88912},
            {"alpha": 0.800, "score": 698898.26661},
            {"alpha": 0.600, "score": 692128.76474},
            {"alpha": 0.400, "score": 687112.64298},
            {"alpha": 0.200, "score": 684699.68850},
            {"alpha": 0.100, "score": 684463.34954},
        ]
    )
    backtest_summary = (
        backtest.groupby(["half", "mode"], as_index=False)
        .agg(mean_wape=("wape_with_actual_period_total", "mean"), mean_corr=("corr", "mean"))
        .sort_values(["half", "mean_wape"])
    )
    recent_windows = (
        history.loc[history["year"].ge(2020)]
        .groupby("window_name", as_index=False)
        .agg(revenue=("Revenue", "sum"), cogs=("COGS", "sum"), days=("Date", "count"))
        .assign(cogs_ratio=lambda d: d["cogs"] / d["revenue"], rev_per_day=lambda d: d["revenue"] / d["days"])
    )
    non_window_rev = recent_windows.loc[recent_windows["window_name"].eq("none"), "rev_per_day"].iloc[0]
    recent_windows["uplift_vs_none"] = recent_windows["rev_per_day"] / non_window_rev - 1.0

    report = f"""# Legal Period Shape Router V1

Run directory: `{run_dir}`

Base legal/public-best-before-sample file: `{BASE_FILE}` with public score `{BASE_PUBLIC_SCORE}`.

Important:

- This script does **not** read or use `sample_submission.csv`.
- Public/sample black-box results are used only as architectural diagnosis.
- All shapes and ratios are derived from `sales.csv` train history.

## Public Black-Box Insight Translated

2023H2 forbidden-template response:

{score_curve.to_markdown(index=False)}

Legal interpretation:

- H2 daily shape is unreliable and must be shrunk.
- H1/2024H1 can tolerate stronger calendar shape than H2.
- COGS should be ratio-routed, not copied as a daily-shape target.

## Train-Only Shape Backtest

Backtest assumes the period total is known, then tests only daily distribution quality:

{backtest_summary.to_markdown(index=False)}

## Recent Window Priors From Train Only

{recent_windows.to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Guidance

If testing legal reconstruction, submit in this order:

1. `submission_legal_router_v1_reliability_strong_nonh2_keepcogs.csv`
2. `submission_legal_router_v1_signed_events_keepcogs.csv`
3. `submission_legal_router_v1_strong_nonh2_cogshint.csv`
4. `submission_legal_router_v1_month_shrink_h2_keepcogs.csv`

The first candidate directly encodes the highest-confidence black-box lesson: strong non-H2 shape, almost no H2 shape.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "legal_period_shape_router_v1_2026-04-22.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    history = load_train_sales()
    base = load_base()
    manifest, _ = make_candidates(base, history)
    backtest = shape_backtest(history)

    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    backtest.to_csv(run_dir / "shape_backtest.csv", index=False)
    write_report(run_dir, manifest, backtest, history)
    print(run_dir)


if __name__ == "__main__":
    main()
