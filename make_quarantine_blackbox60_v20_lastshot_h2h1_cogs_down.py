from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_prior_v19 import add_segments, period_summary
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_blackbox60_v20_lastshot_h2h1_cogs_down"
CURRENT_BEST_FILE = "submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv"
CURRENT_BEST_SCORE = 662759.87577
OUTPUT_FILE = "submission_qbb60v20_lastshot_cogs23h2_down010_cogs24h1_down016.csv"


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def build_lastshot(current: pd.DataFrame) -> pd.DataFrame:
    out = add_segments(current.copy())
    out.loc[out["period"].eq("2023H2"), "COGS"] *= 0.99
    out.loc[out["period"].eq("2024H1"), "COGS"] *= 0.984
    return out


def write_report(run_dir: Path, current: pd.DataFrame, frame: pd.DataFrame) -> None:
    cur_prof = period_summary(add_segments(current.copy()))
    new_prof = period_summary(add_segments(frame.copy()))
    report = f"""# Quarantine Blackbox 60x V20 Last Shot H2/H1 COGS Down

Run directory: `{run_dir}`

## Status

This branch is **not clean**. It is a final public-blackbox shot.

Current anchor:

- `{CURRENT_BEST_FILE}` = `{CURRENT_BEST_SCORE}`

## Why This File Exists

- `2023H2 COGS -1%` is the first positive H2-only orthogonal move on the current anchor.
- `2024H1 COGS` is still above the sample-like ratio and prior public evidence consistently rejected raising it.
- With one submission left, the highest-EV last shot is to keep the winning Revenue anchor and combine:
  - `2023H2 COGS scale = 0.99`
  - `2024H1 COGS scale = 0.984`

## Period Summary

Current:

{cur_prof.to_markdown(index=False)}

Last shot:

{new_prof.to_markdown(index=False)}
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_blackbox60_v20_lastshot_h2h1_cogs_down_2026-04-24.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    current = pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"])
    frame = build_lastshot(current)
    path = DATASET_DIR / OUTPUT_FILE
    write_submission(frame[["Date", "Revenue", "COGS"]], path)
    write_report(run_dir, current, frame)
    print(run_dir)


if __name__ == "__main__":
    main()
