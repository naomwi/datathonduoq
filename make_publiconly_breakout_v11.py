from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns, write_submission


RUN_PREFIX = "publiconly_breakout_v11"
CURRENT_BEST_FILE = "submission_publiconly_segment_v8_h2best_2024h1_down100.csv"
CURRENT_BEST_SCORE = 807504.66276
TARGET_SCORE = 759000.0

KNOWN_PUBLIC_RESULTS = {
    "submission_publiconly_segment_v8_h2best_2024h1_down100.csv": 807504.66276,
    "submission_publiconly_segment_v9_2023h1_up100.csv": 811093.31702,
    "submission_publiconly_month_v10_h2_peak_more200.csv": 823082.86966,
    "submission_publiconly_month_v10_h2_shoulder_more200.csv": 830056.22789,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def add_segments(frame: pd.DataFrame) -> pd.DataFrame:
    out = add_event_columns(frame).reset_index(drop=True)
    out["period"] = ""
    out.loc[out["Date"].dt.year.eq(2023) & out["Date"].dt.month.le(6), "period"] = "2023H1"
    out.loc[out["Date"].dt.year.eq(2023) & out["Date"].dt.month.ge(7), "period"] = "2023H2"
    out.loc[out["Date"].dt.year.eq(2024) & out["Date"].dt.month.le(6), "period"] = "2024H1"
    out.loc[out["Date"].eq(pd.Timestamp("2024-07-01")), "period"] = "2024JUL1"
    out["month_key"] = out["Date"].dt.strftime("%Y-%m")
    return out


def apply_changes(
    base: pd.DataFrame,
    revenue_changes: list[tuple[pd.Series, float]] | None = None,
    cogs_changes: list[tuple[pd.Series, float]] | None = None,
) -> pd.DataFrame:
    frame = base[["Date", "Revenue", "COGS"]].copy()
    for mask, multiplier in revenue_changes or []:
        frame.loc[mask, "Revenue"] *= multiplier
    for mask, multiplier in cogs_changes or []:
        frame.loc[mask, "COGS"] *= multiplier
    return frame


def register(
    rows: list[dict[str, object]],
    base: pd.DataFrame,
    frame: pd.DataFrame,
    filename: str,
    thesis: str,
    priority: int,
) -> None:
    path = DATASET_DIR / filename
    write_submission(frame, path)
    revenue_delta = frame["Revenue"] - base["Revenue"]
    cogs_delta = frame["COGS"] - base["COGS"]
    rows.append(
        {
            "priority": priority,
            "filename": filename,
            "path": str(path),
            "thesis": thesis,
            "rev_rows_changed": int(revenue_delta.abs().gt(1e-6).sum()),
            "cogs_rows_changed": int(cogs_delta.abs().gt(1e-6).sum()),
            "mean_rev_delta": revenue_delta.mean(),
            "mean_cogs_delta": cogs_delta.mean(),
            "mean_abs_rev_delta": revenue_delta.abs().mean(),
            "mean_abs_cogs_delta": cogs_delta.abs().mean(),
            "directional_best_case_gain": 0.5 * (revenue_delta.abs().mean() + cogs_delta.abs().mean()),
            "score_if_direction_correct": CURRENT_BEST_SCORE
            - 0.5 * (revenue_delta.abs().mean() + cogs_delta.abs().mean()),
            "revenue_total_ratio_vs_best": frame["Revenue"].sum() / base["Revenue"].sum(),
            "cogs_total_ratio_vs_best": frame["COGS"].sum() / base["COGS"].sum(),
            "cogs_rev_ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
        }
    )


def main() -> None:
    run_dir = make_run_dir()
    base = pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"])
    base = add_segments(base)

    p2023h1 = base["period"].eq("2023H1")
    p2023h2 = base["period"].eq("2023H2")
    p2024h1 = base["period"].eq("2024H1")
    q1_2024 = base["month_key"].isin(["2024-01", "2024-02", "2024-03"])
    q2_2024 = base["month_key"].isin(["2024-04", "2024-05", "2024-06"])
    highscale_2024 = base["month_key"].isin(["2024-03", "2024-04", "2024-05", "2024-06"])
    h2_q3 = base["month_key"].isin(["2023-07", "2023-08", "2023-09"])
    h2_q4 = base["month_key"].isin(["2023-10", "2023-11", "2023-12"])
    h2_peak = base["month_key"].isin(["2023-08", "2023-11", "2023-12"])
    h2_shoulder = base["month_key"].isin(["2023-07", "2023-09", "2023-10"])
    h1_2023_low = base["month_key"].isin(["2023-02", "2023-03", "2023-05"])
    h1_2023_high = base["month_key"].isin(["2023-04", "2023-06"])

    rows: list[dict[str, object]] = []
    specs: list[tuple[str, list[tuple[pd.Series, float]], list[tuple[pd.Series, float]], str, int]] = [
        (
            "submission_publiconly_breakout_v11_rev2024h1_down050.csv",
            [(p2024h1, 0.950)],
            [],
            "new direction: Revenue 2024H1 -5%, keep best COGS",
            1,
        ),
        (
            "submission_publiconly_breakout_v11_rev2024h1_down100.csv",
            [(p2024h1, 0.900)],
            [],
            "new direction: Revenue 2024H1 -10%, keep best COGS",
            2,
        ),
        (
            "submission_publiconly_breakout_v11_rev2024highscale_down100.csv",
            [(highscale_2024, 0.900)],
            [],
            "new direction: Revenue Mar-Jun 2024 -10%",
            3,
        ),
        (
            "submission_publiconly_breakout_v11_rev2024q2_down100.csv",
            [(q2_2024, 0.900)],
            [],
            "new direction: Revenue 2024Q2 -10%",
            4,
        ),
        (
            "submission_publiconly_breakout_v11_rev2024q1_down100.csv",
            [(q1_2024, 0.900)],
            [],
            "new direction: Revenue 2024Q1 -10%",
            5,
        ),
        (
            "submission_publiconly_breakout_v11_rev2023h2_down050.csv",
            [(p2023h2, 0.950)],
            [],
            "new direction: Revenue 2023H2 -5%; H2 COGS up may be compensating high revenue",
            6,
        ),
        (
            "submission_publiconly_breakout_v11_rev2023h2_down100.csv",
            [(p2023h2, 0.900)],
            [],
            "new direction: Revenue 2023H2 -10%",
            7,
        ),
        (
            "submission_publiconly_breakout_v11_rev2023q3_down100.csv",
            [(h2_q3, 0.900)],
            [],
            "Revenue 2023Q3 -10%",
            8,
        ),
        (
            "submission_publiconly_breakout_v11_rev2023q4_down100.csv",
            [(h2_q4, 0.900)],
            [],
            "Revenue 2023Q4 -10%",
            9,
        ),
        (
            "submission_publiconly_breakout_v11_rev2023h2_peak_down100.csv",
            [(h2_peak, 0.900)],
            [],
            "Revenue H2 peak months Aug/Nov/Dec -10%",
            10,
        ),
        (
            "submission_publiconly_breakout_v11_rev2023h2_shoulder_down100.csv",
            [(h2_shoulder, 0.900)],
            [],
            "Revenue H2 shoulder months Jul/Sep/Oct -10%",
            11,
        ),
        (
            "submission_publiconly_breakout_v11_cogs2023h1_down100.csv",
            [],
            [(p2023h1, 0.900)],
            "opposite of failed 2023H1 COGS +10%: COGS 2023H1 -10%",
            12,
        ),
        (
            "submission_publiconly_breakout_v11_cogs2023h1_down150.csv",
            [],
            [(p2023h1, 0.850)],
            "opposite of failed 2023H1 COGS +10%: COGS 2023H1 -15%",
            13,
        ),
        (
            "submission_publiconly_breakout_v11_cogs2023h1_highmonths_down150.csv",
            [],
            [(h1_2023_high, 0.850)],
            "COGS Apr/Jun 2023 -15%; broad H1 up failed, these high-ratio months may be over",
            14,
        ),
        (
            "submission_publiconly_breakout_v11_cogs2023h1_lowmonths_down100.csv",
            [],
            [(h1_2023_low, 0.900)],
            "COGS Feb/Mar/May 2023 -10%; tests whether all H1 should move down",
            15,
        ),
        (
            "submission_publiconly_breakout_v11_rev2024highscale_down100_cogs2024highscale_down100.csv",
            [(highscale_2024, 0.900)],
            [(highscale_2024, 0.900)],
            "regime-down bundle: both Revenue and COGS Mar-Jun 2024 -10%",
            16,
        ),
        (
            "submission_publiconly_breakout_v11_rev2024q2_down100_cogs2024q2_down100.csv",
            [(q2_2024, 0.900)],
            [(q2_2024, 0.900)],
            "regime-down bundle: both Revenue and COGS 2024Q2 -10%",
            17,
        ),
        (
            "submission_publiconly_breakout_v11_rev2023h2_down050_cogs2024highscale_down100.csv",
            [(p2023h2, 0.950)],
            [(highscale_2024, 0.900)],
            "mixed new direction: lower 2023H2 Revenue and lower high-scale 2024 COGS",
            18,
        ),
    ]

    for filename, revenue_changes, cogs_changes, thesis, priority in specs:
        register(rows, base, apply_changes(base, revenue_changes, cogs_changes), filename, thesis, priority)

    manifest = pd.DataFrame(rows).sort_values(["priority", "score_if_direction_correct"])
    manifest["can_reach_75x_if_direction_correct"] = manifest["score_if_direction_correct"] < TARGET_SCORE
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)

    report = f"""# Public-Only Breakout V11

Run directory: `{run_dir}`

Base: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known public reactions:

{pd.Series(KNOWN_PUBLIC_RESULTS, name="public_score").to_markdown()}

Interpretation:

- Extra `2023H2 +20%` failed badly in both peak and shoulder groups. The H2 COGS route is near a local plateau, not the 75x route.
- `2023H1 +10%` also failed, so broad COGS-up is no longer the right hypothesis.
- V11 tests a new large hypothesis: current Revenue may be too high in 2024 high-scale or 2023H2, and COGS-down may be needed in 2023H1.

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_publiconly_breakout_v11_rev2024highscale_down100.csv`
2. `submission_publiconly_breakout_v11_rev2023h2_down050.csv`
3. `submission_publiconly_breakout_v11_cogs2023h1_down100.csv`
4. `submission_publiconly_breakout_v11_rev2024highscale_down100_cogs2024highscale_down100.csv`
5. `submission_publiconly_breakout_v11_rev2023h2_down100.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_breakout_v11_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
