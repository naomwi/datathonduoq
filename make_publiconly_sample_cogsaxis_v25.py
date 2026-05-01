from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, period_summary
from make_publiconly_sample_scale_ratio_v23 import cogs_ratio_blend, global_scale, period_blend_totals, write_and_summarize
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR


RUN_PREFIX = "publiconly_sample_cogsaxis_v25"
CURRENT_BEST_FILE = "submission_sampleprior_v22_periodshape_both_a0725.csv"
CURRENT_BEST_SCORE = 701005.12470

KNOWN_RESULTS = {
    "submission_sampleprior_v22_periodshape_both_a0725.csv": CURRENT_BEST_SCORE,
    "submission_sample_v23_a0725_scale_to_sample005.csv": 707716.51463,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def main() -> None:
    run_dir = make_run_dir()
    current = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    sample = add_segments(pd.read_csv(DATASET_DIR / SAMPLE_FILE, parse_dates=["Date"]))

    rows: list[dict[str, object]] = []
    specs = [
        (
            "submission_sample_v25_a0725_ratio_to_sample0025.csv",
            cogs_ratio_blend(current, sample, 0.025),
            "keep Revenue and day shape, move COGS/Revenue period ratios 2.5% toward sample",
            1,
        ),
        (
            "submission_sample_v25_a0725_ratio_to_sample0050.csv",
            cogs_ratio_blend(current, sample, 0.050),
            "keep Revenue and day shape, move COGS/Revenue period ratios 5% toward sample",
            2,
        ),
        (
            "submission_sample_v25_a0725_ratio_to_sample0075.csv",
            cogs_ratio_blend(current, sample, 0.075),
            "keep Revenue and day shape, move COGS/Revenue period ratios 7.5% toward sample",
            3,
        ),
        (
            "submission_sample_v25_a0725_ratio_to_sample0100.csv",
            cogs_ratio_blend(current, sample, 0.100),
            "keep Revenue and day shape, move COGS/Revenue period ratios 10% toward sample",
            4,
        ),
        (
            "submission_sample_v25_a0725_cogsscale_to_sample0025.csv",
            period_blend_totals(current, sample, rev_alpha=0.000, cogs_alpha=0.025),
            "keep Revenue, move period COGS totals 2.5% toward sample",
            5,
        ),
        (
            "submission_sample_v25_a0725_cogsscale_to_sample0050.csv",
            period_blend_totals(current, sample, rev_alpha=0.000, cogs_alpha=0.050),
            "keep Revenue, move period COGS totals 5% toward sample",
            6,
        ),
        (
            "submission_sample_v25_a0725_cogsscale_down0025.csv",
            global_scale(current, revenue_multiplier=1.0, cogs_multiplier=0.9975),
            "global COGS -0.25%, keep Revenue",
            7,
        ),
        (
            "submission_sample_v25_a0725_cogsscale_down0050.csv",
            global_scale(current, revenue_multiplier=1.0, cogs_multiplier=0.9950),
            "global COGS -0.5%, keep Revenue",
            8,
        ),
        (
            "submission_sample_v25_a0725_cogsscale_up0025.csv",
            global_scale(current, revenue_multiplier=1.0, cogs_multiplier=1.0025),
            "global COGS +0.25%, keep Revenue",
            9,
        ),
        (
            "submission_sample_v25_a0725_cogsscale_up0050.csv",
            global_scale(current, revenue_multiplier=1.0, cogs_multiplier=1.0050),
            "global COGS +0.5%, keep Revenue",
            10,
        ),
    ]

    for filename, frame, thesis, priority in specs:
        write_and_summarize(rows, current, sample, frame, filename, thesis, priority)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest["best_case_score_if_direction_correct"] = CURRENT_BEST_SCORE - manifest[
        "directional_best_case_gain_vs_current"
    ]
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_a0725_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)

    report = f"""# Public-Only Sample COGS Axis V25

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known results:

{pd.Series(KNOWN_RESULTS, name="public_score").to_markdown()}

Interpretation:

- Symmetric scale-to-sample 5% failed badly, so period Revenue+COGS totals toward sample are wrong.
- To identify whether the remaining error is COGS-side, test COGS-only ratio/scale.
- These probes are smaller than failed symmetric scale but still have enough amplitude to cross `699k` if COGS direction is right.

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_sample_v25_a0725_ratio_to_sample0050.csv`
2. If it improves: `submission_sample_v25_a0725_ratio_to_sample0100.csv`
3. If ratio-to-sample fails, test sign with `submission_sample_v25_a0725_cogsscale_up0025.csv`.
4. If COGS-down fails and COGS-up improves, continue with `cogsscale_up0050`.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_cogsaxis_v25_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
