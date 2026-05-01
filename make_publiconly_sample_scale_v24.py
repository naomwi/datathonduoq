from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, period_summary
from make_publiconly_sample_scale_ratio_v23 import period_blend_totals, write_and_summarize
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR


RUN_PREFIX = "publiconly_sample_scale_v24"
CURRENT_BEST_FILE = "submission_sampleprior_v22_periodshape_both_a0725.csv"
CURRENT_BEST_SCORE = 701005.12470

KNOWN_RESULTS = {
    "submission_sampleprior_v20_periodshape_both_a070.csv": 701103.47903,
    "submission_sampleprior_v22_periodshape_both_a0725.csv": CURRENT_BEST_SCORE,
    "submission_sampleprior_v21_periodshape_both_a075.csv": 701144.82924,
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
            "submission_sample_v24_a0725_scale_to_sample0025.csv",
            period_blend_totals(current, sample, rev_alpha=0.025, cogs_alpha=0.025),
            "keep a0725 shape, move period Revenue and COGS totals 2.5% toward sample totals",
            1,
        ),
        (
            "submission_sample_v24_a0725_scale_to_sample0075.csv",
            period_blend_totals(current, sample, rev_alpha=0.075, cogs_alpha=0.075),
            "keep a0725 shape, move period Revenue and COGS totals 7.5% toward sample totals",
            2,
        ),
        (
            "submission_sample_v24_a0725_scale_to_sample0125.csv",
            period_blend_totals(current, sample, rev_alpha=0.125, cogs_alpha=0.125),
            "keep a0725 shape, move period Revenue and COGS totals 12.5% toward sample totals",
            3,
        ),
        (
            "submission_sample_v24_a0725_scale_to_sample0150.csv",
            period_blend_totals(current, sample, rev_alpha=0.150, cogs_alpha=0.150),
            "keep a0725 shape, move period Revenue and COGS totals 15% toward sample totals",
            4,
        ),
        (
            "submission_sample_v24_a0725_scale_to_sample0200.csv",
            period_blend_totals(current, sample, rev_alpha=0.200, cogs_alpha=0.200),
            "keep a0725 shape, move period Revenue and COGS totals 20% toward sample totals",
            5,
        ),
        (
            "submission_sample_v24_a0725_revscale_to_sample005.csv",
            period_blend_totals(current, sample, rev_alpha=0.050, cogs_alpha=0.000),
            "keep a0725 shape, move only period Revenue totals 5% toward sample",
            6,
        ),
        (
            "submission_sample_v24_a0725_cogsscale_to_sample005.csv",
            period_blend_totals(current, sample, rev_alpha=0.000, cogs_alpha=0.050),
            "keep a0725 shape, move only period COGS totals 5% toward sample",
            7,
        ),
        (
            "submission_sample_v24_a0725_rev005_cogs010.csv",
            period_blend_totals(current, sample, rev_alpha=0.050, cogs_alpha=0.100),
            "keep a0725 shape, move Revenue 5% and COGS 10% toward sample",
            8,
        ),
        (
            "submission_sample_v24_a0725_rev010_cogs005.csv",
            period_blend_totals(current, sample, rev_alpha=0.100, cogs_alpha=0.050),
            "keep a0725 shape, move Revenue 10% and COGS 5% toward sample",
            9,
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

    report = f"""# Public-Only Sample Scale V24

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known alpha-only results:

{pd.Series(KNOWN_RESULTS, name="public_score").to_markdown()}

Goal:

- New target is `67x`.
- Alpha-only sample shape has plateaued around `701k`.
- The only remaining high-leverage sample-prior axis is period-level scale toward `sample_submission`.

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. First sign test remains `submission_sample_v23_a0725_scale_to_sample005.csv`.
2. If 5% improves, submit `submission_sample_v23_a0725_scale_to_sample010.csv`.
3. If 10% improves, continue with `submission_sample_v24_a0725_scale_to_sample0150.csv`.
4. If symmetric scale fails, use the separate Revenue/COGS probes to identify which target needs the scale move.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_scale_v24_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
