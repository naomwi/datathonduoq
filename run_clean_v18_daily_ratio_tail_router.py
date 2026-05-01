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
from run_clean_v16_foldlearned_daily_allocator import add_boundary_features, apply_v16
from run_clean_v17_period_ratio_head import CandidateSpec as V17Spec
from run_clean_v17_period_ratio_head import apply_period_ratio_head, monthly_history, period_key
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v18_daily_ratio_tail_router"
FULL_MONTH_END = pd.Timestamp("2024-06-30")
RATIO_FEATURES = ("discount_rate", "promo_line_share", "paid_search_share", "mobile_share")


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    scopes: tuple[str, ...]
    regime: str
    alpha: float
    mode: str
    preserve: str
    tail_quantile: float
    tail_boost: float
    note: str


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def select_regime(history: pd.DataFrame, regime: str, cutoff_year: int) -> pd.DataFrame:
    hist = history.loc[history["year"].lt(cutoff_year)].copy()
    if regime == "recent_weighted":
        return hist
    if regime == "recent_even":
        even = hist.loc[hist["year"].mod(2).eq(0)]
        keep = sorted(even["year"].unique())[-3:]
        return even.loc[even["year"].isin(keep)] if keep else hist
    if regime == "recovery_low":
        selected = hist.loc[hist["year"].isin([2019, 2020, 2021])]
        return selected if not selected.empty else hist
    if regime == "pre2019_high":
        selected = hist.loc[hist["year"].between(2014, 2018)]
        return selected if not selected.empty else hist
    if regime == "all_median":
        return hist
    raise ValueError(f"Unknown regime: {regime}")


def prepare_daily_ratio_history(daily: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, tuple[float, float]]]:
    hist = add_boundary_features(daily)
    hist["ratio"] = hist["COGS"] / hist["Revenue"].replace(0.0, np.nan)
    hist["ratio"] = hist["ratio"].replace([np.inf, -np.inf], np.nan)
    lo, hi = hist["ratio"].quantile([0.01, 0.99])
    hist["ratio"] = hist["ratio"].clip(float(lo), float(hi))

    cuts: dict[str, tuple[float, float]] = {}
    for col in RATIO_FEATURES:
        values = hist[col].replace([np.inf, -np.inf], np.nan)
        q1, q2 = values.quantile([0.40, 0.75])
        cuts[col] = (float(q1), float(q2))
        hist[f"{col}_bucket"] = bucketize(values, cuts[col])
    return hist, cuts


def bucketize(values: pd.Series, cut: tuple[float, float]) -> pd.Series:
    low, high = cut
    return pd.Series(
        np.select([values.le(low), values.ge(high)], ["low", "high"], default="mid"),
        index=values.index,
        dtype="object",
    )


def weighted_lookup(
    history: pd.DataFrame,
    future: pd.DataFrame,
    keys: list[str],
    value_col: str,
    method: str = "weighted",
) -> pd.Series:
    rows = []
    for key_values, group in history.groupby(keys, sort=False):
        if not isinstance(key_values, tuple):
            key_values = (key_values,)
        row = dict(zip(keys, key_values))
        if method == "median":
            row[value_col] = float(group[value_col].median())
        else:
            row[value_col] = weighted_mean(group[value_col], group["year"], decay=2.0)
        rows.append(row)
    lookup = pd.DataFrame(rows)
    if lookup.empty:
        return pd.Series(np.nan, index=future.index, dtype=float)
    out = future[keys].copy().merge(lookup, on=keys, how="left")
    return pd.Series(out[value_col].to_numpy(dtype=float), index=future.index)


def recurring_feature_prior(history: pd.DataFrame, future: pd.DataFrame, col: str) -> pd.Series:
    global_value = float(history[col].replace([np.inf, -np.inf], np.nan).median())
    md = weighted_lookup(history, future, ["month", "day"], col)
    dow = weighted_lookup(history, future, ["month", "dow"], col)
    month = weighted_lookup(history, future, ["month"], col)
    prior = 0.50 * md.fillna(month) + 0.30 * dow.fillna(month) + 0.20 * month
    return prior.fillna(global_value)


def add_future_feature_priors(history: pd.DataFrame, future: pd.DataFrame, cuts: dict[str, tuple[float, float]]) -> pd.DataFrame:
    out = future.copy()
    for col in RATIO_FEATURES:
        out[col] = recurring_feature_prior(history, out, col)
        out[f"{col}_bucket"] = bucketize(out[col], cuts[col])
    return out


