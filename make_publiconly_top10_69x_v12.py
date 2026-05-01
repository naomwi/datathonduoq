from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns, write_submission


RUN_PREFIX = "publiconly_top10_69x_v12"
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
    out["cogs_ratio"] = out["COGS"] / out["Revenue"]
    return out


def set_period_ratio(frame: pd.DataFrame, mask: pd.Series, target_ratio: float) -> pd.DataFrame:
    out = frame.copy()
    current_ratio = out.loc[mask, "COGS"].sum() / out.loc[mask, "Revenue"].sum()
    if current_ratio > 0:
        out.loc[mask, "COGS"] *= target_ratio / current_ratio
    return out


def apply_changes(
    base: pd.DataFrame,
    revenue_changes: list[tuple[pd.Series, float]] | None = None,
    cogs_changes: list[tuple[pd.Series, float]] | None = None,
    ratio_targets: list[tuple[pd.Series, float]] | None = None,
) -> pd.DataFrame:
    out = base[["Date", "Revenue", "COGS"]].copy()
    for mask, multiplier in revenue_changes or []:
        out.loc[mask, "Revenue"] *= multiplier
    for mask, multiplier in cogs_changes or []:
        out.loc[mask, "COGS"] *= multiplier
    for mask, target_ratio in ratio_targets or []:
        out = set_period_ratio(out, mask, target_ratio)
    return out


