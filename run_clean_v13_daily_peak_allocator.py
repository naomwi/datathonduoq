from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_clean_v2_train_evidence import build_daily_panel
from run_clean_regime_recovery_scenarios import load_sales
from run_clean_v10_h1_regime_shape import (
    CandidateSpec as V10Spec,
    add_period_columns,
    apply_h1_regime_shape,
    build_current_clean_frame,
    h1_train_priors,
    sanity_check,
)
from run_clean_v12_monthly_funnel_router import (
    CandidateSpec as V12Spec,
    apply_monthly_router,
    build_monthly_table,
)
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v13_daily_peak_allocator"
FORECAST_START = pd.Timestamp("2023-01-01")
FORECAST_END = pd.Timestamp("2024-07-01")
FULL_FORECAST_END = pd.Timestamp("2024-06-30")
TARGETS = ("Revenue", "COGS")


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    base_kind: str
    prior_kind: str
    alpha: float
    scope: str
    targets: tuple[str, ...]
    note: str


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def add_daily_calendar(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out["year"] = out["Date"].dt.year
    out["month"] = out["Date"].dt.month
    out["day"] = out["Date"].dt.day
    out["dow"] = out["Date"].dt.dayofweek
    out["days_in_month"] = out["Date"].dt.days_in_month
    out["is_month_start"] = out["Date"].dt.is_month_start.astype(int)
    out["is_month_end"] = out["Date"].dt.is_month_end.astype(int)
    return out


def weighted_mean(values: pd.Series, years: pd.Series, decay: float = 3.0) -> float:
    clean = pd.DataFrame({"value": values, "year": years}).replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return np.nan
    weights = np.exp((clean["year"].to_numpy(dtype=float) - clean["year"].max()) / decay)
    return float(np.average(clean["value"].to_numpy(dtype=float), weights=weights))


def weighted_lookup(frame: pd.DataFrame, keys: list[str], value_col: str) -> pd.DataFrame:
    rows = []
    for key_values, group in frame.groupby(keys, sort=False):
        if not isinstance(key_values, tuple):
            key_values = (key_values,)
        row = dict(zip(keys, key_values))
        row[value_col] = weighted_mean(group[value_col], group["year"])
        rows.append(row)
    return pd.DataFrame(rows)


def target_share_history(daily: pd.DataFrame, target: str, years: list[int] | None = None) -> pd.DataFrame:
    hist = add_daily_calendar(daily)
    hist = hist.loc[hist["Date"].le(pd.Timestamp("2022-12-31"))].copy()
    if years is not None:
        hist = hist.loc[hist["year"].isin(years)].copy()
    hist = hist.loc[hist[target].notna()].copy()
    month_total = hist.groupby(["year", "month"])[target].transform("sum")
    hist["target_share"] = hist[target] / month_total.replace(0.0, np.nan)
    hist["target_rel"] = hist["target_share"] * hist["days_in_month"]
    hist["target_rel"] = hist["target_rel"].replace([np.inf, -np.inf], np.nan).clip(0.10, 6.00)
    return hist


def rel_from_lookups(history: pd.DataFrame, future: pd.DataFrame) -> pd.Series:
    md = weighted_lookup(history, ["month", "day"], "target_rel").rename(columns={"target_rel": "md_rel"})
    dow = weighted_lookup(history, ["month", "dow"], "target_rel").rename(columns={"target_rel": "dow_rel"})
    month = weighted_lookup(history, ["month"], "target_rel").rename(columns={"target_rel": "month_rel"})

    out = future[["month", "day", "dow"]].copy()
    out = out.merge(md, on=["month", "day"], how="left")
    out = out.merge(dow, on=["month", "dow"], how="left")
    out = out.merge(month, on=["month"], how="left")
    out["month_rel"] = out["month_rel"].fillna(1.0)
    out["md_rel"] = out["md_rel"].fillna(out["month_rel"])
    out["dow_rel"] = out["dow_rel"].fillna(out["month_rel"])
    return (0.72 * out["md_rel"] + 0.28 * out["dow_rel"]).clip(0.20, 5.00)


def add_relative_operational_columns(history: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = history.copy()
    for col in columns:
        if col not in out.columns:
            out[f"{col}_rel"] = 1.0
            continue
        values = out[col].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(lower=0.0)
        totals = values.groupby([out["year"], out["month"]]).transform("sum")
        rel = values / totals.replace(0.0, np.nan) * out["days_in_month"]
        out[f"{col}_rel"] = rel.replace([np.inf, -np.inf], np.nan).fillna(1.0).clip(0.10, 8.00)
    return out


def operational_score(history: pd.DataFrame, future: pd.DataFrame, target: str) -> pd.Series:
    if target == "Revenue":
        weights = {
            "orders": 0.30,
            "sessions": 0.20,
            "gross_item_value": 0.25,
            "payment_value": 0.15,
            "promo_lines": 0.10,
        }
    else:
        weights = {
            "units": 0.22,
            "product_cogs_value": 0.34,
            "gross_item_value": 0.20,
            "orders": 0.14,
            "promo_lines": 0.10,
        }
    cols = list(weights)
    hist = add_relative_operational_columns(history, cols)
    result = pd.Series(0.0, index=future.index, dtype=float)
    for col, weight in weights.items():
        rel_col = f"{col}_rel"
        md = weighted_lookup(hist, ["month", "day"], rel_col).rename(columns={rel_col: "md_rel"})
        dow = weighted_lookup(hist, ["month", "dow"], rel_col).rename(columns={rel_col: "dow_rel"})
        month = weighted_lookup(hist, ["month"], rel_col).rename(columns={rel_col: "month_rel"})
        look = future[["month", "day", "dow"]].copy()
        look = look.merge(md, on=["month", "day"], how="left")
        look = look.merge(dow, on=["month", "dow"], how="left")
        look = look.merge(month, on=["month"], how="left")
        look["month_rel"] = look["month_rel"].fillna(1.0)
        look["md_rel"] = look["md_rel"].fillna(look["month_rel"])
        look["dow_rel"] = look["dow_rel"].fillna(look["month_rel"])
        result += weight * (0.65 * look["md_rel"] + 0.35 * look["dow_rel"]).to_numpy(dtype=float)
    return result.clip(0.20, 5.00)


def prior_scores(daily: pd.DataFrame, future: pd.DataFrame, target: str, prior_kind: str) -> pd.Series:
    future = add_daily_calendar(future)
    if prior_kind == "stable_h1_mddow":
        stable = target_share_history(daily, target, years=[2014, 2016, 2017])
        recent = target_share_history(daily, target)
        stable_rel = rel_from_lookups(stable, future)
        recent_rel = rel_from_lookups(recent, future)
        return pd.Series(
            np.where(
                future["month"].le(6).to_numpy(dtype=bool),
                np.asarray(stable_rel, dtype=float),
                np.asarray(recent_rel, dtype=float),
            ),
            index=future.index,
        )

    history = target_share_history(daily, target)
    md_dow = rel_from_lookups(history, future)
    if prior_kind == "mddow_recent":
        return pd.Series(np.asarray(md_dow, dtype=float), index=future.index)
    if prior_kind == "ops_peak":
        ops = operational_score(history, future, target)
        return pd.Series(
            (0.58 * np.asarray(md_dow, dtype=float) + 0.42 * np.asarray(ops, dtype=float)).clip(0.20, 5.00),
            index=future.index,
        )
    raise ValueError(f"Unknown prior kind: {prior_kind}")


def normalized_profile(daily: pd.DataFrame, dates: pd.Series, target: str, prior_kind: str) -> pd.Series:
    future = add_daily_calendar(pd.DataFrame({"Date": pd.to_datetime(dates)}))
    # prior_scores uses merge operations internally, so bind by position rather
    # than by pandas index to keep rolling validation folds from reindexing to NaN.
    scores = pd.Series(np.asarray(prior_scores(daily, future, target, prior_kind), dtype=float), index=future.index)
    scores = scores.replace([np.inf, -np.inf], np.nan).fillna(1.0).clip(0.20, 5.00)
    shares = pd.Series(index=future.index, dtype=float)
    for _, idx in future.groupby(["year", "month"], sort=False).groups.items():
        total = float(scores.loc[idx].sum())
        if total <= 0:
            shares.loc[idx] = 1.0 / len(idx)
        else:
            shares.loc[idx] = scores.loc[idx] / total
    shares.index = dates.index
    return shares


def scope_mask(frame: pd.DataFrame, scope: str) -> pd.Series:
    work = add_period_columns(frame)
    if scope == "2023H1":
        return work["period"].eq("2023H1")
    if scope == "h1_all":
        return work["month"].le(6) & work["Date"].le(FULL_FORECAST_END)
    if scope == "all_full_months":
        return work["Date"].le(FULL_FORECAST_END)
    raise ValueError(f"Unknown scope: {scope}")


def apply_daily_allocator(base_frame: pd.DataFrame, daily: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    out = add_daily_calendar(base_frame[["Date", "Revenue", "COGS"]])
    mask = scope_mask(out, spec.scope)
    for target in spec.targets:
        profile = normalized_profile(daily, out["Date"], target, spec.prior_kind)
        for _, idx in out.loc[mask].groupby(["year", "month"], sort=False).groups.items():
            idx = pd.Index(idx)
            total = float(out.loc[idx, target].sum())
            if total <= 0:
                continue
            base_share = out.loc[idx, target].to_numpy(dtype=float) / total
            prior_share = profile.loc[idx].to_numpy(dtype=float)
            prior_share = prior_share / max(float(prior_share.sum()), 1e-12)
            blended = (1.0 - spec.alpha) * base_share + spec.alpha * prior_share
            blended = np.clip(blended, 1e-9, None)
            blended = blended / blended.sum()
            out.loc[idx, target] = total * blended
    return out[["Date", "Revenue", "COGS"]]


def build_base_frames(run_dir: Path, daily: pd.DataFrame, sales: pd.DataFrame) -> dict[str, pd.DataFrame]:
    root = build_current_clean_frame(run_dir)
    monthly = build_monthly_table(daily)
    revenue_share, cogs_ratio = h1_train_priors(sales)

    v10 = apply_h1_regime_shape(
        root,
        revenue_share,
        cogs_ratio,
        V10Spec(
            name="cleanv10_h1_shape141617_ratio1719_a075",
            alpha=0.75,
            use_revenue_shape=True,
            note="Current best MAE base rebuilt from raw clean inputs.",
        ),
    )
    v12_month = apply_monthly_router(
        root,
        monthly,
        sales,
        V12Spec(
            name="cleanv12_monthfunnel_h1_ratio_discount_a050",
            alpha=0.50,
            revenue_profile="ops",
            ratio_profile="ops",
            preserve_h1_cogs_total=False,
            note="Balanced RMSE/R2 base rebuilt from raw clean inputs.",
        ),
    )
    v12_hybrid = apply_monthly_router(
        root,
        monthly,
        sales,
        V12Spec(
            name="cleanv12_v10ops_h1_ratio_discount_a075",
            alpha=0.75,
            revenue_profile="v10_ops",
            ratio_profile="ops",
            preserve_h1_cogs_total=False,
            note="MAE/RMSE compromise base rebuilt from raw clean inputs.",
        ),
    )
    return {
        "source_v7": root[["Date", "Revenue", "COGS"]],
        "v10": v10,
        "v12_month": v12_month,
        "v12_hybrid": v12_hybrid,
    }


def validation_rows(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for target in TARGETS:
        for prior_kind in ["mddow_recent", "ops_peak", "stable_h1_mddow"]:
            for scope in ["h1_all", "all_full_months"]:
                actuals = []
                preds = []
                for year in range(2018, 2023):
                    history = daily.loc[pd.to_datetime(daily["Date"]).dt.year < year].copy()
                    fold = add_daily_calendar(daily.loc[pd.to_datetime(daily["Date"]).dt.year.eq(year)].copy())
                    fold = fold.loc[fold["month"].le(6) if scope == "h1_all" else pd.Series(True, index=fold.index)]
                    if fold.empty:
                        continue
                    profile = normalized_profile(history, fold["Date"], target, prior_kind)
                    for _, idx in fold.groupby(["year", "month"], sort=False).groups.items():
                        idx = pd.Index(idx)
                        month_total = float(fold.loc[idx, target].sum())
                        pred = month_total * profile.loc[idx].to_numpy(dtype=float)
                        actuals.extend(fold.loc[idx, target].to_numpy(dtype=float))
                        preds.extend(pred)
                y = np.asarray(actuals, dtype=float)
                p = np.asarray(preds, dtype=float)
                if len(y) == 0:
                    continue
                sst = float(np.sum((y - y.mean()) ** 2))
                sse = float(np.sum((y - p) ** 2))
                rows.append(
                    {
                        "target": target,
                        "prior_kind": prior_kind,
                        "scope": scope,
                        "rows": len(y),
                        "mae": float(np.mean(np.abs(y - p))),
                        "rmse": float(np.sqrt(np.mean((y - p) ** 2))),
                        "r2": 1.0 - sse / sst if sst > 0 else np.nan,
                    }
                )
    return pd.DataFrame(rows).sort_values(["target", "scope", "rmse", "mae"])


def build_specs() -> list[CandidateSpec]:
    return [
        CandidateSpec(
            name="cleanv13_v12month_h1_opspeak_a020",
            base_kind="v12_month",
            prior_kind="ops_peak",
            alpha=0.20,
            scope="h1_all",
            targets=("Revenue", "COGS"),
            note="Balanced-base daily allocator; preserve each month total; shape both targets toward train operational peak prior.",
        ),
        CandidateSpec(
            name="cleanv13_v12month_h1_opspeak_a035",
            base_kind="v12_month",
            prior_kind="ops_peak",
            alpha=0.35,
            scope="h1_all",
            targets=("Revenue", "COGS"),
            note="Stronger balanced-base daily peak allocation for RMSE/R2.",
        ),
        CandidateSpec(
            name="cleanv13_v12month_h1_mddow_a020",
            base_kind="v12_month",
            prior_kind="mddow_recent",
            alpha=0.20,
            scope="h1_all",
            targets=("Revenue", "COGS"),
            note="Calendar-only daily shape, conservative alpha.",
        ),
        CandidateSpec(
            name="cleanv13_v12month_h1_mddow_a030",
            base_kind="v12_month",
            prior_kind="mddow_recent",
            alpha=0.30,
            scope="h1_all",
            targets=("Revenue", "COGS"),
            note="Calendar-only daily shape; no operational prior.",
        ),
        CandidateSpec(
            name="cleanv13_v12month_h1_mddow_a040",
            base_kind="v12_month",
            prior_kind="mddow_recent",
            alpha=0.40,
            scope="h1_all",
            targets=("Revenue", "COGS"),
            note="Calendar-only daily shape, stronger alpha for RMSE/R2.",
        ),
        CandidateSpec(
            name="cleanv13_v10_h1_mddow_a010",
            base_kind="v10",
            prior_kind="mddow_recent",
            alpha=0.10,
            scope="h1_all",
            targets=("Revenue", "COGS"),
            note="Current best MAE base with very small H1 calendar allocator.",
        ),
        CandidateSpec(
            name="cleanv13_v10_h1_mddow_a020",
            base_kind="v10",
            prior_kind="mddow_recent",
            alpha=0.20,
            scope="h1_all",
            targets=("Revenue", "COGS"),
            note="Current best MAE base with conservative H1 calendar allocator.",
        ),
        CandidateSpec(
            name="cleanv13_v10_all_mddow_a005",
            base_kind="v10",
            prior_kind="mddow_recent",
            alpha=0.05,
            scope="all_full_months",
            targets=("Revenue", "COGS"),
            note="Current best MAE base with tiny all-month calendar allocator.",
        ),
        CandidateSpec(
            name="cleanv13_v10_all_mddow_a010",
            base_kind="v10",
            prior_kind="mddow_recent",
            alpha=0.10,
            scope="all_full_months",
            targets=("Revenue", "COGS"),
            note="Current best MAE base with small all-month calendar allocator.",
        ),
        CandidateSpec(
            name="cleanv13_v10_all_mddow_a015",
            base_kind="v10",
            prior_kind="mddow_recent",
            alpha=0.15,
            scope="all_full_months",
            targets=("Revenue", "COGS"),
            note="Current best MAE base with V12-confirmed all-month calendar allocator strength.",
        ),
        CandidateSpec(
            name="cleanv13_v10_h1_opspeak_a020",
            base_kind="v10",
            prior_kind="ops_peak",
            alpha=0.20,
            scope="h1_all",
            targets=("Revenue", "COGS"),
            note="Current best MAE base with conservative daily peak allocator.",
        ),
        CandidateSpec(
            name="cleanv13_v10_h1_opspeak_a035",
            base_kind="v10",
            prior_kind="ops_peak",
            alpha=0.35,
            scope="h1_all",
            targets=("Revenue", "COGS"),
            note="Current best MAE base with stronger daily peak allocator.",
        ),
        CandidateSpec(
            name="cleanv13_v10_h1_cogs_opspeak_a035",
            base_kind="v10",
            prior_kind="ops_peak",
            alpha=0.35,
            scope="h1_all",
            targets=("COGS",),
            note="COGS-only allocator to improve squared COGS errors while keeping Revenue exact.",
        ),
        CandidateSpec(
            name="cleanv13_v12hybrid_h1_opspeak_a025",
            base_kind="v12_hybrid",
            prior_kind="ops_peak",
            alpha=0.25,
            scope="h1_all",
            targets=("Revenue", "COGS"),
            note="Hybrid base with moderate daily peak allocation.",
        ),
        CandidateSpec(
            name="cleanv13_v12month_all_opspeak_a015",
            base_kind="v12_month",
            prior_kind="ops_peak",
            alpha=0.15,
            scope="all_full_months",
            targets=("Revenue", "COGS"),
            note="Small all-month allocator for equal-metric hedge; preserves every month total.",
        ),
        CandidateSpec(
            name="cleanv13_v12month_all_mddow_a015",
            base_kind="v12_month",
            prior_kind="mddow_recent",
            alpha=0.15,
            scope="all_full_months",
            targets=("Revenue", "COGS"),
            note="Small all-month calendar allocator for equal-metric hedge; preserves every month total.",
        ),
    ]


def summarize(frame: pd.DataFrame, base: pd.DataFrame, spec: CandidateSpec, filename: str) -> dict[str, object]:
    work = add_period_columns(frame)
    base_work = add_period_columns(base)
    delta = frame[["Revenue", "COGS"]] - base[["Revenue", "COGS"]]
    rows = {
        "filename": filename,
        "base_kind": spec.base_kind,
        "prior_kind": spec.prior_kind,
        "alpha": spec.alpha,
        "scope": spec.scope,
        "targets": ",".join(spec.targets),
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
    for period in ["2023H1", "2023H2", "2024H1"]:
        mask = work["period"].eq(period)
        base_mask = base_work["period"].eq(period)
        rows[f"{period}_revenue_delta_total"] = float(work.loc[mask, "Revenue"].sum() - base_work.loc[base_mask, "Revenue"].sum())
        rows[f"{period}_cogs_delta_total"] = float(work.loc[mask, "COGS"].sum() - base_work.loc[base_mask, "COGS"].sum())
    return rows


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
                "revenue_total": group["Revenue"].sum(),
                "base_revenue_total": base_group["Revenue"].sum(),
                "cogs_total": group["COGS"].sum(),
                "base_cogs_total": base_group["COGS"].sum(),
                "revenue_total_delta": group["Revenue"].sum() - base_group["Revenue"].sum(),
                "cogs_total_delta": group["COGS"].sum() - base_group["COGS"].sum(),
                "max_revenue": group["Revenue"].max(),
                "max_cogs": group["COGS"].max(),
            }
        )
    return pd.DataFrame(rows)


def write_report(run_dir: Path, manifest: pd.DataFrame, validation: pd.DataFrame) -> None:
    report = f"""# Clean V13 Daily Peak Allocator

Run directory: `{run_dir}`

## Boundary

This is **clean-input / public-guided model selection**. The script rebuilds base forecasts from raw train inputs and does not read `sample_submission.csv`, previous submissions, quarantine files, or test target values as inputs.

The post-model layer is a deterministic daily allocation model. It preserves every affected month total for every affected target, so it does not tune target level from leaderboard feedback. It only reallocates within-month daily shape using train-derived calendar and operational recurrence priors.

## Hypothesis

If final scoring weights MAE, RMSE, and R2 equally, then daily peak placement matters more than MAE-only leaderboard tuning. RMSE and R2 both punish squared peak errors, so the clean route is to keep proven monthly/period totals and improve daily allocation.

## Rolling Shape Validation

{validation.to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Read

1. For balanced equal-metric risk: `submission_cleanv13_v12month_h1_mddow_a030.csv`.
2. If it improves and RMSE/R2 proxy is trusted: `submission_cleanv13_v12month_h1_mddow_a040.csv`.
3. If public MAE must be protected: `submission_cleanv13_v12month_h1_mddow_a020.csv`.
4. If H1-only shape helps but looks under-scoped: `submission_cleanv13_v12month_all_mddow_a015.csv`.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v13_daily_peak_allocator_2026-04-29.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    sales = load_sales()
    daily = build_daily_panel()
    bases = build_base_frames(run_dir, daily, sales)
    validation = validation_rows(daily)

    rows = []
    audit_frames = []
    for priority, spec in enumerate(build_specs(), start=1):
        base = bases[spec.base_kind].reset_index(drop=True)
        frame = apply_daily_allocator(base, daily, spec)
        sanity_check(frame, spec.name)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame, path)
        rows.append({"priority": priority, **summarize(frame, base, spec, path.name)})
        audit_frames.append(month_total_audit(frame, base, path.name))

    manifest = pd.DataFrame(rows)
    month_audit = pd.concat(audit_frames, ignore_index=True)
    validation.to_csv(run_dir / "shape_validation.csv", index=False)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    month_audit.to_csv(run_dir / "month_total_audit.csv", index=False)
    write_report(run_dir, manifest, validation)

    print(run_dir)
    print(
        manifest[
            [
                "priority",
                "filename",
                "base_kind",
                "prior_kind",
                "alpha",
                "scope",
                "targets",
                "mean_abs_revenue_delta",
                "mean_abs_cogs_delta",
                "delta_revenue_total",
                "delta_cogs_total",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
