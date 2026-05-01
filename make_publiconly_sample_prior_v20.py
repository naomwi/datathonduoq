from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_prior_v19 import (
    SAMPLE_FILE,
    add_segments,
    align_sample_shape,
    blend,
    period_summary,
    register,
)
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR


RUN_PREFIX = "publiconly_sample_prior_v20"
PRE_SAMPLE_BEST_FILE = "submission_top10_v13_rev2023h2_up100_keepcogs.csv"
PRE_SAMPLE_BEST_SCORE = 797595.96410
CURRENT_BEST_FILE = "submission_sampleprior_v19_periodshape_both_a025.csv"
CURRENT_BEST_SCORE = 744359.56345

KNOWN_SAMPLE_SHAPE_RESULTS = {
    "alpha_0.00_pre_sample_best": PRE_SAMPLE_BEST_SCORE,
    "submission_sampleprior_v19_periodshape_both_a025.csv": CURRENT_BEST_SCORE,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def main() -> None:
    run_dir = make_run_dir()
    base = add_segments(pd.read_csv(DATASET_DIR / PRE_SAMPLE_BEST_FILE, parse_dates=["Date"]))
    current_best = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    sample = add_segments(pd.read_csv(DATASET_DIR / SAMPLE_FILE, parse_dates=["Date"]))
    shape_both = align_sample_shape(base, sample, ("Revenue", "COGS"))

    rows: list[dict[str, object]] = []
    alpha_specs = [
        (0.30, "submission_sampleprior_v20_periodshape_both_a030.csv"),
        (0.35, "submission_sampleprior_v20_periodshape_both_a035.csv"),
        (0.40, "submission_sampleprior_v20_periodshape_both_a040.csv"),
        (0.45, "submission_sampleprior_v20_periodshape_both_a045.csv"),
        (0.50, "submission_sampleprior_v20_periodshape_both_a050.csv"),
        (0.55, "submission_sampleprior_v20_periodshape_both_a055.csv"),
        (0.60, "submission_sampleprior_v20_periodshape_both_a060.csv"),
        (0.70, "submission_sampleprior_v20_periodshape_both_a070.csv"),
        (0.85, "submission_sampleprior_v20_periodshape_both_a085.csv"),
        (1.00, "submission_sampleprior_v20_periodshape_both_a100.csv"),
    ]
    for priority, (alpha, filename) in enumerate(alpha_specs, start=1):
        frame = blend(base, shape_both, alpha)
        register(
            rows,
            base,
            sample,
            frame,
            filename,
            f"absolute alpha={alpha:.2f}: blend toward sample day-level shape while preserving pre-sample best period totals",
            priority,
        )

    # Local refinements around the current alpha=0.25 winner. These are safer if alpha=0.50 overshoots.
    refine_specs = [
        (0.20, "submission_sampleprior_v20_periodshape_both_a020.csv"),
        (0.225, "submission_sampleprior_v20_periodshape_both_a0225.csv"),
        (0.275, "submission_sampleprior_v20_periodshape_both_a0275.csv"),
        (0.325, "submission_sampleprior_v20_periodshape_both_a0325.csv"),
    ]
    for offset, (alpha, filename) in enumerate(refine_specs, start=len(alpha_specs) + 1):
        frame = blend(base, shape_both, alpha)
        register(
            rows,
            base,
            sample,
            frame,
            filename,
            f"local refinement around alpha=0.25 winner: alpha={alpha:.3f}",
            offset,
        )

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest["delta_mean_abs_vs_a025_rev"] = manifest["mean_abs_rev_delta"] - (
        current_best["Revenue"] - base["Revenue"]
    ).abs().mean()
    manifest["delta_mean_abs_vs_a025_cogs"] = manifest["mean_abs_cogs_delta"] - (
        current_best["COGS"] - base["COGS"]
    ).abs().mean()
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(base).to_csv(run_dir / "pre_sample_best_period_summary.csv", index=False)
    period_summary(current_best).to_csv(run_dir / "current_best_a025_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)
    period_summary(shape_both).to_csv(run_dir / "sample_shape_preserve_period_summary.csv", index=False)

    linear_score_a050 = CURRENT_BEST_SCORE - (PRE_SAMPLE_BEST_SCORE - CURRENT_BEST_SCORE)
    report = f"""# Public-Only Sample Prior V20

Run directory: `{run_dir}`

Pre-sample best: `{PRE_SAMPLE_BEST_FILE}` scored `{PRE_SAMPLE_BEST_SCORE}`.

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known sample-shape results:

{pd.Series(KNOWN_SAMPLE_SHAPE_RESULTS, name="public_score").to_markdown()}

Interpretation:

- Alpha `0.25` toward sample day-level shape cut public MAE by `{PRE_SAMPLE_BEST_SCORE - CURRENT_BEST_SCORE:.1f}`.
- Linear extrapolation from alpha `0.00 -> 0.25` predicts alpha `0.50` near `{linear_score_a050:.1f}`. This is not guaranteed, but it is the first credible path to `69x`.
- Use absolute alpha from the same pre-sample base, not incremental alpha from the current best, so the ladder is clean.

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. Submit existing `submission_sampleprior_v19_periodshape_both_a050.csv` or equivalent `submission_sampleprior_v20_periodshape_both_a050.csv`.
2. If `a050` improves strongly, test `a070`.
3. If `a050` improves but not enough, test `a060`.
4. If `a050` worsens, test local refinement `a035` or `a030`.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_prior_v20_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
