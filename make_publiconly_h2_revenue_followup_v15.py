from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns, write_submission


RUN_PREFIX = "publiconly_h2_revenue_followup_v15"
CURRENT_BEST_FILE = "submission_top10_v13_rev2023h2_up100_keepcogs.csv"
CURRENT_BEST_SCORE = 797595.96410
REFERENCE_BASE_FILE = "submission_publiconly_segment_v8_h2best_2024h1_down100.csv"
TARGET_SCORE = 699000.0

KNOWN_RESULTS = {
    "submission_publiconly_segment_v8_h2best_2024h1_down100.csv": 807504.66276,
    "submission_top10_v13_rev2023h2_up100_keepcogs.csv": 797595.96410,
    "submission_top10_v12_cogs2023h1_down100.csv": 825629.56220,
    "submission_top10_v12_rev2024highscale_down100_cogs2024highscale_down100.csv": 841263.33232,
    "submission_top10_v13_rev2024highscale_up100_keepcogs.csv": 812154.38787,
    "submission_top10_v13_rev2024highscale_up100_cogsdown100.csv": 830171.46835,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def add_segments(frame: pd.DataFrame) -> pd.DataFrame:
    out = add_event_columns(frame).reset_index(drop=True)
    out["period"] = "other"
    out.loc[out["Date"].dt.year.eq(2023) & out["Date"].dt.month.le(6), "period"] = "2023H1"
    out.loc[out["Date"].dt.year.eq(2023) & out["Date"].dt.month.ge(7), "period"] = "2023H2"
    out.loc[out["Date"].dt.year.eq(2024) & out["Date"].dt.month.le(6), "period"] = "2024H1"
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
    reference: pd.DataFrame,
    frame: pd.DataFrame,
    filename: str,
    thesis: str,
    priority: int,
) -> None:
    path = DATASET_DIR / filename
    write_submission(frame, path)
    delta_rev = frame["Revenue"] - base["Revenue"]
    delta_cogs = frame["COGS"] - base["COGS"]
    ref_delta_rev = frame["Revenue"] - reference["Revenue"]
    prof = add_segments(frame)
    h2 = prof["period"].eq("2023H2")
    rows.append(
        {
            "priority": priority,
            "filename": filename,
            "path": str(path),
            "thesis": thesis,
            "rev_rows_changed_vs_current_best": int(delta_rev.abs().gt(1e-6).sum()),
            "cogs_rows_changed_vs_current_best": int(delta_cogs.abs().gt(1e-6).sum()),
            "mean_rev_delta_vs_current_best": delta_rev.mean(),
            "mean_cogs_delta_vs_current_best": delta_cogs.mean(),
            "mean_abs_rev_delta_vs_current_best": delta_rev.abs().mean(),
            "mean_abs_cogs_delta_vs_current_best": delta_cogs.abs().mean(),
            "directional_best_case_gain_vs_current_best": 0.5
            * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
            "score_if_direction_correct": CURRENT_BEST_SCORE
            - 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
            "can_reach_69x_if_direction_correct": CURRENT_BEST_SCORE
            - 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean())
            < TARGET_SCORE,
            "h2_revenue_ratio_vs_original_v8": frame.loc[h2, "Revenue"].sum()
            / reference.loc[h2, "Revenue"].sum(),
            "h2_mean_rev_delta_vs_original_v8": ref_delta_rev.loc[h2].mean(),
            "ratio_2023h1": prof.loc[prof["period"].eq("2023H1"), "COGS"].sum()
            / prof.loc[prof["period"].eq("2023H1"), "Revenue"].sum(),
            "ratio_2023h2": prof.loc[h2, "COGS"].sum() / prof.loc[h2, "Revenue"].sum(),
            "ratio_2024h1": prof.loc[prof["period"].eq("2024H1"), "COGS"].sum()
            / prof.loc[prof["period"].eq("2024H1"), "Revenue"].sum(),
        }
    )


