from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_clean_v2_train_evidence import build_daily_panel
from run_clean_regime_recovery_scenarios import load_sales
from run_clean_v10_h1_regime_shape import (
    add_period_columns,
    build_current_clean_frame,
    h1_train_priors,
    sanity_check,
)
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v12_monthly_funnel_router"
FORECAST_START = pd.Timestamp("2023-01-01")
FORECAST_END = pd.Timestamp("2024-07-01")
H1_MONTHS = tuple(range(1, 7))


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    alpha: float
    revenue_profile: str
    ratio_profile: str
    preserve_h1_cogs_total: bool
    apply_revenue: bool = True
    apply_ratio: bool = True
    note: str = ""


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def weighted_recent(group: pd.DataFrame, col: str, n: int = 4) -> float:
    recent = group.sort_values("year").tail(n)
    values = recent[col].replace([np.inf, -np.inf], np.nan).dropna()
    if values.empty:
        return np.nan
    years = recent.loc[values.index, "year"].to_numpy(dtype=float)
    weights = np.exp((years - years.max()) / 2.0)
    return float(np.average(values.to_numpy(dtype=float), weights=weights))


def safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    return num / den.replace(0.0, np.nan)


def build_monthly_table(daily: pd.DataFrame) -> pd.DataFrame:
    work = daily.copy()
    work["Date"] = pd.to_datetime(work["Date"])
    work["year"] = work["Date"].dt.year
    work["month"] = work["Date"].dt.month
    work["half"] = np.where(work["month"].le(6), "H1", "H2")
    grouped = (
        work.groupby(["year", "month", "half"], as_index=False)
        .agg(
            days=("Date", "count"),
            revenue=("Revenue", "sum"),
            cogs=("COGS", "sum"),
            sessions=("sessions", "sum"),
            orders=("orders", "sum"),
            gross_item_value=("gross_item_value", "sum"),
            discount_amount=("discount_amount", "sum"),
            promo_lines=("promo_lines", "sum"),
            item_lines=("item_lines", "sum"),
            stockout_days=("stockout_days", "sum"),
            fill_rate=("fill_rate", "mean"),
            stockout_flag=("stockout_flag", "mean"),
            active_promo_count=("active_promo_count", "mean"),
            promo_discount_max=("promo_discount_max", "mean"),
        )
        .sort_values(["year", "month"])
    )
    grouped["cogs_ratio"] = safe_ratio(grouped["cogs"], grouped["revenue"])
    grouped["conversion"] = safe_ratio(grouped["orders"], grouped["sessions"])
    grouped["aov"] = safe_ratio(grouped["revenue"], grouped["orders"])
    grouped["discount_rate"] = safe_ratio(grouped["discount_amount"], grouped["gross_item_value"])
    grouped["promo_line_share"] = safe_ratio(grouped["promo_lines"], grouped["item_lines"])
    grouped["stockout_per_day"] = safe_ratio(grouped["stockout_days"], grouped["days"])
    grouped["h1_revenue_total"] = grouped.groupby(["year", "half"])["revenue"].transform("sum")
    grouped["h1_cogs_total"] = grouped.groupby(["year", "half"])["cogs"].transform("sum")
    grouped["revenue_share"] = safe_ratio(grouped["revenue"], grouped["h1_revenue_total"])
    grouped["cogs_share"] = safe_ratio(grouped["cogs"], grouped["h1_cogs_total"])
    return grouped


def continuous_feature_columns() -> list[str]:
    return [
        "discount_rate",
        "promo_line_share",
        "active_promo_count",
        "promo_discount_max",
        "stockout_per_day",
        "fill_rate",
        "stockout_flag",
    ]


def month_history(monthly: pd.DataFrame, target_year: int) -> pd.DataFrame:
    return monthly.loc[
        monthly["year"].lt(target_year)
        & monthly["year"].ge(2013)
        & monthly["month"].isin(H1_MONTHS)
    ].copy()