def ratio_prior(daily: pd.DataFrame, dates: pd.Series, regime: str) -> pd.Series:
    if regime == "router":
        h1_prior = ratio_prior(daily, dates, "recovery_low")
        h2_prior = ratio_prior(daily, dates, "recent_even")
        months = pd.to_datetime(dates).dt.month
        return pd.Series(np.where(months.le(6), h1_prior, h2_prior), index=dates.index).clip(0.72, 1.18)

    history, cuts = prepare_daily_ratio_history(daily)
    future = add_boundary_features(pd.DataFrame({"Date": pd.to_datetime(dates)}))
    future = add_future_feature_priors(history, future, cuts)
    cutoff_year = int(pd.to_datetime(dates).dt.year.min())
    hist = select_regime(history, regime, cutoff_year)
    if hist.empty:
        hist = history

    method = "median" if regime == "all_median" else "weighted"
    global_ratio = float(hist["ratio"].median())
    month = weighted_lookup(hist, future, ["month"], "ratio", method=method).fillna(global_ratio)
    md = weighted_lookup(hist, future, ["month", "day"], "ratio", method=method).fillna(month)
    dow = weighted_lookup(hist, future, ["month", "dow"], "ratio", method=method).fillna(month)
    boundary = weighted_lookup(hist, future, ["month", "boundary_bucket", "dow"], "ratio", method=method).fillna(dow)
    ops = weighted_lookup(
        hist,
        future,
        ["month", "dow", "discount_rate_bucket", "promo_line_share_bucket"],
        "ratio",
        method=method,
    ).fillna(dow)
    source = weighted_lookup(
        hist,
        future,
        ["month", "paid_search_share_bucket", "mobile_share_bucket"],
        "ratio",
        method=method,
    ).fillna(month)

    prior = 0.30 * md + 0.20 * dow + 0.20 * boundary + 0.20 * ops + 0.10 * source
    return pd.Series(np.asarray(prior, dtype=float), index=dates.index).clip(0.72, 1.18)


def scope_mask(frame: pd.DataFrame, scopes: tuple[str, ...]) -> pd.Series:
    return frame["period"].isin(scopes) & frame["Date"].le(FULL_MONTH_END)


def effective_alpha(out: pd.DataFrame, mask: pd.Series, spec: CandidateSpec) -> pd.Series:
    alpha = pd.Series(0.0, index=out.index, dtype=float)
    alpha.loc[mask] = spec.alpha
    if spec.mode != "tail":
        return alpha

    for scope, group in out.loc[mask].groupby("period", sort=False):
        threshold = float(group["Revenue"].quantile(spec.tail_quantile))
        tail_idx = group.index[group["Revenue"].ge(threshold)]
        alpha.loc[tail_idx] = np.minimum(1.0, spec.alpha * (1.0 + spec.tail_boost))
    return alpha


def preserve_group_total(out: pd.DataFrame, base: pd.DataFrame, mask: pd.Series, preserve: str) -> None:
    if preserve == "none":
        return
    keys = ["period"] if preserve == "period" else ["year", "month"]
    for _, idx in out.loc[mask].groupby(keys, sort=False).groups.items():
        idx = pd.Index(idx)
        target_total = float(base.loc[idx, "COGS"].sum())
        current_total = float(out.loc[idx, "COGS"].sum())
        if current_total > 0:
            out.loc[idx, "COGS"] *= target_total / current_total


