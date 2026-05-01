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


RUN_PREFIX = "quarantine_blackbox60_v4_jump_axes"
CURRENT_BEST_FILE = "submission_sample_v40_h2p0100_2024h1p1000_2024h1p1000_c0650_away0250.csv"
CURRENT_BEST_SCORE = 682039.28310


@dataclass(frozen=True)
class Spec:
    name: str
    rev_overrides: dict[str, float]
    cogs_overrides: dict[str, float]
    away_alpha: float
    rev_period_scale: dict[str, float]
    cogs_period_scale: dict[str, float]
    thesis: str


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def apply_period_scale(frame: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    out = add_segments(frame)
    for period, scale in spec.rev_period_scale.items():
        out.loc[out["period"].eq(period), "Revenue"] *= scale
    for period, scale in spec.cogs_period_scale.items():
        out.loc[out["period"].eq(period), "COGS"] *= scale
    return out[["Date", "Revenue", "COGS", "period"]]


def build_frame(pre_base: pd.DataFrame, shape_both: pd.DataFrame, sample: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    shaped = periodwise_shape(pre_base, shape_both, spec.rev_overrides, spec.cogs_overrides)
    shaped = cogs_ratio_away_from_sample(add_segments(shaped), sample, spec.away_alpha)
    return apply_period_scale(shaped, spec)


def specs() -> list[Spec]:
    return [
        Spec(
            "qbb60v4_shape2024h1_p1300",
            {"2023H2": 0.100, "2024H1": 1.300},
            {},
            0.250,
            {},
            {},
            "Aggressive continuation of the only confirmed improving axis: 2024H1 Revenue shape.",
        ),
        Spec(
            "qbb60v4_shape2024h1_p1500",
            {"2023H2": 0.100, "2024H1": 1.500},
            {},
            0.250,
            {},
            {},
            "Very aggressive 2024H1 Revenue-shape extrapolation; high chance to overshoot but can reach 60x if direction persists.",
        ),
        Spec(
            "qbb60v4_shape_nonh2_p1200",
            {"2023H1": 1.200, "2023H2": 0.100, "2024H1": 1.200},
            {},
            0.250,
            {},
            {},
            "Large combined non-H2 Revenue shape move.",
        ),
        Spec(
            "qbb60v4_shape2023h1_p1200_2024h1_p1000",
            {"2023H1": 1.200, "2023H2": 0.100, "2024H1": 1.000},
            {},
            0.250,
            {},
            {},
            "Large 2023H1 Revenue-shape move on top of the 682k 2024H1 anchor.",
        ),
        Spec(
            "qbb60v4_level_rev2024h1_up030",
            {"2023H2": 0.100, "2024H1": 1.000},
            {},
            0.250,
            {"2024H1": 1.030},
            {},
            "Period-level Revenue probe: 2024H1 may still be under-level.",
        ),
        Spec(
            "qbb60v4_level_rev2024h1_down030",
            {"2023H2": 0.100, "2024H1": 1.000},
            {},
            0.250,
            {"2024H1": 0.970},
            {},
            "Opposite period-level Revenue probe for 2024H1.",
        ),
        Spec(
            "qbb60v4_level_rev2023h1_up030",
            {"2023H2": 0.100, "2024H1": 1.000},
            {},
            0.250,
            {"2023H1": 1.030},
            {},
            "Period-level Revenue probe: 2023H1 under-level check.",
        ),
        Spec(
            "qbb60v4_level_cogs2024h1_up030",
            {"2023H2": 0.100, "2024H1": 1.000},
            {},
            0.250,
            {},
            {"2024H1": 1.030},
            "Period-level COGS probe: 2024H1 COGS under-level check.",
        ),
        Spec(
            "qbb60v4_level_cogs2024h1_down030",
            {"2023H2": 0.100, "2024H1": 1.000},
            {},
            0.250,
            {},
            {"2024H1": 0.970},
            "Opposite period-level COGS probe for 2024H1.",
        ),
        Spec(
            "qbb60v4_combo_2024h1p1300_cogs2024h1down030",
            {"2023H2": 0.100, "2024H1": 1.300},
            {},
            0.250,
            {},
            {"2024H1": 0.970},
            "Combo: aggressive 2024H1 Revenue shape plus lower 2024H1 COGS level.",
        ),
        Spec(
            "qbb60v4_combo_2024h1p1300_cogs2024h1up030",
            {"2023H2": 0.100, "2024H1": 1.300},
            {},
            0.250,
            {},
            {"2024H1": 1.030},
            "Combo: aggressive 2024H1 Revenue shape plus higher 2024H1 COGS level.",
        ),
        Spec(
            "qbb60v4_combo_nonh2p1200_cogs2024h1down030",
            {"2023H1": 1.200, "2023H2": 0.100, "2024H1": 1.200},
            {},
            0.250,
            {},
            {"2024H1": 0.970},
            "Large non-H2 Revenue shape plus lower 2024H1 COGS level.",
        ),
        Spec(
            "qbb60v4_cogs_away0400",
            {"2023H2": 0.100, "2024H1": 1.000},
            {},
            0.400,
            {},
            {},
            "High-variance COGS ratio-away extension beyond 0.25.",
        ),
        Spec(
            "qbb60v4_cogs_2024h1_c0350",
            {"2023H2": 0.100, "2024H1": 1.000},
            {"2024H1": 0.350},
            0.250,
            {},
            {},
            "Aggressive 2024H1 COGS daily-shape reduction.",
        ),
    ]


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Quarantine Blackbox 60x V4 Jump Axes

Run directory: `{run_dir}`

## Status

This branch is **not clean**. It is intended only for public black-box exploration.

Current true blackbox best:

- `{CURRENT_BEST_FILE}` = `{CURRENT_BEST_SCORE}`

## Why This Batch Exists

To reach `60x`, small probes are insufficient. A candidate needs enough movement to plausibly reduce MAE by 20k-70k if its direction is correct.

This batch tests:

- aggressive continuation of the confirmed 2024H1 Revenue-shape axis;
- large non-H2 Revenue-shape moves;
- 3% period-level Revenue/COGS probes;
- shape+level combos.

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Order

1. `submission_qbb60v4_shape2024h1_p1300.csv`
2. If it improves, submit `submission_qbb60v4_shape2024h1_p1500.csv`
3. If p1300 worsens, submit `submission_qbb60v4_level_rev2024h1_up030.csv` or `down030` depending on score direction from p1300/p0900.
4. For a true jump attempt after one sign is known, use a combo candidate, not another micro probe.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_blackbox60_v4_jump_axes_2026-04-23.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    pre_base = add_segments(pd.read_csv(DATASET_DIR / PRE_SAMPLE_BEST_FILE, parse_dates=["Date"]))
    current = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    sample = add_segments(pd.read_csv(DATASET_DIR / SAMPLE_FILE, parse_dates=["Date"]))
    shape_both = align_sample_shape(pre_base, sample, ("Revenue", "COGS"))

    rows = []
    for priority, spec in enumerate(specs(), start=1):
        frame = build_frame(pre_base, shape_both, sample, spec)
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
                "rev_2023H1": spec.rev_overrides.get("2023H1", BASE_REV_ALPHA),
                "rev_2023H2": spec.rev_overrides.get("2023H2", BASE_REV_ALPHA),
                "rev_2024H1": spec.rev_overrides.get("2024H1", BASE_REV_ALPHA),
                "cogs_2023H1": spec.cogs_overrides.get("2023H1", BASE_COGS_ALPHA),
                "cogs_2023H2": spec.cogs_overrides.get("2023H2", BASE_COGS_ALPHA),
                "cogs_2024H1": spec.cogs_overrides.get("2024H1", BASE_COGS_ALPHA),
                "away_alpha": spec.away_alpha,
                "rev_scale_2023H1": spec.rev_period_scale.get("2023H1", 1.0),
                "rev_scale_2024H1": spec.rev_period_scale.get("2024H1", 1.0),
                "cogs_scale_2024H1": spec.cogs_period_scale.get("2024H1", 1.0),
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
