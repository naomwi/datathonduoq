from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns, write_submission


RUN_PREFIX = "publiconly_cogs_break_followup_v5"
CURRENT_BEST_FILE = "submission_publiconly_cogs_break_followup_all_plus035.csv"
CURRENT_BEST_SCORE = 828569.81120
TARGET_SCORE = 799000.0


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
            "cogs_total_ratio_vs_best": frame["COGS"].sum() / base["COGS"].sum(),
            "mean_cogs_delta_vs_best": delta.mean(),
            "best_case_gain_vs_best": 0.5 * delta.clip(lower=0).mean(),
            "score_if_best_case": CURRENT_BEST_SCORE - 0.5 * delta.clip(lower=0).mean(),
            "cogs_ratio_mean": ratio.mean(),
            "cogs_ratio_promo": ratio.loc[base["win_main_promo"]].mean(),
            "cogs_ratio_nonpromo": ratio.loc[~base["win_main_promo"]].mean(),
            "cogs_ratio_2024h1": ratio.loc[base["is_2024h1"]].mean(),
        }
    )


def multiply(base: pd.DataFrame, mask: pd.Series, mult: float) -> pd.DataFrame:
    frame = base[["Date", "Revenue", "COGS"]].copy()
    frame.loc[mask, "COGS"] *= mult
    return frame


def ratio_floor(base: pd.DataFrame, mask: pd.Series, floor: float, blend: float) -> pd.DataFrame:
    frame = base[["Date", "Revenue", "COGS"]].copy()
    target = frame["Revenue"] * floor
    needs = mask & (frame["COGS"] < target)
    frame.loc[needs, "COGS"] = (1.0 - blend) * frame.loc[needs, "COGS"] + blend * target.loc[needs]
    return frame


def ratio_cap(base: pd.DataFrame, cap: float) -> pd.DataFrame:
    frame = base[["Date", "Revenue", "COGS"]].copy()
    frame["COGS"] = frame["COGS"].clip(upper=frame["Revenue"] * cap)
    return frame


def main() -> None:
    run_dir = make_run_dir()
    base = pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"])
    base = add_event_columns(base).reset_index(drop=True)
    base["is_2024h1"] = base["Date"].dt.year.eq(2024) & base["Date"].dt.month.le(6)
    base["is_2023h2"] = base["Date"].dt.year.eq(2023) & base["Date"].dt.month.ge(7)
    promo = base["win_main_promo"].astype(bool)
    nonpromo = ~promo
    all_mask = pd.Series(True, index=base.index)
    h1_2024 = base["is_2024h1"].astype(bool)
    h1_2024_nonpromo = h1_2024 & nonpromo
    low_ratio = (base["COGS"] / base["Revenue"]).lt(0.94)
    low_ratio_nonpromo = low_ratio & nonpromo

    rows: list[dict[str, object]] = []
    specs = [
        ("submission_publiconly_cogs_break_v5_all_plus010.csv", all_mask, 1.010, "fine continuation: all COGS +1.0%"),
        ("submission_publiconly_cogs_break_v5_all_plus015.csv", all_mask, 1.015, "fine continuation: all COGS +1.5%"),
        ("submission_publiconly_cogs_break_v5_all_plus020.csv", all_mask, 1.020, "fine continuation: all COGS +2.0%"),
        ("submission_publiconly_cogs_break_v5_all_plus025.csv", all_mask, 1.025, "fine continuation: all COGS +2.5%"),
        ("submission_publiconly_cogs_break_v5_nonpromo_plus020.csv", nonpromo, 1.020, "fine continuation: nonpromo COGS +2.0%"),
        ("submission_publiconly_cogs_break_v5_nonpromo_plus035.csv", nonpromo, 1.035, "fine continuation: nonpromo COGS +3.5%"),
        ("submission_publiconly_cogs_break_v5_2024h1_nonpromo_plus040.csv", h1_2024_nonpromo, 1.040, "fine continuation: 2024H1 nonpromo COGS +4.0%"),
        ("submission_publiconly_cogs_break_v5_lowratio_nonpromo_plus050.csv", low_ratio_nonpromo, 1.050, "target only nonpromo days still below 0.94 ratio, COGS +5%"),
    ]
    for filename, mask, mult, thesis in specs:
        register(rows, base, multiply(base, mask, mult), filename, thesis)

    floor_specs = [
        ("submission_publiconly_cogs_break_v5_all_floor096_b35.csv", all_mask, 0.96, 0.35, "all ratio floor 0.96 blend 35%"),
        ("submission_publiconly_cogs_break_v5_all_floor098_b35.csv", all_mask, 0.98, 0.35, "all ratio floor 0.98 blend 35%"),
        ("submission_publiconly_cogs_break_v5_all_floor100_b25.csv", all_mask, 1.00, 0.25, "all ratio floor 1.00 blend 25%"),
        ("submission_publiconly_cogs_break_v5_nonpromo_floor098_b40.csv", nonpromo, 0.98, 0.40, "nonpromo ratio floor 0.98 blend 40%"),
        ("submission_publiconly_cogs_break_v5_2024h1_floor100_b35.csv", h1_2024, 1.00, 0.35, "2024H1 ratio floor 1.00 blend 35%"),
    ]
    for filename, mask, floor, blend, thesis in floor_specs:
        register(rows, base, ratio_floor(base, mask, floor, blend), filename, thesis)

    for cap in [1.02, 1.05]:
        filename = f"submission_publiconly_cogs_break_v5_cap{str(cap).replace('.', '')}.csv"
        register(rows, base, ratio_cap(base, cap), filename, f"diagnostic cap COGS/Revenue at {cap}")

    manifest = pd.DataFrame(rows)
    manifest["can_reach_7xx_best_case"] = manifest["score_if_best_case"] < TARGET_SCORE
    manifest = manifest.sort_values(["can_reach_7xx_best_case", "score_if_best_case"], ascending=[False, True])
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)

    required = CURRENT_BEST_SCORE - TARGET_SCORE
    report = f"""# Public-Only COGS Break Followup V5

Run directory: `{run_dir}`

Base: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Need `{required:.0f}` more MAE to reach `{TARGET_SCORE}`. The `+3.5%` follow-up improved, but marginal gain decelerated; this sweep tests whether the remaining correction should be broad, nonpromo, low-ratio only, or floor-shaped.

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_publiconly_cogs_break_v5_all_plus020.csv`
2. `submission_publiconly_cogs_break_v5_nonpromo_floor098_b40.csv`
3. `submission_publiconly_cogs_break_v5_all_floor098_b35.csv`
4. `submission_publiconly_cogs_break_v5_lowratio_nonpromo_plus050.csv`
5. `submission_publiconly_cogs_break_v5_all_plus025.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_cogs_break_followup_v5_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
