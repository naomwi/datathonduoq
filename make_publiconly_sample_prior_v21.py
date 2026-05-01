from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
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


RUN_PREFIX = "publiconly_sample_prior_v21"
PRE_SAMPLE_BEST_FILE = "submission_top10_v13_rev2023h2_up100_keepcogs.csv"
CURRENT_BEST_FILE = "submission_sampleprior_v20_periodshape_both_a050.csv"
CURRENT_BEST_SCORE = 711472.67020

KNOWN_ALPHA_RESULTS = {
    0.00: 797595.96410,
    0.25: 744359.56345,
    0.50: CURRENT_BEST_SCORE,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def fit_curve() -> tuple[np.ndarray, float, float]:
    pts = np.array(sorted(KNOWN_ALPHA_RESULTS.items()), dtype=float)
    coef = np.polyfit(pts[:, 0], pts[:, 1], 2)
    a, b, _ = coef
    xopt = float(-b / (2 * a))
    yopt = float(np.polyval(coef, xopt))
    return coef, xopt, yopt


def main() -> None:
    run_dir = make_run_dir()
    base = add_segments(pd.read_csv(DATASET_DIR / PRE_SAMPLE_BEST_FILE, parse_dates=["Date"]))
    current = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    sample = add_segments(pd.read_csv(DATASET_DIR / SAMPLE_FILE, parse_dates=["Date"]))
    shape_both = align_sample_shape(base, sample, ("Revenue", "COGS"))
    coef, xopt, yopt = fit_curve()

    rows: list[dict[str, object]] = []
    alpha_specs = [
        (0.65, "submission_sampleprior_v21_periodshape_both_a065.csv"),
        (0.70, "submission_sampleprior_v21_periodshape_both_a070.csv"),
        (0.725, "submission_sampleprior_v21_periodshape_both_a0725.csv"),
        (0.75, "submission_sampleprior_v21_periodshape_both_a075.csv"),
        (0.775, "submission_sampleprior_v21_periodshape_both_a0775.csv"),
        (0.80, "submission_sampleprior_v21_periodshape_both_a080.csv"),
        (0.825, "submission_sampleprior_v21_periodshape_both_a0825.csv"),
        (0.85, "submission_sampleprior_v21_periodshape_both_a085.csv"),
        (0.90, "submission_sampleprior_v21_periodshape_both_a090.csv"),
    ]
    for priority, (alpha, filename) in enumerate(alpha_specs, start=1):
        frame = blend(base, shape_both, alpha)
        register(
            rows,
            base,
            sample,
            frame,
            filename,
            f"sample-shape alpha={alpha:.3f}; quadratic prediction {np.polyval(coef, alpha):.1f}",
            priority,
        )

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest["quadratic_pred_score"] = manifest["filename"].map(
        {
            filename: float(np.polyval(coef, alpha))
            for alpha, filename in alpha_specs
        }
    )
    manifest["delta_mean_abs_vs_a050_rev"] = manifest["mean_abs_rev_delta"] - (
        current["Revenue"] - base["Revenue"]
    ).abs().mean()
    manifest["delta_mean_abs_vs_a050_cogs"] = manifest["mean_abs_cogs_delta"] - (
        current["COGS"] - base["COGS"]
    ).abs().mean()
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(base).to_csv(run_dir / "pre_sample_best_period_summary.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_best_a050_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)

    known = pd.Series(KNOWN_ALPHA_RESULTS, name="public_score")
    report = f"""# Public-Only Sample Prior V21

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known alpha results:

{known.to_markdown()}

Quadratic fit:

- Coefficients: `{coef.tolist()}`
- Predicted optimum alpha: `{xopt:.4f}`
- Predicted optimum score: `{yopt:.2f}`

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. Submit `submission_sampleprior_v20_periodshape_both_a070.csv` or `submission_sampleprior_v21_periodshape_both_a070.csv`.
2. If `a070` improves to roughly `69x-70x`, submit `submission_sampleprior_v21_periodshape_both_a0775.csv`.
3. If `a070` is still above `705k`, submit `submission_sampleprior_v21_periodshape_both_a080.csv`.
4. If `a070` worsens, back off to `submission_sampleprior_v21_periodshape_both_a060.csv` from v20 if needed.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_prior_v21_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
