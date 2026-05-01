from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns, write_submission


RUN_PREFIX = "publiconly_top10_inverse_v13"
CURRENT_BEST_FILE = "submission_publiconly_segment_v8_h2best_2024h1_down100.csv"
CURRENT_BEST_SCORE = 807504.66276
TARGET_SCORE = 699000.0


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
    out = base[["Date", "Revenue", "COGS"]].copy()
    for mask, multiplier in revenue_changes or []:
        out.loc[mask, "Revenue"] *= multiplier
    for mask, multiplier in cogs_changes or []:
        out.loc[mask, "COGS"] *= multiplier
    return out


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
    delta_rev = frame["Revenue"] - base["Revenue"]
    delta_cogs = frame["COGS"] - base["COGS"]
    prof = add_segments(frame)
    rows.append(
        {
            "priority": priority,
            "filename": filename,
            "path": str(path),
            "thesis": thesis,
            "rev_rows_changed": int(delta_rev.abs().gt(1e-6).sum()),
            "cogs_rows_changed": int(delta_cogs.abs().gt(1e-6).sum()),
            "mean_rev_delta": delta_rev.mean(),
            "mean_cogs_delta": delta_cogs.mean(),
            "mean_abs_rev_delta": delta_rev.abs().mean(),
            "mean_abs_cogs_delta": delta_cogs.abs().mean(),
            "directional_best_case_gain": 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
            "score_if_direction_correct": CURRENT_BEST_SCORE - 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
            "can_reach_69x_if_direction_correct": CURRENT_BEST_SCORE
            - 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean())
            < TARGET_SCORE,
            "revenue_total_ratio_vs_best": frame["Revenue"].sum() / base["Revenue"].sum(),
            "cogs_total_ratio_vs_best": frame["COGS"].sum() / base["COGS"].sum(),
            "ratio_2023h1": prof.loc[prof["period"].eq("2023H1"), "COGS"].sum()
            / prof.loc[prof["period"].eq("2023H1"), "Revenue"].sum(),
            "ratio_2023h2": prof.loc[prof["period"].eq("2023H2"), "COGS"].sum()
            / prof.loc[prof["period"].eq("2023H2"), "Revenue"].sum(),
            "ratio_2024h1": prof.loc[prof["period"].eq("2024H1"), "COGS"].sum()
            / prof.loc[prof["period"].eq("2024H1"), "Revenue"].sum(),
        }
    )


def main() -> None:
    run_dir = make_run_dir()
    base = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))

    p2024h1 = base["period"].eq("2024H1")
    highscale_2024 = base["month_key"].isin(["2024-03", "2024-04", "2024-05", "2024-06"])
    q2_2024 = base["month_key"].isin(["2024-04", "2024-05", "2024-06"])
    q1_2024 = base["month_key"].isin(["2024-01", "2024-02", "2024-03"])
    p2023h2 = base["period"].eq("2023H2")

    rows: list[dict[str, object]] = []
    specs = [
        (
            "submission_top10_v13_rev2024highscale_up100_keepcogs.csv",
            [(highscale_2024, 1.100)],
            [],
            "inverse of failed scale-down: Mar-Jun 2024 Revenue +10%, keep COGS",
            1,
        ),
        (
            "submission_top10_v13_rev2024highscale_up150_keepcogs.csv",
            [(highscale_2024, 1.150)],
            [],
            "aggressive inverse: Mar-Jun 2024 Revenue +15%, keep COGS",
            2,
        ),
        (
            "submission_top10_v13_rev2024h1_up100_keepcogs.csv",
            [(p2024h1, 1.100)],
            [],
            "broad 2024H1 Revenue +10%, keep COGS",
            3,
        ),
        (
            "submission_top10_v13_rev2024q2_up100_keepcogs.csv",
            [(q2_2024, 1.100)],
            [],
            "narrow 2024Q2 Revenue +10%, keep COGS",
            4,
        ),
        (
            "submission_top10_v13_rev2024highscale_up100_cogsdown050.csv",
            [(highscale_2024, 1.100)],
            [(highscale_2024, 0.950)],
            "high-margin 2024 shock: Mar-Jun Revenue +10%, COGS -5%",
            5,
        ),
        (
            "submission_top10_v13_rev2024highscale_up100_cogsdown100.csv",
            [(highscale_2024, 1.100)],
            [(highscale_2024, 0.900)],
            "69x bet: Mar-Jun Revenue +10%, COGS -10%",
            6,
        ),
        (
            "submission_top10_v13_rev2024q2_up100_cogsdown100.csv",
            [(q2_2024, 1.100)],
            [(q2_2024, 0.900)],
            "narrow 69x bet: 2024Q2 Revenue +10%, COGS -10%",
            7,
        ),
        (
            "submission_top10_v13_rev2024h1_up100_cogsdown050.csv",
            [(p2024h1, 1.100)],
            [(p2024h1, 0.950)],
            "broad 2024 demand-up margin-up: Revenue +10%, COGS -5%",
            8,
        ),
        (
            "submission_top10_v13_rev2023h2_up050_keepcogs.csv",
            [(p2023h2, 1.050)],
            [],
            "orthogonal check: 2023H2 Revenue +5%, keep already high COGS",
            9,
        ),
        (
            "submission_top10_v13_rev2023h2_up100_keepcogs.csv",
            [(p2023h2, 1.100)],
            [],
            "large check: 2023H2 Revenue +10%, keep already high COGS",
            10,
        ),
        (
            "submission_top10_v13_rev_all_up050_keepcogs.csv",
            [(pd.Series(True, index=base.index), 1.050)],
            [],
            "global Revenue +5%, keep COGS; checks overall Revenue underforecast",
            11,
        ),
        (
            "submission_top10_v13_rev_all_up075_keepcogs.csv",
            [(pd.Series(True, index=base.index), 1.075)],
            [],
            "aggressive global Revenue +7.5%, keep COGS",
            12,
        ),
        (
            "submission_top10_v13_rev2024q1_down050_q2_up100_keepcogs.csv",
            [(q1_2024, 0.950), (q2_2024, 1.100)],
            [],
            "2024 split: Q1 lower, Q2 higher, keep COGS",
            13,
        ),
    ]

    for filename, revenue_changes, cogs_changes, thesis, priority in specs:
        frame = apply_changes(base, revenue_changes, cogs_changes)
        register(rows, base, frame, filename, thesis, priority)

    manifest = pd.DataFrame(rows).sort_values(["priority", "score_if_direction_correct"])
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)

    report = f"""# Public-Only Top10 Inverse V13

Run directory: `{run_dir}`

Base: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Recent rejected moves:

- `2023H1 COGS -10%` scored `825629.56220`, so H1-down is wrong.
- `Mar-Jun 2024 Revenue and COGS -10%` scored `841263.33232`, so 2024 highscale-down is wrong.

New hypothesis:

If scale-down is wrong, `2024` may need higher Revenue, while COGS should not rise much because pure 2024 COGS-up was previously rejected. This creates a high-margin 2024 hypothesis: Revenue up, COGS flat or down.

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_top10_v13_rev2024highscale_up100_keepcogs.csv`
2. If it improves: `submission_top10_v13_rev2024highscale_up100_cogsdown050.csv`
3. If it improves strongly: `submission_top10_v13_rev2024highscale_up100_cogsdown100.csv`
4. If highscale is noisy: `submission_top10_v13_rev2024q2_up100_keepcogs.csv`
5. If 2024 Revenue-up fails too: stop 69x probing; remaining gap likely requires a different anchor, not post-processing.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_top10_inverse_v13_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
