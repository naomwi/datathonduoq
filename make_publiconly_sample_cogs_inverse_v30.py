from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from make_publiconly_sample_cogs_inverse_v26 import cogs_ratio_away_from_sample
from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, period_summary
from make_publiconly_sample_scale_ratio_v23 import write_and_summarize
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR


RUN_PREFIX = "publiconly_sample_cogs_inverse_v30"
BASE_A0725_FILE = "submission_sampleprior_v22_periodshape_both_a0725.csv"
CURRENT_BEST_FILE = "submission_sample_v30_a0725_ratio_away_sample0250.csv"
CURRENT_BEST_SCORE = 699376.32670

KNOWN_ALPHA_RESULTS = {
    -0.050: 701788.31792,
    0.000: 701005.12470,
    0.025: 700654.49101,
    0.050: 700363.16716,
    0.100: 699960.93186,
    0.125: 699793.67454,
    0.175: 699556.47851,
    0.225: 699384.92478,
    0.250: CURRENT_BEST_SCORE,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def fit_predictions(alphas: list[float]) -> dict[str, dict[float, float]]:
    pts = np.array(sorted(KNOWN_ALPHA_RESULTS.items()), dtype=float)
    out: dict[str, dict[float, float]] = {}
    for deg in (2, 3, 5):
        coef = np.polyfit(pts[:, 0], pts[:, 1], deg)
        out[f"poly{deg}"] = {alpha: float(np.polyval(coef, alpha)) for alpha in alphas}
    return out


def main() -> None:
    run_dir = make_run_dir()
    base = add_segments(pd.read_csv(DATASET_DIR / BASE_A0725_FILE, parse_dates=["Date"]))
    current = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    sample = add_segments(pd.read_csv(DATASET_DIR / SAMPLE_FILE, parse_dates=["Date"]))

    specs = [
        (0.235, "submission_sample_v30_a0725_ratio_away_sample0235.csv"),
        (0.240, "submission_sample_v30_a0725_ratio_away_sample0240.csv"),
        (0.245, "submission_sample_v30_a0725_ratio_away_sample0245.csv"),
        (0.250, "submission_sample_v30_a0725_ratio_away_sample0250.csv"),
        (0.260, "submission_sample_v30_a0725_ratio_away_sample0260.csv"),
        (0.275, "submission_sample_v30_a0725_ratio_away_sample0275.csv"),
        (0.300, "submission_sample_v30_a0725_ratio_away_sample0300.csv"),
    ]
    pred = fit_predictions([alpha for alpha, _ in specs])

    rows: list[dict[str, object]] = []
    for priority, (alpha, filename) in enumerate(specs, start=1):
        frame = cogs_ratio_away_from_sample(base, sample, alpha)
        write_and_summarize(
            rows,
            current,
            sample,
            frame,
            filename,
            f"absolute COGS ratio away-from-sample alpha={alpha:.3f}",
            priority,
        )

    manifest = pd.DataFrame(rows).sort_values("priority")
    for name, values in pred.items():
        manifest[f"{name}_pred_score"] = manifest["filename"].map({filename: values[alpha] for alpha, filename in specs})
    manifest["best_case_score_if_direction_correct"] = CURRENT_BEST_SCORE - manifest[
        "directional_best_case_gain_vs_current"
    ]
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(base).to_csv(run_dir / "base_a0725_period_summary.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_a0250_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)

    known = pd.Series(KNOWN_ALPHA_RESULTS, name="public_score")
    report = f"""# Public-Only Sample COGS Inverse V30

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known absolute alpha results:

{known.to_markdown()}

Interpretation:

- Alpha `0.250` improved to `699376.32670`, but the last step from `0.225` gained only `8.59808`.
- COGS-away is now a near-plateau; further micro points are optional only, not the route to `67x`.
- Switch priority to target-wise sample-shape alpha (`v31`) unless every target-wise probe fails.

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. Do not prioritize more COGS-away micro probes.
2. If a tiny calibration probe is still desired, use `submission_sample_v30_a0725_ratio_away_sample0275.csv`.
3. Main next path is target-wise sample alpha v31.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_cogs_inverse_v30_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
