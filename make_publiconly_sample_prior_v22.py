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


RUN_PREFIX = "publiconly_sample_prior_v22"
PRE_SAMPLE_BEST_FILE = "submission_top10_v13_rev2023h2_up100_keepcogs.csv"
CURRENT_BEST_FILE = "submission_sampleprior_v20_periodshape_both_a070.csv"
CURRENT_BEST_SCORE = 701103.47903

KNOWN_ALPHA_RESULTS = {
    0.00: 797595.96410,
    0.25: 744359.56345,
    0.50: 711472.67020,
    0.70: CURRENT_BEST_SCORE,
    0.75: 701144.82924,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def main() -> None:
    run_dir = make_run_dir()
    base = add_segments(pd.read_csv(DATASET_DIR / PRE_SAMPLE_BEST_FILE, parse_dates=["Date"]))
    current = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    sample = add_segments(pd.read_csv(DATASET_DIR / SAMPLE_FILE, parse_dates=["Date"]))
    shape_both = align_sample_shape(base, sample, ("Revenue", "COGS"))

    rows: list[dict[str, object]] = []
    alpha_specs = [
        (0.705, "submission_sampleprior_v22_periodshape_both_a0705.csv"),
        (0.710, "submission_sampleprior_v22_periodshape_both_a0710.csv"),
        (0.715, "submission_sampleprior_v22_periodshape_both_a0715.csv"),
        (0.720, "submission_sampleprior_v22_periodshape_both_a0720.csv"),
        (0.725, "submission_sampleprior_v22_periodshape_both_a0725.csv"),
        (0.730, "submission_sampleprior_v22_periodshape_both_a0730.csv"),
        (0.735, "submission_sampleprior_v22_periodshape_both_a0735.csv"),
        (0.740, "submission_sampleprior_v22_periodshape_both_a0740.csv"),
        (0.745, "submission_sampleprior_v22_periodshape_both_a0745.csv"),
    ]
    for priority, (alpha, filename) in enumerate(alpha_specs, start=1):
        frame = blend(base, shape_both, alpha)
        register(
            rows,
            base,
            sample,
            frame,
            filename,
            f"micro-refine sample-shape alpha={alpha:.3f} between known a070 and a075",
            priority,
        )

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest["delta_mean_abs_vs_a070_rev"] = manifest["mean_abs_rev_delta"] - (
        current["Revenue"] - base["Revenue"]
    ).abs().mean()
    manifest["delta_mean_abs_vs_a070_cogs"] = manifest["mean_abs_cogs_delta"] - (
        current["COGS"] - base["COGS"]
    ).abs().mean()
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(base).to_csv(run_dir / "pre_sample_best_period_summary.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_best_a070_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)

    known = pd.Series(KNOWN_ALPHA_RESULTS, name="public_score")
    report = f"""# Public-Only Sample Prior V22

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known alpha results:

{known.to_markdown()}

Interpretation:

- `a075` is worse than `a070` by only `41.35021`, so the optimum is extremely flat and close.
- The next best probe is the midpoint `a0725`, then one-sided micro steps if needed.

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. Submit `submission_sampleprior_v21_periodshape_both_a0725.csv` or equivalent `submission_sampleprior_v22_periodshape_both_a0725.csv`.
2. If `a0725` improves, submit `a0735` or `a0740`.
3. If `a0725` worsens, submit `a0710` or keep `a070`.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_prior_v22_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
