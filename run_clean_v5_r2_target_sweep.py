from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_clean_regime_recovery_scenarios import period_summary
from run_clean_v4_r2_frontier_candidates import (
    BASE_FILE,
    DATASET_DIR,
    LOG_ROOT,
    NOTES_DIR,
    blend_level,
    blend_shape_preserve_totals,
    load_submission,
)
from run_transaction_decomposition_v2 import write_submission


RUN_PREFIX = "clean_v5_r2_target_sweep"
TXN_MONTH_DONOR = "submission_txndecomp_v2_monthshape_r18_c12.csv"


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    mode: str
    alpha: float
    note: str


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def add_period(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out["period"] = out["Date"].dt.year.astype(str) + np.where(out["Date"].dt.month.le(6), "H1", "H2")
    out.loc[out["Date"].eq(pd.Timestamp("2024-07-01")), "period"] = "2024-07-01"
    return out


def normalize_to_total(values: pd.Series, total: float) -> pd.Series:
    current = float(values.sum())
    if current <= 0:
        return pd.Series(total / len(values), index=values.index)
    return values * total / current


def period_total_shape_mix(base: pd.DataFrame, donor: pd.DataFrame, alpha: float, shape_alpha: float = 1.0) -> pd.DataFrame:
    merged = add_period(base).merge(add_period(donor), on=["Date", "period"], suffixes=("_base", "_donor"))
    out = pd.DataFrame({"Date": merged["Date"], "period": merged["period"]})
    for target in ["Revenue", "COGS"]:
        out[target] = np.nan
        for _, idx in merged.groupby("period").groups.items():
            idx = list(idx)
            base_values = merged.loc[idx, f"{target}_base"].astype(float)
            donor_values = merged.loc[idx, f"{target}_donor"].astype(float)
            target_total = (1.0 - alpha) * float(base_values.sum()) + alpha * float(donor_values.sum())
            donor_shape = normalize_to_total(donor_values, float(base_values.sum()))
            shape_values = (1.0 - shape_alpha) * base_values + shape_alpha * donor_shape
            out.loc[idx, target] = normalize_to_total(shape_values, target_total)
    return out[["Date", "Revenue", "COGS"]]


def build_specs() -> list[CandidateSpec]:
    specs: list[CandidateSpec] = []
    for alpha in [0.35, 0.50, 0.65, 0.80, 1.00]:
        specs.append(
            CandidateSpec(
                name=f"cleanv5_r2_txnshape_preserve_a{int(alpha * 1000):03d}",
                mode="shape_preserve",
                alpha=alpha,
                note="Increase transaction-derived intra-period shape while preserving c110 period totals.",
            )
        )
    for alpha in [0.10, 0.20, 0.30, 0.40, 0.50]:
        specs.append(
            CandidateSpec(
                name=f"cleanv5_r2_level_to_txnmonth_a{int(alpha * 1000):03d}",
                mode="level_blend",
                alpha=alpha,
                note="Blend c110 directly toward txn-month donor to map the R2-vs-level tradeoff.",
            )
        )
    for alpha in [0.10, 0.20, 0.30, 0.40]:
        specs.append(
            CandidateSpec(
                name=f"cleanv5_r2_periodlevel_txnshape_a{int(alpha * 1000):03d}",
                mode="period_total_shape_mix",
                alpha=alpha,
                note="Use full txn-month daily shape, but move only period totals gradually toward txn-month donor.",
            )
        )
    return specs


def build_candidate(base: pd.DataFrame, donor: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    if spec.mode == "shape_preserve":
        return blend_shape_preserve_totals(base, donor, spec.alpha, ("Revenue", "COGS"))
    if spec.mode == "level_blend":
        return blend_level(base, donor, spec.alpha)
    if spec.mode == "period_total_shape_mix":
        return period_total_shape_mix(base, donor, spec.alpha, shape_alpha=1.0)
    raise ValueError(f"Unknown mode: {spec.mode}")


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Clean V5 R2 Target Sweep

Run directory: `{run_dir}`

## Goal

Map how far we must move from `c110` toward transaction-month shape/level to reach public-like R2 around 0.72.

## Boundary

This is a research sweep. The transaction-month donor uses provided transaction tables and preserves or partially moves period totals depending on mode. Do not present the `level_blend` candidates as strict clean final without explaining their calibration source.

## Candidate Manifest

{manifest.to_markdown(index=False)}
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v5_r2_target_sweep_2026-04-24.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    base = load_submission(BASE_FILE)
    donor = load_submission(TXN_MONTH_DONOR)
    rows = []
    for priority, spec in enumerate(build_specs(), start=1):
        frame = build_candidate(base, donor, spec)
        if len(frame) != len(base):
            raise ValueError(f"{spec.name} row count mismatch")
        if frame[["Revenue", "COGS"]].isna().any().any():
            raise ValueError(f"{spec.name} has NaN values")
        if (frame[["Revenue", "COGS"]] < 0).any().any():
            raise ValueError(f"{spec.name} has negative values")

        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame, path)
        prof = period_summary(frame)
        prof.to_csv(run_dir / f"{spec.name}_period_summary.csv", index=False)
        rows.append(
            {
                "priority": priority,
                "filename": path.name,
                "mode": spec.mode,
                "alpha": spec.alpha,
                "revenue_total": float(frame["Revenue"].sum()),
                "cogs_total": float(frame["COGS"].sum()),
                "ratio_total": float(frame["COGS"].sum() / frame["Revenue"].sum()),
                "max_revenue": float(frame["Revenue"].max()),
                "max_cogs": float(frame["COGS"].max()),
                "note": spec.note,
            }
        )
    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    write_report(run_dir, manifest)
    print(run_dir)
    print(manifest[["priority", "filename", "mode", "alpha", "revenue_total", "cogs_total"]].to_string(index=False))


if __name__ == "__main__":
    main()
