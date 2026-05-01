from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_clean_regime_recovery_scenarios import load_sales, period_summary
from run_clean_v2_eda_guided_candidates import base_totals
from run_clean_v6_merch_margin_priors import build_daily_merch_features, build_monthday_priors
from run_clean_v7_period_funnel_council import build_source_period_table, source_quality_revenue, weighted_recent, high_regime_mean
from run_cleaninput_rawmdshape_pubguided import apply_period_totals, build_shape_base
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v8_bottomup_funnel_council"
TRAIN_END = pd.Timestamp("2022-12-31")
FORECAST_START = pd.Timestamp("2023-01-01")
FORECAST_END = pd.Timestamp("2024-07-01")


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    source_alpha: float
    scope: str = "2023H1"
    cogs_mode: str = "keep"
    merch_gamma: float = 0.0
    source_recovery_h1: float = 0.20
    source_recovery_h2: float = 0.30
    h1_ratio: float = 0.870
    note: str = ""


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def add_period_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out["year"] = out["Date"].dt.year
    out["month"] = out["Date"].dt.month
    out["month_day"] = out["Date"].dt.strftime("%m-%d")
    out["half"] = np.where(out["month"].le(6), "H1", "H2")
    out["period"] = out["year"].astype(str) + out["half"]
    out.loc[out["Date"].eq(FORECAST_END), "period"] = "2024-07-01"
    return out


def safe_div(num: pd.Series | float, den: pd.Series | float) -> pd.Series | float:
    if np.isscalar(num) and np.isscalar(den):
        return float(num) / float(den) if float(den) else np.nan
    return pd.Series(num, dtype=float) / pd.Series(den, dtype=float).replace(0.0, np.nan)


def period_dates(period: str) -> pd.DatetimeIndex:
    if period == "2024-07-01":
        return pd.DatetimeIndex([pd.Timestamp("2024-07-01")])
    year, half = period_year_half(period)
    if half == "H1":
        return pd.date_range(f"{year}-01-01", f"{year}-06-30", freq="D")
    if half == "H2":
        return pd.date_range(f"{year}-07-01", f"{year}-12-31", freq="D")
    raise ValueError(f"Unknown period: {period}")


def period_year_half(period: str) -> tuple[int, str]:
    if period == "2024-07-01":
        return 2024, "H2"
    return int(period[:4]), period[4:]


def scope_periods(scope: str) -> tuple[str, ...]:
    if scope == "2023H1":
        return ("2023H1",)
    if scope == "H1":
        return ("2023H1", "2024H1")
    if scope == "major":
        return ("2023H1", "2023H2", "2024H1")
    raise ValueError(f"Unknown scope: {scope}")


