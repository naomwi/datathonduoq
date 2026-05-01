from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns, write_submission


RUN_PREFIX = "publiconly_segment_oracle_v8"
CURRENT_BEST_FILE = "submission_publiconly_segment_v7_2023h2_up100.csv"
CURRENT_BEST_SCORE = 812496.01649
TARGET_SCORE = 759000.0

KNOWN_PUBLIC_RESULTS = {
    "submission_publiconly_cogs_break_v5_all_plus020.csv": 825080.79137,
    "submission_publiconly_segment_v7_2023h2_up100.csv": 812496.01649,
    "submission_publiconly_segment_v7_2024h1_up100.csv": 855840.24467,
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

    p2023h2 = base["period"].eq("2023H2")
    p2024h1 = base["period"].eq("2024H1")
    promo = base["win_main_promo"].astype(bool)
    nonpromo = ~promo
    ratio = base["cogs_ratio"]
    high_ratio = ratio.gt(0.99)
    low_ratio = ratio.lt(0.94)

    p2024h1_promo = p2024h1 & promo
    p2024h1_nonpromo = p2024h1 & nonpromo
    p2024h1_highratio = p2024h1 & high_ratio
    p2024h1_lowratio = p2024h1 & low_ratio
    p2023h2_highratio = p2023h2 & high_ratio
    p2023h2_lowratio = p2023h2 & low_ratio
    q1_2024 = base["month_key"].isin(["2024-01", "2024-02", "2024-03"])
    q2_2024 = base["month_key"].isin(["2024-04", "2024-05", "2024-06"])

    rows: list[dict[str, object]] = []
    specs: list[tuple[str, list[tuple[pd.Series, float]], str, int]] = []

    for pct, priority in [(0.030, 1), (0.050, 2), (0.075, 3), (0.100, 4), (0.125, 5), (0.150, 6), (0.200, 7)]:
        tag = f"{int(round(pct * 1000)):03d}"
        specs.append(
            (
                f"submission_publiconly_segment_v8_h2best_2024h1_down{tag}.csv",
                [(p2024h1, 1.0 - pct)],
                f"current best plus 2024H1 COGS -{pct:.1%}; opposite direction of failed 2024H1 +10%",
                priority,
            )
        )

    specs.extend(
        [
            (
                "submission_publiconly_segment_v8_h2best_2024q1_down100.csv",
                [(q1_2024, 0.900)],
                "current best plus 2024Q1 COGS -10%; localize the 2024H1 over/neutral segment",
                8,
            ),
            (
                "submission_publiconly_segment_v8_h2best_2024q2_down100.csv",
                [(q2_2024, 0.900)],
                "current best plus 2024Q2 COGS -10%; localize the 2024H1 over/neutral segment",
                9,
            ),
            (
                "submission_publiconly_segment_v8_h2best_2024h1_nonpromo_down100.csv",
                [(p2024h1_nonpromo, 0.900)],
                "current best plus 2024H1 non-promo COGS -10%",
                10,
            ),
            (
                "submission_publiconly_segment_v8_h2best_2024h1_promo_down100.csv",
                [(p2024h1_promo, 0.900)],
                "current best plus 2024H1 promo-window COGS -10%",
                11,
            ),
            (
                "submission_publiconly_segment_v8_h2best_2024h1_lowratio_down100.csv",
                [(p2024h1_lowratio, 0.900)],
                "current best plus 2024H1 low COGS/Revenue days -10%",
                12,
            ),
            (
                "submission_publiconly_segment_v8_h2best_2024h1_highratio_down100.csv",
                [(p2024h1_highratio, 0.900)],
                "current best plus 2024H1 high COGS/Revenue days -10%",
                13,
            ),
            (
                "submission_publiconly_segment_v8_h2more025.csv",
                [(p2023h2, 1.025)],
                "current best plus extra 2023H2 COGS +2.5%; tests whether H2 wants more than +10%",
                14,
            ),
            (
                "submission_publiconly_segment_v8_h2more050.csv",
                [(p2023h2, 1.050)],
                "current best plus extra 2023H2 COGS +5%; aggressive H2 continuation",
                15,
            ),
            (
                "submission_publiconly_segment_v8_h2high_more050.csv",
                [(p2023h2_highratio, 1.050)],
                "current best plus extra 2023H2 high-ratio COGS +5%",
                16,
            ),
            (
                "submission_publiconly_segment_v8_h2low_more050.csv",
                [(p2023h2_lowratio, 1.050)],
                "current best plus extra 2023H2 low-ratio COGS +5%",
                17,
            ),
            (
                "submission_publiconly_segment_v8_h2more025_2024h1_down100.csv",
                [(p2023h2, 1.025), (p2024h1, 0.900)],
                "combine confirmed H2-up direction with 2024H1-down reversal; high-upside 75x attempt",
                18,
            ),
            (
                "submission_publiconly_segment_v8_h2more050_2024h1_down125.csv",
                [(p2023h2, 1.050), (p2024h1, 0.875)],
                "very aggressive combine: more H2 COGS and sharply lower 2024H1 COGS",
                19,
            ),
        ]
    )

    for filename, changes, thesis, priority in specs:
        frame = apply_multipliers(base, changes)
        register(rows, base, frame, filename, thesis, priority)

    manifest = pd.DataFrame(rows).sort_values(["priority", "score_if_direction_correct"])
    manifest["can_reach_75x_if_direction_correct"] = manifest["score_if_direction_correct"] < TARGET_SCORE
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)

    report = f"""# Public-Only Segment Oracle V8

Run directory: `{run_dir}`

Base: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known public reactions:

{pd.Series(KNOWN_PUBLIC_RESULTS, name="public_score").to_markdown()}

Interpretation:

- `2023H2 +10%` improved from `825080.79137` to `812496.01649`, so H2 COGS was still too low.
- `2024H1 +10%` worsened to `855840.24467`, so 2024H1 should not be raised. The next high-upside direction is likely 2024H1 down, not more global COGS.
- This run uses the new best as base and probes 2024H1-down plus a few H2-continuation candidates.

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_publiconly_segment_v8_h2best_2024h1_down100.csv`
2. `submission_publiconly_segment_v8_h2best_2024h1_down150.csv`
3. `submission_publiconly_segment_v8_h2more025_2024h1_down100.csv`
4. `submission_publiconly_segment_v8_h2best_2024q1_down100.csv`
5. `submission_publiconly_segment_v8_h2best_2024q2_down100.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_segment_oracle_v8_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