def apply_daily_ratio_head(base_frame: pd.DataFrame, daily: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    out = add_boundary_features(base_frame[["Date", "Revenue", "COGS"]])
    out["period"] = period_key(out)
    base = out.copy()
    mask = scope_mask(out, spec.scopes)
    if not mask.any():
        return out[["Date", "Revenue", "COGS"]]

    prior = ratio_prior(daily, out["Date"], spec.regime)
    base_ratio = out["COGS"] / out["Revenue"].replace(0.0, np.nan)
    alpha = effective_alpha(out, mask, spec)
    target_ratio = (1.0 - alpha) * base_ratio + alpha * prior
    target_ratio = target_ratio.fillna(base_ratio).clip(0.68, 1.22)
    out.loc[mask, "COGS"] = (out.loc[mask, "Revenue"] * target_ratio.loc[mask]).clip(lower=0.0)
    preserve_group_total(out, base, mask, spec.preserve)
    return out[["Date", "Revenue", "COGS"]]


def daily_ratio_validation(daily: pd.DataFrame) -> pd.DataFrame:
    regimes = ["recent_weighted", "recent_even", "recovery_low", "pre2019_high", "all_median"]
    rows = []
    hist_all = add_boundary_features(daily)
    hist_all["period"] = hist_all["year"].astype(str) + np.where(hist_all["month"].le(6), "H1", "H2")
    for half in ["H1", "H2"]:
        for regime in regimes:
            actuals = []
            preds = []
            for year in range(2018, 2023):
                valid = hist_all.loc[hist_all["year"].eq(year) & hist_all["period"].str.endswith(half)].copy()
                train = daily.loc[pd.to_datetime(daily["Date"]).dt.year.lt(year)].copy()
                if valid.empty or train.empty:
                    continue
                prior = ratio_prior(train, valid["Date"], regime)
                pred = valid["Revenue"].to_numpy(dtype=float) * prior.to_numpy(dtype=float)
                actuals.extend(valid["COGS"].to_numpy(dtype=float))
                preds.extend(pred)
            y = np.asarray(actuals, dtype=float)
            p = np.asarray(preds, dtype=float)
            if len(y) == 0:
                continue
            sst = float(np.sum((y - y.mean()) ** 2))
            rows.append(
                {
                    "half": half,
                    "regime": regime,
                    "mae": float(np.mean(np.abs(y - p))),
                    "rmse": float(np.sqrt(np.mean((y - p) ** 2))),
                    "r2": 1.0 - float(np.sum((y - p) ** 2)) / sst if sst > 0 else np.nan,
                }
            )
    return pd.DataFrame(rows).sort_values(["half", "rmse", "mae"])


def build_current_clean_base(run_dir: Path, daily: pd.DataFrame, sales: pd.DataFrame) -> pd.DataFrame:
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
    return v17


def build_specs() -> list[CandidateSpec]:
    return [
        CandidateSpec(
            name="cleanv18_v17_h2_dailyratio_recenteven_shape_a350",
            scopes=("2023H2",),
            regime="recent_even",
            alpha=0.35,
            mode="all",
            preserve="period",
            tail_quantile=0.80,
            tail_boost=0.0,
            note="Daily COGS ratio shape-only head for H2; preserves V17 2023H2 COGS total.",
        ),
        CandidateSpec(
            name="cleanv18_v17_h2_dailyratio_recenteven_direct_a150",
            scopes=("2023H2",),
            regime="recent_even",
            alpha=0.15,
            mode="all",
            preserve="none",
            tail_quantile=0.80,
            tail_boost=0.0,
            note="Mild direct daily COGS = Revenue * learned_ratio for H2; tests total direction without big overshoot.",
        ),
        CandidateSpec(
            name="cleanv18_v17_h2_tailratio_recenteven_p80_a300",
            scopes=("2023H2",),
            regime="recent_even",
            alpha=0.30,
            mode="tail",
            preserve="period",
            tail_quantile=0.80,
            tail_boost=1.00,
            note="Tail/RMSE head: stronger learned ratio on top 20% H2 Revenue days, preserving period COGS total.",
        ),
        CandidateSpec(
            name="cleanv18_v17_h2_tailratio_recenteven_p90_a400",
            scopes=("2023H2",),
            regime="recent_even",
            alpha=0.40,
            mode="tail",
            preserve="period",
            tail_quantile=0.90,
            tail_boost=1.25,
            note="Sharper tail/RMSE head on top 10% H2 Revenue days; period COGS total preserved.",
        ),
        CandidateSpec(
            name="cleanv18_v17_router_h1recovery_h2recenteven_shape_a300",
            scopes=("2023H1", "2023H2"),
            regime="router",
            alpha=0.30,
            mode="all",
            preserve="period",
            tail_quantile=0.80,
            tail_boost=0.0,
            note="Regime-router candidate: H2 uses recent-even daily ratio; applied period-preserved to avoid level leakage.",
        ),
        CandidateSpec(
            name="cleanv18_v17_h1_dailyratio_recovery_shape_a350",
            scopes=("2023H1",),
            regime="recovery_low",
            alpha=0.35,
            mode="all",
            preserve="period",
            tail_quantile=0.80,
            tail_boost=0.0,
            note="H1 recovery ratio daily shape head; preserves 2023H1 COGS total.",
        ),
        CandidateSpec(
            name="cleanv18_v17_h2_dailyratio_recovery_direct_a200",
            scopes=("2023H2",),
            regime="recovery_low",
            alpha=0.20,
            mode="all",
            preserve="none",
            tail_quantile=0.80,
            tail_boost=0.0,
            note="Mild direct H2 recovery daily ratio; alternate lower-volatility regime.",
        ),
    ]


def summarize(frame: pd.DataFrame, base: pd.DataFrame, spec: CandidateSpec, filename: str) -> dict[str, object]:
    work = add_daily_calendar(frame)
    work["period"] = period_key(work)
    base_work = add_daily_calendar(base)
    base_work["period"] = period_key(base_work)
    delta = frame[["Revenue", "COGS"]] - base[["Revenue", "COGS"]]
    ratio = frame["COGS"] / frame["Revenue"].replace(0.0, np.nan)
    rows = {
        "filename": filename,
        "scopes": ",".join(spec.scopes),
        "regime": spec.regime,
        "alpha": spec.alpha,
        "mode": spec.mode,
        "preserve": spec.preserve,
        "tail_quantile": spec.tail_quantile,
        "tail_boost": spec.tail_boost,
        "note": spec.note,
        "revenue_total": float(frame["Revenue"].sum()),
        "cogs_total": float(frame["COGS"].sum()),
        "delta_revenue_total": float(frame["Revenue"].sum() - base["Revenue"].sum()),
        "delta_cogs_total": float(frame["COGS"].sum() - base["COGS"].sum()),
        "mean_abs_cogs_delta": float(delta["COGS"].abs().mean()),
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
            base_cogs = float(base_work.loc[base_idx, "COGS"].sum())
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
                "ratio": cogs / revenue if revenue > 0 else np.nan,
                "base_ratio": base_cogs / base_revenue if base_revenue > 0 else np.nan,
                "revenue_delta": revenue - base_revenue,
                "cogs_delta": cogs - base_cogs,
                "max_cogs_delta_abs": float((group["COGS"] - base_group["COGS"].to_numpy(dtype=float)).abs().max()),
            }
        )
    return pd.DataFrame(rows)


