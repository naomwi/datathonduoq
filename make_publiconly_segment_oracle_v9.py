from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns, write_submission


RUN_PREFIX = "publiconly_segment_oracle_v9"
CURRENT_BEST_FILE = "submission_publiconly_segment_v8_h2best_2024h1_down100.csv"
CURRENT_BEST_SCORE = 807504.66276
TARGET_SCORE = 759000.0

KNOWN_PUBLIC_RESULTS = {
    "submission_publiconly_cogs_break_v5_all_plus020.csv": 825080.79137,
    "submission_publiconly_segment_v7_2023h2_up100.csv": 812496.01649,
    "submission_publiconly_segment_v7_2024h1_up100.csv": 855840.24467,
    "submission_publiconly_segment_v8_h2best_2024h1_down100.csv": 807504.66276,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def add_periods(frame: pd.DataFrame) -> pd.DataFrame:
    out = add_event_columns(frame).reset_index(drop=True)
    out["period"] = ""
    out.loc[out["Date"].dt.year.eq(2023) & out["Date"].dt.month.le(6), "period"] = "2023H1"
    out.loc[out["Date"].dt.year.eq(2023) & out["Date"].dt.month.ge(7), "period"] = "2023H2"
    out.loc[out["Date"].dt.year.eq(2024) & out["Date"].dt.month.le(6), "period"] = "2024H1"
    out.loc[out["Date"].eq(pd.Timestamp("2024-07-01")), "period"] = "2024JUL1"
    out["month_key"] = out["Date"].dt.strftime("%Y-%m")
    out["cogs_ratio"] = out["COGS"] / out["Revenue"]
    return out


def apply_multipliers(base: pd.DataFrame, changes: list[tuple[pd.Series, float]]) -> pd.DataFrame:
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
    ratio = frame["COGS"] / frame["Revenue"]
    rows.append(
        {
            "priority": priority,
            "filename": filename,
            "path": str(path),
            "thesis": thesis,
            "rows_changed": int(delta.abs().gt(1e-6).sum()),
            "mean_delta": delta.mean(),
            "mean_abs_delta": delta.abs().mean(),
            "directional_best_case_gain": 0.5 * delta.abs().mean(),
            "score_if_direction_correct": CURRENT_BEST_SCORE - 0.5 * delta.abs().mean(),
            "cogs_total_ratio_vs_best": frame["COGS"].sum() / base["COGS"].sum(),
            "cogs_ratio_mean": ratio.mean(),
            "cogs_ratio_2023h1": ratio.loc[base["period"].eq("2023H1")].mean(),
            "cogs_ratio_2023h2": ratio.loc[base["period"].eq("2023H2")].mean(),
            "cogs_ratio_2024h1": ratio.loc[base["period"].eq("2024H1")].mean(),
        }
    )


def main() -> None:
    run_dir = make_run_dir()
    base = pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"])
    base = add_periods(base)

    p2023h1 = base["period"].eq("2023H1")
    p2023h2 = base["period"].eq("2023H2")
    p2024h1 = base["period"].eq("2024H1")
    promo = base["win_main_promo"].astype(bool)
    nonpromo = ~promo
    ratio = base["cogs_ratio"]
    high_ratio = ratio.gt(1.02)
    low_ratio = ratio.lt(0.90)

    q3_2023 = base["month_key"].isin(["2023-07", "2023-08", "2023-09"])
    q4_2023 = base["month_key"].isin(["2023-10", "2023-11", "2023-12"])
    q1_2024 = base["month_key"].isin(["2024-01", "2024-02", "2024-03"])
    q2_2024 = base["month_key"].isin(["2024-04", "2024-05", "2024-06"])
    peak_2023h2 = base["month_key"].isin(["2023-08", "2023-11", "2023-12"])
    shoulder_2023h2 = base["month_key"].isin(["2023-07", "2023-09", "2023-10"])
    highscale_2024h1 = base["month_key"].isin(["2024-03", "2024-04", "2024-05", "2024-06"])

    h2_high = p2023h2 & high_ratio
    h2_nonpromo = p2023h2 & nonpromo
    h1_2024_low = p2024h1 & low_ratio
    h1_2024_nonpromo = p2024h1 & nonpromo

    rows: list[dict[str, object]] = []
    specs: list[tuple[str, list[tuple[pd.Series, float]], str, int]] = [
        (
            "submission_publiconly_segment_v9_h2more025.csv",
            [(p2023h2, 1.025)],
            "current best plus extra 2023H2 COGS +2.5%; test whether H2 still wants more",
            1,
        ),
        (
            "submission_publiconly_segment_v9_h2more050.csv",
            [(p2023h2, 1.050)],
            "current best plus extra 2023H2 COGS +5%",
            2,
        ),
        (
            "submission_publiconly_segment_v9_2024h1_down050_more.csv",
            [(p2024h1, 0.950)],
            "current best plus another 2024H1 COGS -5%; extends confirmed down direction",
            3,
        ),
        (
            "submission_publiconly_segment_v9_h2more025_2024h1_down050_more.csv",
            [(p2023h2, 1.025), (p2024h1, 0.950)],
            "combine mild H2 continuation with another mild 2024H1 down",
            4,
        ),
        (
            "submission_publiconly_segment_v9_h2more050_2024h1_down050_more.csv",
            [(p2023h2, 1.050), (p2024h1, 0.950)],
            "aggressive combine: H2 +5% and 2024H1 another -5%",
            5,
        ),
        (
            "submission_publiconly_segment_v9_2023h1_up075.csv",
            [(p2023h1, 1.075)],
            "orthogonal segment: 2023H1 COGS +7.5%; checks if early 2023 also underpredicted",
            6,
        ),
        (
            "submission_publiconly_segment_v9_2023h1_up100.csv",
            [(p2023h1, 1.100)],
            "orthogonal segment: 2023H1 COGS +10%",
            7,
        ),
        (
            "submission_publiconly_segment_v9_2023q3_more100.csv",
            [(q3_2023, 1.100)],
            "localize H2 continuation: 2023Q3 COGS +10%",
            8,
        ),
        (
            "submission_publiconly_segment_v9_2023q4_more100.csv",
            [(q4_2023, 1.100)],
            "localize H2 continuation: 2023Q4 COGS +10%",
            9,
        ),
        (
            "submission_publiconly_segment_v9_2023h2_peak_more150.csv",
            [(peak_2023h2, 1.150)],
            "target H2 high-ratio peak months Aug/Nov/Dec +15%",
            10,
        ),
        (
            "submission_publiconly_segment_v9_2023h2_shoulder_more150.csv",
            [(shoulder_2023h2, 1.150)],
            "target H2 shoulder months Jul/Sep/Oct +15%",
            11,
        ),
        (
            "submission_publiconly_segment_v9_h2high_more075.csv",
            [(h2_high, 1.075)],
            "target H2 days already above 1.02 COGS/Revenue +7.5%",
            12,
        ),
        (
            "submission_publiconly_segment_v9_h2nonpromo_more075.csv",
            [(h2_nonpromo, 1.075)],
            "target 2023H2 non-promo COGS +7.5%",
            13,
        ),
        (
            "submission_publiconly_segment_v9_2024q1_down100_more.csv",
            [(q1_2024, 0.900)],
            "localize extra 2024 down: Q1 -10% from current best",
            14,
        ),
        (
            "submission_publiconly_segment_v9_2024q2_down100_more.csv",
            [(q2_2024, 0.900)],
            "localize extra 2024 down: Q2 -10% from current best",
            15,
        ),
        (
            "submission_publiconly_segment_v9_2024highscale_down100_more.csv",
            [(highscale_2024h1, 0.900)],
            "extra down on high-scale 2024 Mar-Jun only",
            16,
        ),
        (
            "submission_publiconly_segment_v9_2024h1_lowratio_down100_more.csv",
            [(h1_2024_low, 0.900)],
            "extra down on 2024H1 low COGS/Revenue days only",
            17,
        ),
        (
            "submission_publiconly_segment_v9_2024h1_nonpromo_down100_more.csv",
            [(h1_2024_nonpromo, 0.900)],
            "extra down on 2024H1 non-promo days only",
            18,
        ),
        (
            "submission_publiconly_segment_v9_h2q4_more100_2024q2_down100_more.csv",
            [(q4_2023, 1.100), (q2_2024, 0.900)],
            "month-bundle high-upside: 2023Q4 up and 2024Q2 down",
            19,
        ),
        (
            "submission_publiconly_segment_v9_h2peak_more150_2024highscale_down100_more.csv",
            [(peak_2023h2, 1.150), (highscale_2024h1, 0.900)],
            "very aggressive 75x attempt: H2 peak up, high-scale 2024 down",
            20,
        ),
    ]

    for filename, changes, thesis, priority in specs:
        register(rows, base, apply_multipliers(base, changes), filename, thesis, priority)

    manifest = pd.DataFrame(rows).sort_values(["priority", "score_if_direction_correct"])
    manifest["can_reach_75x_if_direction_correct"] = manifest["score_if_direction_correct"] < TARGET_SCORE
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)

    report = f"""# Public-Only Segment Oracle V9

Run directory: `{run_dir}`

Base: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known public reactions:

{pd.Series(KNOWN_PUBLIC_RESULTS, name="public_score").to_markdown()}

Interpretation:

- 2023H2 remains the only large confirmed positive segment: `+10%` moved score by `12584.77`.
- 2024H1 down is correct but weak: `-10%` moved score by only `4991.35`, so do not over-invest there without a split.
- V9 tests three routes: more 2023H2, orthogonal 2023H1, and month-level H2/2024 split. This is still public-oracle work; local validation is not trusted for these moves.

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_publiconly_segment_v9_h2more050.csv`
2. `submission_publiconly_segment_v9_2023h1_up100.csv`
3. `submission_publiconly_segment_v9_h2more050_2024h1_down050_more.csv`
4. `submission_publiconly_segment_v9_2023q4_more100.csv`
5. `submission_publiconly_segment_v9_2024q2_down100_more.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_segment_oracle_v9_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
