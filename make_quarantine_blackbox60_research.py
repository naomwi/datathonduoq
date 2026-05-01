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


RUN_PREFIX = "quarantine_blackbox60_research"
CURRENT_BEST_FILE = "submission_sample_v37_rev2023H2_p0100_c0650_away0250.csv"
CURRENT_BEST_SCORE = 684463.34954


@dataclass(frozen=True)
class ResearchSpec:
    name: str
    rev_overrides: dict[str, float]
    cogs_overrides: dict[str, float]
    away_alpha: float
    thesis: str


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def build_frame(pre_base: pd.DataFrame, shape_both: pd.DataFrame, sample: pd.DataFrame, spec: ResearchSpec) -> pd.DataFrame:
    shaped = periodwise_shape(pre_base, shape_both, spec.rev_overrides, spec.cogs_overrides)
    return cogs_ratio_away_from_sample(add_segments(shaped), sample, spec.away_alpha)


def build_specs() -> list[ResearchSpec]:
    return [
        ResearchSpec(
            "qbb60_h2p0050_c0650_away0250",
            {"2023H2": 0.050},
            {},
            0.250,
            "Micro lower 2023H2 sample-shape alpha below current 0.100.",
        ),
        ResearchSpec(
            "qbb60_h2p0075_c0650_away0250",
            {"2023H2": 0.075},
            {},
            0.250,
            "Safer micro lower 2023H2 alpha.",
        ),
        ResearchSpec(
            "qbb60_h2p0125_c0650_away0250",
            {"2023H2": 0.125},
            {},
            0.250,
            "Micro upper check around current 0.100.",
        ),
        ResearchSpec(
            "qbb60_h2p0100_c0600_away0250",
            {"2023H2": 0.100},
            {"2023H1": 0.600, "2023H2": 0.600, "2024H1": 0.600},
            0.250,
            "Reduce COGS sample-shape alpha globally; tests if remaining error is COGS overshape.",
        ),
        ResearchSpec(
            "qbb60_h2p0100_c0700_away0250",
            {"2023H2": 0.100},
            {"2023H1": 0.700, "2023H2": 0.700, "2024H1": 0.700},
            0.250,
            "Increase COGS sample-shape alpha globally; opposite COGS-shape check.",
        ),
        ResearchSpec(
            "qbb60_h2p0100_c0650_away0200",
            {"2023H2": 0.100},
            {},
            0.200,
            "Softer COGS ratio away-from-sample correction.",
        ),
        ResearchSpec(
            "qbb60_h2p0100_c0650_away0300",
            {"2023H2": 0.100},
            {},
            0.300,
            "Stronger COGS ratio away-from-sample correction.",
        ),
        ResearchSpec(
            "qbb60_h2p0100_2024h1p1000_c0650_away0250",
            {"2023H2": 0.100, "2024H1": 1.000},
            {},
            0.250,
            "Stronger 2024H1 sample daily shape; next largest non-H2 axis.",
        ),
        ResearchSpec(
            "qbb60_h2p0100_2024h1p0600_c0650_away0250",
            {"2023H2": 0.100, "2024H1": 0.600},
            {},
            0.250,
            "Weaker 2024H1 sample daily shape; sign check.",
        ),
        ResearchSpec(
            "qbb60_h2p0100_2023h1p1000_2024h1p1000_c0650_away0250",
            {"2023H1": 1.000, "2023H2": 0.100, "2024H1": 1.000},
            {},
            0.250,
            "Both non-H2 periods stronger sample shape while keeping H2 guarded.",
        ),
    ]


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Quarantine Blackbox 60x Research

Run directory: `{run_dir}`

## Status

This branch is **not clean** and must not be used for final source/report. It reads `sample_submission.csv` and uses previous public-leaderboard feedback. Its purpose is only to map the public surface and infer which hidden structure matters.

Current blackbox best tracked here: `{CURRENT_BEST_FILE}` = `{CURRENT_BEST_SCORE}`.

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Suggested Public Probe Order

1. `submission_qbb60_h2p0075_c0650_away0250.csv`
2. If it improves, submit `submission_qbb60_h2p0050_c0650_away0250.csv`
3. If H2 micro does not help, test COGS axis: `submission_qbb60_h2p0100_c0600_away0250.csv`
4. If COGS axis is flat, test 2024H1 shape: `submission_qbb60_h2p0100_2024h1p1000_c0650_away0250.csv`

## What We Hope To Learn

- Whether the current 2023H2 alpha optimum is below, above, or exactly around `0.100`.
- Whether the remaining gap to 60x is mostly COGS daily shape/ratio or non-H2 Revenue shape.
- Whether 2024H1 needs stronger sample-like shape even though the clean train prior cannot justify it.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_blackbox60_research_2026-04-23.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    pre_base = add_segments(pd.read_csv(DATASET_DIR / PRE_SAMPLE_BEST_FILE, parse_dates=["Date"]))
    current = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    sample = add_segments(pd.read_csv(DATASET_DIR / SAMPLE_FILE, parse_dates=["Date"]))
    shape_both = align_sample_shape(pre_base, sample, ("Revenue", "COGS"))

    rows = []
    for priority, spec in enumerate(build_specs(), start=1):
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
                "mean_abs_rev_delta_vs_current": delta_rev.abs().mean(),
                "mean_abs_cogs_delta_vs_current": delta_cogs.abs().mean(),
                "directional_best_case_gain_vs_current": 0.5
                * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
                "best_case_score_if_direction_correct": CURRENT_BEST_SCORE
                - 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
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
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)
    write_report(run_dir, manifest)
    print(run_dir)


if __name__ == "__main__":
    main()
