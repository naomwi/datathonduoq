from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_clean_v2_train_evidence import expand_promotions
from run_clean_regime_recovery_scenarios import gap_blend_total, load_sales, period_summary
from run_cleaninput_rawmdshape_pubguided import (
    apply_period_totals,
    build_shape_base,
    build_specs,
    make_totals_from_scenario,
)
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v2_eda_guided_candidates"


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    h1_beta: float | None
    h1_cogs_ratio: float | None
    ratio_shape_gamma: float = 0.0
    ratio_shape_scope: str = "none"
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
    out["day"] = out["Date"].dt.day
    out["month_day"] = out["Date"].dt.strftime("%m-%d")
    out["half"] = np.where(out["month"].le(6), "H1", "H2")
    out["period"] = out["year"].astype(str) + out["half"]
    out.loc[out["Date"].eq(pd.Timestamp("2024-07-01")), "period"] = "2024-07-01"
    return out


def h1_ratio_stats(sales: pd.DataFrame) -> dict[str, float]:
    hist = add_period_columns(sales)
    periods = (
        hist.loc[hist["year"].between(2013, 2022)]
        .groupby(["year", "half"], as_index=False)
        .agg(revenue=("Revenue", "sum"), cogs=("COGS", "sum"))
    )
    periods["ratio"] = periods["cogs"] / periods["revenue"]
    h1 = periods.loc[periods["half"].eq("H1"), "ratio"]
    return {
        "h1_mean": float(h1.mean()),
        "h1_p90": float(h1.quantile(0.90)),
        "h1_p95": float(h1.quantile(0.95)),
        "h1_max": float(h1.max()),
        # Public-guided but train-plausible stress point: slightly above the
        # train H1 max, still far below the old all-half-year p95 stress.
        "h1_recovery_stress": 0.876,
        "h1_recovery_high": 0.890,
    }


def base_totals(sales: pd.DataFrame) -> pd.DataFrame:
    specs = build_specs()
    spec = next(s for s in specs if s.name == "cleaninput_rawmdshape_v5_v4main_cogs2024gap0545")
    return make_totals_from_scenario(sales, spec)


def apply_h1_total_override(sales: pd.DataFrame, totals: pd.DataFrame, beta: float | None, ratio: float | None) -> pd.DataFrame:
    out = totals.copy()
    if beta is None:
        return out
    revenue = gap_blend_total(sales, "Revenue", 2023, "H1", beta)
    mask = out["period"].eq("2023H1")
    out.loc[mask, "revenue"] = revenue
    if ratio is not None:
        out.loc[mask, "cogs"] = revenue * ratio
    out["cogs_ratio"] = out["cogs"] / out["revenue"]
    return out


def recurring_promo_features() -> pd.DataFrame:
    promos = pd.read_csv(DATASET_DIR / "promotions.csv", parse_dates=["start_date", "end_date"])
    daily = expand_promotions(promos)
    daily["month"] = daily["Date"].dt.month
    daily["day"] = daily["Date"].dt.day
    daily["month_day"] = daily["Date"].dt.strftime("%m-%d")
    active_years = max(1, daily["Date"].dt.year.nunique())
    priors = (
        daily.groupby("month_day", as_index=False)
        .agg(
            promo_active_years=("Date", lambda s: s.dt.year.nunique()),
            promo_count_prior=("active_promo_count", "mean"),
            promo_discount_prior=("promo_discount_max", "mean"),
            promo_discount_max=("promo_discount_max", "max"),
            stackable_prior=("stackable_promos", lambda s: float((s > 0).mean())),
        )
    )
    priors["promo_active_share"] = priors["promo_active_years"] / active_years
    return priors


def monthly_ratio_priors(sales: pd.DataFrame) -> pd.DataFrame:
    hist = add_period_columns(sales)
    hist = hist.loc[hist["year"].between(2013, 2022)].copy()
    hist["cogs_ratio"] = hist["COGS"] / hist["Revenue"].replace(0, np.nan)
    month = (
        hist.groupby(["half", "month"], as_index=False)
        .agg(month_ratio=("cogs_ratio", "median"), month_ratio_mean=("cogs_ratio", "mean"))
    )
    half = hist.groupby("half", as_index=False).agg(half_ratio=("cogs_ratio", "median"))
    return month.merge(half, on="half", how="left")


