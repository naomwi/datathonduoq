from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_leaderboard_sprint import (
    FORECAST_END,
    FORECAST_START,
    apply_future_context_policy,
    apply_future_hierarchy_policy,
    apply_future_price_policy,
    apply_future_promo_policy,
    recursive_forecast,
)
from train_recursive_forecast import TRAIN_END, ensure_inputs, get_candidate_feature_sets
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "cleanroom_rawmd_pipeline"


ANCHOR_CANDIDATE = {
    "candidate_id": "cleanroom_catboost_md2y_core_recencyexp20",
    "kind": "model",
    "model_family": "catboost",
    "revenue_experiment": "curated_promo_cogs",
    "cogs_experiment": "curated_promo_cogs",
    "promo_future_policy": "seasonal_month_day_recent_2y",
    "context_future_policy": "zero",
    "price_future_policy": "zero",
    "hierarchy_future_policy": "zero",
    "cogs_postprocess_variant": "blend60_clip_q99",
    "sample_weight_mode": "exp_years",
    "sample_weight_decay": 0.20,
}


@dataclass(frozen=True)
class RawMdConfig:
    name: str
    revenue_alpha_non_h2: float
    revenue_alpha_h2: float
    cogs_alpha: float
    cogs_period_scale: dict[str, float]
    note: str


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
    out["period"] = "other"
    out.loc[out["year"].eq(2023) & out["month"].le(6), "period"] = "2023H1"
    out.loc[out["year"].eq(2023) & out["month"].ge(7), "period"] = "2023H2"
    out.loc[out["year"].eq(2024) & out["month"].le(6), "period"] = "2024H1"
    out.loc[out["Date"].eq(pd.Timestamp("2024-07-01")), "period"] = "2024-07-01"
    return out


def build_clean_anchor(feature_store: pd.DataFrame, base: pd.DataFrame, feature_sets: dict[str, list[str]]) -> pd.DataFrame:
    candidate = ANCHOR_CANDIDATE
    adjusted_base = apply_future_promo_policy(base, TRAIN_END, str(candidate["promo_future_policy"]))
    adjusted_base = apply_future_context_policy(adjusted_base, TRAIN_END, str(candidate["context_future_policy"]))
    adjusted_base = apply_future_price_policy(adjusted_base, TRAIN_END, str(candidate["price_future_policy"]))
    adjusted_base = apply_future_hierarchy_policy(adjusted_base, TRAIN_END, str(candidate["hierarchy_future_policy"]))
    preds = recursive_forecast(
        feature_store=feature_store,
        full_base=adjusted_base,
        train_end_date=TRAIN_END,
        forecast_start=FORECAST_START,
        forecast_end=FORECAST_END,
        revenue_features=feature_sets[str(candidate["revenue_experiment"])],
        cogs_features=feature_sets[str(candidate["cogs_experiment"])],
        cogs_postprocess_variant=str(candidate["cogs_postprocess_variant"]),
        model_family=str(candidate["model_family"]),
        sample_weight_mode=str(candidate["sample_weight_mode"]),
        sample_weight_decay=float(candidate["sample_weight_decay"]),
    )
    out = preds.rename(columns={"Revenue_pred": "Revenue", "COGS_pred": "COGS"})[["Date", "Revenue", "COGS"]]
    return add_period_columns(out)