def feature_priors(history: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for month in H1_MONTHS:
        group = history.loc[history["month"].eq(month)]
        row = {"month": month}
        for col in [
            "sessions",
            "conversion",
            "aov",
            "cogs_ratio",
            "revenue_share",
            *continuous_feature_columns(),
        ]:
            recent = weighted_recent(group, col, n=4)
            median = float(group[col].replace([np.inf, -np.inf], np.nan).median())
            pre = group.loc[group["year"].le(2018), col].replace([np.inf, -np.inf], np.nan)
            high = float(pre.median()) if not pre.dropna().empty else median
            row[f"{col}_recent"] = recent if np.isfinite(recent) else median
            row[f"{col}_median"] = median
            row[f"{col}_pre"] = high
        rows.append(row)
    return pd.DataFrame(rows)


def funnel_revenue_profile(monthly: pd.DataFrame, target_year: int, recovery: float = 0.35) -> pd.Series:
    history = month_history(monthly, target_year)
    priors = feature_priors(history)
    scores = []
    for row in priors.itertuples(index=False):
        sessions = getattr(row, "sessions_recent")
        conversion = getattr(row, "conversion_recent") + recovery * (
            getattr(row, "conversion_pre") - getattr(row, "conversion_recent")
        )
        aov = getattr(row, "aov_recent") + recovery * (getattr(row, "aov_pre") - getattr(row, "aov_recent"))
        scores.append(max(float(sessions * conversion * aov), 0.0))
    profile = pd.Series(scores, index=H1_MONTHS, dtype=float)
    if profile.sum() <= 0:
        profile = pd.Series(1.0, index=H1_MONTHS, dtype=float)
    return profile / profile.sum()


def v10_revenue_profile(sales: pd.DataFrame) -> pd.Series:
    revenue_share, _ = h1_train_priors(sales)
    return revenue_share.reindex(H1_MONTHS).astype(float) / revenue_share.reindex(H1_MONTHS).sum()


def fit_ratio_model(history: pd.DataFrame) -> tuple[np.ndarray, pd.Series, pd.Series, list[str]]:
    rows = history.copy()
    cols = continuous_feature_columns()
    for col in cols:
        rows[col] = rows[col].replace([np.inf, -np.inf], np.nan)
        rows[col] = rows[col].fillna(rows[col].median())
    rows = rows.loc[rows["cogs_ratio"].notna()].copy()
    month_dummies = pd.get_dummies(rows["month"].astype(int), prefix="m", dtype=float)
    x_cont = rows[cols].astype(float)
    mean = x_cont.mean()
    std = x_cont.std().replace(0.0, 1.0).fillna(1.0)
    x = pd.concat([month_dummies, (x_cont - mean) / std], axis=1)
    x.insert(0, "intercept", 1.0)
    y = rows["cogs_ratio"].to_numpy(dtype=float)
    xtx = x.to_numpy(dtype=float).T @ x.to_numpy(dtype=float)
    ridge = np.eye(xtx.shape[0]) * 0.75
    ridge[0, 0] = 0.0
    beta = np.linalg.solve(xtx + ridge, x.to_numpy(dtype=float).T @ y)
    return beta, mean, std, list(x.columns)


def ratio_model_profile(monthly: pd.DataFrame, target_year: int) -> pd.Series:
    history = month_history(monthly, target_year)
    beta, mean, std, columns = fit_ratio_model(history)
    priors = feature_priors(history)
    rows = []
    for row in priors.itertuples(index=False):
        data = {col: 0.0 for col in columns}
        data["intercept"] = 1.0
        data[f"m_{int(row.month)}"] = 1.0
        for col in continuous_feature_columns():
            value = getattr(row, f"{col}_recent")
            data[col] = (value - mean[col]) / std[col]
        rows.append(data)
    x = pd.DataFrame(rows, columns=columns).to_numpy(dtype=float)
    pred = pd.Series(x @ beta, index=H1_MONTHS, dtype=float)
    return pred.clip(0.78, 0.93)


def v10_ratio_profile(sales: pd.DataFrame) -> pd.Series:
    _, ratio = h1_train_priors(sales)
    return ratio.reindex(H1_MONTHS).astype(float)


def build_profiles(monthly: pd.DataFrame, sales: pd.DataFrame, target_year: int, mode: str) -> tuple[pd.Series, pd.Series]:
    funnel = funnel_revenue_profile(monthly, target_year)
    ratio = ratio_model_profile(monthly, target_year)
    if mode == "ops":
        return funnel, ratio
    if mode == "v10_ops":
        return 0.50 * funnel + 0.50 * v10_revenue_profile(sales), ratio
    if mode == "v10":
        return v10_revenue_profile(sales), v10_ratio_profile(sales)
    raise ValueError(f"Unknown profile mode: {mode}")


def scale_month(frame: pd.DataFrame, month: int, target: str, total: float) -> None:
    idx = frame.index[frame["month"].eq(month)]
    current = float(frame.loc[idx, target].sum())
    if current <= 0:
        frame.loc[idx, target] = total / max(len(idx), 1)
    else:
        frame.loc[idx, target] *= total / current


def apply_monthly_router(
    base_frame: pd.DataFrame,
    monthly: pd.DataFrame,
    sales: pd.DataFrame,
    spec: CandidateSpec,
) -> pd.DataFrame:
    out = add_period_columns(base_frame)
    h1_mask = out["period"].eq("2023H1")
    base_h1 = out.loc[h1_mask].copy()
    target = base_h1.copy()
    h1_revenue_total = float(base_h1["Revenue"].sum())
    h1_cogs_total = float(base_h1["COGS"].sum())
    base_month = (
        base_h1.groupby("month")
        .agg(revenue=("Revenue", "sum"), cogs=("COGS", "sum"))
        .reindex(H1_MONTHS)
    )
    base_revenue_share = base_month["revenue"] / base_month["revenue"].sum()
    base_ratio = base_month["cogs"] / base_month["revenue"].replace(0.0, np.nan)
    revenue_profile, ratio_profile = build_profiles(monthly, sales, 2023, spec.revenue_profile)

    blended_revenue_share = base_revenue_share.copy()
    if spec.apply_revenue:
        blended_revenue_share = (1.0 - spec.alpha) * base_revenue_share + spec.alpha * revenue_profile
        blended_revenue_share = blended_revenue_share / blended_revenue_share.sum()
    blended_ratio = base_ratio.copy()
    if spec.apply_ratio:
        ratio_alpha = spec.alpha if spec.ratio_profile != "soft" else 0.50 * spec.alpha
        blended_ratio = (1.0 - ratio_alpha) * base_ratio + ratio_alpha * ratio_profile

    month_revenue_totals = {}
    month_cogs_totals = {}
    for month in H1_MONTHS:
        month_revenue = h1_revenue_total * float(blended_revenue_share.loc[month])
        month_cogs = month_revenue * float(blended_ratio.loc[month])
        month_revenue_totals[month] = month_revenue
        month_cogs_totals[month] = month_cogs
    if spec.preserve_h1_cogs_total:
        current_cogs = sum(month_cogs_totals.values())
        if current_cogs > 0:
            scale = h1_cogs_total / current_cogs
            month_cogs_totals = {month: value * scale for month, value in month_cogs_totals.items()}

    for month in H1_MONTHS:
        scale_month(target, month, "Revenue", month_revenue_totals[month])
        scale_month(target, month, "COGS", month_cogs_totals[month])
    out.loc[h1_mask, ["Revenue", "COGS"]] = target[["Revenue", "COGS"]].to_numpy(dtype=float)
    return out[["Date", "Revenue", "COGS"]]


def r2_score(actual: np.ndarray, pred: np.ndarray) -> float:
    denom = float(np.sum((actual - actual.mean()) ** 2))
    if denom <= 0:
        return np.nan
    return float(1.0 - np.sum((actual - pred) ** 2) / denom)


def validate_monthly_router(monthly: pd.DataFrame, sales: pd.DataFrame, specs: list[CandidateSpec]) -> pd.DataFrame:
    rows = []
    for spec in specs:
        actuals = []
        preds = []
        for year in range(2018, 2023):
            history_ok = monthly["year"].lt(year).sum() > 0
            if not history_ok:
                continue
            actual = monthly.loc[monthly["year"].eq(year) & monthly["month"].isin(H1_MONTHS)].copy()
            if len(actual) != 6:
                continue
            base_rev_share = actual["revenue_share"].to_numpy(dtype=float)
            base_ratio = actual["cogs_ratio"].to_numpy(dtype=float)
            revenue_profile, ratio_profile = build_profiles(monthly, sales.loc[sales["Date"].dt.year.lt(year)], year, spec.revenue_profile)
            rev_share = base_rev_share.copy()
            if spec.apply_revenue:
                rev_share = (1.0 - spec.alpha) * base_rev_share + spec.alpha * revenue_profile.to_numpy(dtype=float)
                rev_share = rev_share / rev_share.sum()
            ratio = base_ratio.copy()
            if spec.apply_ratio:
                ratio_alpha = spec.alpha if spec.ratio_profile != "soft" else 0.50 * spec.alpha
                ratio = (1.0 - ratio_alpha) * base_ratio + ratio_alpha * ratio_profile.to_numpy(dtype=float)
            h1_rev_total = float(actual["revenue"].sum())
            h1_cogs_total = float(actual["cogs"].sum())
            pred_rev = h1_rev_total * rev_share
            pred_cogs = pred_rev * ratio
            if spec.preserve_h1_cogs_total and pred_cogs.sum() > 0:
                pred_cogs *= h1_cogs_total / pred_cogs.sum()
            actuals.append(actual[["revenue", "cogs"]].to_numpy(dtype=float).ravel())
            preds.append(np.column_stack([pred_rev, pred_cogs]).ravel())
        y_true = np.concatenate(actuals)
        y_pred = np.concatenate(preds)
        rows.append(
            {
                "name": spec.name,
                "alpha": spec.alpha,
                "revenue_profile": spec.revenue_profile,
                "preserve_h1_cogs_total": spec.preserve_h1_cogs_total,
                "apply_revenue": spec.apply_revenue,
                "apply_ratio": spec.apply_ratio,
                "mae": float(np.mean(np.abs(y_true - y_pred))),
                "rmse": float(np.sqrt(np.mean((y_true - y_pred) ** 2))),
                "r2": r2_score(y_true, y_pred),
            }
        )
    return pd.DataFrame(rows).sort_values(["mae", "rmse"], ascending=[True, True])


def summarize(frame: pd.DataFrame, base: pd.DataFrame, filename: str, spec: CandidateSpec) -> dict[str, float | str | bool]:
    work = add_period_columns(frame)
    base_work = add_period_columns(base)
    h1 = work.loc[work["period"].eq("2023H1")]
    base_h1 = base_work.loc[base_work["period"].eq("2023H1")]
    q = h1.assign(quarter=np.where(h1["month"].le(3), "Q1", "Q2")).groupby("quarter")
    base_q = base_h1.assign(quarter=np.where(base_h1["month"].le(3), "Q1", "Q2")).groupby("quarter")
    return {
        "filename": filename,
        "alpha": spec.alpha,
        "revenue_profile": spec.revenue_profile,
        "ratio_profile": spec.ratio_profile,
        "preserve_h1_cogs_total": spec.preserve_h1_cogs_total,
        "apply_revenue": spec.apply_revenue,
        "apply_ratio": spec.apply_ratio,
        "note": spec.note,
        "revenue_total": frame["Revenue"].sum(),
        "cogs_total": frame["COGS"].sum(),
        "delta_revenue_total": frame["Revenue"].sum() - base["Revenue"].sum(),
        "delta_cogs_total": frame["COGS"].sum() - base["COGS"].sum(),
        "h1_revenue": h1["Revenue"].sum(),
        "h1_cogs": h1["COGS"].sum(),
        "h1_ratio": h1["COGS"].sum() / h1["Revenue"].sum(),
        "h1_q1_rev_share": q["Revenue"].sum().loc["Q1"] / h1["Revenue"].sum(),
        "h1_q2_rev_share": q["Revenue"].sum().loc["Q2"] / h1["Revenue"].sum(),
        "h1_q1_ratio": q["COGS"].sum().loc["Q1"] / q["Revenue"].sum().loc["Q1"],
        "h1_q2_ratio": q["COGS"].sum().loc["Q2"] / q["Revenue"].sum().loc["Q2"],
        "base_h1_q1_rev_share": base_q["Revenue"].sum().loc["Q1"] / base_h1["Revenue"].sum(),
        "base_h1_q1_ratio": base_q["COGS"].sum().loc["Q1"] / base_q["Revenue"].sum().loc["Q1"],
    }


def build_specs() -> list[CandidateSpec]:
    return [
        CandidateSpec(
            name="cleanv12_monthfunnel_h1_ratio_discount_a050",
            alpha=0.50,
            revenue_profile="ops",
            ratio_profile="ops",
            preserve_h1_cogs_total=False,
            note="Monthly funnel Revenue profile plus operational COGS-ratio head; allows H1 COGS level movement.",
        ),
        CandidateSpec(
            name="cleanv12_monthfunnel_h1_ratio_discount_a075",
            alpha=0.75,
            revenue_profile="ops",
            ratio_profile="ops",
            preserve_h1_cogs_total=False,
            note="Stronger monthly funnel and COGS-ratio router.",
        ),
        CandidateSpec(
            name="cleanv12_monthfunnel_h1_preservecogs_a050",
            alpha=0.50,
            revenue_profile="ops",
            ratio_profile="ops",
            preserve_h1_cogs_total=True,
            note="RMSE/R2 hedge: monthly router but preserve total H1 COGS.",
        ),
        CandidateSpec(
            name="cleanv12_monthfunnel_h1_preservecogs_a075",
            alpha=0.75,
            revenue_profile="ops",
            ratio_profile="ops",
            preserve_h1_cogs_total=True,
            note="Stronger preserve-total COGS monthly router.",
        ),
        CandidateSpec(
            name="cleanv12_monthfunnel_h1_revenue_only_a050",
            alpha=0.50,
            revenue_profile="ops",
            ratio_profile="ops",
            preserve_h1_cogs_total=True,
            apply_ratio=False,
            note="Isolate monthly Revenue timing from COGS-ratio changes.",
        ),
        CandidateSpec(
            name="cleanv12_v10ops_h1_ratio_discount_a050",
            alpha=0.50,
            revenue_profile="v10_ops",
            ratio_profile="ops",
            preserve_h1_cogs_total=False,
            note="Blend V10 train-regime Revenue shape with operational funnel profile and ratio model.",
        ),
        CandidateSpec(
            name="cleanv12_v10ops_h1_ratio_discount_a075",
            alpha=0.75,
            revenue_profile="v10_ops",
            ratio_profile="ops",
            preserve_h1_cogs_total=False,
            note="Stronger V10/ops hybrid router.",
        ),
        CandidateSpec(
            name="cleanv12_v10control_h1_a075",
            alpha=0.75,
            revenue_profile="v10",
            ratio_profile="ops",
            preserve_h1_cogs_total=False,
            note="Control: reproduce V10-style train profile inside V12 framework.",
        ),
    ]


def write_report(
    run_dir: Path,
    manifest: pd.DataFrame,
    validation: pd.DataFrame,
    final_profiles: pd.DataFrame,
) -> None:
    report = f"""# Clean V12 Monthly Funnel Router

Run directory: `{run_dir}`

## Boundary

This is **clean-input research**. It does not read `sample_submission.csv`, prior submission files, quarantine files, or test target values as inputs. Operational inputs are summarized only from train rows through `2022-12-31`.

## Why This Exists

V10 showed that public likes a paired 2023H1 signal: Q1->Q2 Revenue timing plus lower monthly COGS-ratio regime. Ratio-only V10 failed, so V12 tries to explain the paired signal with monthly funnel and operational COGS-ratio drivers instead of hard-coded year donors.

## Validation Summary

{validation.to_markdown(index=False)}

## Final Forecast Priors

{final_profiles.to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Read

1. If prioritizing public MAE: test `submission_cleanv12_v10ops_h1_ratio_discount_a050.csv`.
2. If prioritizing RMSE/R2/report: test `submission_cleanv12_monthfunnel_h1_preservecogs_a050.csv`.
3. Do not submit ratio-only variants; `cleanv10_h1_ratio1719_keeprev_a100` already rejected that isolated hypothesis.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v12_monthly_funnel_router_2026-04-28.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    run_dir = make_run_dir()
    sales = load_sales()
    daily = build_daily_panel()
    monthly = build_monthly_table(daily)
    base_frame = build_current_clean_frame(run_dir)
    specs = build_specs()
    validation = validate_monthly_router(monthly, sales, specs)

    final_profile_rows = []
    for mode in ["ops", "v10_ops", "v10"]:
        rev_profile, ratio_profile = build_profiles(monthly, sales, 2023, mode)
        for month in H1_MONTHS:
            final_profile_rows.append(
                {
                    "mode": mode,
                    "month": month,
                    "revenue_share": rev_profile.loc[month],
                    "cogs_ratio": ratio_profile.loc[month],
                }
            )
    final_profiles = pd.DataFrame(final_profile_rows)

    rows = []
    month_rows = []
    for priority, spec in enumerate(specs, start=1):
        frame = apply_monthly_router(base_frame, monthly, sales, spec)
        sanity_check(frame, spec.name)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame, path)
        rows.append({"priority": priority, **summarize(frame, base_frame, path.name, spec)})

        work = add_period_columns(frame)
        h1 = work.loc[work["period"].eq("2023H1")].copy()
        for month, group in h1.groupby("month"):
            month_rows.append(
                {
                    "filename": path.name,
                    "month": month,
                    "revenue_share": group["Revenue"].sum() / h1["Revenue"].sum(),
                    "cogs_share": group["COGS"].sum() / h1["COGS"].sum(),
                    "cogs_ratio": group["COGS"].sum() / group["Revenue"].sum(),
                }
            )

    manifest = pd.DataFrame(rows)
    monthly_profiles = pd.DataFrame(month_rows)
    validation.to_csv(run_dir / "validation_summary.csv", index=False)
    monthly.to_csv(run_dir / "train_monthly_features.csv", index=False)
    final_profiles.to_csv(run_dir / "final_forecast_priors.csv", index=False)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    monthly_profiles.to_csv(run_dir / "candidate_h1_month_profiles.csv", index=False)
    write_report(run_dir, manifest, validation, final_profiles)

    print(run_dir)
    print(manifest[[
        "priority",
        "filename",
        "delta_revenue_total",
        "delta_cogs_total",
        "h1_q1_rev_share",
        "h1_q1_ratio",
        "h1_q2_ratio",
    ]].to_string(index=False))
