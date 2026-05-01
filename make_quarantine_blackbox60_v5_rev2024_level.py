from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_cogs_inverse_v26 import cogs_ratio_away_from_sample
from make_publiconly_sample_periodwise_shape_v35 import BASE_COGS_ALPHA, BASE_REV_ALPHA, periodwise_shape
from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, align_sample_shape, period_summary
from make_publiconly_sample_targetwise_v31 import PRE_SAMPLE_BEST_FILE
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_blackbox60_v5_rev2024_level"
CURRENT_BEST_FILE = "submission_qbb60v4_level_rev2024h1_up030.csv"
CURRENT_BEST_SCORE = 680506.89709


@dataclass(frozen=True)
class Spec:
    name: str
    rev_scale_2024h1: float
    cogs_scale_2024h1: float
    rev_scale_2023h1: float
    thesis: str


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def base_frame(pre_base: pd.DataFrame, shape_both: pd.DataFrame, sample: pd.DataFrame) -> pd.DataFrame:
    shaped = periodwise_shape(pre_base, shape_both, {"2023H2": 0.100, "2024H1": 1.000}, {})
    return cogs_ratio_away_from_sample(add_segments(shaped), sample, 0.250)


def apply_scales(frame: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    out = add_segments(frame)
    out.loc[out["period"].eq("2024H1"), "Revenue"] *= spec.rev_scale_2024h1
    out.loc[out["period"].eq("2024H1"), "COGS"] *= spec.cogs_scale_2024h1
    out.loc[out["period"].eq("2023H1"), "Revenue"] *= spec.rev_scale_2023h1
    return out[["Date", "Revenue", "COGS", "period"]]


def specs() -> list[Spec]:
    return [
        Spec("qbb60v5_rev2024h1_up040", 1.040, 1.000, 1.000, "Continue 2024H1 Revenue level from +3% to +4%."),
        Spec("qbb60v5_rev2024h1_up050", 1.050, 1.000, 1.000, "Continue 2024H1 Revenue level to +5%."),
        Spec("qbb60v5_rev2024h1_up060", 1.060, 1.000, 1.000, "High-information +6% 2024H1 Revenue level."),
        Spec("qbb60v5_rev2024h1_up080", 1.080, 1.000, 1.000, "Aggressive +8% 2024H1 Revenue level; jump probe."),
        Spec("qbb60v5_rev2024h1_up040_cogsdown020", 1.040, 0.980, 1.000, "+4% Revenue 2024H1 plus -2% COGS 2024H1."),
        Spec("qbb60v5_rev2024h1_up050_cogsdown020", 1.050, 0.980, 1.000, "+5% Revenue 2024H1 plus -2% COGS 2024H1."),
        Spec("qbb60v5_rev2024h1_up040_cogsup020", 1.040, 1.020, 1.000, "+4% Revenue 2024H1 plus +2% COGS 2024H1."),
        Spec("qbb60v5_rev2024h1_up050_cogsup020", 1.050, 1.020, 1.000, "+5% Revenue 2024H1 plus +2% COGS 2024H1."),
        Spec("qbb60v5_rev2024h1_up040_rev2023h1_up020", 1.040, 1.000, 1.020, "+4% Revenue 2024H1 plus +2% Revenue 2023H1."),
        Spec("qbb60v5_rev2024h1_up050_rev2023h1_up020", 1.050, 1.000, 1.020, "+5% Revenue 2024H1 plus +2% Revenue 2023H1."),
    ]


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Quarantine Blackbox 60x V5 Revenue 2024H1 Level

Run directory: `{run_dir}`

## Status

This is **not clean**. It is public black-box exploration only.

Current best:

- `{CURRENT_BEST_FILE}` = `{CURRENT_BEST_SCORE}`

## Read

`+3% Revenue 2024H1` improved from `682039.28310` to `680506.89709`, so the missing signal is period-level Revenue in 2024H1, not more daily shape.

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Order

1. `submission_qbb60v5_rev2024h1_up050.csv`
2. If it improves, submit `submission_qbb60v5_rev2024h1_up060.csv`
3. If +5 worsens, submit `submission_qbb60v5_rev2024h1_up040.csv`
4. Once Revenue level optimum is bracketed, test COGS combo around the best Revenue level.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_blackbox60_v5_rev2024_level_2026-04-23.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    pre_base = add_segments(pd.read_csv(DATASET_DIR / PRE_SAMPLE_BEST_FILE, parse_dates=["Date"]))
    current = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    sample = add_segments(pd.read_csv(DATASET_DIR / SAMPLE_FILE, parse_dates=["Date"]))
    shape_both = align_sample_shape(pre_base, sample, ("Revenue", "COGS"))
    base = base_frame(pre_base, shape_both, sample)

    rows = []
    for priority, spec in enumerate(specs(), start=1):
        frame = apply_scales(base, spec)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)
        delta_rev = frame["Revenue"] - current["Revenue"]
        delta_cogs = frame["COGS"] - current["COGS"]
        prof = period_summary(frame)
        rows.append(
            {
                "priority": priority,
                "filename": path.name,
                "thesis": spec.thesis,
                "rev_scale_2024H1": spec.rev_scale_2024h1,
                "cogs_scale_2024H1": spec.cogs_scale_2024h1,
                "rev_scale_2023H1": spec.rev_scale_2023h1,
                "mean_abs_rev_delta_vs_current": delta_rev.abs().mean(),
                "mean_abs_cogs_delta_vs_current": delta_cogs.abs().mean(),
                "movement": 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
                "revenue_total_ratio_vs_current": frame["Revenue"].sum() / current["Revenue"].sum(),
                "cogs_total_ratio_vs_current": frame["COGS"].sum() / current["COGS"].sum(),
                "ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
                "ratio_2023H1": prof.loc[prof["period"].eq("2023H1"), "ratio"].iloc[0],
                "ratio_2023H2": prof.loc[prof["period"].eq("2023H2"), "ratio"].iloc[0],
                "ratio_2024H1": prof.loc[prof["period"].eq("2024H1"), "ratio"].iloc[0],
            }
        )

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_best_period_summary.csv", index=False)
    write_report(run_dir, manifest)
    print(run_dir)


if __name__ == "__main__":
    main()
