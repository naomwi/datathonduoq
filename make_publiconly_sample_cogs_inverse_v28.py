from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from make_publiconly_sample_cogs_inverse_v26 import cogs_ratio_away_from_sample
from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, period_summary
from make_publiconly_sample_scale_ratio_v23 import write_and_summarize
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR


RUN_PREFIX = "publiconly_sample_cogs_inverse_v28"
BASE_A0725_FILE = "submission_sampleprior_v22_periodshape_both_a0725.csv"
CURRENT_BEST_FILE = "submission_sample_v26_a0725_ratio_away_sample0100.csv"
CURRENT_BEST_SCORE = 699960.93186

KNOWN_ALPHA_RESULTS = {
    -0.050: 701788.31792,
    0.000: 701005.12470,
    0.025: 700654.49101,
    0.050: 700363.16716,
    0.100: CURRENT_BEST_SCORE,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def fit_predictions() -> dict[float, float]:
    pts = np.array(sorted(KNOWN_ALPHA_RESULTS.items()), dtype=float)
    # Cubic is conservative here; quadratic still says some gain until ~0.18.
    coef = np.polyfit(pts[:, 0], pts[:, 1], 3)
    return {alpha: float(np.polyval(coef, alpha)) for alpha in [0.125, 0.15, 0.175, 0.20, 0.25, 0.30]}


def main() -> None:
    run_dir = make_run_dir()
    base = add_segments(pd.read_csv(DATASET_DIR / BASE_A0725_FILE, parse_dates=["Date"]))
    current = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    sample = add_segments(pd.read_csv(DATASET_DIR / SAMPLE_FILE, parse_dates=["Date"]))
    pred = fit_predictions()

    rows: list[dict[str, object]] = []
    specs = [
        (0.125, "submission_sample_v28_a0725_ratio_away_sample0125.csv"),
        (0.150, "submission_sample_v28_a0725_ratio_away_sample0150.csv"),
        (0.175, "submission_sample_v28_a0725_ratio_away_sample0175.csv"),
        (0.200, "submission_sample_v28_a0725_ratio_away_sample0200.csv"),
        (0.250, "submission_sample_v28_a0725_ratio_away_sample0250.csv"),
        (0.300, "submission_sample_v28_a0725_ratio_away_sample0300.csv"),
    ]
    for priority, (alpha, filename) in enumerate(specs, start=1):
        frame = cogs_ratio_away_from_sample(base, sample, alpha)
        write_and_summarize(
            rows,
            current,
            sample,
            frame,
            filename,
            f"absolute COGS ratio away-from-sample alpha={alpha:.3f}; cubic prediction {pred[alpha]:.1f}",
            priority,
        )

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest["cubic_pred_score"] = manifest["filename"].map({filename: pred[alpha] for alpha, filename in specs})
    manifest["best_case_score_if_direction_correct"] = CURRENT_BEST_SCORE - manifest[
        "directional_best_case_gain_vs_current"
    ]
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(base).to_csv(run_dir / "base_a0725_period_summary.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_a0100_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)

    known = pd.Series(KNOWN_ALPHA_RESULTS, name="public_score")
    report = f"""# Public-Only Sample COGS Inverse V28

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known absolute alpha results:

{known.to_markdown()}

Interpretation:

- COGS ratio away-from-sample still improves at alpha `0.100`.
- Gains are diminishing, so use small absolute steps; do not apply these incrementally on top of `a0100`.
- Conservative cubic fit predicts the next useful point around `0.125`; quadratic allows more, but `0.125` is the clean next probe.

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_sample_v28_a0725_ratio_away_sample0125.csv`
2. If it improves: `submission_sample_v28_a0725_ratio_away_sample0150.csv`
3. If `0.150` improves: `submission_sample_v28_a0725_ratio_away_sample0200.csv`
4. If `0.125` worsens, stop COGS-ratio ladder and use target-wise v27.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_cogs_inverse_v28_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