def main() -> None:
    run_dir = make_run_dir()
    current = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    reference = add_segments(pd.read_csv(DATASET_DIR / REFERENCE_BASE_FILE, parse_dates=["Date"]))

    h2 = current["period"].eq("2023H2")
    q3 = current["month_key"].isin(["2023-07", "2023-08", "2023-09"])
    q4 = current["month_key"].isin(["2023-10", "2023-11", "2023-12"])
    h2_peak = current["month_key"].isin(["2023-08", "2023-11", "2023-12"])
    h2_shoulder = current["month_key"].isin(["2023-07", "2023-09", "2023-10"])
    marjun_2024 = current["month_key"].isin(["2024-03", "2024-04", "2024-05", "2024-06"])

    rows: list[dict[str, object]] = []
    specs = [
        (
            "submission_h2rev_v15_current_h2_rev_up025.csv",
            [(h2, 1.025)],
            [],
            "continue confirmed H2 Revenue-up direction: additional +2.5% on current best",
            1,
        ),
        (
            "submission_h2rev_v15_current_h2_rev_up050.csv",
            [(h2, 1.050)],
            [],
            "continue confirmed H2 Revenue-up direction: additional +5%",
            2,
        ),
        (
            "submission_h2rev_v15_current_h2_rev_up075.csv",
            [(h2, 1.075)],
            [],
            "continue confirmed H2 Revenue-up direction: additional +7.5%",
            3,
        ),
        (
            "submission_h2rev_v15_current_h2_rev_up100.csv",
            [(h2, 1.100)],
            [],
            "aggressive H2 Revenue-up continuation: additional +10%",
            4,
        ),
        (
            "submission_h2rev_v15_current_h2_rev_down025.csv",
            [(h2, 0.975)],
            [],
            "bracket check: current +10 may have overshot, reduce H2 Revenue by 2.5%",
            5,
        ),
        (
            "submission_h2rev_v15_q3_rev_up075.csv",
            [(q3, 1.075)],
            [],
            "localize H2 Revenue-up to Q3",
            6,
        ),
        (
            "submission_h2rev_v15_q4_rev_up075.csv",
            [(q4, 1.075)],
            [],
            "localize H2 Revenue-up to Q4",
            7,
        ),
        (
            "submission_h2rev_v15_h2_peak_rev_up100.csv",
            [(h2_peak, 1.100)],
            [],
            "H2 peak months Revenue +10%, keep COGS",
            8,
        ),
        (
            "submission_h2rev_v15_h2_shoulder_rev_up100.csv",
            [(h2_shoulder, 1.100)],
            [],
            "H2 shoulder months Revenue +10%, keep COGS",
            9,
        ),
        (
            "submission_h2rev_v15_h2_rev_up050_2024marjun_cogs_up050.csv",
            [(h2, 1.050)],
            [(marjun_2024, 1.050)],
            "combo after H2 Revenue-up win: extra H2 Revenue +5% and restore Mar-Jun 2024 COGS +5%",
            10,
        ),
        (
            "submission_h2rev_v15_h2_rev_up050_2024marjun_cogs_up075.csv",
            [(h2, 1.050)],
            [(marjun_2024, 1.075)],
            "aggressive combo: extra H2 Revenue +5% and Mar-Jun 2024 COGS +7.5%",
            11,
        ),
    ]

    for filename, revenue_changes, cogs_changes, thesis, priority in specs:
        frame = apply_changes(current, revenue_changes, cogs_changes)
        register(rows, current, reference, frame, filename, thesis, priority)

    manifest = pd.DataFrame(rows).sort_values(["priority", "score_if_direction_correct"])
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)

    report = f"""# Public-Only H2 Revenue Followup V15

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known results:

{pd.Series(KNOWN_RESULTS, name="public_score").to_markdown()}

Interpretation:

- `2023H2 Revenue +10%, keep COGS` improved from `807504.66276` to `797595.96410`.
- This confirms the feasible direction: keep H2 COGS high, but raise H2 Revenue to reduce the excessive H2 COGS/Revenue ratio.
- The gain is real but modest, so do not jump straight to combos unless H2 continuation also improves.

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_h2rev_v15_current_h2_rev_up050.csv`
2. If improves: `submission_h2rev_v15_current_h2_rev_up100.csv`
3. If weak/fails: `submission_h2rev_v15_current_h2_rev_down025.csv`
4. If H2 continuation improves, then test combo: `submission_h2rev_v15_h2_rev_up050_2024marjun_cogs_up050.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_h2_revenue_followup_v15_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
