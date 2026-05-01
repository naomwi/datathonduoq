from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_clean_v2_train_evidence import build_daily_panel
from run_clean_regime_recovery_scenarios import load_sales
from run_clean_v10_h1_regime_shape import sanity_check
from run_clean_v13_daily_peak_allocator import add_daily_calendar, build_base_frames, weighted_mean
from run_clean_v16_foldlearned_daily_allocator import CandidateSpec as V16Spec
from run_clean_v16_foldlearned_daily_allocator import apply_v16
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v17_period_ratio_head"
FULL_MONTH_END = pd.Timestamp("2024-06-30")
TARGETS = ("Revenue", "COGS")


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    scopes: tuple[str, ...]
    revenue_profile: str
    revenue_alpha: float
    ratio_profile: str
    cogs_alpha: float
    preserve_period_cogs_total: bool
    note: str


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def period_key(frame: pd.DataFrame) -> pd.Series:
    dates = pd.to_datetime(frame["Date"])
    half = np.where(dates.dt.month.le(6), "H1", "H2")
    period = dates.dt.year.astype(str) + half
    period = pd.Series(period, index=frame.index, dtype="object")
    period.loc[dates.eq(pd.Timestamp("2024-07-01"))] = "2024-07-01"
    return period


def monthly_history(daily: pd.DataFrame) -> pd.DataFrame:
    work = add_daily_calendar(daily)
    work["half"] = np.where(work["month"].le(6), "H1", "H2")
    grouped = (
        work.groupby(["year", "month", "half"], as_index=False)
        .agg(
            revenue=("Revenue", "sum"),
            cogs=("COGS", "sum"),
            orders=("orders", "sum"),
            sessions=("sessions", "sum"),
            gross_item_value=("gross_item_value", "sum"),
            discount_amount=("discount_amount", "sum"),
            promo_lines=("promo_lines", "sum"),
            item_lines=("item_lines", "sum"),
        )
        .sort_values(["year", "month"])
    )
    grouped["ratio"] = grouped["cogs"] / grouped["revenue"].replace(0.0, np.nan)
    grouped["discount_rate"] = grouped["discount_amount"] / grouped["gross_item_value"].replace(0.0, np.nan)
    grouped["promo_share"] = grouped["promo_lines"] / grouped["item_lines"].replace(0.0, np.nan)
    grouped["period_revenue"] = grouped.groupby(["year", "half"])["revenue"].transform("sum")
    grouped["period_cogs"] = grouped.groupby(["year", "half"])["cogs"].transform("sum")
    grouped["revenue_share"] = grouped["revenue"] / grouped["period_revenue"].replace(0.0, np.nan)
    grouped["cogs_share"] = grouped["cogs"] / grouped["period_cogs"].replace(0.0, np.nan)
    return grouped.replace([np.inf, -np.inf], np.nan)


def select_years(history: pd.DataFrame, target_year: int, half: str, profile: str) -> pd.DataFrame:
    hist = history.loc[history["year"].lt(target_year) & history["half"].eq(half)].copy()
    if hist.empty:
        return hist
    if profile in {"recent_weighted", "share_recent_weighted"}:
        return hist
    if profile in {"recent_3", "share_recent_3"}:
        keep = sorted(hist["year"].unique())[-3:]
        return hist.loc[hist["year"].isin(keep)]
    if profile in {"recent_even", "share_recent_even"}:
        even = hist.loc[hist["year"].mod(2).eq(0)]
        keep = sorted(even["year"].unique())[-3:]
        return even.loc[even["year"].isin(keep)]
    if profile in {"recent_odd", "share_recent_odd"}:
        odd = hist.loc[hist["year"].mod(2).eq(1)]
        keep = sorted(odd["year"].unique())[-3:]
        return odd.loc[odd["year"].isin(keep)]
    if profile in {"recovery_low", "share_recovery_low"}:
        keep = [2019, 2020, 2021]
        chosen = hist.loc[hist["year"].isin(keep)]
        return chosen if not chosen.empty else hist
    if profile in {"even_all", "share_even_all"}:
        even = hist.loc[hist["year"].mod(2).eq(0)]
        return even if not even.empty else hist
    if profile in {"all_median", "share_all_median"}:
        return hist
    raise ValueError(f"Unknown profile: {profile}")