def build_rawmd_share(history: pd.DataFrame, future: pd.DataFrame, target: str) -> pd.Series:
    hist = add_period_columns(history.loc[history["Date"].dt.year.between(2013, 2022)].copy())
    hist = hist.loc[hist[target].notna()].copy()
    rows = []
    for (year, half), group in hist.groupby(["year", "half"]):
        total = group[target].sum()
        if total <= 0:
            continue
        tmp = group[["month_day", "month"]].copy()
        tmp["year"] = year
        tmp["half"] = half
        tmp["daily_share"] = group[target].to_numpy() / total
        rows.append(tmp)
    shares = pd.concat(rows, ignore_index=True)
    md = shares.groupby(["half", "month_day"], as_index=False).agg(md_share=("daily_share", "mean"))
    month = shares.groupby(["half", "month"], as_index=False).agg(month_share=("daily_share", "mean"))

    out = pd.Series(index=future.index, dtype=float)
    for period, group in future.groupby("period"):
        if period == "2024-07-01":
            out.loc[group.index] = 1.0
            continue
        half = "H1" if period in {"2023H1", "2024H1"} else "H2"
        tmp = group[["month_day", "month"]].copy()
        tmp["half"] = half
        tmp = tmp.merge(md, on=["half", "month_day"], how="left")
        tmp = tmp.merge(month, on=["half", "month"], how="left")
        values = tmp["md_share"].fillna(tmp["month_share"]).fillna(1.0 / len(group)).clip(lower=1e-9)
        values = values / values.sum()
        out.loc[group.index] = values.to_numpy()
    return out


def apply_rawmd_config(anchor: pd.DataFrame, history: pd.DataFrame, config: RawMdConfig) -> pd.DataFrame:
    future = add_period_columns(anchor)
    rev_share = build_rawmd_share(history, future, "Revenue")
    cogs_share = build_rawmd_share(history, future, "COGS")
    out = future[["Date", "Revenue", "COGS", "period"]].copy()
    for period, idx in future.groupby("period").groups.items():
        idx = list(idx)
        if period == "2024-07-01":
            continue
        revenue_alpha = config.revenue_alpha_h2 if period == "2023H2" else config.revenue_alpha_non_h2
        cogs_alpha = config.cogs_alpha
        rev_total = anchor.loc[idx, "Revenue"].sum()
        cogs_total = anchor.loc[idx, "COGS"].sum()
        rev_donor = rev_share.loc[idx].to_numpy() * rev_total
        cogs_donor = cogs_share.loc[idx].to_numpy() * cogs_total
        out.loc[idx, "Revenue"] = (1.0 - revenue_alpha) * anchor.loc[idx, "Revenue"].to_numpy() + revenue_alpha * rev_donor
        out.loc[idx, "COGS"] = (1.0 - cogs_alpha) * anchor.loc[idx, "COGS"].to_numpy() + cogs_alpha * cogs_donor
        out.loc[idx, "COGS"] *= config.cogs_period_scale.get(period, 1.0)
    return out[["Date", "Revenue", "COGS", "period"]]


def period_summary(frame: pd.DataFrame) -> pd.DataFrame:
    prof = add_period_columns(frame)
    return (
        prof.groupby("period", as_index=False)
        .agg(days=("Date", "count"), revenue=("Revenue", "sum"), cogs=("COGS", "sum"))
        .assign(cogs_ratio=lambda d: d["cogs"] / d["revenue"])
    )


