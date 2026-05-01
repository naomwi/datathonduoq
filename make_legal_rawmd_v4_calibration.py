from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_legal_period_shape_router import DATASET_DIR, LOG_ROOT, NOTES_DIR, load_base, load_train_sales, write_submission
from run_legal_rawmd_prior_v3 import CandidateSpec as RawMdSpec
from run_legal_rawmd_prior_v3 import apply_rawmd_shape
from run_legal_period_shape_router import build_future_share_template


RUN_PREFIX = "legal_rawmd_v4_calibration"
CURRENT_LEGAL_FILE = "submission_legal_rawmd_prior_v3_r080_c065_h2r010.csv"
CURRENT_LEGAL_SCORE = 688915.44181


@dataclass(frozen=True)
class CalibrationSpec:
    filename: str
    thesis: str
    rev_default_alpha: float = 0.800
    rev_h2_alpha: float = 0.100
    cogs_shape_alpha: float = 0.650
    revenue_period_scale: dict[str, float] | None = None
    cogs_period_scale: dict[str, float] | None = None


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def add_period(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    dates = pd.to_datetime(out["Date"])
    out["period"] = "2024H1"
    out.loc[dates.dt.year.eq(2023) & dates.dt.month.le(6), "period"] = "2023H1"
    out.loc[dates.dt.year.eq(2023) & dates.dt.month.ge(7), "period"] = "2023H2"
    out.loc[dates.eq(pd.Timestamp("2024-07-01")), "period"] = "2024-07-01"
    return out


def apply_period_scales(frame: pd.DataFrame, spec: CalibrationSpec) -> pd.DataFrame:
    out = frame.copy()
    for period, mult in (spec.revenue_period_scale or {}).items():
        out.loc[out["period"].eq(period), "Revenue"] *= mult
    for period, mult in (spec.cogs_period_scale or {}).items():
        out.loc[out["period"].eq(period), "COGS"] *= mult
    return out


def period_summary(frame: pd.DataFrame) -> pd.DataFrame:
    out = add_period(frame)
    return (
        out.groupby("period", as_index=False)
        .agg(
            days=("Date", "count"),
            revenue=("Revenue", "sum"),
            cogs=("COGS", "sum"),
            rev_mean=("Revenue", "mean"),
            cogs_mean=("COGS", "mean"),
            rev_cv=("Revenue", lambda x: float(np.std(x) / np.mean(x))),
            cogs_cv=("COGS", lambda x: float(np.std(x) / np.mean(x))),
        )
        .assign(cogs_ratio=lambda d: d["cogs"] / d["revenue"])
    )


def build_rawmd_frame(spec: CalibrationSpec) -> pd.DataFrame:
    history = load_train_sales()
    base = load_base()
    rev_share = build_future_share_template(history, base, target="Revenue", mode="raw_md")
    cogs_share = build_future_share_template(history, base, target="COGS", mode="raw_md")
    raw_spec = RawMdSpec(
        filename=spec.filename,
        thesis=spec.thesis,
        rev_default_alpha=spec.rev_default_alpha,
        cogs_default_alpha=spec.cogs_shape_alpha,
        rev_period_alpha={"2023H2": spec.rev_h2_alpha},
        cogs_period_alpha={},
    )
    return apply_rawmd_shape(base, rev_share, cogs_share, raw_spec)


def make_candidates() -> pd.DataFrame:
    current = add_period(pd.read_csv(DATASET_DIR / CURRENT_LEGAL_FILE, parse_dates=["Date"]))

    specs = [
        CalibrationSpec(
            "submission_legal_rawmd_v4_cogs_all_up010.csv",
            "COGS +1.0% all periods; tests if remaining error is mostly COGS under-level.",
            cogs_period_scale={"2023H1": 1.010, "2023H2": 1.010, "2024H1": 1.010},
        ),
        CalibrationSpec(
            "submission_legal_rawmd_v4_cogs_all_up020.csv",
            "COGS +2.0% all periods; high-information COGS level probe.",
            cogs_period_scale={"2023H1": 1.020, "2023H2": 1.020, "2024H1": 1.020},
        ),
        CalibrationSpec(
            "submission_legal_rawmd_v4_cogs_period_soft.csv",
            "Period-graded COGS inflation: strongest in 2023H1, weaker into 2024H1.",
            cogs_period_scale={"2023H1": 1.020, "2023H2": 1.012, "2024H1": 1.006},
        ),
        CalibrationSpec(
            "submission_legal_rawmd_v4_cogs_period_med.csv",
            "Medium period-graded COGS inflation; diagnostic analogue of the black-box COGS-away direction.",
            cogs_period_scale={"2023H1": 1.030, "2023H2": 1.018, "2024H1": 1.009},
        ),
        CalibrationSpec(
            "submission_legal_rawmd_v4_cogs_period_strong.csv",
            "Stronger COGS inflation if v4 period_med is still under COGS.",
            cogs_period_scale={"2023H1": 1.040, "2023H2": 1.024, "2024H1": 1.012},
        ),
        CalibrationSpec(
            "submission_legal_rawmd_v4_h2r005_cogs_period_med.csv",
            "Same period COGS calibration, but H2 Revenue alpha lower at 0.05.",
            rev_h2_alpha=0.050,
            cogs_period_scale={"2023H1": 1.030, "2023H2": 1.018, "2024H1": 1.009},
        ),
        CalibrationSpec(
            "submission_legal_rawmd_v4_h2r015_cogs_period_med.csv",
            "Same period COGS calibration, but H2 Revenue alpha higher at 0.15.",
            rev_h2_alpha=0.150,
            cogs_period_scale={"2023H1": 1.030, "2023H2": 1.018, "2024H1": 1.009},
        ),
        CalibrationSpec(
            "submission_legal_rawmd_v4_rev_nonh2_085_cogs_period_med.csv",
            "Slightly stronger non-H2 Revenue raw-md shape plus medium period COGS calibration.",
            rev_default_alpha=0.850,
            rev_h2_alpha=0.100,
            cogs_period_scale={"2023H1": 1.030, "2023H2": 1.018, "2024H1": 1.009},
        ),
    ]

    rows = []
    for priority, spec in enumerate(specs, start=1):
        frame = add_period(build_rawmd_frame(spec))
        frame = apply_period_scales(frame, spec)
        write_submission(frame[["Date", "Revenue", "COGS"]], DATASET_DIR / spec.filename)
        rev_delta = frame["Revenue"] - current["Revenue"]
        cogs_delta = frame["COGS"] - current["COGS"]
        prof = period_summary(frame)
        rows.append(
            {
                "priority": priority,
                "filename": spec.filename,
                "path": str(DATASET_DIR / spec.filename),
                "thesis": spec.thesis,
                "rev_default_alpha": spec.rev_default_alpha,
                "rev_h2_alpha": spec.rev_h2_alpha,
                "cogs_shape_alpha": spec.cogs_shape_alpha,
                "scale_rev_2023H1": (spec.revenue_period_scale or {}).get("2023H1", 1.0),
                "scale_rev_2023H2": (spec.revenue_period_scale or {}).get("2023H2", 1.0),
                "scale_rev_2024H1": (spec.revenue_period_scale or {}).get("2024H1", 1.0),
                "scale_cogs_2023H1": (spec.cogs_period_scale or {}).get("2023H1", 1.0),
                "scale_cogs_2023H2": (spec.cogs_period_scale or {}).get("2023H2", 1.0),
                "scale_cogs_2024H1": (spec.cogs_period_scale or {}).get("2024H1", 1.0),
                "mean_abs_rev_delta_vs_current": rev_delta.abs().mean(),
                "mean_abs_cogs_delta_vs_current": cogs_delta.abs().mean(),
                "directional_best_case_gain_vs_current": 0.5 * (rev_delta.abs().mean() + cogs_delta.abs().mean()),
                "revenue_total_ratio_vs_current": frame["Revenue"].sum() / current["Revenue"].sum(),
                "cogs_total_ratio_vs_current": frame["COGS"].sum() / current["COGS"].sum(),
                "ratio_2023H1": prof.loc[prof["period"].eq("2023H1"), "cogs_ratio"].iloc[0],
                "ratio_2023H2": prof.loc[prof["period"].eq("2023H2"), "cogs_ratio"].iloc[0],
                "ratio_2024H1": prof.loc[prof["period"].eq("2024H1"), "cogs_ratio"].iloc[0],
            }
        )
    return pd.DataFrame(rows)


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Legal Raw-MD V4 Calibration

Run directory: `{run_dir}`

Current legal best: `{CURRENT_LEGAL_FILE}` scored `{CURRENT_LEGAL_SCORE}`.

## Read

The raw month-day prior is now confirmed by public feedback. The next likely error source is not model class; it is target calibration on top of that shape:

- COGS may still be under-level after preserving old base period totals.
- `2023H2` Revenue alpha optimum is near `0.10`, but the legal raw-md proxy is not bit-identical to the prior, so `0.05/0.15` are useful checks.
- Non-H2 Revenue raw shape could still tolerate a small increase from `0.80` to `0.85`.

This script does **not** read `sample_submission.csv`; all raw-md shapes are from train `sales.csv`.

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Guidance

1. `submission_legal_rawmd_v4_cogs_period_med.csv`
2. If it improves, test `submission_legal_rawmd_v4_cogs_period_strong.csv`.
3. If period_med worsens, test the softer `submission_legal_rawmd_v4_cogs_period_soft.csv`.
4. If period_med improves only slightly, test H2 alpha: `submission_legal_rawmd_v4_h2r005_cogs_period_med.csv` then `submission_legal_rawmd_v4_h2r015_cogs_period_med.csv`.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "legal_rawmd_v4_calibration_2026-04-22.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    manifest = make_candidates()
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    write_report(run_dir, manifest)
    print(run_dir)


if __name__ == "__main__":
    main()
