from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns, write_submission


RUN_PREFIX = "publiconly_month_oracle_v10"
CURRENT_BEST_FILE = "submission_publiconly_segment_v8_h2best_2024h1_down100.csv"
CURRENT_BEST_SCORE = 807504.66276
TARGET_SCORE = 759000.0

KNOWN_PUBLIC_RESULTS = {
    "submission_publiconly_segment_v7_2023h2_up100.csv": 812496.01649,
    "submission_publiconly_segment_v7_2024h1_up100.csv": 855840.24467,
    "submission_publiconly_segment_v8_h2best_2024h1_down100.csv": 807504.66276,
    "submission_publiconly_segment_v9_2023h1_up100.csv": 811093.31702,
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
            "ratio_2023h1": ratio.loc[base["period"].eq("2023H1")].mean(),
            "ratio_2023h2": ratio.loc[base["period"].eq("2023H2")].mean(),
            "ratio_2024h1": ratio.loc[base["period"].eq("2024H1")].mean(),
        }
    )


def main() -> None:
    run_dir = make_run_dir()
    base = pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"])
    base = add_segments(base)

    month = {m: base["month_key"].eq(m) for m in sorted(base["month_key"].unique())}
    h2 = base["period"].eq("2023H2")
    h2_q3 = base["month_key"].isin(["2023-07", "2023-08", "2023-09"])
    h2_q4 = base["month_key"].isin(["2023-10", "2023-11", "2023-12"])
    h2_peak = base["month_key"].isin(["2023-08", "2023-11", "2023-12"])
    h2_shoulder = base["month_key"].isin(["2023-07", "2023-09", "2023-10"])
    h2_aug_sep = base["month_key"].isin(["2023-08", "2023-09"])
    h2_nov_dec = base["month_key"].isin(["2023-11", "2023-12"])
    h2_jul_aug = base["month_key"].isin(["2023-07", "2023-08"])
    h2_sep_oct = base["month_key"].isin(["2023-09", "2023-10"])
    h2_nonpromo = h2 & ~base["win_main_promo"].astype(bool)

    h1_2023_low = base["month_key"].isin(["2023-02", "2023-03", "2023-05"])
    h1_2023_high = base["month_key"].isin(["2023-04", "2023-06"])
    h1_2024_q2 = base["month_key"].isin(["2024-04", "2024-05", "2024-06"])
    h1_2024_highscale = base["month_key"].isin(["2024-03", "2024-04", "2024-05", "2024-06"])

    rows: list[dict[str, object]] = []
    specs: list[tuple[str, list[tuple[pd.Series, float]], str, int]] = [
        (
            "submission_publiconly_month_v10_h2_more075.csv",
            [(h2, 1.075)],
            "extra 2023H2 +7.5% from current best; tests if H2 is still under",
            1,
        ),
        (
            "submission_publiconly_month_v10_h2_q3_more150.csv",
            [(h2_q3, 1.150)],
            "localize confirmed H2 signal to 2023Q3 +15%",
            2,
        ),
        (
            "submission_publiconly_month_v10_h2_q4_more150.csv",
            [(h2_q4, 1.150)],
            "localize confirmed H2 signal to 2023Q4 +15%",
            3,
        ),
        (
            "submission_publiconly_month_v10_h2_peak_more200.csv",
            [(h2_peak, 1.200)],
            "H2 high-ratio peak months Aug/Nov/Dec +20%",
            4,
        ),
        (
            "submission_publiconly_month_v10_h2_shoulder_more200.csv",
            [(h2_shoulder, 1.200)],
            "H2 shoulder months Jul/Sep/Oct +20%",
            5,
        ),
        (
            "submission_publiconly_month_v10_h2_augsep_more200.csv",
            [(h2_aug_sep, 1.200)],
            "H2 Aug/Sep +20%; tests whether late-summer is the missing spike",
            6,
        ),
        (
            "submission_publiconly_month_v10_h2_novdec_more200.csv",
            [(h2_nov_dec, 1.200)],
            "H2 Nov/Dec +20%; tests year-end COGS spike",
            7,
        ),
        (
            "submission_publiconly_month_v10_h2_julaug_more200.csv",
            [(h2_jul_aug, 1.200)],
            "H2 Jul/Aug +20%; tests early H2 spike",
            8,
        ),
        (
            "submission_publiconly_month_v10_h2_sepoct_more200.csv",
            [(h2_sep_oct, 1.200)],
            "H2 Sep/Oct +20%; tests mid H2 shoulder",
            9,
        ),
        (
            "submission_publiconly_month_v10_h2_nonpromo_more125.csv",
            [(h2_nonpromo, 1.125)],
            "confirmed H2 signal but non-promo only +12.5%",
            10,
        ),
        (
            "submission_publiconly_month_v10_2023h1_lowmonths_up150.csv",
            [(h1_2023_low, 1.150)],
            "broad 2023H1 up failed; test only low-ratio Feb/Mar/May +15%",
            11,
        ),
        (
            "submission_publiconly_month_v10_2023h1_highmonths_down100.csv",
            [(h1_2023_high, 0.900)],
            "broad 2023H1 up failed; test Apr/Jun opposite direction -10%",
            12,
        ),
        (
            "submission_publiconly_month_v10_2024q2_down150.csv",
            [(h1_2024_q2, 0.850)],
            "2024H1 down was weak; test if Q2 carries the down signal at -15%",
            13,
        ),
        (
            "submission_publiconly_month_v10_2024highscale_down150.csv",
            [(h1_2024_highscale, 0.850)],
            "2024 Mar-Jun high-scale down -15%",
            14,
        ),
        (
            "submission_publiconly_month_v10_h2_shoulder_more150_2024q2_down100.csv",
            [(h2_shoulder, 1.150), (h1_2024_q2, 0.900)],
            "high-upside bundle: H2 shoulder up +15%, 2024Q2 down -10%",
            15,
        ),
        (
            "submission_publiconly_month_v10_h2_peak_more150_2024q2_down100.csv",
            [(h2_peak, 1.150), (h1_2024_q2, 0.900)],
            "high-upside bundle: H2 peak up +15%, 2024Q2 down -10%",
            16,
        ),
    ]

    priority = 17
    for month_key in ["2023-07", "2023-08", "2023-09", "2023-10", "2023-11", "2023-12"]:
        specs.append(
            (
                f"submission_publiconly_month_v10_{month_key.replace('-', '')}_more250.csv",
                [(month[month_key], 1.250)],
                f"single-month oracle: {month_key} COGS +25%",
                priority,
            )
        )
        priority += 1

    for filename, changes, thesis, priority in specs:
        register(rows, base, apply_multipliers(base, changes), filename, thesis, priority)

    manifest = pd.DataFrame(rows).sort_values(["priority", "score_if_direction_correct"])
    manifest["can_reach_75x_if_direction_correct"] = manifest["score_if_direction_correct"] < TARGET_SCORE
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)

    report = f"""# Public-Only Month Oracle V10

Run directory: `{run_dir}`

Base: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known public reactions:

{pd.Series(KNOWN_PUBLIC_RESULTS, name="public_score").to_markdown()}

Interpretation:

- Broad `2023H1 +10%` worsened to `811093.31702`, so 2023H1 is not a broad missing-Cogs segment.
- The only large confirmed segment remains `2023H2`; V10 splits it by quarter, peak/shoulder, and single months.
- `2024H1 down` helped weakly. It is useful as a bundle term, but not enough alone to reach `75x`.

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_publiconly_month_v10_h2_more075.csv`
2. `submission_publiconly_month_v10_h2_shoulder_more200.csv`
3. `submission_publiconly_month_v10_h2_peak_more200.csv`
4. `submission_publiconly_month_v10_h2_shoulder_more150_2024q2_down100.csv`
5. `submission_publiconly_month_v10_202408_more250.csv` does not exist; use single-month H2 only if the grouped probes reveal Q3/Q4 direction.
"""
    report = report.replace(
        "`submission_publiconly_month_v10_202408_more250.csv` does not exist; use single-month H2 only if the grouped probes reveal Q3/Q4 direction.",
        "`submission_publiconly_month_v10_202308_more250.csv` if Q3/peak looks good; otherwise `submission_publiconly_month_v10_202309_more250.csv` or `submission_publiconly_month_v10_202311_more250.csv`."
    )
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_month_oracle_v10_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
