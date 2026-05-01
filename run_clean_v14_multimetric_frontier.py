from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from analyze_clean_v2_train_evidence import build_daily_panel
from run_clean_regime_recovery_scenarios import load_sales
from run_clean_v10_h1_regime_shape import sanity_check
from run_clean_v13_daily_peak_allocator import (
    CandidateSpec as AllocatorSpec,
    apply_daily_allocator,
    build_base_frames,
)
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v14_multimetric_frontier"


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    base_kind: str
    revenue_alpha: float
    cogs_alpha: float
    scope: str
    note: str


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def apply_target_specific_allocator(base: pd.DataFrame, daily: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    out = base.copy()
    for target, alpha in [("Revenue", spec.revenue_alpha), ("COGS", spec.cogs_alpha)]:
        if alpha <= 0:
            continue
        out = apply_daily_allocator(
            out,
            daily,
            AllocatorSpec(
                name=f"{spec.name}_{target.lower()}",
                base_kind=spec.base_kind,
                prior_kind="mddow_recent",
                alpha=alpha,
                scope=spec.scope,
                targets=(target,),
                note=spec.note,
            ),
        )
    return out[["Date", "Revenue", "COGS"]]


def build_specs() -> list[CandidateSpec]:
    specs: list[CandidateSpec] = []
    for base_kind in ["v12_month", "v10"]:
        alpha_grid = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
        if base_kind == "v10":
            alpha_grid += [0.35, 0.40, 0.45, 0.50, 0.60, 0.70, 0.80]
        for alpha in alpha_grid:
            suffix = f"{int(alpha * 1000):03d}"
            specs.append(
                CandidateSpec(
                    name=f"cleanv14_{base_kind}_all_mddow_both_a{suffix}",
                    base_kind=base_kind,
                    revenue_alpha=alpha,
                    cogs_alpha=alpha,
                    scope="all_full_months",
                    note="All-month month-day/day-of-week allocator on both targets; preserves each month total.",
                )
            )
        target_pairs = [(0.10, 0.20), (0.15, 0.25), (0.20, 0.10), (0.25, 0.15)]
        if base_kind == "v10":
            target_pairs += [
                (0.20, 0.30),
                (0.20, 0.35),
                (0.225, 0.325),
                (0.225, 0.35),
                (0.25, 0.325),
                (0.25, 0.35),
                (0.275, 0.325),
                (0.275, 0.35),
                (0.275, 0.375),
                (0.30, 0.35),
                (0.30, 0.375),
                (0.30, 0.40),
                (0.35, 0.25),
                (0.40, 0.30),
                (0.45, 0.55),
                (0.50, 0.60),
                (0.60, 0.45),
            ]
        for revenue_alpha, cogs_alpha in target_pairs:
            specs.append(
                CandidateSpec(
                    name=(
                        f"cleanv14_{base_kind}_all_mddow_"
                        f"r{int(revenue_alpha * 1000):03d}_c{int(cogs_alpha * 1000):03d}"
                    ),
                    base_kind=base_kind,
                    revenue_alpha=revenue_alpha,
                    cogs_alpha=cogs_alpha,
                    scope="all_full_months",
                    note="Target-specific allocator strength to balance MAE, RMSE, and R2.",
                )
            )
    return specs


def summarize(frame: pd.DataFrame, base: pd.DataFrame, spec: CandidateSpec, filename: str) -> dict[str, object]:
    delta = frame[["Revenue", "COGS"]] - base[["Revenue", "COGS"]]
    return {
        "filename": filename,
        "base_kind": spec.base_kind,
        "scope": spec.scope,
        "revenue_alpha": spec.revenue_alpha,
        "cogs_alpha": spec.cogs_alpha,
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


def month_total_audit(frame: pd.DataFrame, base: pd.DataFrame, filename: str) -> pd.DataFrame:
    work = frame.copy()
    work["Date"] = pd.to_datetime(work["Date"])
    work["year"] = work["Date"].dt.year
    work["month"] = work["Date"].dt.month
    base_work = base.copy()
    base_work["Date"] = pd.to_datetime(base_work["Date"])
    base_work["year"] = base_work["Date"].dt.year
    base_work["month"] = base_work["Date"].dt.month

    rows = []
    for (year, month), group in work.groupby(["year", "month"], sort=False):
        base_group = base_work.loc[base_work["year"].eq(year) & base_work["month"].eq(month)]
        rows.append(
            {
                "filename": filename,
                "year": year,
                "month": month,
                "revenue_delta": float(group["Revenue"].sum() - base_group["Revenue"].sum()),
                "cogs_delta": float(group["COGS"].sum() - base_group["COGS"].sum()),
                "max_revenue": float(group["Revenue"].max()),
                "max_cogs": float(group["COGS"].max()),
            }
        )
    return pd.DataFrame(rows)


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Clean V14 Multimetric Frontier

Run directory: `{run_dir}`

## Boundary

This is **clean-input public-guided research**. It rebuilds deterministic V10/V12 bases from raw train inputs and never reads `sample_submission.csv`, previous submission files, quarantine files, or test targets as inputs.

## Hypothesis

`submission_cleanv13_v12month_all_mddow_a015.csv = 671121.37456` confirms a real daily allocation signal. V14 sweeps that same train-derived month-day/day-of-week allocator across:

- V12 monthly-funnel base, which has better RMSE/R2 proxy.
- V10 base, which has better public MAE.
- Target-specific strengths, because Revenue and COGS may prefer different daily sharpness.

Every candidate preserves each affected month total, so this layer changes daily peak placement, not level.

## Candidate Manifest

{manifest.to_markdown(index=False)}
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v14_multimetric_frontier_2026-04-29.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    daily = build_daily_panel()
    sales = load_sales()
    bases = build_base_frames(run_dir, daily, sales)

    rows = []
    audits = []
    for priority, spec in enumerate(build_specs(), start=1):
        base = bases[spec.base_kind].reset_index(drop=True)
        frame = apply_target_specific_allocator(base, daily, spec)
        sanity_check(frame, spec.name)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame, path)
        rows.append({"priority": priority, **summarize(frame, base, spec, path.name)})
        audits.append(month_total_audit(frame, base, path.name))

    manifest = pd.DataFrame(rows)
    month_audit = pd.concat(audits, ignore_index=True)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    month_audit.to_csv(run_dir / "month_total_audit.csv", index=False)
    write_report(run_dir, manifest)

    print(run_dir)
    print(
        manifest[
            [
                "priority",
                "filename",
                "base_kind",
                "revenue_alpha",
                "cogs_alpha",
                "mean_abs_revenue_delta",
                "mean_abs_cogs_delta",
                "delta_revenue_total",
                "delta_cogs_total",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
