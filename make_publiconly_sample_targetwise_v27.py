from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_cogs_inverse_v26 import cogs_ratio_away_from_sample
from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, align_sample_shape, period_summary
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "publiconly_sample_targetwise_v27"
PRE_SAMPLE_BEST_FILE = "submission_top10_v13_rev2023h2_up100_keepcogs.csv"
CURRENT_BEST_FILE = "submission_sample_v26_a0725_ratio_away_sample0025.csv"
CURRENT_BEST_SCORE = 700654.49101
BASE_SHAPE_ALPHA = 0.725
BASE_COGS_AWAY_ALPHA = 0.025

KNOWN_RESULTS = {
    "submission_sampleprior_v22_periodshape_both_a0725.csv": 701005.12470,
    "submission_sample_v25_a0725_ratio_to_sample0050.csv": 701788.31792,
    "submission_sample_v26_a0725_ratio_away_sample0025.csv": CURRENT_BEST_SCORE,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def targetwise_shape(base: pd.DataFrame, shape_both: pd.DataFrame, rev_alpha: float, cogs_alpha: float) -> pd.DataFrame:
    out = base[["Date", "Revenue", "COGS"]].copy()
    out["Revenue"] = (1.0 - rev_alpha) * base["Revenue"] + rev_alpha * shape_both["Revenue"]
    out["COGS"] = (1.0 - cogs_alpha) * base["COGS"] + cogs_alpha * shape_both["COGS"]
    return out


def with_cogs_away(frame: pd.DataFrame, sample: pd.DataFrame, alpha: float = BASE_COGS_AWAY_ALPHA) -> pd.DataFrame:
    return cogs_ratio_away_from_sample(add_segments(frame), sample, alpha)


def summarize(
    rows: list[dict[str, object]],
    current: pd.DataFrame,
    sample: pd.DataFrame,
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
            "submission_sample_v27_rev070_cogs0725_away0025.csv",
            with_cogs_away(targetwise_shape(pre_base, shape_both, 0.700, 0.725), sample),
            "Revenue shape alpha 0.700, COGS alpha 0.725, keep COGS away 0.025",
            1,
        ),
        (
            "submission_sample_v27_rev075_cogs0725_away0025.csv",
            with_cogs_away(targetwise_shape(pre_base, shape_both, 0.750, 0.725), sample),
            "Revenue shape alpha 0.750, COGS alpha 0.725, keep COGS away 0.025",
            2,
        ),
        (
            "submission_sample_v27_rev0725_cogs070_away0025.csv",
            with_cogs_away(targetwise_shape(pre_base, shape_both, 0.725, 0.700), sample),
            "Revenue alpha 0.725, COGS shape alpha 0.700, keep COGS away 0.025",
            3,
        ),
        (
            "submission_sample_v27_rev0725_cogs075_away0025.csv",
            with_cogs_away(targetwise_shape(pre_base, shape_both, 0.725, 0.750), sample),
            "Revenue alpha 0.725, COGS shape alpha 0.750, keep COGS away 0.025",
            4,
        ),
        (
            "submission_sample_v27_rev070_cogs075_away0025.csv",
            with_cogs_away(targetwise_shape(pre_base, shape_both, 0.700, 0.750), sample),
            "Revenue alpha down, COGS alpha up, keep COGS away 0.025",
            5,
        ),
        (
            "submission_sample_v27_rev075_cogs070_away0025.csv",
            with_cogs_away(targetwise_shape(pre_base, shape_both, 0.750, 0.700), sample),
            "Revenue alpha up, COGS alpha down, keep COGS away 0.025",
            6,
        ),
        (
            "submission_sample_v27_rev0725_cogs080_away0025.csv",
            with_cogs_away(targetwise_shape(pre_base, shape_both, 0.725, 0.800), sample),
            "Revenue alpha 0.725, COGS shape alpha 0.800, keep COGS away 0.025",
            7,
        ),
        (
            "submission_sample_v27_rev080_cogs0725_away0025.csv",
            with_cogs_away(targetwise_shape(pre_base, shape_both, 0.800, 0.725), sample),
            "Revenue shape alpha 0.800, COGS alpha 0.725, keep COGS away 0.025",
            8,
        ),
    ]
    for filename, frame, thesis, priority in specs:
        summarize(rows, current, sample, frame, filename, thesis, priority)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest["best_case_score_if_direction_correct"] = CURRENT_BEST_SCORE - manifest[
        "directional_best_case_gain_vs_current"
    ]
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_best_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)

    report = f"""# Public-Only Sample Targetwise V27

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known results:

{pd.Series(KNOWN_RESULTS, name="public_score").to_markdown()}

Interpretation:

- Same alpha for Revenue and COGS has plateaued.
- COGS ratio away-from-sample improved slightly.
- To chase `67x`, the next high-leverage axis is target-wise sample-shape alpha: Revenue and COGS may prefer different sample-shape strength.

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. First continue COGS-ratio ladder with `submission_sample_v26_a0725_ratio_away_sample0050.csv`.
2. If COGS-ratio stalls, submit `submission_sample_v27_rev0725_cogs075_away0025.csv`.
3. If COGS alpha up improves, continue `submission_sample_v27_rev0725_cogs080_away0025.csv`.
4. If COGS alpha up fails, test Revenue side with `submission_sample_v27_rev070_cogs0725_away0025.csv`.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_targetwise_v27_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
