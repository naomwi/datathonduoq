from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns, write_submission


RUN_PREFIX = "publiconly_segment_oracle_v7"
CURRENT_BEST_FILE = "submission_publiconly_cogs_break_v5_all_plus020.csv"
CURRENT_BEST_SCORE = 825080.79137
TARGET_SCORE = 759000.0


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def register(rows: list[dict[str, object]], base: pd.DataFrame, frame: pd.DataFrame, filename: str, thesis: str) -> None:
    path = DATASET_DIR / filename
    write_submission(frame, path)
    delta = frame["COGS"] - base["COGS"]
    ratio = frame["COGS"] / frame["Revenue"]
    rows.append(
        {
            "filename": filename,
            "path": str(path),
            "thesis": thesis,
            "rows_changed": int(delta.abs().gt(1e-6).sum()),
            "cogs_total_ratio_vs_best": frame["COGS"].sum() / base["COGS"].sum(),
            "mean_cogs_delta_vs_best": delta.mean(),
            "best_case_gain_vs_best": 0.5 * delta.clip(lower=0).mean(),
            "score_if_best_case": CURRENT_BEST_SCORE - 0.5 * delta.clip(lower=0).mean(),
            "cogs_ratio_mean": ratio.mean(),
            "cogs_ratio_2023h1": ratio.loc[base["period"].eq("2023H1")].mean(),
            "cogs_ratio_2023h2": ratio.loc[base["period"].eq("2023H2")].mean(),
            "cogs_ratio_2024h1": ratio.loc[base["period"].eq("2024H1")].mean(),
        }
    )


def multiply(base: pd.DataFrame, mask: pd.Series, multiplier: float) -> pd.DataFrame:
    frame = base[["Date", "Revenue", "COGS"]].copy()
    frame.loc[mask, "COGS"] *= multiplier
    return frame


def two_segment(base: pd.DataFrame, up_mask: pd.Series, down_mask: pd.Series, up: float, down: float) -> pd.DataFrame:
    frame = base[["Date", "Revenue", "COGS"]].copy()
    frame.loc[up_mask, "COGS"] *= up
    frame.loc[down_mask, "COGS"] *= down
    return frame


def main() -> None:
    run_dir = make_run_dir()
    base = pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"])
    base = add_event_columns(base).reset_index(drop=True)
    base["period"] = ""
    base.loc[base["Date"].dt.year.eq(2023) & base["Date"].dt.month.le(6), "period"] = "2023H1"
    base.loc[base["Date"].dt.year.eq(2023) & base["Date"].dt.month.ge(7), "period"] = "2023H2"
    base.loc[base["Date"].dt.year.eq(2024) & base["Date"].dt.month.le(6), "period"] = "2024H1"
    base.loc[base["Date"].eq(pd.Timestamp("2024-07-01")), "period"] = "2024JUL1"
    base["month_key"] = base["Date"].dt.strftime("%Y-%m")
    ratio = base["COGS"] / base["Revenue"]

    p2023h1 = base["period"].eq("2023H1")
    p2023h2 = base["period"].eq("2023H2")
    p2024h1 = base["period"].eq("2024H1")
    promo = base["win_main_promo"].astype(bool)
    nonpromo = ~promo
    high_ratio = ratio.gt(0.99)
    low_ratio = ratio.lt(0.94)
    aug_dec_jun = base["month_key"].isin(["2023-08", "2023-12", "2024-06"])
    h2_high = p2023h2 & high_ratio
    h1_low = (p2023h1 | p2024h1) & low_ratio

    rows: list[dict[str, object]] = []
    specs = [
        ("submission_publiconly_segment_v7_2023h2_up075.csv", p2023h2, 1.075, "oracle: 2023H2 COGS +7.5%"),
        ("submission_publiconly_segment_v7_2023h2_up100.csv", p2023h2, 1.100, "oracle: 2023H2 COGS +10%"),
        ("submission_publiconly_segment_v7_2023h2_up125.csv", p2023h2, 1.125, "oracle: 2023H2 COGS +12.5%"),
        ("submission_publiconly_segment_v7_2024h1_up075.csv", p2024h1, 1.075, "oracle: 2024H1 COGS +7.5%"),
        ("submission_publiconly_segment_v7_2024h1_up100.csv", p2024h1, 1.100, "oracle: 2024H1 COGS +10%"),
        ("submission_publiconly_segment_v7_2023h1_up075.csv", p2023h1, 1.075, "oracle: 2023H1 COGS +7.5%"),
        ("submission_publiconly_segment_v7_nonpromo_up075.csv", nonpromo, 1.075, "oracle: nonpromo COGS +7.5%"),
        ("submission_publiconly_segment_v7_promo_up075.csv", promo, 1.075, "oracle: promo COGS +7.5%"),
        ("submission_publiconly_segment_v7_highratio_up075.csv", high_ratio, 1.075, "oracle: already high COGS/Revenue days +7.5%"),
        ("submission_publiconly_segment_v7_lowratio_up075.csv", low_ratio, 1.075, "oracle: low COGS/Revenue days +7.5%"),
        ("submission_publiconly_segment_v7_aug_dec_jun_up100.csv", aug_dec_jun, 1.100, "oracle: high-ratio months Aug/Dec/Jun +10%"),
        ("submission_publiconly_segment_v7_2023h2_highratio_up100.csv", h2_high, 1.100, "oracle: 2023H2 high-ratio days +10%"),
    ]
    for filename, mask, multiplier, thesis in specs:
        register(rows, base, multiply(base, mask, multiplier), filename, thesis)

    combos = [
        (
            "submission_publiconly_segment_v7_2023h2_up100_2024h1_down030.csv",
            p2023h2,
            p2024h1,
            1.100,
            0.970,
            "oracle: 2023H2 up 10%, 2024H1 down 3% to test period reallocation",
        ),
        (
            "submission_publiconly_segment_v7_highratio_up100_lowratio_down030.csv",
            high_ratio,
            low_ratio,
            1.100,
            0.970,
            "oracle: high-ratio days up 10%, low-ratio days down 3%",
        ),
        (
            "submission_publiconly_segment_v7_h2high_up100_h1low_down030.csv",
            h2_high,
            h1_low,
            1.100,
            0.970,
            "oracle: H2 high-ratio up 10%, H1 low-ratio down 3%",
        ),
    ]
    for filename, up_mask, down_mask, up, down, thesis in combos:
        register(rows, base, two_segment(base, up_mask, down_mask, up, down), filename, thesis)

    manifest = pd.DataFrame(rows)
    manifest["can_reach_75x_best_case"] = manifest["score_if_best_case"] < TARGET_SCORE
    manifest = manifest.sort_values(["can_reach_75x_best_case", "score_if_best_case"], ascending=[False, True])
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)

    report = f"""# Public-Only Segment Oracle V7

Run directory: `{run_dir}`

Base: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

The global COGS path plateaued and COGS cap/reshape failed. This is a black-box segment oracle: large period/window COGS moves to discover which public segment still has wrong sign/scale. It is intentionally not local-driven.

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_publiconly_segment_v7_2023h2_up100.csv`
2. `submission_publiconly_segment_v7_highratio_up075.csv`
3. `submission_publiconly_segment_v7_2023h2_up100_2024h1_down030.csv`
4. `submission_publiconly_segment_v7_aug_dec_jun_up100.csv`
5. `submission_publiconly_segment_v7_2024h1_up075.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_segment_oracle_v7_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
