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
    add_daily_calendar,
    build_base_frames,
    normalized_profile,
    weighted_mean,
)
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v16_foldlearned_daily_allocator"
TARGETS = ("Revenue", "COGS")


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    correction_alpha: float
    base_alpha: float
    target_mode: str
    use_boundary: bool
    note: str


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def add_boundary_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = add_daily_calendar(frame)
    out["days_to_month_end"] = out["days_in_month"] - out["day"]
    out["week_of_month"] = ((out["day"] - 1) // 7 + 1).astype(int)
    out["boundary_bucket"] = np.select(
        [
            out["day"].le(3),
            out["days_to_month_end"].le(2),
            out["day"].between(4, 10),
            out["days_to_month_end"].between(3, 9),
        ],
        ["start3", "end3", "early", "late"],
        default="middle",
    )
    return out


def monthly_relative_target(daily: pd.DataFrame, target: str) -> pd.DataFrame:
    hist = add_boundary_features(daily)
    total = hist.groupby(["year", "month"])[target].transform("sum")
    hist["target_share"] = hist[target] / total.replace(0.0, np.nan)
    hist["actual_rel"] = hist["target_share"] * hist["days_in_month"]
    hist["actual_rel"] = hist["actual_rel"].replace([np.inf, -np.inf], np.nan).clip(0.05, 8.00)
    return hist.loc[hist["actual_rel"].notna()].copy()


def correction_training_table(daily: pd.DataFrame, target: str, use_boundary: bool) -> pd.DataFrame:
    hist = monthly_relative_target(daily, target)
    rows = []
    for year in range(2017, 2023):
        train = hist.loc[hist["year"].lt(year)].copy()
        valid = hist.loc[hist["year"].eq(year)].copy()
        if train.empty or valid.empty:
            continue
        base_profile = normalized_profile(train, valid["Date"], target, "mddow_recent")
        valid["base_rel"] = base_profile.to_numpy(dtype=float) * valid["days_in_month"].to_numpy(dtype=float)
        valid["correction"] = (valid["actual_rel"] / valid["base_rel"].replace(0.0, np.nan)).replace(
            [np.inf, -np.inf], np.nan
        )
        valid["fold_year"] = year
        rows.append(valid)
    table = pd.concat(rows, ignore_index=True)
    table["correction"] = table["correction"].clip(0.25, 4.00)
    keys = ["month", "day", "dow"]
    if use_boundary:
        keys += ["boundary_bucket"]
    return table[["Date", "year", "fold_year", "correction", *keys]].copy()


def correction_lookup(table: pd.DataFrame, future: pd.DataFrame, use_boundary: bool) -> pd.Series:
    keys = ["month", "day", "dow"]
    if use_boundary:
        keys += ["boundary_bucket"]

    rows = []
    for key_values, group in table.groupby(keys, sort=False):
        if not isinstance(key_values, tuple):
            key_values = (key_values,)
        row = dict(zip(keys, key_values))
        row["correction"] = weighted_mean(group["correction"], group["fold_year"], decay=2.0)
        rows.append(row)
    lookup = pd.DataFrame(rows)
    out = future[keys].copy().merge(lookup, on=keys, how="left")

    fallback_keys = ["month", "dow"]
    fallback_rows = []
    for key_values, group in table.groupby(fallback_keys, sort=False):
        if not isinstance(key_values, tuple):
            key_values = (key_values,)
        row = dict(zip(fallback_keys, key_values))
        row["fallback"] = weighted_mean(group["correction"], group["fold_year"], decay=2.0)
        fallback_rows.append(row)
    fallback = pd.DataFrame(fallback_rows)
    out = out.merge(fallback, on=fallback_keys, how="left")
    out["correction"] = out["correction"].fillna(out["fallback"]).fillna(1.0)
    return pd.Series(out["correction"].to_numpy(dtype=float), index=future.index).clip(0.35, 3.00)


def learned_profile(
    daily: pd.DataFrame,
    dates: pd.Series,
    target: str,
    correction_alpha: float,
    use_boundary: bool,
) -> pd.Series:
    future = add_boundary_features(pd.DataFrame({"Date": pd.to_datetime(dates)}))
    base_share = normalized_profile(daily, dates, target, "mddow_recent")
    table = correction_training_table(daily, target, use_boundary=use_boundary)
    corr = correction_lookup(table, future, use_boundary=use_boundary)
    score = base_share.to_numpy(dtype=float) * future["days_in_month"].to_numpy(dtype=float)
    score = score * ((1.0 - correction_alpha) + correction_alpha * corr.to_numpy(dtype=float))
    score = pd.Series(score, index=future.index).replace([np.inf, -np.inf], np.nan).fillna(1.0).clip(0.05, 8.00)

    shares = pd.Series(index=future.index, dtype=float)
    for _, idx in future.groupby(["year", "month"], sort=False).groups.items():
        total = float(score.loc[idx].sum())
        shares.loc[idx] = 1.0 / len(idx) if total <= 0 else score.loc[idx] / total
    shares.index = dates.index
    return shares


def apply_v16(base: pd.DataFrame, daily: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    out = add_boundary_features(base[["Date", "Revenue", "COGS"]])
    target_list = TARGETS if spec.target_mode == "both" else (spec.target_mode,)
    for target in target_list:
        learned = learned_profile(daily, out["Date"], target, spec.correction_alpha, spec.use_boundary)
        base_prior = normalized_profile(daily, out["Date"], target, "mddow_recent")
        target_profile = (1.0 - spec.base_alpha) * base_prior + spec.base_alpha * learned
        for _, idx in out.loc[out["Date"].le(pd.Timestamp("2024-06-30"))].groupby(["year", "month"], sort=False).groups.items():
            idx = pd.Index(idx)
            total = float(out.loc[idx, target].sum())
            if total <= 0:
                continue
            base_share = out.loc[idx, target].to_numpy(dtype=float) / total
            prior_share = target_profile.loc[idx].to_numpy(dtype=float)
            prior_share = prior_share / max(float(prior_share.sum()), 1e-12)
            blended = (1.0 - spec.base_alpha) * base_share + spec.base_alpha * prior_share
            blended = np.clip(blended, 1e-9, None)
            blended = blended / blended.sum()
            out.loc[idx, target] = total * blended
    return out[["Date", "Revenue", "COGS"]]


def validation_table(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for target in TARGETS:
        hist = monthly_relative_target(daily, target)
        for use_boundary in [False, True]:
            for correction_alpha in [0.25, 0.50, 0.75, 1.00]:
                actuals = []
                preds = []
                for year in range(2018, 2023):
                    train = hist.loc[hist["year"].lt(year)].copy()
                    valid = hist.loc[hist["year"].eq(year)].copy()
                    if train.empty or valid.empty:
                        continue
                    base = normalized_profile(train, valid["Date"], target, "mddow_recent")
                    table = correction_training_table(train, target, use_boundary=use_boundary)
                    corr = correction_lookup(table, add_boundary_features(valid[["Date"]]), use_boundary=use_boundary)
                    score = base.to_numpy(dtype=float) * valid["days_in_month"].to_numpy(dtype=float)
                    score = score * ((1.0 - correction_alpha) + correction_alpha * corr.to_numpy(dtype=float))
                    pred_share = pd.Series(index=valid.index, dtype=float)
                    for _, idx in valid.groupby(["year", "month"], sort=False).groups.items():
                        idx = pd.Index(idx)
                        local = pd.Series(score, index=valid.index).loc[idx]
                        pred_share.loc[idx] = local / max(float(local.sum()), 1e-12)
                    actual_share = valid["actual_rel"] / valid["days_in_month"]
                    month_total = valid.groupby(["year", "month"])[target].transform("sum")
                    actuals.extend(valid[target].to_numpy(dtype=float))
                    preds.extend((pred_share * month_total).to_numpy(dtype=float))
                y = np.asarray(actuals, dtype=float)
                p = np.asarray(preds, dtype=float)
                sst = float(np.sum((y - y.mean()) ** 2))
                rows.append(
                    {
                        "target": target,
                        "use_boundary": use_boundary,
                        "correction_alpha": correction_alpha,
                        "mae": float(np.mean(np.abs(y - p))),
                        "rmse": float(np.sqrt(np.mean((y - p) ** 2))),
                        "r2": 1.0 - float(np.sum((y - p) ** 2)) / sst if sst > 0 else np.nan,
                    }
                )
    return pd.DataFrame(rows).sort_values(["target", "rmse"])


def build_specs() -> list[CandidateSpec]:
    specs = []
    for use_boundary, label in [(False, "plain"), (True, "boundary")]:
        for correction_alpha in [0.25, 0.50, 0.75, 1.00]:
            for base_alpha in [0.20, 0.30, 0.40]:
                specs.append(
                    CandidateSpec(
                        name=f"cleanv16_v10_{label}_both_c{int(correction_alpha*1000):03d}_a{int(base_alpha*1000):03d}",
                        correction_alpha=correction_alpha,
                        base_alpha=base_alpha,
                        target_mode="both",
                        use_boundary=use_boundary,
                        note="Fold-learned daily share correction over train-only mddow base; preserve monthly totals.",
                    )
                )
        for correction_alpha, base_alpha in [(0.50, 0.40), (0.75, 0.40), (1.00, 0.40)]:
            specs.append(
                CandidateSpec(
                    name=f"cleanv16_v10_{label}_cogs_c{int(correction_alpha*1000):03d}_a{int(base_alpha*1000):03d}",
                    correction_alpha=correction_alpha,
                    base_alpha=base_alpha,
                    target_mode="COGS",
                    use_boundary=use_boundary,
                    note="COGS-only fold-learned daily correction.",
                )
            )
    return specs


def summarize(frame: pd.DataFrame, base: pd.DataFrame, spec: CandidateSpec, filename: str) -> dict[str, object]:
    delta = frame[["Revenue", "COGS"]] - base[["Revenue", "COGS"]]
    return {
        "filename": filename,
        "correction_alpha": spec.correction_alpha,
        "base_alpha": spec.base_alpha,
        "target_mode": spec.target_mode,
        "use_boundary": spec.use_boundary,
        "note": spec.note,
        "revenue_total": float(frame["Revenue"].sum()),
        "cogs_total": float(frame["COGS"].sum()),
        "delta_revenue_total": float(frame["Revenue"].sum() - base["Revenue"].sum()),
        "delta_cogs_total": float(frame["COGS"].sum() - base["COGS"].sum()),
        "mean_abs_revenue_delta": float(delta["Revenue"].abs().mean()),
        "mean_abs_cogs_delta": float(delta["COGS"].abs().mean()),
        "max_abs_revenue_delta": float(delta["Revenue"].abs().max()),
        "max_abs_cogs_delta": float(delta["COGS"].abs().max()),
    }


def write_report(run_dir: Path, manifest: pd.DataFrame, validation: pd.DataFrame) -> None:
    report = f"""# Clean V16 Fold-Learned Daily Allocator

Run directory: `{run_dir}`

## Boundary

This is **clean-input research**. It rebuilds V10 from raw/train inputs and uses train-only rolling folds to learn daily share corrections. It does not read test targets, sample submission, previous submissions, or quarantine files.

## Hypothesis

V14 hand-tuned month-day/day-of-week allocation reached a plateau. V16 learns a correction to the train-derived daily profile from historical rolling folds, including optional month-boundary features, while preserving each month total.

## Validation

{validation.to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v16_foldlearned_daily_allocator_2026-04-29.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    daily = build_daily_panel()
    sales = load_sales()
    base = build_base_frames(run_dir, daily, sales)["v10"].reset_index(drop=True)
    validation = validation_table(daily)

    rows = []
    for priority, spec in enumerate(build_specs(), start=1):
        frame = apply_v16(base, daily, spec)
        sanity_check(frame, spec.name)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame, path)
        rows.append({"priority": priority, **summarize(frame, base, spec, path.name)})

    manifest = pd.DataFrame(rows)
    validation.to_csv(run_dir / "validation.csv", index=False)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    write_report(run_dir, manifest, validation)
    print(run_dir)
    print(
        manifest[
            [
                "priority",
                "filename",
                "correction_alpha",
                "base_alpha",
                "target_mode",
                "use_boundary",
                "mean_abs_revenue_delta",
                "mean_abs_cogs_delta",
                "delta_revenue_total",
                "delta_cogs_total",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