def profile_values(history: pd.DataFrame, target_year: int, half: str, value_col: str, profile: str) -> pd.Series:
    months = list(range(1, 7)) if half == "H1" else list(range(7, 13))
    selected = select_years(history, target_year, half, profile)
    rows = []
    for month in months:
        group = selected.loc[selected["month"].eq(month)]
        if group.empty:
            rows.append(np.nan)
        elif profile.endswith("median") or profile in {"even_all", "share_even_all"}:
            rows.append(float(group[value_col].median()))
        else:
            rows.append(weighted_mean(group[value_col], group["year"], decay=2.0))
    out = pd.Series(rows, index=months, dtype=float)
    fallback = history.loc[history["half"].eq(half)].groupby("month")[value_col].median().reindex(months)
    out = out.fillna(fallback).astype(float)
    return out


def revenue_share_profile(history: pd.DataFrame, target_year: int, half: str, profile: str) -> pd.Series:
    share_profile = f"share_{profile}" if not profile.startswith("share_") else profile
    values = profile_values(history, target_year, half, "revenue_share", share_profile)
    values = values.clip(0.02, 0.45)
    return values / values.sum()


def ratio_profile(history: pd.DataFrame, target_year: int, half: str, profile: str) -> pd.Series:
    values = profile_values(history, target_year, half, "ratio", profile)
    # Monthly COGS/Revenue is structurally high in some H2 promo months, but
    # unconstrained ratios above this range create unstable public RMSE tails.
    return values.clip(0.76, 1.12)


def scale_month(out: pd.DataFrame, period: str, month: int, target: str, total: float) -> None:
    idx = out.index[out["period"].eq(period) & out["month"].eq(month)]
    if len(idx) == 0:
        return
    current = float(out.loc[idx, target].sum())
    if current <= 0:
        out.loc[idx, target] = total / len(idx)
    else:
        out.loc[idx, target] *= total / current


