from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_clean_regime_recovery_scenarios import period_summary
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v4_r2_frontier_candidates"
BASE_FILE = "submission_cleanv3_funnel_c110_h1r0876.csv"
C10_FILE = "submission_cleanv3_head_funnel_last_c10_h1only_r0876.csv"


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    mode: str
    donor_file: str
    alpha: float
    note: str


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def load_submission(filename: str) -> pd.DataFrame:
    path = DATASET_DIR / filename
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, parse_dates=["Date"])
    return frame[["Date", "Revenue", "COGS"]].copy()


def add_period(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out["period"] = out["Date"].dt.year.astype(str) + np.where(out["Date"].dt.month.le(6), "H1", "H2")
    out.loc[out["Date"].eq(pd.Timestamp("2024-07-01")), "period"] = "2024-07-01"
    return out


def period_normalize(values: pd.Series, base_total: float) -> pd.Series:
    current = float(values.sum())
    if current <= 0:
        return pd.Series(base_total / len(values), index=values.index)
    return values * (base_total / current)


def blend_level(base: pd.DataFrame, donor: pd.DataFrame, alpha: float) -> pd.DataFrame:
    merged = base.merge(donor, on="Date", suffixes=("_base", "_donor"))
    out = pd.DataFrame({"Date": merged["Date"]})
    for target in ["Revenue", "COGS"]:
        out[target] = (1.0 - alpha) * merged[f"{target}_base"] + alpha * merged[f"{target}_donor"]
    return out


def blend_shape_preserve_totals(base: pd.DataFrame, donor: pd.DataFrame, alpha: float, targets: tuple[str, ...]) -> pd.DataFrame:
    merged = add_period(base).merge(add_period(donor), on=["Date", "period"], suffixes=("_base", "_donor"))
    out = pd.DataFrame({"Date": merged["Date"], "period": merged["period"]})
    for target in ["Revenue", "COGS"]:
        out[target] = merged[f"{target}_base"].astype(float)

    for period, idx in merged.groupby("period").groups.items():
        idx = list(idx)
        for target in targets:
            base_values = merged.loc[idx, f"{target}_base"].astype(float)
            donor_values = merged.loc[idx, f"{target}_donor"].astype(float)
            base_total = float(base_values.sum())
            donor_scaled = period_normalize(donor_values, base_total)
            blended = (1.0 - alpha) * base_values + alpha * donor_scaled
            out.loc[idx, target] = period_normalize(blended, base_total)
    return out[["Date", "Revenue", "COGS"]]


def build_specs() -> list[CandidateSpec]:
    return [
        CandidateSpec(
            name="cleanv4_r2_level_c110_to_c10_a025",
            mode="level_blend",
            donor_file=C10_FILE,
            alpha=0.25,
            note="Small move from public-best c110 toward c10, which has better public-like RMSE/R2.",
        ),
        CandidateSpec(
            name="cleanv4_r2_level_c110_to_c10_a050",
            mode="level_blend",
            donor_file=C10_FILE,
            alpha=0.50,
            note="Midpoint on MAE/R2 frontier between c110 and c10.",
        ),
        CandidateSpec(
            name="cleanv4_r2_level_c110_to_c10_a075",
            mode="level_blend",
            donor_file=C10_FILE,
            alpha=0.75,
            note="Aggressive R2 move toward c10 while staying inside the known clean-public band.",
        ),
        CandidateSpec(
            name="cleanv4_r2_shape_legalrawmd_a010_preserve",
            mode="shape_preserve_both",
            donor_file="submission_legal_rawmd_prior_v3_r080_c065_h2r010.csv",
            alpha=0.10,
            note="Borrow only daily shape from legal raw-md prior; preserve c110 period totals.",
        ),
        CandidateSpec(
            name="cleanv4_r2_shape_legalrawmd_a020_preserve",
            mode="shape_preserve_both",
            donor_file="submission_legal_rawmd_prior_v3_r080_c065_h2r010.csv",
            alpha=0.20,
            note="Stronger daily-shape borrow from legal raw-md prior; preserve period totals.",
        ),
        CandidateSpec(
            name="cleanv4_r2_shape_cleanroom_a010_preserve",
            mode="shape_preserve_both",
            donor_file="submission_cleanroom_rawmd_r070_c060_h2r020_conservative.csv",
            alpha=0.10,
            note="Strict-clean raw-md daily-shape borrow; preserve c110 period totals.",
        ),
        CandidateSpec(
            name="cleanv4_r2_shape_cleanroom_a020_preserve",
            mode="shape_preserve_both",
            donor_file="submission_cleanroom_rawmd_r070_c060_h2r020_conservative.csv",
            alpha=0.20,
            note="Stronger strict-clean shape borrow; preserve c110 period totals.",
        ),
        CandidateSpec(
            name="cleanv4_r2_shape_txnmonth_a010_preserve",
            mode="shape_preserve_both",
            donor_file="submission_txndecomp_v2_monthshape_r18_c12.csv",
            alpha=0.10,
            note="Research shape donor with strong public-like R2; preserve c110 period totals.",
        ),
        CandidateSpec(
            name="cleanv4_r2_shape_txnmonth_a020_preserve",
            mode="shape_preserve_both",
            donor_file="submission_txndecomp_v2_monthshape_r18_c12.csv",
            alpha=0.20,
            note="Stronger transaction-month shape borrow; preserve c110 period totals.",
        ),
        CandidateSpec(
            name="cleanv4_r2_level025_shape_cleanroom015",
            mode="level025_shape_cleanroom015",
            donor_file="submission_cleanroom_rawmd_r070_c060_h2r020_conservative.csv",
            alpha=0.15,
            note="Hybrid: small c10 level move plus strict-clean shape smoothing, period totals after level move preserved.",
        ),
    ]


def build_candidate(base: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    donor = load_submission(spec.donor_file)
    if spec.mode == "level_blend":
        return blend_level(base, donor, spec.alpha)
    if spec.mode == "shape_preserve_both":
        return blend_shape_preserve_totals(base, donor, spec.alpha, ("Revenue", "COGS"))
    if spec.mode == "level025_shape_cleanroom015":
        c10 = load_submission(C10_FILE)
        level = blend_level(base, c10, 0.25)
        return blend_shape_preserve_totals(level, donor, spec.alpha, ("Revenue", "COGS"))
    raise ValueError(f"Unknown mode: {spec.mode}")


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Clean V4 R2 Frontier Candidates

Run directory: `{run_dir}`

## Goal

Improve final-score safety by lifting public-like R2 and reducing RMSE while keeping public MAE close to the current clean best.

## Base

- Base file: `{BASE_FILE}`
- R2 level donor: `{C10_FILE}`

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Suggested Test Order

1. `submission_cleanv4_r2_level_c110_to_c10_a025.csv`
2. `submission_cleanv4_r2_level025_shape_cleanroom015.csv`
3. `submission_cleanv4_r2_shape_cleanroom_a010_preserve.csv`
4. `submission_cleanv4_r2_level_c110_to_c10_a050.csv`

Interpretation: if level blend improves or holds MAE, move toward c10. If shape-preserve improves, R2 is coming from daily allocation rather than period level.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v4_r2_frontier_candidates_2026-04-24.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    base = load_submission(BASE_FILE)
    rows = []
    for priority, spec in enumerate(build_specs(), start=1):
        try:
            frame = build_candidate(base, spec)
        except FileNotFoundError as exc:
            rows.append(
                {
                    "priority": priority,
                    "filename": f"submission_{spec.name}.csv",
                    "status": f"skipped_missing_donor:{exc}",
                    "mode": spec.mode,
                    "donor_file": spec.donor_file,
                    "alpha": spec.alpha,
                    "note": spec.note,
                }
            )
            continue

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
                "status": "written",
                "mode": spec.mode,
                "donor_file": spec.donor_file,
                "alpha": spec.alpha,
                "rows": len(frame),
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
    print(manifest[["priority", "filename", "status", "mode", "alpha"]].to_string(index=False))


if __name__ == "__main__":
    main()
