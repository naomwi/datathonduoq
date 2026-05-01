from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_clean_v2_train_evidence import build_daily_panel, period_metrics
from run_clean_regime_recovery_scenarios import load_sales
from run_clean_v10_h1_regime_shape import sanity_check
from run_clean_v13_daily_peak_allocator import add_daily_calendar, weighted_mean
from run_clean_v16_foldlearned_daily_allocator import add_boundary_features
from run_clean_v16_foldlearned_daily_allocator import CandidateSpec as V16Spec
from run_clean_v16_foldlearned_daily_allocator import apply_v16
from run_clean_v17_period_ratio_head import CandidateSpec as V17Spec
from run_clean_v17_period_ratio_head import apply_period_ratio_head, monthly_history, period_key
from run_clean_v13_daily_peak_allocator import build_base_frames
from run_clean_v18_daily_ratio_tail_router import ratio_prior
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v19_multimetric_frontier"
FULL_MONTH_END = pd.Timestamp("2024-06-30")
TARGETS = ("Revenue", "COGS")


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    family: str
    scopes: tuple[str, ...]
    targets: tuple[str, ...]
    alpha: float
    profile: str
    preserve: str
    note: str


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def add_scope_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = add_boundary_features(frame)
    out["period"] = period_key(out)
    out["half"] = np.where(out["month"].le(6), "H1", "H2")
    return out


def scope_mask(frame: pd.DataFrame, scopes: tuple[str, ...]) -> pd.Series:
    return frame["period"].isin(scopes) & frame["Date"].le(FULL_MONTH_END)


def preserve_totals(out: pd.DataFrame, base: pd.DataFrame, mask: pd.Series, target: str, mode: str) -> None:
    if mode == "none":
        return
    keys = ["period"] if mode == "period" else ["year", "month"]
    for _, idx in out.loc[mask].groupby(keys, sort=False).groups.items():
        idx = pd.Index(idx)
        current_total = float(out.loc[idx, target].sum())
        target_total = float(base.loc[idx, target].sum())
        if current_total > 0:
            out.loc[idx, target] *= target_total / current_total


def relative_history(daily: pd.DataFrame, target: str) -> pd.DataFrame:
    hist = add_scope_columns(daily)
    month_total = hist.groupby(["year", "month"])[target].transform("sum")
    hist["month_avg"] = month_total / hist["days_in_month"].replace(0, np.nan)
    hist["relative_value"] = hist[target] / hist["month_avg"].replace(0, np.nan)
    hist["relative_value"] = hist["relative_value"].replace([np.inf, -np.inf], np.nan)
    hist = hist.loc[hist["relative_value"].notna()].copy()
    return hist


def tail_cap_lookup(history: pd.DataFrame, future: pd.DataFrame, profile: str) -> pd.Series:
    quantile = 0.95 if profile == "tailcap95" else 0.90
    keys = ["month", "dow", "boundary_bucket"]
    rows = []
    for key_values, group in history.groupby(keys, sort=False):
        if not isinstance(key_values, tuple):
            key_values = (key_values,)
        row = dict(zip(keys, key_values))
        row["cap"] = float(group["relative_value"].quantile(quantile))
        rows.append(row)
    lookup = pd.DataFrame(rows)
    out = future[keys].copy().merge(lookup, on=keys, how="left")

    fallback = (
        history.groupby(["month", "dow"], as_index=False)["relative_value"]
        .quantile(quantile)
        .rename(columns={"relative_value": "fallback_cap"})
    )
    out = out.merge(fallback, on=["month", "dow"], how="left")
    month_fallback = history.groupby("month")["relative_value"].quantile(quantile)
    out["cap"] = out["cap"].fillna(out["fallback_cap"])
    out["cap"] = out["cap"].fillna(future["month"].map(month_fallback))
    out["cap"] = out["cap"].fillna(float(history["relative_value"].quantile(quantile)))
    return pd.Series(out["cap"].to_numpy(dtype=float), index=future.index).clip(0.75, 5.0)