def apply_period_ratio_head(base_frame: pd.DataFrame, history: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    out = add_daily_calendar(base_frame[["Date", "Revenue", "COGS"]])
    out["period"] = period_key(out)
    out["half"] = np.where(out["month"].le(6), "H1", "H2")

    for scope in spec.scopes:
        mask = out["period"].eq(scope) & out["Date"].le(FULL_MONTH_END)
        if not mask.any():
            continue
        target_year = int(scope[:4])
        half = scope[-2:]
        months = list(range(1, 7)) if half == "H1" else list(range(7, 13))
        period_revenue_total = float(out.loc[mask, "Revenue"].sum())
        period_cogs_total = float(out.loc[mask, "COGS"].sum())
        month_base = (
            out.loc[mask]
            .groupby("month")
            .agg(revenue=("Revenue", "sum"), cogs=("COGS", "sum"))
            .reindex(months)
            .fillna(0.0)
        )

        revenue_targets = month_base["revenue"].copy()
        if spec.revenue_alpha > 0:
            base_share = month_base["revenue"] / max(float(month_base["revenue"].sum()), 1e-12)
            prior_share = revenue_share_profile(history, target_year, half, spec.revenue_profile)
            blended_share = (1.0 - spec.revenue_alpha) * base_share + spec.revenue_alpha * prior_share
            blended_share = blended_share.clip(1e-6, None)
            blended_share = blended_share / blended_share.sum()
            revenue_targets = period_revenue_total * blended_share

        cogs_targets = month_base["cogs"].copy()
        if spec.cogs_alpha > 0:
            ratios = ratio_profile(history, target_year, half, spec.ratio_profile)
            ratio_cogs = revenue_targets * ratios
            cogs_targets = (1.0 - spec.cogs_alpha) * month_base["cogs"] + spec.cogs_alpha * ratio_cogs
            if spec.preserve_period_cogs_total and float(cogs_targets.sum()) > 0:
                cogs_targets *= period_cogs_total / float(cogs_targets.sum())

        for month in months:
            scale_month(out, scope, month, "Revenue", float(revenue_targets.loc[month]))
            scale_month(out, scope, month, "COGS", float(cogs_targets.loc[month]))

    return out[["Date", "Revenue", "COGS"]]


def validation_table(history: pd.DataFrame) -> pd.DataFrame:
    rows = []
    profiles = ["recent_weighted", "recent_3", "recent_even", "recovery_low", "even_all", "all_median"]
    for half in ["H1", "H2"]:
        for profile in profiles:
            actuals = []
            preds = []
            for year in range(2018, 2023):
                valid = history.loc[history["year"].eq(year) & history["half"].eq(half)].copy()
                if valid.empty:
                    continue
                ratios = ratio_profile(history.loc[history["year"].lt(year)], year, half, profile)
                pred_cogs = valid.set_index("month")["revenue"] * ratios
                actuals.extend(valid.set_index("month")["cogs"].reindex(ratios.index).to_numpy(dtype=float))
                preds.extend(pred_cogs.to_numpy(dtype=float))
            y = np.asarray(actuals, dtype=float)
            p = np.asarray(preds, dtype=float)
            mask = np.isfinite(y) & np.isfinite(p)
            y = y[mask]
            p = p[mask]
            if len(y) == 0:
                continue
            sst = float(np.sum((y - y.mean()) ** 2))
            rows.append(
                {
                    "head": "cogs_ratio",
                    "half": half,
                    "profile": profile,
                    "mae": float(np.mean(np.abs(y - p))),
                    "rmse": float(np.sqrt(np.mean((y - p) ** 2))),
                    "r2": 1.0 - float(np.sum((y - p) ** 2)) / sst if sst > 0 else np.nan,
                }
            )
    return pd.DataFrame(rows).sort_values(["half", "rmse", "mae"])


def build_specs() -> list[CandidateSpec]:
    specs: list[CandidateSpec] = []
    # Main new axis: lower/reshape H2 COGS totals using train-derived recovery
    # ratio profiles. These are not daily allocators; they change monthly totals.
    for profile in ["recent_weighted", "recent_even", "recovery_low", "all_median"]:
        for alpha in [0.25, 0.40, 0.55, 0.70]:
            specs.append(
                CandidateSpec(
                    name=f"cleanv17_v16_h2ratio_{profile}_c{int(alpha * 1000):03d}",
                    scopes=("2023H2",),
                    revenue_profile="recent_weighted",
                    revenue_alpha=0.0,
                    ratio_profile=profile,
                    cogs_alpha=alpha,
                    preserve_period_cogs_total=False,
                    note="Apply train-derived H2 monthly COGS/Revenue ratio head on top of V16; Revenue unchanged.",
                )
            )

    # Conservative H1 COGS ratio route. This tests whether early-year COGS
    # should follow lower recovery ratios while leaving Revenue untouched.
    for alpha in [0.20, 0.35, 0.50]:
        specs.append(
            CandidateSpec(
                name=f"cleanv17_v16_2023h1ratio_recoverylow_c{int(alpha * 1000):03d}",
                scopes=("2023H1",),
                revenue_profile="recent_weighted",
                revenue_alpha=0.0,
                ratio_profile="recovery_low",
                cogs_alpha=alpha,
                preserve_period_cogs_total=False,
                note="Apply 2019-2021 recovery COGS/Revenue ratio head to 2023H1; Revenue unchanged.",
            )
        )

    # Month-total head: preserve period revenue but move H2 month distribution
    # toward train-derived recovery/even profiles before COGS ratio is applied.
    for profile in ["recent_even", "recovery_low"]:
        specs.append(
            CandidateSpec(
                name=f"cleanv17_v16_h2revshare_{profile}_r250_c400",
                scopes=("2023H2",),
                revenue_profile=profile,
                revenue_alpha=0.25,
                ratio_profile="recent_weighted",
                cogs_alpha=0.40,
                preserve_period_cogs_total=False,
                note="Period-total head: preserve 2023H2 Revenue total but learn month share and COGS ratio from train.",
            )
        )

    return specs


def summarize(frame: pd.DataFrame, base: pd.DataFrame, spec: CandidateSpec, filename: str) -> dict[str, object]:
    work = add_daily_calendar(frame)
    work["period"] = period_key(work)
    base_work = add_daily_calendar(base)
    base_work["period"] = period_key(base_work)
    delta = frame[["Revenue", "COGS"]] - base[["Revenue", "COGS"]]

    rows = {
        "filename": filename,
        "scopes": ",".join(spec.scopes),
        "revenue_profile": spec.revenue_profile,
        "revenue_alpha": spec.revenue_alpha,
        "ratio_profile": spec.ratio_profile,
        "cogs_alpha": spec.cogs_alpha,
        "preserve_period_cogs_total": spec.preserve_period_cogs_total,
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
    for scope in ["2023H1", "2023H2", "2024H1"]:
        idx = work["period"].eq(scope)
        base_idx = base_work["period"].eq(scope)
        if not idx.any():
            continue
        revenue = float(work.loc[idx, "Revenue"].sum())
        cogs = float(work.loc[idx, "COGS"].sum())
        base_revenue = float(base_work.loc[base_idx, "Revenue"].sum())
        base_cogs = float(base_work.loc[base_idx, "COGS"].sum())
        rows[f"{scope}_revenue_delta"] = revenue - base_revenue
        rows[f"{scope}_cogs_delta"] = cogs - base_cogs
        rows[f"{scope}_ratio"] = cogs / revenue if revenue > 0 else np.nan
    return rows


def month_audit(frame: pd.DataFrame, base: pd.DataFrame, filename: str) -> pd.DataFrame:
    work = add_daily_calendar(frame)
    work["period"] = period_key(work)
    base_work = add_daily_calendar(base)
    base_work["period"] = period_key(base_work)
    rows = []
    for (year, month), group in work.groupby(["year", "month"], sort=False):
        base_group = base_work.loc[base_work["year"].eq(year) & base_work["month"].eq(month)]
        revenue = float(group["Revenue"].sum())
        cogs = float(group["COGS"].sum())
        base_revenue = float(base_group["Revenue"].sum())
        base_cogs = float(base_group["COGS"].sum())
        rows.append(
            {
                "filename": filename,
                "year": year,
                "month": month,
                "period": str(group["period"].iloc[0]),
                "revenue": revenue,
                "cogs": cogs,
                "ratio": cogs / revenue if revenue > 0 else np.nan,
                "revenue_delta": revenue - base_revenue,
                "cogs_delta": cogs - base_cogs,
                "base_ratio": base_cogs / base_revenue if base_revenue > 0 else np.nan,
            }
        )
    return pd.DataFrame(rows)


def write_report(run_dir: Path, manifest: pd.DataFrame, validation: pd.DataFrame) -> None:
    report = f"""# Clean V17 Period Ratio Head

Run directory: `{run_dir}`

## Boundary

This is **clean-input public-guided research**. It rebuilds V16 from raw/train inputs, then applies train-derived period/month heads. It does not read `sample_submission.csv`, previous submission files, quarantine files, or test target values as inputs.

## Hypothesis

V16 proved that daily allocation helps, but `c750_a300` over-shaped public. V17 pivots to a different axis:

1. Keep the V16 daily allocator as the within-month shape.
2. Learn period/month COGS totals through train-derived `COGS / Revenue` ratio profiles.
3. Optionally preserve period Revenue total while changing H2 month shares.

This directly targets the remaining structural error: H2 and early-H1 COGS ratios, not another daily-shape alpha.

## Ratio Head Validation

{validation.to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Read

Submit one sign test first. Preferred first probe is the moderate H2 ratio profile with unchanged Revenue. If it improves, escalate alpha or combine with H1 recovery ratio. If it fails, do not keep tuning daily shape; test the revenue-share head separately.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v17_period_ratio_head_2026-04-29.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    daily = build_daily_panel()
    sales = load_sales()
    history = monthly_history(daily)
    base_v10 = build_base_frames(run_dir, daily, sales)["v10"].reset_index(drop=True)
    v16_best = apply_v16(
        base_v10,
        daily,
        V16Spec(
            name="cleanv16_v10_boundary_both_c500_a300",
            correction_alpha=0.50,
            base_alpha=0.30,
            target_mode="both",
            use_boundary=True,
            note="Current clean best daily allocator.",
        ),
    ).reset_index(drop=True)
    sanity_check(v16_best, "cleanv17_v16_rebuild_anchor")

    validation = validation_table(history)
    rows = []
    audits = []
    for priority, spec in enumerate(build_specs(), start=1):
        frame = apply_period_ratio_head(v16_best, history, spec)
        sanity_check(frame, spec.name)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame, path)
        rows.append({"priority": priority, **summarize(frame, v16_best, spec, path.name)})
        audits.append(month_audit(frame, v16_best, path.name))

    manifest = pd.DataFrame(rows)
    audit = pd.concat(audits, ignore_index=True)
    validation.to_csv(run_dir / "ratio_head_validation.csv", index=False)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    audit.to_csv(run_dir / "month_audit.csv", index=False)
    write_report(run_dir, manifest, validation)

    print(run_dir)
    print(
        manifest[
            [
                "priority",
                "filename",
                "scopes",
                "ratio_profile",
                "cogs_alpha",
                "revenue_alpha",
                "delta_revenue_total",
                "delta_cogs_total",
                "2023H1_cogs_delta",
                "2023H2_cogs_delta",
                "2023H2_ratio",
                "mean_abs_cogs_delta",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