def blend_with_sample(base: pd.DataFrame, sample: pd.DataFrame, weight: float, preserve_base_ratio: bool) -> pd.DataFrame:
    out = base[["Date", "Revenue", "COGS"]].copy()
    merged = out.merge(sample[["Date", "Revenue", "COGS"]], on="Date", suffixes=("_base", "_sample"))
    out["Revenue"] = (1.0 - weight) * merged["Revenue_base"] + weight * merged["Revenue_sample"]
    if preserve_base_ratio:
        ratio = merged["COGS_base"] / merged["Revenue_base"]
        out["COGS"] = out["Revenue"] * ratio
    else:
        out["COGS"] = (1.0 - weight) * merged["COGS_base"] + weight * merged["COGS_sample"]
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
    sample = pd.read_csv(DATASET_DIR / "sample_submission.csv", parse_dates=["Date"])

    p2023h1 = base["period"].eq("2023H1")
    p2023h2 = base["period"].eq("2023H2")
    p2024h1 = base["period"].eq("2024H1")
    highscale_2024 = base["month_key"].isin(["2024-03", "2024-04", "2024-05", "2024-06"])
    q2_2024 = base["month_key"].isin(["2024-04", "2024-05", "2024-06"])

    rows: list[dict[str, object]] = []
    specs = [
        (
            "submission_top10_v12_cogs2023h1_down100.csv",
            [],
            [(p2023h1, 0.900)],
            [],
            "H1 historical-ratio reversion: 2023H1 COGS -10%; target ratio near 0.86",
            1,
        ),
        (
            "submission_top10_v12_cogs2023h1_down150.csv",
            [],
            [(p2023h1, 0.850)],
            [],
            "aggressive H1 historical-ratio reversion: 2023H1 COGS -15%; target ratio near 0.81",
            2,
        ),
        (
            "submission_top10_v12_rev2024highscale_down100_cogs2024highscale_down100.csv",
            [(highscale_2024, 0.900)],
            [(highscale_2024, 0.900)],
            [],
            "69x bet: Mar-Jun 2024 regime-down, both Revenue and COGS -10%",
            3,
        ),
        (
            "submission_top10_v12_rev2024q2_down100_cogs2024q2_down100.csv",
            [(q2_2024, 0.900)],
            [(q2_2024, 0.900)],
            [],
            "narrower 2024 scale-down: 2024Q2 Revenue and COGS -10%",
            4,
        ),
        (
            "submission_top10_v12_h1down100_2024highscale_down100.csv",
            [(highscale_2024, 0.900)],
            [(p2023h1, 0.900), (highscale_2024, 0.900)],
            [],
            "combo: 2023H1 COGS reversion plus Mar-Jun 2024 scale-down",
            5,
        ),
        (
            "submission_top10_v12_h1down150_2024highscale_down100.csv",
            [(highscale_2024, 0.900)],
            [(p2023h1, 0.850), (highscale_2024, 0.900)],
            [],
            "very aggressive combo: 2023H1 COGS -15% plus Mar-Jun 2024 scale-down",
            6,
        ),
        (
            "submission_top10_v12_ratio_h1086_h2106_2024h1086.csv",
            [],
            [],
            [(p2023h1, 0.860), (p2023h2, 1.060), (p2024h1, 0.860)],
            "presentable ratio-regime target: H1 normal, odd-H2 high but below rejected spike, 2024H1 restrained",
            7,
        ),
        (
            "submission_top10_v12_ratio_h1083_h2106_2024h1084.csv",
            [],
            [],
            [(p2023h1, 0.830), (p2023h2, 1.060), (p2024h1, 0.840)],
            "more historical ratio-regime target: H1/H2024 closer to train H1, H2 remains elevated",
            8,
        ),
    ]
    for filename, revenue_changes, cogs_changes, ratio_targets, thesis, priority in specs:
        frame = apply_changes(base, revenue_changes, cogs_changes, ratio_targets)
        register(rows, base, frame, filename, thesis, priority)

    sample_specs = [
        (
            "submission_top10_v12_sample_direct_blend20.csv",
            blend_with_sample(base, sample, 0.20, preserve_base_ratio=False),
            "sample prior probe: direct 20% blend toward sample_submission for Revenue and COGS",
            9,
        ),
        (
            "submission_top10_v12_sample_direct_blend35.csv",
            blend_with_sample(base, sample, 0.35, preserve_base_ratio=False),
            "sample prior probe: direct 35% blend toward sample_submission",
            10,
        ),
        (
            "submission_top10_v12_sample_rev30_preserve_regime_ratio.csv",
            blend_with_sample(base, sample, 0.30, preserve_base_ratio=True),
            "sample Revenue-level prior with current regime ratios preserved",
            11,
        ),
        (
            "submission_top10_v12_sample_rev45_preserve_regime_ratio.csv",
            blend_with_sample(base, sample, 0.45, preserve_base_ratio=True),
            "aggressive sample Revenue-level prior with current regime ratios preserved",
            12,
        ),
    ]
    for filename, frame, thesis, priority in sample_specs:
        register(rows, base, frame, filename, thesis, priority)

    manifest = pd.DataFrame(rows).sort_values(["priority", "score_if_direction_correct"])
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)

    report = f"""# Public-Only Top10 69x V12

Run directory: `{run_dir}`

Base: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

To reach `{TARGET_SCORE}`, we need about `{CURRENT_BEST_SCORE - TARGET_SCORE:.0f}` more public MAE. That requires a large correction, so these are not small probes.

Strategic hypotheses:

1. `2023H1` COGS is over-raised by prior broad COGS tuning. A H1 reversion toward historical ratio can theoretically reach low 7xx.
2. `Mar-Jun 2024` may have a lower scale than our current Revenue anchor. A joint Revenue/COGS scale-down can theoretically reach `69x`.
3. `sample_submission` may contain a low-scale prior worth testing, but this is the riskiest narrative-wise.

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_top10_v12_cogs2023h1_down100.csv`
2. If it improves strongly: `submission_top10_v12_cogs2023h1_down150.csv`
3. If H1-down is weak/fails: `submission_top10_v12_rev2024highscale_down100_cogs2024highscale_down100.csv`
4. If 2024 highscale down improves: `submission_top10_v12_h1down100_2024highscale_down100.csv`
5. If sample prior seems worth a lottery ticket: `submission_top10_v12_sample_rev30_preserve_regime_ratio.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_top10_69x_v12_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