def build_current_clean_base(source_periods: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    sales = load_sales()
    totals = base_totals(sales)
    h1_revenue = source_quality_revenue(source_periods, 2023, "H1", 0.20)
    mask = totals["period"].eq("2023H1")
    totals.loc[mask, "revenue"] = h1_revenue
    totals.loc[mask, "cogs"] = h1_revenue * 0.870
    totals["cogs_ratio"] = totals["cogs"] / totals["revenue"]
    shape_base = build_shape_base()
    frame = apply_period_totals(shape_base, totals).reset_index(drop=True)
    return frame, totals


def build_source_daily_table(run_dir: Path) -> pd.DataFrame:
    orders = pd.read_csv(DATASET_DIR / "orders.csv", parse_dates=["order_date"], low_memory=False)
    items = pd.read_csv(DATASET_DIR / "order_items.csv", low_memory=False)
    traffic = pd.read_csv(DATASET_DIR / "web_traffic.csv", parse_dates=["date"], low_memory=False)

    item_value = (
        items.assign(net_value=items["quantity"] * items["unit_price"] - items["discount_amount"].fillna(0.0))
        .groupby("order_id", as_index=False)
        .agg(order_value=("net_value", "sum"))
    )
    order_values = orders.merge(item_value, on="order_id", how="left")
    order_values = order_values.loc[order_values["order_date"].le(TRAIN_END) & order_values["order_date"].dt.year.between(2013, 2022)].copy()
    order_daily = (
        order_values.groupby(["order_date", "order_source"], as_index=False)
        .agg(order_value=("order_value", "sum"), orders=("order_id", "nunique"))
        .rename(columns={"order_date": "Date", "order_source": "source"})
    )

    traffic = traffic.loc[traffic["date"].le(TRAIN_END) & traffic["date"].dt.year.between(2013, 2022)].copy()
    traffic_daily = (
        traffic.groupby(["date", "traffic_source"], as_index=False)
        .agg(sessions=("sessions", "sum"), unique_visitors=("unique_visitors", "sum"), page_views=("page_views", "sum"))
        .rename(columns={"date": "Date", "traffic_source": "source"})
    )

    daily = traffic_daily.merge(order_daily, on=["Date", "source"], how="outer")
    daily["Date"] = pd.to_datetime(daily["Date"])
    for col in ["sessions", "unique_visitors", "page_views", "order_value", "orders"]:
        daily[col] = daily[col].fillna(0.0)
    daily = add_period_columns(daily)

    period_source = daily.groupby(["year", "half", "source"], as_index=False).agg(
        period_sessions=("sessions", "sum"),
        period_order_value=("order_value", "sum"),
    )
    daily = daily.merge(period_source, on=["year", "half", "source"], how="left")
    daily["session_share"] = safe_div(daily["sessions"], daily["period_sessions"]).fillna(0.0)
    daily["value_share"] = safe_div(daily["order_value"], daily["period_order_value"]).fillna(0.0)
    daily.to_csv(run_dir / "source_daily_train.csv", index=False)
    return daily


def source_revenue_by_source(source_periods: pd.DataFrame, year: int, half: str, recovery: float) -> pd.DataFrame:
    rows = []
    for source_name in sorted(source_periods["source"].dropna().unique()):
        history = source_periods.loc[
            (source_periods["year"].lt(year)) & (source_periods["half"].eq(half)) & (source_periods["source"].eq(source_name))
        ].sort_values("year")
        if history.empty:
            continue
        sessions = weighted_recent(history, "sessions", n=4)
        recent_rps = weighted_recent(history, "revenue_per_session", n=4)
        high_rps = high_regime_mean(history, "revenue_per_session")
        if not np.isfinite(sessions) or not np.isfinite(recent_rps) or not np.isfinite(high_rps):
            continue
        rps = recent_rps + recovery * (high_rps - recent_rps)
        rows.append(
            {
                "source": str(source_name),
                "sessions": sessions,
                "revenue_per_session": rps,
                "source_revenue": sessions * rps,
            }
        )
    return pd.DataFrame(rows)


def source_daily_forecast(
    source_daily: pd.DataFrame,
    source_periods: pd.DataFrame,
    period: str,
    recovery: float,
    shape_mode: str = "session_share",
) -> pd.DataFrame:
    year, half = period_year_half(period)
    dates = period_dates(period)
    target = pd.DataFrame({"Date": dates})
    target["month_day"] = target["Date"].dt.strftime("%m-%d")

    by_source = source_revenue_by_source(source_periods, year, half, recovery)
    frames = []
    for row in by_source.itertuples(index=False):
        hist = source_daily.loc[
            (source_daily["year"].lt(year)) & (source_daily["half"].eq(half)) & (source_daily["source"].eq(row.source))
        ].copy()
        shares = hist.groupby("month_day", as_index=False).agg(day_share=(shape_mode, "median"))
        shaped = target.merge(shares, on="month_day", how="left")
        shaped["day_share"] = shaped["day_share"].fillna(0.0)
        if float(shaped["day_share"].sum()) <= 0:
            shaped["day_share"] = 1.0 / len(shaped)
        else:
            shaped["day_share"] /= float(shaped["day_share"].sum())
        shaped["source"] = row.source
        shaped["source_revenue"] = float(row.source_revenue)
        shaped["Revenue"] = shaped["source_revenue"] * shaped["day_share"]
        frames.append(shaped[["Date", "source", "Revenue"]])

    if not frames:
        raise ValueError(f"No source daily forecast available for {period}")
    out = pd.concat(frames, ignore_index=True).groupby("Date", as_index=False).agg(Revenue=("Revenue", "sum"))
    expected_total = float(by_source["source_revenue"].sum())
    current_total = float(out["Revenue"].sum())
    if current_total > 0:
        out["Revenue"] *= expected_total / current_total
    return out


def normalize_to_total(values: pd.Series, total: float) -> pd.Series:
    current = float(values.sum())
    if current <= 0:
        return pd.Series(total / len(values), index=values.index)
    return values * total / current


def apply_merch_cogs_shape(frame: pd.DataFrame, priors: pd.DataFrame, active_idx: list[int], gamma: float, period_total: float) -> pd.Series:
    if gamma <= 0:
        return normalize_to_total(frame.loc[active_idx, "COGS"], period_total)
    period = add_period_columns(frame.loc[active_idx].copy())
    merged = period.merge(priors[["month_day", "merch_cogs_factor"]], on="month_day", how="left")
    factor = (1.0 + gamma * (merged["merch_cogs_factor"].fillna(1.0) - 1.0)).clip(0.75, 1.25)
    cogs = frame.loc[active_idx, "COGS"].reset_index(drop=True) * factor.to_numpy()
    return normalize_to_total(pd.Series(cogs, index=active_idx), period_total)


def apply_candidate(
    base_frame: pd.DataFrame,
    source_daily: pd.DataFrame,
    source_periods: pd.DataFrame,
    merch_priors: pd.DataFrame,
    spec: CandidateSpec,
) -> pd.DataFrame:
    out = add_period_columns(base_frame).reset_index(drop=True)
    for period in scope_periods(spec.scope):
        recovery = spec.source_recovery_h1 if period.endswith("H1") else spec.source_recovery_h2
        source_forecast = source_daily_forecast(source_daily, source_periods, period, recovery)
        idx = out.index[out["period"].eq(period)].tolist()
        if not idx:
            continue

        base_rev = out.loc[idx, "Revenue"].reset_index(drop=True)
        source_rev = source_forecast["Revenue"].reset_index(drop=True)
        source_rev = normalize_to_total(source_rev, float(base_rev.sum()))
        blended_rev = (1.0 - spec.source_alpha) * base_rev + spec.source_alpha * source_rev
        out.loc[idx, "Revenue"] = normalize_to_total(blended_rev, float(base_rev.sum())).to_numpy()

        base_cogs_total = float(out.loc[idx, "COGS"].sum())
        if spec.cogs_mode == "keep":
            continue
        if spec.cogs_mode in {"comove", "merch"}:
            ratio = base_cogs_total / max(float(out.loc[idx, "Revenue"].sum()), 1e-9)
            out.loc[idx, "COGS"] = out.loc[idx, "Revenue"] * ratio
            if spec.cogs_mode == "merch":
                out.loc[idx, "COGS"] = apply_merch_cogs_shape(out, merch_priors, idx, spec.merch_gamma, base_cogs_total)
            else:
                out.loc[idx, "COGS"] = normalize_to_total(out.loc[idx, "COGS"], base_cogs_total).to_numpy()
        else:
            raise ValueError(f"Unknown COGS mode: {spec.cogs_mode}")
    return out[["Date", "Revenue", "COGS", "period"]]


def validate_source_daily_shape(source_daily: pd.DataFrame, source_periods: pd.DataFrame) -> pd.DataFrame:
    rows = []
    actual_daily = (
        source_daily.groupby("Date", as_index=False)
        .agg(Revenue=("order_value", "sum"))
        .pipe(add_period_columns)
    )
    for year in range(2018, 2023):
        for half in ["H1", "H2"]:
            period = f"{year}{half}"
            actual = actual_daily.loc[actual_daily["period"].eq(period), ["Date", "Revenue"]].copy()
            if actual.empty:
                continue
            for recovery in [0.10, 0.15, 0.20, 0.25, 0.30]:
                pred = source_daily_forecast(source_daily, source_periods, period, recovery)
                merged = actual.merge(pred, on="Date", how="left", suffixes=("_actual", "_pred"))
                mae = float((merged["Revenue_actual"] - merged["Revenue_pred"]).abs().mean())
                total_ape = abs(float(merged["Revenue_pred"].sum()) - float(merged["Revenue_actual"].sum())) / max(
                    abs(float(merged["Revenue_actual"].sum())), 1e-9
                )
                rows.append(
                    {
                        "period": period,
                        "year": year,
                        "half": half,
                        "recovery": recovery,
                        "daily_mae": mae,
                        "period_total_ape": total_ape,
                    }
                )
    return pd.DataFrame(rows)


def build_specs() -> list[CandidateSpec]:
    return [
        CandidateSpec(
            name="cleanv8_bottomup_h1_sourceblend_a002_keepcogs",
            source_alpha=0.02,
            cogs_mode="keep",
            note="Micro source-channel daily Revenue shape; safest test after a010 showed large local movement.",
        ),
        CandidateSpec(
            name="cleanv8_bottomup_h1_sourceblend_a005_keepcogs",
            source_alpha=0.05,
            cogs_mode="keep",
            note="Small source-channel daily Revenue shape; COGS daily shape unchanged.",
        ),
        CandidateSpec(
            name="cleanv8_bottomup_h1_sourceblend_a005_comove",
            source_alpha=0.05,
            cogs_mode="comove",
            note="Small source-channel daily Revenue shape with COGS co-moving at period ratio.",
        ),
        CandidateSpec(
            name="cleanv8_bottomup_h1_sourceblend_a010_keepcogs",
            source_alpha=0.10,
            cogs_mode="keep",
            note="Low-risk source-channel daily Revenue shape; COGS daily shape unchanged.",
        ),
        CandidateSpec(
            name="cleanv8_bottomup_h1_sourceblend_a025_keepcogs",
            source_alpha=0.25,
            cogs_mode="keep",
            note="Moderate source-channel daily Revenue shape; COGS daily shape unchanged.",
        ),
        CandidateSpec(
            name="cleanv8_bottomup_h1_sourceblend_a050_keepcogs",
            source_alpha=0.50,
            cogs_mode="keep",
            note="Strong source-channel daily Revenue shape; COGS daily shape unchanged.",
        ),
        CandidateSpec(
            name="cleanv8_bottomup_h1_sourceblend_a025_comove",
            source_alpha=0.25,
            cogs_mode="comove",
            note="Source-channel daily Revenue shape with COGS co-moving at period ratio.",
        ),
        CandidateSpec(
            name="cleanv8_bottomup_h1_sourceblend_a050_comove",
            source_alpha=0.50,
            cogs_mode="comove",
            note="Stronger source-channel daily Revenue shape with COGS co-moving.",
        ),
        CandidateSpec(
            name="cleanv8_bottomup_h1_sourceblend_a025_merch010",
            source_alpha=0.25,
            cogs_mode="merch",
            merch_gamma=0.10,
            note="Source-channel daily Revenue shape plus merchandise economics COGS shape.",
        ),
        CandidateSpec(
            name="cleanv8_bottomup_h1_sourceblend_a050_merch010",
            source_alpha=0.50,
            cogs_mode="merch",
            merch_gamma=0.10,
            note="Stronger source-channel daily Revenue shape plus merchandise COGS shape.",
        ),
        CandidateSpec(
            name="cleanv8_bottomup_all_sourceblend_a010_keepcogs",
            source_alpha=0.10,
            scope="major",
            cogs_mode="keep",
            note="Apply small bottom-up source daily shape to all major periods; high-risk broad test.",
        ),
    ]


def sanity_check(frame: pd.DataFrame, name: str) -> None:
    if len(frame) != 548:
        raise ValueError(f"{name}: expected 548 rows, got {len(frame)}")
    dates = pd.to_datetime(frame["Date"])
    if dates.min() != FORECAST_START or dates.max() != FORECAST_END:
        raise ValueError(f"{name}: bad date range {dates.min()} - {dates.max()}")
    if frame[["Revenue", "COGS"]].isna().any().any():
        raise ValueError(f"{name}: contains NaN")
    if frame[["Revenue", "COGS"]].lt(0).any().any():
        raise ValueError(f"{name}: contains negative target values")


def movement_summary(frame: pd.DataFrame, base: pd.DataFrame) -> dict[str, float]:
    rev_delta = frame["Revenue"] - base["Revenue"]
    cogs_delta = frame["COGS"] - base["COGS"]
    return {
        "rev_abs_delta_mean": float(rev_delta.abs().mean()),
        "cogs_abs_delta_mean": float(cogs_delta.abs().mean()),
        "rev_abs_delta_max": float(rev_delta.abs().max()),
        "cogs_abs_delta_max": float(cogs_delta.abs().max()),
        "revenue_total_ratio_vs_base": float(frame["Revenue"].sum() / base["Revenue"].sum()),
        "cogs_total_ratio_vs_base": float(frame["COGS"].sum() / base["COGS"].sum()),
        "max_revenue": float(frame["Revenue"].max()),
        "max_cogs": float(frame["COGS"].max()),
    }


def write_report(run_dir: Path, manifest: pd.DataFrame, validation: pd.DataFrame) -> None:
    validation_summary = (
        validation.groupby(["half", "recovery"], as_index=False)
        .agg(mean_daily_mae=("daily_mae", "mean"), mean_total_ape=("period_total_ape", "mean"))
        .sort_values(["half", "mean_daily_mae", "mean_total_ape"])
    )
    report = f"""# Clean V8 Bottom-Up Funnel Council

Run directory: `{run_dir}`

## Boundary

This is clean-input public-guided. It does not read `sample_submission.csv`, previous submissions, quarantine files, or test targets.

Known public signals used only for candidate focus:

- `submission_cleanv7_source_h1_s020_r0870.csv = 673720.88479`
- `submission_cleanv7_sourcefine_s0190_r0870.csv = 674415.02000`, so do not lower H1 source recovery aggressively.

## Model Change

V7 changed only period totals and kept raw-md daily shape.

V8 tests a more bottom-up daily model:

1. Source/channel sessions shape from `web_traffic.csv`.
2. Source revenue/session recovery from `orders.csv` + `order_items.csv`.
3. Optional product economics COGS shape from `order_items.csv` + `products.csv`.
4. Period totals remain controlled at the current clean-best source-quality head.

## Source Daily Shape Validation

{validation_summary.to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Order

1. `submission_cleanv8_bottomup_h1_sourceblend_a002_keepcogs.csv`
2. If improves: `submission_cleanv8_bottomup_h1_sourceblend_a005_keepcogs.csv`
3. If Revenue shape improves but COGS looks suspect: `submission_cleanv8_bottomup_h1_sourceblend_a005_comove.csv`
4. Do not submit all-period sourceblend unless H1-only is positive.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v8_bottomup_funnel_council_2026-04-28.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    source_periods = build_source_period_table(run_dir)
    base_frame, base_totals_frame = build_current_clean_base(source_periods)
    sanity_check(base_frame, "base_frame")
    source_daily = build_source_daily_table(run_dir)
    merch_daily = build_daily_merch_features(run_dir)
    merch_priors = build_monthday_priors(merch_daily, run_dir)
    validation = validate_source_daily_shape(source_daily, source_periods)
    validation.to_csv(run_dir / "source_daily_shape_validation.csv", index=False)
    base_totals_frame.to_csv(run_dir / "base_period_totals.csv", index=False)

    rows: list[dict[str, object]] = []
    for priority, spec in enumerate(build_specs(), start=1):
        frame = apply_candidate(base_frame, source_daily, source_periods, merch_priors, spec).reset_index(drop=True)
        sanity_check(frame, spec.name)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)
        prof = period_summary(frame)
        prof.to_csv(run_dir / f"{spec.name}_period_summary.csv", index=False)
        row = {
            "priority": priority,
            "filename": path.name,
            "scope": spec.scope,
            "source_alpha": spec.source_alpha,
            "cogs_mode": spec.cogs_mode,
            "merch_gamma": spec.merch_gamma,
            "source_recovery_h1": spec.source_recovery_h1,
            "source_recovery_h2": spec.source_recovery_h2,
            "h1_ratio": spec.h1_ratio,
            "revenue_total": float(frame["Revenue"].sum()),
            "cogs_total": float(frame["COGS"].sum()),
            "ratio_total": float(frame["COGS"].sum() / frame["Revenue"].sum()),
            "note": spec.note,
        }
        for _, period_row in prof.iterrows():
            period = str(period_row["period"])
            row[f"rev_{period}"] = float(period_row["revenue"])
            row[f"cogs_{period}"] = float(period_row["cogs"])
            row[f"ratio_{period}"] = float(period_row["cogs_ratio"])
        row.update(movement_summary(frame, base_frame))
        rows.append(row)

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    write_report(run_dir, manifest, validation)
    print(run_dir)
    print(manifest[["priority", "filename", "scope", "source_alpha", "cogs_mode", "rev_abs_delta_mean", "cogs_abs_delta_mean"]].to_string(index=False))


if __name__ == "__main__":
    main()