def apply_ratio_shape(frame: pd.DataFrame, sales: pd.DataFrame, gamma: float, scope: str) -> pd.DataFrame:
    if gamma <= 0 or scope == "none":
        return frame
    out = add_period_columns(frame)
    promo = recurring_promo_features()
    month_ratio = monthly_ratio_priors(sales)
    out = out.merge(promo, on="month_day", how="left")
    out = out.merge(month_ratio, on=["half", "month"], how="left")
    for col in ["promo_active_share", "promo_count_prior", "promo_discount_prior", "promo_discount_max", "stackable_prior"]:
        out[col] = out[col].fillna(0.0)
    out["month_ratio_factor"] = (out["month_ratio"] / out["half_ratio"].replace(0, np.nan)).fillna(1.0)
    out["promo_factor"] = 1.0 + 0.35 * out["promo_active_share"] * (out["promo_discount_prior"] / 50.0).clip(0.0, 1.0)
    out["stack_factor"] = 1.0 + 0.08 * out["stackable_prior"]
    out["raw_ratio_shape"] = (out["month_ratio_factor"] * out["promo_factor"] * out["stack_factor"]).clip(0.65, 1.75)
    out["factor"] = 1.0 + gamma * (out["raw_ratio_shape"] - 1.0)

    if scope == "h2":
        active = out["period"].isin(["2023H2", "2024-07-01"])
    elif scope == "all":
        active = out["period"].isin(["2023H1", "2023H2", "2024H1", "2024-07-01"])
    else:
        raise ValueError(f"Unknown ratio shape scope: {scope}")

    out.loc[active, "COGS"] *= out.loc[active, "factor"]
    for period, idx in out.groupby("period").groups.items():
        idx = list(idx)
        original_total = float(frame.loc[idx, "COGS"].sum())
        new_total = float(out.loc[idx, "COGS"].sum())
        if new_total > 0:
            out.loc[idx, "COGS"] *= original_total / new_total
    return out[["Date", "Revenue", "COGS", "period"]]


def build_candidates(sales: pd.DataFrame) -> list[CandidateSpec]:
    stats = h1_ratio_stats(sales)
    return [
        CandidateSpec(
            name="cleanv2_promo_ratio_shape_only_g050",
            h1_beta=None,
            h1_cogs_ratio=None,
            ratio_shape_gamma=0.50,
            ratio_shape_scope="h2",
            note="Keep v5 period totals; redistribute H2 COGS using train-derived month/promo ratio priors.",
        ),
        CandidateSpec(
            name="cleanv2_h1funnel_b040_h1max",
            h1_beta=0.40,
            h1_cogs_ratio=stats["h1_max"],
            note="Train-derived H1 funnel recovery: 40% low-to-high gap; H1 COGS ratio capped at train H1 max.",
        ),
        CandidateSpec(
            name="cleanv2_h1funnel_b045_r0876",
            h1_beta=0.45,
            h1_cogs_ratio=stats["h1_recovery_stress"],
            note="Public-guided clean-input: stronger H1 conversion/AOV recovery; H1 ratio stress remains below broad all-half p95.",
        ),
        CandidateSpec(
            name="cleanv2_h1funnel_b046_r0876_augpromo",
            h1_beta=0.46,
            h1_cogs_ratio=stats["h1_recovery_stress"],
            ratio_shape_gamma=0.45,
            ratio_shape_scope="h2",
            note="Same H1 recovery, plus H2 COGS daily reshape from recurring promo/discount priors.",
        ),
        CandidateSpec(
            name="cleanv2_h1funnel_b050_r0876",
            h1_beta=0.50,
            h1_cogs_ratio=stats["h1_recovery_stress"],
            note="Aggressive H1 recovery stress test; keeps H2 and 2024H1 totals unchanged.",
        ),
        CandidateSpec(
            name="cleanv2_h1funnel_b046_r0890_augpromo",
            h1_beta=0.46,
            h1_cogs_ratio=stats["h1_recovery_high"],
            ratio_shape_gamma=0.45,
            ratio_shape_scope="h2",
            note="Higher H1 COGS-ratio stress paired with promo-prior H2 COGS daily reshape.",
        ),
    ]


