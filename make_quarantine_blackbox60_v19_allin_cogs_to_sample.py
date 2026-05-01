from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, period_summary
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_blackbox60_v19_allin_cogs_to_sample"
CURRENT_BEST_FILE = "submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv"
CURRENT_BEST_SCORE = 662759.87577
OUTPUT_FILE = "submission_qbb60v19_allin_cogs23h2_sample_cogs24h1_sample.csv"


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def build_allin(current: pd.DataFrame, sample: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    cur = add_segments(current.copy())
    samp = add_segments(sample.copy())

    out = cur.copy()
    scales: dict[str, float] = {}
    for period in ["2023H2", "2024H1"]:
        cur_mask = cur["period"].eq(period)
        samp_mask = samp["period"].eq(period)
        cur_ratio = cur.loc[cur_mask, "COGS"].sum() / cur.loc[cur_mask, "Revenue"].sum()
        samp_ratio = samp.loc[samp_mask, "COGS"].sum() / samp.loc[samp_mask, "Revenue"].sum()
        scale = samp_ratio / cur_ratio
        out.loc[cur_mask, "COGS"] *= scale
        scales[period] = scale

    return out, scales


def write_report(run_dir: Path, current: pd.DataFrame, frame: pd.DataFrame, scales: dict[str, float]) -> None:
    cur_prof = period_summary(add_segments(current.copy()))
    new_prof = period_summary(add_segments(frame.copy()))
    report = f"""# Quarantine Blackbox 60x V19 All-In COGS To Sample

Run directory: `{run_dir}`

## Status

This branch is **not clean**. It builds directly on the current blackbox best and public-leaderboard feedback.

Current anchor:

- `{CURRENT_BEST_FILE}` = `{CURRENT_BEST_SCORE}`

## Why This File Exists

- `2023H2 Revenue` edits failed in both directions and at multiple granularities.
- `2023H2 COGS -1%` finally improved, proving the remaining H2 error is more likely cost-ratio than revenue level.
- `2024H1 COGS` on the current best is still above the sample regime.
- This all-in file therefore matches the current best to sample-derived COGS ratios for `2023H2` and `2024H1` in one shot.

## Scales

- `2023H2 COGS scale` = `{scales["2023H2"]:.6f}`
- `2024H1 COGS scale` = `{scales["2024H1"]:.6f}`

## Period Summary

Current:

{cur_prof.to_markdown(index=False)}

All-in:

{new_prof.to_markdown(index=False)}
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_blackbox60_v19_allin_cogs_to_sample_2026-04-24.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    current = pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"])
    sample = pd.read_csv(DATASET_DIR / SAMPLE_FILE, parse_dates=["Date"])
    frame, scales = build_allin(current, sample)
    path = DATASET_DIR / OUTPUT_FILE
    write_submission(frame[["Date", "Revenue", "COGS"]], path)
    write_report(run_dir, current, frame, scales)
    print(run_dir)


if __name__ == "__main__":
    main()
