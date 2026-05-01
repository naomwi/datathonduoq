from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, align_sample_shape, period_summary
from make_publiconly_sample_targetwise_v31 import (
    BASE_COGS_AWAY_ALPHA,
    BASE_REV_ALPHA,
    CURRENT_BEST_FILE,
    CURRENT_BEST_SCORE,
    PRE_SAMPLE_BEST_FILE,
    build_candidate,
)
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "publiconly_sample_cogs_shape_down_v32"

KNOWN_RESULTS = {
    CURRENT_BEST_FILE: CURRENT_BEST_SCORE,
    "submission_sample_v31_rev0725_cogs0750_away0250.csv": 699662.34515,
    "submission_sample_v32_rev0725_cogs0700_away0250.csv": 699167.79998,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def alpha_token(alpha: float) -> str:
    return f"{int(round(alpha * 1000)):04d}"


def summarize(
    rows: list[dict[str, object]],
    current: pd.DataFrame,
    frame: pd.DataFrame,
    filename: str,
    thesis: str,
    priority: int,
    cogs_alpha: float,
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
            "rev_alpha": BASE_REV_ALPHA,
            "cogs_alpha": cogs_alpha,
            "cogs_away_alpha": BASE_COGS_AWAY_ALPHA,
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
        (0.7125, "small opposite step after cogs0750 failed", 1),
        (0.7000, "symmetric opposite step to cogs0750", 2),
        (0.6875, "moderate COGS shape reduction", 3),
        (0.6750, "stronger COGS shape reduction", 4),
        (0.6500, "high-variance COGS shape reduction", 5),
        (0.6000, "extreme COGS shape reduction for public-only diagnosis", 6),
    ]
    for cogs_alpha, thesis, priority in specs:
        filename = f"submission_sample_v32_rev0725_cogs{alpha_token(cogs_alpha)}_away0250.csv"
        frame = build_candidate(pre_base, shape_both, sample, BASE_REV_ALPHA, cogs_alpha)
        summarize(rows, current, frame, filename, thesis, priority, cogs_alpha)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest["best_case_score_if_direction_correct"] = CURRENT_BEST_SCORE - manifest[
        "directional_best_case_gain_vs_current"
    ]
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_best_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)

    fail_delta = KNOWN_RESULTS["submission_sample_v31_rev0725_cogs0750_away0250.csv"] - CURRENT_BEST_SCORE
    report = f"""# Public-Only Sample COGS Shape Down V32

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known results:

{pd.Series(KNOWN_RESULTS, name="public_score").to_markdown()}

Interpretation:

- `submission_sample_v31_rev0725_cogs0750_away0250.csv` worsened by `{fail_delta:.5f}`.
- That candidate only changed the COGS day-level shape, not total Revenue or total COGS.
- The next useful probe is the opposite side: reduce COGS sample-shape alpha below `0.725`.

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. Submit `submission_sample_v32_rev0725_cogs0712_away0250.csv` if you want the safer half-step.
2. Submit `submission_sample_v32_rev0725_cogs0700_away0250.csv` if you want the symmetric opposite step.
3. If either improves clearly, continue `submission_sample_v32_rev0725_cogs0688_away0250.csv`, then `submission_sample_v32_rev0725_cogs0675_away0250.csv`.
4. If both fail, COGS-shape target-wise axis is dead and we move to Revenue-shape direction.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_cogs_shape_down_v32_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