def apply_tail_cap_allocator(base_frame: pd.DataFrame, daily: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    out = add_scope_columns(base_frame[["Date", "Revenue", "COGS"]])
    base = out.copy()
    mask = scope_mask(out, spec.scopes)
    if not mask.any():
        return out[["Date", "Revenue", "COGS"]]

    future = out.loc[mask].copy()
    for target in spec.targets:
        hist = relative_history(daily, target)
        cap = tail_cap_lookup(hist, future, spec.profile)
        for _, idx in future.groupby(["year", "month"], sort=False).groups.items():
            idx = pd.Index(idx)
            total = float(out.loc[idx, target].sum())
            if total <= 0:
                continue
            rel = out.loc[idx, target].to_numpy(dtype=float) / (total / len(idx))
            capped_rel = np.minimum(rel, cap.loc[idx].to_numpy(dtype=float))
            capped_rel = np.clip(capped_rel, 1e-6, None)
            capped_share = capped_rel / capped_rel.sum()
            base_share = out.loc[idx, target].to_numpy(dtype=float) / total
            blended = (1.0 - spec.alpha) * base_share + spec.alpha * capped_share
            blended = np.clip(blended, 1e-9, None)
            blended = blended / blended.sum()
            out.loc[idx, target] = total * blended
        preserve_totals(out, base, mask, target, spec.preserve)
    return out[["Date", "Revenue", "COGS"]]


def apply_ratio_smooth(base_frame: pd.DataFrame, daily: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    out = add_scope_columns(base_frame[["Date", "Revenue", "COGS"]])
    base = out.copy()
    mask = scope_mask(out, spec.scopes)
    if not mask.any():
        return out[["Date", "Revenue", "COGS"]]

    prior = ratio_prior(daily, out["Date"], spec.profile)
    base_ratio = out["COGS"] / out["Revenue"].replace(0.0, np.nan)
    target_ratio = (1.0 - spec.alpha) * base_ratio + spec.alpha * prior
    target_ratio = target_ratio.fillna(base_ratio).clip(0.70, 1.18)
    out.loc[mask, "COGS"] = (out.loc[mask, "Revenue"] * target_ratio.loc[mask]).clip(lower=0.0)
    preserve_totals(out, base, mask, "COGS", spec.preserve)
    return out[["Date", "Revenue", "COGS"]]


def period_total_priors(daily: pd.DataFrame) -> pd.DataFrame:
    periods = period_metrics(daily)
    periods = periods.loc[periods["year"].between(2016, 2022)].copy()
    rows = []
    for half in ["H1", "H2"]:
        hist = periods.loc[periods["half"].eq(half)].copy()
        recent = hist.loc[hist["year"].ge(2019)].copy()
        if recent.empty:
            recent = hist
        weights = np.exp((recent["year"] - recent["year"].max()) / 2.0)
        rows.append(
            {
                "half": half,
                "revenue_per_day": weighted_mean(recent["revenue"] / recent["days"], recent["year"], decay=2.0),
                "cogs_ratio": float(np.average(recent["cogs_ratio"], weights=weights)),
                "conversion": float(np.average(recent["conversion"], weights=weights)),
                "aov": float(np.average(recent["aov"], weights=weights)),
            }
        )
    return pd.DataFrame(rows)


def apply_period_funnel_head(base_frame: pd.DataFrame, daily: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    out = add_scope_columns(base_frame[["Date", "Revenue", "COGS"]])
    priors = period_total_priors(daily).set_index("half")
    for scope in spec.scopes:
        mask = out["period"].eq(scope) & out["Date"].le(FULL_MONTH_END)
        if not mask.any():
            continue
        half = "H1" if scope.endswith("H1") else "H2"
        if half not in priors.index:
            continue
        current_revenue = float(out.loc[mask, "Revenue"].sum())
        current_cogs = float(out.loc[mask, "COGS"].sum())
        days = int(mask.sum())
        prior_revenue = float(priors.loc[half, "revenue_per_day"]) * days
        # The current model already learned the public high-level regime. The
        # train funnel prior is used only as a weak stabilizer, not a replacement.
        if "Revenue" in spec.targets and current_revenue > 0:
            target_revenue = (1.0 - spec.alpha) * current_revenue + spec.alpha * prior_revenue
            out.loc[mask, "Revenue"] *= target_revenue / current_revenue
        if "COGS" in spec.targets:
            revenue_after = float(out.loc[mask, "Revenue"].sum())
            prior_ratio = float(priors.loc[half, "cogs_ratio"])
            ratio_cogs = revenue_after * prior_ratio
            target_cogs = (1.0 - spec.alpha) * current_cogs + spec.alpha * ratio_cogs
            if current_cogs > 0:
                out.loc[mask, "COGS"] *= target_cogs / current_cogs
    return out[["Date", "Revenue", "COGS"]]


def build_clean_anchors(run_dir: Path, daily: pd.DataFrame, sales: pd.DataFrame) -> dict[str, pd.DataFrame]:
    base_v10 = build_base_frames(run_dir, daily, sales)["v10"].reset_index(drop=True)
    v16 = apply_v16(
        base_v10,
        daily,
        V16Spec(
            name="cleanv16_v10_boundary_both_c500_a300",
            correction_alpha=0.50,
            base_alpha=0.30,
            target_mode="both",
            use_boundary=True,
            note="Current clean daily allocator.",
        ),
    ).reset_index(drop=True)
    v17 = apply_period_ratio_head(
        v16,
        monthly_history(daily),
        V17Spec(
            name="cleanv17_v16_h2ratio_recent_weighted_c400",
            scopes=("2023H2",),
            revenue_profile="recent_weighted",
            revenue_alpha=0.0,
            ratio_profile="recent_weighted",
            cogs_alpha=0.40,
            preserve_period_cogs_total=False,
            note="Current clean best period COGS ratio head.",
        ),
    ).reset_index(drop=True)
    return {"v16": v16, "v17": v17}


def apply_existing_period_ratio(
    base_frame: pd.DataFrame,
    daily: pd.DataFrame,
    spec: CandidateSpec,
) -> pd.DataFrame:
    if spec.profile.startswith("h2_recent_weighted_c"):
        cogs_alpha = float(spec.profile.rsplit("c", 1)[1]) / 1000.0
        v17 = V17Spec(
            name=spec.name,
            scopes=("2023H2",),
            revenue_profile="recent_weighted",
            revenue_alpha=0.0,
            ratio_profile="recent_weighted",
            cogs_alpha=cogs_alpha,
            preserve_period_cogs_total=False,
            note=spec.note,
        )
    elif spec.profile.startswith("h1_recovery_low_c"):
        cogs_alpha = float(spec.profile.rsplit("c", 1)[1]) / 1000.0
        v17 = V17Spec(
            name=spec.name,
            scopes=("2023H1",),
            revenue_profile="recent_weighted",
            revenue_alpha=0.0,
            ratio_profile="recovery_low",
            cogs_alpha=cogs_alpha,
            preserve_period_cogs_total=False,
            note=spec.note,
        )
    else:
        raise ValueError(f"Unknown period-ratio profile: {spec.profile}")
    return apply_period_ratio_head(base_frame, monthly_history(daily), v17)


def build_specs() -> list[CandidateSpec]:
    return [
        CandidateSpec(
            name="cleanv19_v17_tailcap_both_p95_a150",
            family="tail_cap",
            scopes=("2023H1", "2023H2", "2024H1"),
            targets=("Revenue", "COGS"),
            alpha=0.15,
            profile="tailcap95",
            preserve="month",
            note="Lightly cap extreme within-month daily shares for both targets; preserve month totals.",
        ),
        CandidateSpec(
            name="cleanv19_v17_tailcap_cogs_p95_a250",
            family="tail_cap",
            scopes=("2023H1", "2023H2", "2024H1"),
            targets=("COGS",),
            alpha=0.25,
            profile="tailcap95",
            preserve="month",
            note="COGS-only tail cap to reduce RMSE without changing Revenue or monthly COGS totals.",
        ),
        CandidateSpec(
            name="cleanv19_v17_tailcap_both_p90_a100",
            family="tail_cap",
            scopes=("2023H1", "2023H2", "2024H1"),
            targets=("Revenue", "COGS"),
            alpha=0.10,
            profile="tailcap90",
            preserve="month",
            note="Stricter cap but lower alpha; targets RMSE/R2 tail risk while preserving month totals.",
        ),
        CandidateSpec(
            name="cleanv19_v17_ratio_monthsmooth_h2_recenteven_a150",
            family="ratio_smooth",
            scopes=("2023H2",),
            targets=("COGS",),
            alpha=0.15,
            profile="recent_even",
            preserve="month",
            note="Monthly-preserved H2 COGS ratio smoothing using recent-even train regime.",
        ),
        CandidateSpec(
            name="cleanv19_v17_ratio_monthsmooth_h2_recenteven_a160",
            family="ratio_smooth",
            scopes=("2023H2",),
            targets=("COGS",),
            alpha=0.16,
            profile="recent_even",
            preserve="month",
            note="Fine-search alpha just above validated a150, trying to improve RMSE/R2 without hurting MAE.",
        ),
        CandidateSpec(
            name="cleanv19_v17_ratio_monthsmooth_h2_recenteven_a175",
            family="ratio_smooth",
            scopes=("2023H2",),
            targets=("COGS",),
            alpha=0.175,
            profile="recent_even",
            preserve="month",
            note="Midpoint between a150 and a200 for balanced MAE/RMSE/R2 search.",
        ),
        CandidateSpec(
            name="cleanv19_v17_ratio_monthsmooth_h2_recenteven_a200",
            family="ratio_smooth",
            scopes=("2023H2",),
            targets=("COGS",),
            alpha=0.20,
            profile="recent_even",
            preserve="month",
            note="Slightly stronger monthly-preserved H2 COGS ratio smoothing.",
        ),
        CandidateSpec(
            name="cleanv19_v17_ratio_monthsmooth_h2_recenteven_a250",
            family="ratio_smooth",
            scopes=("2023H2",),
            targets=("COGS",),
            alpha=0.25,
            profile="recent_even",
            preserve="month",
            note="Upper follow-up for the validated H2 COGS ratio smoothing axis.",
        ),
        CandidateSpec(
            name="cleanv19_v17_ratio_monthsmooth_all_router_a100",
            family="ratio_smooth",
            scopes=("2023H1", "2023H2", "2024H1"),
            targets=("COGS",),
            alpha=0.10,
            profile="router",
            preserve="month",
            note="Low-alpha router ratio smoothing across all periods; preserve monthly COGS totals.",
        ),
        CandidateSpec(
            name="cleanv19_v17_periodratio_h2_mid_c300",
            family="period_ratio",
            scopes=("2023H2",),
            targets=("COGS",),
            alpha=0.300,
            profile="h2_recent_weighted_c300",
            preserve="none",
            note="Slightly weaker than V17 c400; tests public optimum below current clean best.",
        ),
        CandidateSpec(
            name="cleanv19_v17_periodratio_h2_mid_c325",
            family="period_ratio",
            scopes=("2023H2",),
            targets=("COGS",),
            alpha=0.325,
            profile="h2_recent_weighted_c325",
            preserve="none",
            note="Interpolate between V17 c250/c400; tests whether clean public optimum is below c400.",
        ),
        CandidateSpec(
            name="cleanv19_v17_periodratio_h2_mid_c350",
            family="period_ratio",
            scopes=("2023H2",),
            targets=("COGS",),
            alpha=0.350,
            profile="h2_recent_weighted_c350",
            preserve="none",
            note="Intermediate H2 COGS ratio head between c325 and current c400.",
        ),
        CandidateSpec(
            name="cleanv19_v17_periodratio_h2_mid_c375",
            family="period_ratio",
            scopes=("2023H2",),
            targets=("COGS",),
            alpha=0.375,
            profile="h2_recent_weighted_c375",
            preserve="none",
            note="Near-current H2 COGS ratio head; lower-risk than c400 if public optimum is softer.",
        ),
        CandidateSpec(
            name="cleanv19_v17_periodratio_h1_recovery_c200",
            family="period_ratio",
            scopes=("2023H1",),
            targets=("COGS",),
            alpha=0.200,
            profile="h1_recovery_low_c200",
            preserve="none",
            note="Very mild clean H1 COGS ratio recovery head.",
        ),
        CandidateSpec(
            name="cleanv19_v17_periodratio_h1_recovery_c250",
            family="period_ratio",
            scopes=("2023H1",),
            targets=("COGS",),
            alpha=0.25,
            profile="h1_recovery_low_c250",
            preserve="none",
            note="Mild clean H1 COGS ratio recovery head; tests Q1/H1 COGS signal without blackbox inputs.",
        ),
        CandidateSpec(
            name="cleanv19_v17_periodratio_h1_recovery_c300",
            family="period_ratio",
            scopes=("2023H1",),
            targets=("COGS",),
            alpha=0.300,
            profile="h1_recovery_low_c300",
            preserve="none",
            note="Moderate clean H1 COGS ratio recovery head.",
        ),
        CandidateSpec(
            name="cleanv19_v17_periodfunnel_h1_cogs_a080",
            family="period_funnel",
            scopes=("2023H1",),
            targets=("COGS",),
            alpha=0.08,
            profile="recent_funnel",
            preserve="none",
            note="Weak train-derived period funnel stabilizer for H1 COGS ratio only.",
        ),
        CandidateSpec(
            name="cleanv19_v17_hybrid_tailcap_cogs_h1ratio",
            family="hybrid",
            scopes=("2023H1", "2023H2", "2024H1"),
            targets=("COGS",),
            alpha=0.20,
            profile="tailcap95+h1ratio",
            preserve="month",
            note="COGS tail cap plus mild H1 recovery ratio head; intended balanced MAE/RMSE/R2 candidate.",
        ),
        CandidateSpec(
            name="cleanv19_v17_combo_h2c325_h1c200",
            family="combo_period_ratio",
            scopes=("2023H1", "2023H2"),
            targets=("COGS",),
            alpha=0.0,
            profile="h2_recent_weighted_c325+h1_recovery_low_c200",
            preserve="none",
            note="Combine best proxy H2 midpoint with very mild H1 recovery ratio.",
        ),
        CandidateSpec(
            name="cleanv19_v17_combo_h2c350_h1c200",
            family="combo_period_ratio",
            scopes=("2023H1", "2023H2"),
            targets=("COGS",),
            alpha=0.0,
            profile="h2_recent_weighted_c350+h1_recovery_low_c200",
            preserve="none",
            note="Slightly stronger H2 midpoint plus mild H1 recovery ratio.",
        ),
        CandidateSpec(
            name="cleanv19_v17_combo_h2smooth_h1c250",
            family="combo_ratio_h1",
            scopes=("2023H1", "2023H2"),
            targets=("COGS",),
            alpha=0.0,
            profile="h2smooth_recenteven_a150+h1_recovery_low_c250",
            preserve="mixed",
            note="Combine H2 month-preserved ratio smoothing with mild H1 recovery COGS ratio.",
        ),
        CandidateSpec(
            name="cleanv19_v17_combo_h2smooth_h1c300",
            family="combo_ratio_h1",
            scopes=("2023H1", "2023H2"),
            targets=("COGS",),
            alpha=0.0,
            profile="h2smooth_recenteven_a150+h1_recovery_low_c300",
            preserve="mixed",
            note="Combine H2 month-preserved ratio smoothing with moderate H1 recovery COGS ratio.",
        ),
    ]


def apply_candidate(anchors: dict[str, pd.DataFrame], daily: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    base = anchors["v17"]
    if spec.family == "tail_cap":
        return apply_tail_cap_allocator(base, daily, spec)
    if spec.family == "ratio_smooth":
        return apply_ratio_smooth(base, daily, spec)
    if spec.family == "period_ratio":
        anchor_name = "v16" if spec.profile.startswith("h2_recent_weighted_c") else "v17"
        return apply_existing_period_ratio(anchors[anchor_name], daily, spec)
    if spec.family == "period_funnel":
        return apply_period_funnel_head(base, daily, spec)
    if spec.family == "hybrid":
        first = apply_tail_cap_allocator(base, daily, spec)
        h1 = CandidateSpec(
            name=f"{spec.name}_inner_h1",
            family="period_ratio",
            scopes=("2023H1",),
            targets=("COGS",),
            alpha=0.20,
            profile="h1_recovery_low_c200",
            preserve="none",
            note=spec.note,
        )
        return apply_existing_period_ratio(first, daily, h1)
    if spec.family == "combo_period_ratio":
        h2_profile, h1_profile = spec.profile.split("+", 1)
        h2 = CandidateSpec(
            name=f"{spec.name}_inner_h2",
            family="period_ratio",
            scopes=("2023H2",),
            targets=("COGS",),
            alpha=0.0,
            profile=h2_profile,
            preserve="none",
            note=spec.note,
        )
        h1 = CandidateSpec(
            name=f"{spec.name}_inner_h1",
            family="period_ratio",
            scopes=("2023H1",),
            targets=("COGS",),
            alpha=0.0,
            profile=h1_profile,
            preserve="none",
            note=spec.note,
        )
        h2_frame = apply_existing_period_ratio(anchors["v16"], daily, h2)
        return apply_existing_period_ratio(h2_frame, daily, h1)
    if spec.family == "combo_ratio_h1":
        h2_profile, h1_profile = spec.profile.split("+", 1)
        if h2_profile != "h2smooth_recenteven_a150":
            raise ValueError(f"Unknown combo ratio profile: {h2_profile}")
        h2 = CandidateSpec(
            name=f"{spec.name}_inner_h2smooth",
            family="ratio_smooth",
            scopes=("2023H2",),
            targets=("COGS",),
            alpha=0.15,
            profile="recent_even",
            preserve="month",
            note=spec.note,
        )
        h1 = CandidateSpec(
            name=f"{spec.name}_inner_h1",
            family="period_ratio",
            scopes=("2023H1",),
            targets=("COGS",),
            alpha=0.0,
            profile=h1_profile,
            preserve="none",
            note=spec.note,
        )
        return apply_existing_period_ratio(apply_ratio_smooth(base, daily, h2), daily, h1)
    raise ValueError(f"Unknown family: {spec.family}")


def summarize(frame: pd.DataFrame, base: pd.DataFrame, spec: CandidateSpec, filename: str) -> dict[str, object]:
    work = add_scope_columns(frame)
    base_work = add_scope_columns(base)
    delta = frame[["Revenue", "COGS"]] - base[["Revenue", "COGS"]]
    ratio = frame["COGS"] / frame["Revenue"].replace(0.0, np.nan)
    rows: dict[str, object] = {
        "filename": filename,
        "family": spec.family,
        "scopes": ",".join(spec.scopes),
        "targets": ",".join(spec.targets),
        "alpha": spec.alpha,
        "profile": spec.profile,
        "preserve": spec.preserve,
        "note": spec.note,
        "revenue_total": float(frame["Revenue"].sum()),
        "cogs_total": float(frame["COGS"].sum()),
        "delta_revenue_total": float(frame["Revenue"].sum() - base["Revenue"].sum()),
        "delta_cogs_total": float(frame["COGS"].sum() - base["COGS"].sum()),
        "mean_abs_revenue_delta": float(delta["Revenue"].abs().mean()),
        "mean_abs_cogs_delta": float(delta["COGS"].abs().mean()),
        "max_abs_revenue_delta": float(delta["Revenue"].abs().max()),
        "max_abs_cogs_delta": float(delta["COGS"].abs().max()),
        "ratio_p95": float(ratio.quantile(0.95)),
        "ratio_max": float(ratio.max()),
    }
    for scope in ["2023H1", "2023H2", "2024H1"]:
        idx = work["period"].eq(scope)
        base_idx = base_work["period"].eq(scope)
        if idx.any():
            revenue = float(work.loc[idx, "Revenue"].sum())
            cogs = float(work.loc[idx, "COGS"].sum())
            base_revenue = float(base_work.loc[base_idx, "Revenue"].sum())
            base_cogs = float(base_work.loc[base_idx, "COGS"].sum())
            rows[f"{scope}_revenue_delta"] = revenue - base_revenue
            rows[f"{scope}_cogs_delta"] = cogs - base_cogs
            rows[f"{scope}_ratio"] = cogs / revenue if revenue > 0 else np.nan
    return rows


def month_audit(frame: pd.DataFrame, base: pd.DataFrame, filename: str) -> pd.DataFrame:
    work = add_scope_columns(frame)
    base_work = add_scope_columns(base)
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
                "year": int(year),
                "month": int(month),
                "period": str(group["period"].iloc[0]),
                "revenue": revenue,
                "cogs": cogs,
                "ratio": cogs / revenue if revenue > 0 else np.nan,
                "revenue_delta": revenue - base_revenue,
                "cogs_delta": cogs - base_cogs,
                "base_ratio": base_cogs / base_revenue if base_revenue > 0 else np.nan,
                "max_abs_revenue_delta": float((group["Revenue"] - base_group["Revenue"].to_numpy()).abs().max()),
                "max_abs_cogs_delta": float((group["COGS"] - base_group["COGS"].to_numpy()).abs().max()),
            }
        )
    return pd.DataFrame(rows)


def write_report(run_dir: Path, manifest: pd.DataFrame, base_summary: pd.DataFrame) -> None:
    report = f"""# Clean V19 Multi-Metric Frontier

Run directory: `{run_dir}`

## Boundary

This is **clean-input public-guided research**. It rebuilds current clean V17 from raw/train inputs, then applies train-derived stabilizers. It does not read `sample_submission.csv`, previous submissions, quarantine files, or test target values as inputs.

## Goal

Improve the chance of a balanced final score across MAE, RMSE, and R2:

1. Keep public MAE close to current clean best.
2. Reduce tail-day RMSE risk by smoothing extreme within-month daily shares.
3. Stabilize COGS/Revenue ratio without broad level over-shoot.

## Base Summary

{base_summary.to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Suggested Evaluation

Run `python run_multimetric_publiclike_research.py` and prioritize candidates whose proxy RMSE/R2 improves while public MAE is expected to stay near current clean best.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v19_multimetric_frontier_2026-04-30.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    daily = build_daily_panel()
    sales = load_sales()
    anchors = build_clean_anchors(run_dir, daily, sales)
    base = anchors["v17"].reset_index(drop=True)
    sanity_check(base, "cleanv19_rebuilt_v17_current_best")
    base_summary = (
        add_scope_columns(base)
        .groupby("period", as_index=False)
        .agg(days=("Date", "count"), revenue=("Revenue", "sum"), cogs=("COGS", "sum"))
    )
    base_summary["ratio"] = base_summary["cogs"] / base_summary["revenue"]

    rows = []
    audits = []
    for priority, spec in enumerate(build_specs(), start=1):
        frame = apply_candidate(anchors, daily, spec).reset_index(drop=True)
        sanity_check(frame, spec.name)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame, path)
        rows.append({"priority": priority, **summarize(frame, base, spec, path.name)})
        audits.append(month_audit(frame, base, path.name))

    manifest = pd.DataFrame(rows)
    audit = pd.concat(audits, ignore_index=True)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    audit.to_csv(run_dir / "month_audit.csv", index=False)
    base_summary.to_csv(run_dir / "base_summary.csv", index=False)
    write_report(run_dir, manifest, base_summary)

    print(run_dir)
    print(
        manifest[
            [
                "priority",
                "filename",
                "family",
                "targets",
                "alpha",
                "profile",
                "preserve",
                "delta_revenue_total",
                "delta_cogs_total",
                "2023H1_cogs_delta",
                "2023H2_cogs_delta",
                "mean_abs_revenue_delta",
                "mean_abs_cogs_delta",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
