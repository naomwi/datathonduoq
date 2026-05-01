from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_clean_v2_train_evidence import build_daily_panel
from run_clean_regime_recovery_scenarios import load_sales
from run_clean_v10_h1_regime_shape import sanity_check
from run_clean_v13_daily_peak_allocator import (
    CandidateSpec as AllocatorSpec,
    add_daily_calendar,
    build_base_frames,
    normalized_profile,
)
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v15_ratio_first_cogs_allocator"


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    revenue_alpha: float
    ratio_alpha: float
    ratio_prior: str
    note: str


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def weighted_mean(values: pd.Series, years: pd.Series, decay: float = 3.0) -> float:
    clean = pd.DataFrame({"value": values, "year": years}).replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return np.nan
    weights = np.exp((clean["year"].to_numpy(dtype=float) - clean["year"].max()) / decay)
    return float(np.average(clean["value"].to_numpy(dtype=float), weights=weights))


def add_boundary_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = add_daily_calendar(frame)
    out["days_to_month_end"] = out["days_in_month"] - out["day"]
    out["week_of_month"] = ((out["day"] - 1) // 7 + 1).astype(int)
    out["is_last_3_days"] = out["days_to_month_end"].le(2).astype(int)
    out["is_first_3_days"] = out["day"].le(3).astype(int)
    return out


def ratio_history(daily: pd.DataFrame) -> pd.DataFrame:
    hist = add_boundary_columns(daily)
    hist = hist.loc[pd.to_datetime(hist["Date"]).le(pd.Timestamp("2022-12-31"))].copy()
    hist["ratio"] = hist["COGS"] / hist["Revenue"].replace(0.0, np.nan)
    hist["ratio"] = hist["ratio"].replace([np.inf, -np.inf], np.nan)
    # Daily COGS/Revenue has genuine tails; clip only pathological days so the
    # allocator does not inject extreme ratios into future rows.
    lo, hi = hist["ratio"].quantile([0.02, 0.98])
    hist["ratio"] = hist["ratio"].clip(float(lo), float(hi))
    return hist


def lookup_prior(history: pd.DataFrame, future: pd.DataFrame, keys: list[str]) -> pd.Series:
    rows = []
    for key_values, group in history.groupby(keys, sort=False):
        if not isinstance(key_values, tuple):
            key_values = (key_values,)
        row = dict(zip(keys, key_values))
        row["ratio_prior"] = weighted_mean(group["ratio"], group["year"])
        rows.append(row)
    lookup = pd.DataFrame(rows)
    out = future[keys].copy().merge(lookup, on=keys, how="left")
    return out["ratio_prior"]


def daily_ratio_prior(daily: pd.DataFrame, dates: pd.Series, mode: str) -> pd.Series:
    hist = ratio_history(daily)
    future = add_boundary_columns(pd.DataFrame({"Date": pd.to_datetime(dates)}))
    global_ratio = float(hist["ratio"].median())

    md = lookup_prior(hist, future, ["month", "day"])
    dow = lookup_prior(hist, future, ["month", "dow"])
    boundary = lookup_prior(hist, future, ["month", "week_of_month", "dow"])
    month = lookup_prior(hist, future, ["month"])

    md = md.fillna(month).fillna(global_ratio)
    dow = dow.fillna(month).fillna(global_ratio)
    boundary = boundary.fillna(dow).fillna(month).fillna(global_ratio)
    month = month.fillna(global_ratio)

    if mode == "mddow":
        ratio = 0.70 * md + 0.30 * dow
    elif mode == "boundary":
        ratio = 0.55 * md + 0.25 * dow + 0.20 * boundary
    elif mode == "smooth":
        ratio = 0.45 * md + 0.25 * dow + 0.30 * month
    else:
        raise ValueError(f"Unknown ratio prior mode: {mode}")

    return pd.Series(np.asarray(ratio, dtype=float), index=dates.index).clip(0.70, 1.18)


def apply_revenue_allocator(base: pd.DataFrame, daily: pd.DataFrame, revenue_alpha: float) -> pd.DataFrame:
    if revenue_alpha <= 0:
        return base.copy()
    out = base.copy()
    spec = AllocatorSpec(
        name="v15_revenue_allocator",
        base_kind="v10",
        prior_kind="mddow_recent",
        alpha=revenue_alpha,
        scope="all_full_months",
        targets=("Revenue",),
        note="Revenue month-day/DOW allocator used before ratio-first COGS.",
    )
    # Import lazily to avoid exposing this helper as part of V13 API.
    from run_clean_v13_daily_peak_allocator import apply_daily_allocator

    return apply_daily_allocator(out, daily, spec)


def apply_ratio_first_cogs(base: pd.DataFrame, daily: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    out = add_daily_calendar(apply_revenue_allocator(base, daily, spec.revenue_alpha))
    base = add_daily_calendar(base)
    ratio_prior = daily_ratio_prior(daily, out["Date"], spec.ratio_prior)

    for _, idx in out.groupby(["year", "month"], sort=False).groups.items():
        idx = pd.Index(idx)
        monthly_cogs_total = float(base.loc[idx, "COGS"].sum())
        if monthly_cogs_total <= 0:
            continue
        base_cogs = out.loc[idx, "COGS"].to_numpy(dtype=float)
        ratio_cogs = out.loc[idx, "Revenue"].to_numpy(dtype=float) * ratio_prior.loc[idx].to_numpy(dtype=float)
        if ratio_cogs.sum() > 0:
            ratio_cogs *= monthly_cogs_total / ratio_cogs.sum()
        blended = (1.0 - spec.ratio_alpha) * base_cogs + spec.ratio_alpha * ratio_cogs
        blended = np.clip(blended, 0.0, None)
        if blended.sum() > 0:
            blended *= monthly_cogs_total / blended.sum()
        out.loc[idx, "COGS"] = blended
    return out[["Date", "Revenue", "COGS"]]


def build_specs() -> list[CandidateSpec]:
    specs = []
    for ratio_prior in ["mddow", "boundary", "smooth"]:
        for revenue_alpha, ratio_alpha in [
            (0.30, 0.20),
            (0.30, 0.35),
            (0.30, 0.50),
            (0.25, 0.35),
            (0.35, 0.35),
            (0.50, 0.50),
        ]:
            specs.append(
                CandidateSpec(
                    name=(
                        f"cleanv15_v10_ratiofirst_{ratio_prior}_"
                        f"r{int(revenue_alpha * 1000):03d}_q{int(ratio_alpha * 1000):03d}"
                    ),
                    revenue_alpha=revenue_alpha,
                    ratio_alpha=ratio_alpha,
                    ratio_prior=ratio_prior,
                    note="V10 base; Revenue uses mddow allocator; COGS is generated from train-derived daily COGS/Revenue ratio prior and rescaled to preserve monthly COGS.",
                )
            )
    return specs


def summarize(frame: pd.DataFrame, base: pd.DataFrame, spec: CandidateSpec, filename: str) -> dict[str, object]:
    delta = frame[["Revenue", "COGS"]] - base[["Revenue", "COGS"]]
    ratio = frame["COGS"] / frame["Revenue"].replace(0.0, np.nan)
    return {
        "filename": filename,
        "revenue_alpha": spec.revenue_alpha,
        "ratio_alpha": spec.ratio_alpha,
        "ratio_prior": spec.ratio_prior,
        "note": spec.note,
        "revenue_total": float(frame["Revenue"].sum()),
        "cogs_total": float(frame["COGS"].sum()),
        "delta_revenue_total": float(frame["Revenue"].sum() - base["Revenue"].sum()),
        "delta_cogs_total": float(frame["COGS"].sum() - base["COGS"].sum()),
        "mean_abs_revenue_delta": float(delta["Revenue"].abs().mean()),
        "mean_abs_cogs_delta": float(delta["COGS"].abs().mean()),
        "max_abs_revenue_delta": float(delta["Revenue"].abs().max()),
        "max_abs_cogs_delta": float(delta["COGS"].abs().max()),
        "ratio_mean": float(ratio.mean()),
        "ratio_p95": float(ratio.quantile(0.95)),
        "ratio_max": float(ratio.max()),
    }


def month_total_audit(frame: pd.DataFrame, base: pd.DataFrame, filename: str) -> pd.DataFrame:
    work = add_daily_calendar(frame)
    base_work = add_daily_calendar(base)
    rows = []
    for (year, month), group in work.groupby(["year", "month"], sort=False):
        base_group = base_work.loc[base_work["year"].eq(year) & base_work["month"].eq(month)]
        rows.append(
            {
                "filename": filename,
                "year": year,
                "month": month,
                "revenue_delta": float(group["Revenue"].sum() - base_group["Revenue"].sum()),
                "cogs_delta": float(group["COGS"].sum() - base_group["COGS"].sum()),
                "ratio_mean": float((group["COGS"] / group["Revenue"].replace(0.0, np.nan)).mean()),
                "ratio_p95": float((group["COGS"] / group["Revenue"].replace(0.0, np.nan)).quantile(0.95)),
            }
        )
    return pd.DataFrame(rows)


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Clean V15 Ratio-First COGS Allocator

Run directory: `{run_dir}`

## Boundary

This is **clean-input public-guided research**. It rebuilds V10 base from raw train inputs and does not read `sample_submission.csv`, previous submission files, quarantine files, or test targets.

## Hypothesis

V14 improved R2 by sharpening daily target shape, but COGS-specific alpha worsened public MAE. The issue may be COGS/Revenue ratio shape, not independent COGS daily allocation.

V15 therefore:

1. Keeps V10 monthly/period levels.
2. Applies train-derived month-day/day-of-week allocation to Revenue.
3. Builds daily COGS from a train-derived `COGS / Revenue` ratio prior.
4. Rescales COGS inside every month to preserve the monthly COGS total.

## Candidate Manifest

{manifest.to_markdown(index=False)}
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v15_ratio_first_cogs_allocator_2026-04-29.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    daily = build_daily_panel()
    sales = load_sales()
    bases = build_base_frames(run_dir, daily, sales)
    base = bases["v10"].reset_index(drop=True)

    rows = []
    audits = []
    for priority, spec in enumerate(build_specs(), start=1):
        frame = apply_ratio_first_cogs(base, daily, spec)
        sanity_check(frame, spec.name)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame, path)
        rows.append({"priority": priority, **summarize(frame, base, spec, path.name)})
        audits.append(month_total_audit(frame, base, path.name))

    manifest = pd.DataFrame(rows)
    month_audit = pd.concat(audits, ignore_index=True)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    month_audit.to_csv(run_dir / "month_total_audit.csv", index=False)
    write_report(run_dir, manifest)
    print(run_dir)
    print(
        manifest[
            [
                "priority",
                "filename",
                "revenue_alpha",
                "ratio_alpha",
                "ratio_prior",
                "mean_abs_revenue_delta",
                "mean_abs_cogs_delta",
                "ratio_p95",
                "delta_revenue_total",
                "delta_cogs_total",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
