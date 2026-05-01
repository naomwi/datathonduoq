from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, align_sample_shape, period_summary
from make_publiconly_sample_targetwise_v31 import BASE_COGS_AWAY_ALPHA, PRE_SAMPLE_BEST_FILE, build_candidate
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "publiconly_sample_revenue_shape_v34"
CURRENT_BEST_FILE = "submission_sample_v32_rev0725_cogs0650_away0250.csv"
CURRENT_BEST_SCORE = 698994.05843
BASE_REV_ALPHA = 0.725
BASE_COGS_ALPHA = 0.650

KNOWN_RESULTS = {
    "submission_sample_v30_a0725_ratio_away_sample0250.csv": 699376.32670,
    "submission_sample_v31_rev0725_cogs0750_away0250.csv": 699662.34515,
    "submission_sample_v32_rev0725_cogs0700_away0250.csv": 699167.79998,
    CURRENT_BEST_FILE: CURRENT_BEST_SCORE,
    "submission_sample_v34_rev08000_cogs06500_away0250.csv": 698898.26661,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def alpha_token(alpha: float) -> str:
    return f"{int(round(alpha * 10000)):05d}"


def summarize(
    rows: list[dict[str, object]],
    current: pd.DataFrame,
    frame: pd.DataFrame,
    filename: str,
    thesis: str,
    priority: int,
    rev_alpha: float,
    cogs_alpha: float = BASE_COGS_ALPHA,
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
            "rev_alpha": rev_alpha,
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


def revenue_shape_delta_profile(current: pd.DataFrame, candidates: pd.DataFrame, sample: pd.DataFrame) -> pd.DataFrame:
    out = []
    cur = add_segments(current)
    cand = add_segments(candidates)
    samp = add_segments(sample)
    for period in ["2023H1", "2023H2", "2024H1", "2024-07-01"]:
        cm = cur["period"].eq(period)
        out.append(
            {
                "period": period,
                "current_rev_sum": cur.loc[cm, "Revenue"].sum(),
                "candidate_rev_sum": cand.loc[cm, "Revenue"].sum(),
                "sample_rev_sum": samp.loc[samp["period"].eq(period), "Revenue"].sum(),
                "mean_abs_candidate_rev_delta": (cand.loc[cm, "Revenue"] - cur.loc[cm, "Revenue"]).abs().mean(),
                "candidate_peak_day": cand.loc[cm].sort_values("Revenue", ascending=False)["Date"].iloc[0],
                "sample_peak_day": samp.loc[samp["period"].eq(period)].sort_values("Revenue", ascending=False)["Date"].iloc[0],
            }
        )
    return pd.DataFrame(out)


def main() -> None:
    run_dir = make_run_dir()
    pre_base = add_segments(pd.read_csv(DATASET_DIR / PRE_SAMPLE_BEST_FILE, parse_dates=["Date"]))
    current = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    sample = add_segments(pd.read_csv(DATASET_DIR / SAMPLE_FILE, parse_dates=["Date"]))
    shape_both = align_sample_shape(pre_base, sample, ("Revenue", "COGS"))

    specs = [
        (0.7000, "Revenue sample-shape alpha down; tests if current Revenue is over-shaped", 1),
        (0.7500, "Revenue sample-shape alpha up one step", 2),
        (0.7750, "Revenue sample-shape alpha up two steps", 3),
        (0.8000, "high-variance Revenue sample-shape alpha up", 4),
        (0.8500, "very high-variance Revenue sample-shape alpha up", 5),
        (0.6500, "high-variance Revenue alpha down", 6),
        (0.6000, "extreme Revenue alpha down diagnostic", 7),
        (0.9000, "extreme Revenue alpha up diagnostic", 8),
    ]

    rows: list[dict[str, object]] = []
    profiles = []
    for rev_alpha, thesis, priority in specs:
        filename = f"submission_sample_v34_rev{alpha_token(rev_alpha)}_cogs06500_away0250.csv"
        frame = build_candidate(pre_base, shape_both, sample, rev_alpha, BASE_COGS_ALPHA)
        summarize(rows, current, frame, filename, thesis, priority, rev_alpha)
        if rev_alpha in {0.7000, 0.8000, 0.8500}:
            prof = revenue_shape_delta_profile(current, frame, sample)
            prof.insert(0, "filename", filename)
            prof.insert(1, "rev_alpha", rev_alpha)
            profiles.append(prof)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest["best_case_score_if_direction_correct"] = CURRENT_BEST_SCORE - manifest[
        "directional_best_case_gain_vs_current"
    ]
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    if profiles:
        pd.concat(profiles, ignore_index=True).to_csv(run_dir / "revenue_shape_delta_profiles.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_best_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)

    known = pd.Series(KNOWN_RESULTS, name="public_score")
    cogs_shape_gain = KNOWN_RESULTS["submission_sample_v32_rev0725_cogs0700_away0250.csv"] - CURRENT_BEST_SCORE
    report = f"""# Public-Only Sample Revenue Shape V34

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known results:

{known.to_markdown()}

Interpretation:

- COGS-shape down from `0.700` to `0.650` improved only `{cogs_shape_gain:.5f}`, so the COGS-shape axis is becoming low-yield.
- To reach `67x`, we need a target-wise Revenue-shape move because it can change roughly `7k-50k` score-equivalent if the direction is right.
- These candidates preserve period totals and keep the current best COGS setup: `COGS alpha=0.650`, `COGS-away=0.250`.

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. Submit `submission_sample_v34_rev08000_cogs06500_away0250.csv` if prioritizing a real jump toward `67x`.
2. Submit `submission_sample_v34_rev07500_cogs06500_away0250.csv` if prioritizing lower risk.
3. If Revenue-up fails, test the opposite with `submission_sample_v34_rev07000_cogs06500_away0250.csv`.
4. Do not continue COGS-shape micro unless Revenue-shape fails both directions.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_revenue_shape_v34_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
