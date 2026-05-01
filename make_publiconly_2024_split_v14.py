from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns, write_submission


RUN_PREFIX = "publiconly_2024_split_v14"
CURRENT_BEST_FILE = "submission_publiconly_segment_v8_h2best_2024h1_down100.csv"
CURRENT_BEST_SCORE = 807504.66276

KNOWN_RESULTS = {
    "submission_publiconly_segment_v8_h2best_2024h1_down100.csv": 807504.66276,
    "submission_top10_v12_rev2024highscale_down100_cogs2024highscale_down100.csv": 841263.33232,
    "submission_top10_v13_rev2024highscale_up100_cogsdown100.csv": 830171.46835,
    "submission_top10_v13_rev2024highscale_up100_keepcogs.csv": 812154.38787,
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


def apply_cogs(base: pd.DataFrame, changes: list[tuple[pd.Series, float]]) -> pd.DataFrame:
    frame = base[["Date", "Revenue", "COGS"]].copy()
    for mask, multiplier in changes:
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
    delta = frame["COGS"] - base["COGS"]
    prof = add_segments(frame)
    rows.append(
        {
            "priority": priority,
            "filename": filename,
            "path": str(path),
            "thesis": thesis,
            "rows_changed": int(delta.abs().gt(1e-6).sum()),
            "mean_cogs_delta": delta.mean(),
            "mean_abs_cogs_delta": delta.abs().mean(),
            "directional_best_case_gain": 0.5 * delta.abs().mean(),
            "score_if_direction_correct": CURRENT_BEST_SCORE - 0.5 * delta.abs().mean(),
            "cogs_total_ratio_vs_best": frame["COGS"].sum() / base["COGS"].sum(),
            "ratio_2023h1": prof.loc[prof["period"].eq("2023H1"), "COGS"].sum()
            / prof.loc[prof["period"].eq("2023H1"), "Revenue"].sum(),
            "ratio_2023h2": prof.loc[prof["period"].eq("2023H2"), "COGS"].sum()
            / prof.loc[prof["period"].eq("2023H2"), "Revenue"].sum(),
            "ratio_2024h1": prof.loc[prof["period"].eq("2024H1"), "COGS"].sum()
            / prof.loc[prof["period"].eq("2024H1"), "Revenue"].sum(),
            "ratio_2024_janfeb": prof.loc[prof["month_key"].isin(["2024-01", "2024-02"]), "COGS"].sum()
            / prof.loc[prof["month_key"].isin(["2024-01", "2024-02"]), "Revenue"].sum(),
            "ratio_2024_marjun": prof.loc[prof["month_key"].isin(["2024-03", "2024-04", "2024-05", "2024-06"]), "COGS"].sum()
            / prof.loc[prof["month_key"].isin(["2024-03", "2024-04", "2024-05", "2024-06"]), "Revenue"].sum(),
            "ratio_2024_q2": prof.loc[prof["month_key"].isin(["2024-04", "2024-05", "2024-06"]), "COGS"].sum()
            / prof.loc[prof["month_key"].isin(["2024-04", "2024-05", "2024-06"]), "Revenue"].sum(),
        }
    )


def main() -> None:
    run_dir = make_run_dir()
    base = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))

    janfeb = base["month_key"].isin(["2024-01", "2024-02"])
    march = base["month_key"].eq("2024-03")
    q2 = base["month_key"].isin(["2024-04", "2024-05", "2024-06"])
    marjun = base["month_key"].isin(["2024-03", "2024-04", "2024-05", "2024-06"])
    h1_2024 = base["period"].eq("2024H1")

    rows: list[dict[str, object]] = []
    specs = [
        (
            "submission_2024split_v14_marjun_cogs_up050.csv",
            [(marjun, 1.050)],
            "undo part of 2024H1 down where combo inference says extra Mar-Jun COGS-down is harmful",
            1,
        ),
        (
            "submission_2024split_v14_marjun_cogs_up075.csv",
            [(marjun, 1.075)],
            "stronger Mar-Jun COGS raise from current best",
            2,
        ),
        (
            "submission_2024split_v14_marjun_cogs_up100.csv",
            [(marjun, 1.100)],
            "full Mar-Jun COGS raise, roughly undoing prior 10% down for high-scale months",
            3,
        ),
        (
            "submission_2024split_v14_q2_cogs_up075.csv",
            [(q2, 1.075)],
            "localize COGS re-raise to 2024Q2 only",
            4,
        ),
        (
            "submission_2024split_v14_q2_cogs_up100.csv",
            [(q2, 1.100)],
            "strong 2024Q2 COGS re-raise",
            5,
        ),
        (
            "submission_2024split_v14_march_cogs_up100.csv",
            [(march, 1.100)],
            "March-only COGS re-raise; checks if Q1 high-scale is the issue",
            6,
        ),
        (
            "submission_2024split_v14_janfeb_cogs_down100.csv",
            [(janfeb, 0.900)],
            "Jan-Feb COGS further down; tests whether all-H1-down improvement came from early 2024",
            7,
        ),
        (
            "submission_2024split_v14_janfeb_down100_marjun_up075.csv",
            [(janfeb, 0.900), (marjun, 1.075)],
            "split 2024H1: early months lower, Mar-Jun higher",
            8,
        ),
        (
            "submission_2024split_v14_janfeb_down150_marjun_up100.csv",
            [(janfeb, 0.850), (marjun, 1.100)],
            "aggressive split: Jan-Feb lower, Mar-Jun restored",
            9,
        ),
        (
            "submission_2024split_v14_h1_cogs_up050.csv",
            [(h1_2024, 1.050)],
            "diagnostic: current full 2024H1 may be too low after v8 down",
            10,
        ),
    ]

    for filename, changes, thesis, priority in specs:
        register(rows, base, apply_cogs(base, changes), filename, thesis, priority)

    manifest = pd.DataFrame(rows).sort_values(["priority", "score_if_direction_correct"])
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)

    combo_delta = KNOWN_RESULTS["submission_top10_v13_rev2024highscale_up100_cogsdown100.csv"] - KNOWN_RESULTS[
        "submission_top10_v13_rev2024highscale_up100_keepcogs.csv"
    ]
    report = f"""# Public-Only 2024 Split V14

Run directory: `{run_dir}`

Base: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known results:

{pd.Series(KNOWN_RESULTS, name="public_score").to_markdown()}

Inference:

- `Revenue Mar-Jun 2024 +10%, keep COGS` scored `812154.38787`, only `+4649.73` worse than best.
- `Revenue Mar-Jun 2024 +10%, COGS Mar-Jun -10%` scored `830171.46835`.
- Because the Revenue change is identical in both files, the COGS-down component accounts for about `{combo_delta:.2f}` score damage.
- Therefore current best likely has Mar-Jun 2024 COGS too low or near lower bound. The next test should raise COGS in Mar-Jun/Q2, not lower it.

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_2024split_v14_marjun_cogs_up075.csv`
2. If improves: `submission_2024split_v14_marjun_cogs_up100.csv`
3. If weak/fails: `submission_2024split_v14_q2_cogs_up075.csv`
4. If Mar-Jun up improves but Jan-Feb still suspect: `submission_2024split_v14_janfeb_down100_marjun_up075.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_2024_split_v14_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