def write_report(run_dir: Path, manifest: pd.DataFrame, validation: pd.DataFrame) -> None:
    report = f"""# Clean V18 Daily Ratio Tail Router

Run directory: `{run_dir}`

## Boundary

This is **clean-input public-guided research**. It rebuilds current clean best from raw/train inputs, then uses train-derived recurring priors for daily COGS/Revenue ratio. It does not read `sample_submission.csv`, previous submissions, quarantine files, or test target values as inputs.

## Hypothesis

V17 showed H2 COGS ratio level helps, but stronger period-level COGS-down (`c550`) over-shoots public. V18 therefore stops changing period totals aggressively and tests:

1. Daily `COGS = Revenue * learned_ratio(month, day, dow, discount-prior, source-prior, regime)`.
2. Tail/RMSE routing that applies stronger ratio correction only on high-Revenue days.
3. Regime routing from train folds: recent-even is strongest for H2 ratio validation, recovery-low is strongest for H1.

Future discount/source features are not actual test features; they are recurring priors learned from train history.

## Daily Ratio Validation

{validation.to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v18_daily_ratio_tail_router_2026-04-29.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    daily = build_daily_panel()
    sales = load_sales()
    base = build_current_clean_base(run_dir, daily, sales)
    sanity_check(base, "cleanv18_rebuilt_v17_current_best")
    validation = daily_ratio_validation(daily)

    rows = []
    audits = []
    for priority, spec in enumerate(build_specs(), start=1):
        frame = apply_daily_ratio_head(base, daily, spec)
        sanity_check(frame, spec.name)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame, path)
        rows.append({"priority": priority, **summarize(frame, base, spec, path.name)})
        audits.append(month_audit(frame, base, path.name))

    manifest = pd.DataFrame(rows)
    audit = pd.concat(audits, ignore_index=True)
    validation.to_csv(run_dir / "daily_ratio_validation.csv", index=False)
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
                "regime",
                "alpha",
                "mode",
                "preserve",
                "delta_cogs_total",
                "2023H1_cogs_delta",
                "2023H2_cogs_delta",
                "2023H2_ratio",
                "mean_abs_cogs_delta",
                "ratio_p95",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