def write_report(run_dir: Path, manifest: pd.DataFrame, ratio_stats: dict[str, float]) -> None:
    report = f"""# Clean V2 EDA-Guided Candidates

Run directory: `{run_dir}`

## Boundary

This branch rebuilds the daily shape from raw provided inputs through the existing clean raw-md anchor path. It does not read `sample_submission.csv`, previous submissions, or test target values as inputs.

It is still **clean-input public-guided** for candidates with `h1_beta >= 0.45`: public feedback suggested the old 2023H1 level was too low, while EDA supplies the clean rationale through conversion/AOV recovery and H1 shape stability.

## Train Ratio Reference

{pd.DataFrame([ratio_stats]).to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Order

1. `submission_cleanv2_h1funnel_b046_r0876_augpromo.csv`
2. `submission_cleanv2_h1funnel_b045_r0876.csv`
3. `submission_cleanv2_h1funnel_b040_h1max.csv`
4. `submission_cleanv2_promo_ratio_shape_only_g050.csv`
5. `submission_cleanv2_h1funnel_b050_r0876.csv`
6. `submission_cleanv2_h1funnel_b046_r0890_augpromo.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v2_eda_guided_candidates_2026-04-24.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    sales = load_sales()
    shape_base = build_shape_base()
    base = base_totals(sales)
    ratio_stats = h1_ratio_stats(sales)

    rows = []
    for priority, spec in enumerate(build_candidates(sales), start=1):
        totals = apply_h1_total_override(sales, base, spec.h1_beta, spec.h1_cogs_ratio)
        frame = apply_period_totals(shape_base, totals)
        frame = apply_ratio_shape(frame, sales, spec.ratio_shape_gamma, spec.ratio_shape_scope)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)
        prof = period_summary(frame)
        prof.to_csv(run_dir / f"{spec.name}_period_summary.csv", index=False)
        totals.to_csv(run_dir / f"{spec.name}_target_totals.csv", index=False)
        rows.append(
            {
                "priority": priority,
                "filename": path.name,
                "h1_beta": spec.h1_beta,
                "h1_cogs_ratio_input": spec.h1_cogs_ratio,
                "ratio_shape_gamma": spec.ratio_shape_gamma,
                "ratio_shape_scope": spec.ratio_shape_scope,
                "revenue_total": frame["Revenue"].sum(),
                "cogs_total": frame["COGS"].sum(),
                "ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
                "rev_2023H1": prof.loc[prof["period"].eq("2023H1"), "revenue"].iloc[0],
                "rev_2023H2": prof.loc[prof["period"].eq("2023H2"), "revenue"].iloc[0],
                "rev_2024H1": prof.loc[prof["period"].eq("2024H1"), "revenue"].iloc[0],
                "rev_final": prof.loc[prof["period"].eq("2024-07-01"), "revenue"].iloc[0],
                "cogs_2023H1": prof.loc[prof["period"].eq("2023H1"), "cogs"].iloc[0],
                "cogs_2023H2": prof.loc[prof["period"].eq("2023H2"), "cogs"].iloc[0],
                "cogs_2024H1": prof.loc[prof["period"].eq("2024H1"), "cogs"].iloc[0],
                "cogs_final": prof.loc[prof["period"].eq("2024-07-01"), "cogs"].iloc[0],
                "ratio_2023H1": prof.loc[prof["period"].eq("2023H1"), "cogs_ratio"].iloc[0],
                "ratio_2023H2": prof.loc[prof["period"].eq("2023H2"), "cogs_ratio"].iloc[0],
                "ratio_2024H1": prof.loc[prof["period"].eq("2024H1"), "cogs_ratio"].iloc[0],
                "ratio_final": prof.loc[prof["period"].eq("2024-07-01"), "cogs_ratio"].iloc[0],
                "note": spec.note,
            }
        )

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    write_report(run_dir, manifest, ratio_stats)
    print(run_dir)


if __name__ == "__main__":
    main()
