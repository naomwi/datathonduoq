from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_cogs_inverse_v26 import cogs_ratio_away_from_sample
from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, align_sample_shape, period_summary
from make_publiconly_sample_targetwise_v27 import targetwise_shape
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "publiconly_sample_targetwise_v29"
PRE_SAMPLE_BEST_FILE = "submission_top10_v13_rev2023h2_up100_keepcogs.csv"
CURRENT_BEST_FILE = "submission_sample_v28_a0725_ratio_away_sample0125.csv"
CURRENT_BEST_SCORE = 699793.67454
BASE_REV_ALPHA = 0.725
BASE_COGS_ALPHA = 0.725
BASE_COGS_AWAY_ALPHA = 0.125

KNOWN_RESULTS = {
    "submission_sample_v26_a0725_ratio_away_sample0100.csv": 699960.93186,
    "submission_sample_v28_a0725_ratio_away_sample0125.csv": CURRENT_BEST_SCORE,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def with_cogs_away(frame: pd.DataFrame, sample: pd.DataFrame, alpha: float = BASE_COGS_AWAY_ALPHA) -> pd.DataFrame:
    return cogs_ratio_away_from_sample(add_segments(frame), sample, alpha)


def summarize(
    rows: list[dict[str, object]],
    current: pd.DataFrame,
    frame: pd.DataFrame,
    filename: str,
    thesis: str,
    priority: int,
) -> None:
    write_submission(frame, DATASET_DIR / filename)
    delta_rev = frame["Revenue"] - current["Revenue"]
    delta_cogs = frame["COGS"] - current["COGS"]
    prof = period_summary(frame)
    rows.append(
        {
            "priority": priority,
            "filename": filename,
            "path": str(DATASET_DIR / filename),
            "thesis": thesis,
            "rev_rows_changed_vs_current": int(delta_rev.abs().gt(1e-6).sum()),
            "cogs_rows_changed_vs_current": int(delta_cogs.abs().gt(1e-6).sum()),
            "mean_abs_rev_delta_vs_current": delta_rev.abs().mean(),
            "mean_abs_cogs_delta_vs_current": delta_cogs.abs().mean(),
            "directional_best_case_gain_vs_current": 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
            "revenue_total_ratio_vs_current": frame["Revenue"].sum() / current["Revenue"].sum(),
            "cogs_total_ratio_vs_current": frame["COGS"].sum() / current["COGS"].sum(),
            "ratio_all": frame["COGS"].sum() / frame["Revenue"].sum(),
            "ratio_2023h1": prof.loc[prof["period"].eq("2023H1"), "ratio"].iloc[0],
            "ratio_2023h2": prof.loc[prof["period"].eq("2023H2"), "ratio"].iloc[0],
            "ratio_2024h1": prof.loc[prof["period"].eq("2024H1"), "ratio"].iloc[0],
        }
    )


def main() -> None:
    run_dir = make_run_dir()
    pre_base = add_segments(pd.read_csv(DATASET_DIR / PRE_SAMPLE_BEST_FILE, parse_dates=["Date"]))
    current = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    sample = add_segments(pd.read_csv(DATASET_DIR / SAMPLE_FILE, parse_dates=["Date"]))
    shape_both = align_sample_shape(pre_base, sample, ("Revenue", "COGS"))

    rows: list[dict[str, object]] = []
    specs = [
        (
            "submission_sample_v29_rev070_cogs0725_away0125.csv",
            with_cogs_away(targetwise_shape(pre_base, shape_both, 0.700, 0.725), sample),
            "Revenue shape alpha 0.700, COGS alpha 0.725, COGS away 0.125",
            1,
        ),
        (
            "submission_sample_v29_rev075_cogs0725_away0125.csv",
            with_cogs_away(targetwise_shape(pre_base, shape_both, 0.750, 0.725), sample),
            "Revenue shape alpha 0.750, COGS alpha 0.725, COGS away 0.125",
            2,
        ),
        (
            "submission_sample_v29_rev080_cogs0725_away0125.csv",
            with_cogs_away(targetwise_shape(pre_base, shape_both, 0.800, 0.725), sample),
            "Revenue shape alpha 0.800, COGS alpha 0.725, COGS away 0.125",
            3,
        ),
        (
            "submission_sample_v29_rev0725_cogs070_away0125.csv",
            with_cogs_away(targetwise_shape(pre_base, shape_both, 0.725, 0.700), sample),
            "Revenue alpha 0.725, COGS shape alpha 0.700, COGS away 0.125",
            4,
        ),
        (
            "submission_sample_v29_rev0725_cogs075_away0125.csv",
            with_cogs_away(targetwise_shape(pre_base, shape_both, 0.725, 0.750), sample),
            "Revenue alpha 0.725, COGS shape alpha 0.750, COGS away 0.125",
            5,
        ),
        (
            "submission_sample_v29_rev0725_cogs080_away0125.csv",
            with_cogs_away(targetwise_shape(pre_base, shape_both, 0.725, 0.800), sample),
            "Revenue alpha 0.725, COGS shape alpha 0.800, COGS away 0.125",
            6,
        ),
        (
            "submission_sample_v29_rev070_cogs080_away0125.csv",
            with_cogs_away(targetwise_shape(pre_base, shape_both, 0.700, 0.800), sample),
            "Revenue alpha 0.700, COGS alpha 0.800, COGS away 0.125",
            7,
        ),
        (
            "submission_sample_v29_rev080_cogs070_away0125.csv",
            with_cogs_away(targetwise_shape(pre_base, shape_both, 0.800, 0.700), sample),
            "Revenue alpha 0.800, COGS alpha 0.700, COGS away 0.125",
            8,
        ),
    ]
    for filename, frame, thesis, priority in specs:
        summarize(rows, current, frame, filename, thesis, priority)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest["best_case_score_if_direction_correct"] = CURRENT_BEST_SCORE - manifest[
        "directional_best_case_gain_vs_current"
    ]
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_best_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)

    report = f"""# Public-Only Sample Targetwise V29

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known results:

{pd.Series(KNOWN_RESULTS, name="public_score").to_markdown()}

Interpretation:

- COGS-ratio away ladder is still improving but slowly.
- Target-wise sample-shape alpha is the next high-variance axis for the `67x` goal.
- These candidates keep the improved COGS-away alpha `0.125` and vary Revenue/COGS sample-shape strength separately.

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. Finish COGS-ratio next with `submission_sample_v28_a0725_ratio_away_sample0150.csv`.
2. If that stalls, submit `submission_sample_v29_rev0725_cogs075_away0125.csv`.
3. If COGS shape alpha up improves, continue to `submission_sample_v29_rev0725_cogs080_away0125.csv`.
4. If it fails, test Revenue alpha with `submission_sample_v29_rev070_cogs0725_away0125.csv`.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_targetwise_v29_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