def write_report(run_dir: Path, manifest: pd.DataFrame, anchor_summary: pd.DataFrame) -> None:
    report = f"""# Clean-Room Raw Month-Day Pipeline

Run directory: `{run_dir}`

## Audit Standard

This is the clean-room version of the raw month-day insight.

It does not read:

- `sample_submission.csv` numeric `Revenue` / `COGS`;
- any `sales_test.csv` target values;
- any previous `submission_*.csv` as an input anchor.

It does read only raw provided files through `ensure_inputs()` and rebuilds the model anchor inside this script.

## Roundtable Decision

Business analyst: present the method as a calendar/seasonality allocation correction, not as leaderboard probing.

Data scientist: prove H1/H2 stability from `sales.csv` train by normalized month-day shares; use weaker H2 regularization because H2 historical shape is less stable.

ML engineer: regenerate the CatBoost recency anchor from raw tables, then apply raw-md correction in memory. No submission file is used as a feature source.

Checker: final source package must exclude the old `sample_*` and `publiconly_*` scripts, or place them in a clearly quarantined research folder not used by the final run.

## Anchor Period Summary

{anchor_summary.to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Suggested Clean Submission

Use `dataset/submission_cleanroom_rawmd_r080_c065_h2r010_cogsmed.csv` only if we want the cleanest defensible version. Its score may differ from the current 687k lineage because the anchor is regenerated from the model instead of loaded from public-tuned submissions.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_room_roundtable_rawmd_2026-04-22.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    anchor = build_clean_anchor(feature_store, base, feature_sets)
    history = feature_store.loc[feature_store["Date"] <= TRAIN_END, ["Date", "Revenue", "COGS"]].copy()

    configs = [
        RawMdConfig(
            name="cleanroom_rawmd_r080_c065_h2r010_cogsmed",
            revenue_alpha_non_h2=0.80,
            revenue_alpha_h2=0.10,
            cogs_alpha=0.65,
            cogs_period_scale={"2023H1": 1.030, "2023H2": 1.018, "2024H1": 1.009},
            note="Clean-room analogue of current best insight; alpha values should be justified as validation/calibration.",
        ),
        RawMdConfig(
            name="cleanroom_rawmd_r080_c065_h2r010_nocogsscale",
            revenue_alpha_non_h2=0.80,
            revenue_alpha_h2=0.10,
            cogs_alpha=0.65,
            cogs_period_scale={},
            note="Same clean raw-md correction without public-calibrated COGS period scaling.",
        ),
        RawMdConfig(
            name="cleanroom_rawmd_r070_c060_h2r020_conservative",
            revenue_alpha_non_h2=0.70,
            revenue_alpha_h2=0.20,
            cogs_alpha=0.60,
            cogs_period_scale={},
            note="More conservative config for report if strict train-only validation does not support aggressive alpha.",
        ),
    ]

    rows = []
    anchor_submission = anchor[["Date", "Revenue", "COGS"]].copy()
    write_submission(anchor_submission, DATASET_DIR / "submission_cleanroom_anchor_recencyexp20.csv")
    candidate_frames: dict[str, pd.DataFrame] = {}
    for priority, config in enumerate(configs, start=1):
        frame = apply_rawmd_config(anchor, history, config)
        candidate_frames[config.name] = frame.copy()
        path = DATASET_DIR / f"submission_{config.name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)
        rev_delta = frame["Revenue"] - anchor["Revenue"]
        cogs_delta = frame["COGS"] - anchor["COGS"]
        rows.append(
            {
                "priority": priority,
                "filename": path.name,
                "path": str(path),
                "revenue_alpha_non_h2": config.revenue_alpha_non_h2,
                "revenue_alpha_h2": config.revenue_alpha_h2,
                "cogs_alpha": config.cogs_alpha,
                "cogs_scale_2023H1": config.cogs_period_scale.get("2023H1", 1.0),
                "cogs_scale_2023H2": config.cogs_period_scale.get("2023H2", 1.0),
                "cogs_scale_2024H1": config.cogs_period_scale.get("2024H1", 1.0),
                "mean_abs_rev_delta_vs_anchor": rev_delta.abs().mean(),
                "mean_abs_cogs_delta_vs_anchor": cogs_delta.abs().mean(),
                "revenue_total_ratio_vs_anchor": frame["Revenue"].sum() / anchor["Revenue"].sum(),
                "cogs_total_ratio_vs_anchor": frame["COGS"].sum() / anchor["COGS"].sum(),
                "note": config.note,
            }
        )

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(anchor).to_csv(run_dir / "anchor_period_summary.csv", index=False)
    for config in configs:
        frame = candidate_frames[config.name]
        period_summary(frame).to_csv(run_dir / f"{config.name}_period_summary.csv", index=False)
    write_report(run_dir, manifest, period_summary(anchor))
    print(run_dir)


if __name__ == "__main__":
    main()
