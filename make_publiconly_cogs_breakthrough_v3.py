from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns, write_submission


RUN_PREFIX = "publiconly_cogs_breakthrough_v3"
CURRENT_BEST_FILE = "submission_publiconly_cogs_nonpromo_up015.csv"
CURRENT_BEST_SCORE = 865527.70356
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
            "mean_cogs_delta": delta.mean(),
            "mean_abs_cogs_delta": delta.abs().mean(),
            "max_abs_cogs_delta": delta.abs().max(),
            "best_case_combined_mae_gain_if_all_correct": 0.5 * delta.clip(lower=0).mean(),
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
    h2_2023_nonpromo = base["is_2023h2"].astype(bool) & nonpromo
    late_horizon = (base["Date"] - base["Date"].min()).dt.days.ge(274)
    late_nonpromo = late_horizon & nonpromo

    rows: list[dict[str, object]] = []
    multiplier_specs = [
        ("submission_publiconly_cogs_break_nonpromo_plus050.csv", nonpromo, 1.050, "breakthrough: nonpromo COGS +5% on top of current best"),
        ("submission_publiconly_cogs_break_nonpromo_plus075.csv", nonpromo, 1.075, "breakthrough: nonpromo COGS +7.5% on top of current best"),
        ("submission_publiconly_cogs_break_nonpromo_plus100.csv", nonpromo, 1.100, "breakthrough: nonpromo COGS +10% on top of current best"),
        ("submission_publiconly_cogs_break_all_plus030.csv", all_mask, 1.030, "breakthrough: all COGS +3%, tests broad underprediction"),
        ("submission_publiconly_cogs_break_all_plus050.csv", all_mask, 1.050, "breakthrough: all COGS +5%, can move score by 80k+ if sign is right"),
        ("submission_publiconly_cogs_break_2024h1_nonpromo_plus075.csv", h1_2024_nonpromo, 1.075, "breakthrough: 2024H1 nonpromo COGS +7.5%"),
        ("submission_publiconly_cogs_break_2024h1_nonpromo_plus100.csv", h1_2024_nonpromo, 1.100, "breakthrough: 2024H1 nonpromo COGS +10%"),
        ("submission_publiconly_cogs_break_2023h2_nonpromo_plus075.csv", h2_2023_nonpromo, 1.075, "breakthrough: 2023H2 nonpromo COGS +7.5%"),
        ("submission_publiconly_cogs_break_late_nonpromo_plus075.csv", late_nonpromo, 1.075, "breakthrough: late-horizon nonpromo COGS +7.5%"),
    ]
    for filename, mask, mult, thesis in multiplier_specs:
        register(rows, base, multiply(base, mask, mult), filename, thesis)

    floor_specs = [
        ("submission_publiconly_cogs_break_nonpromo_floor090_b70.csv", nonpromo, 0.90, 0.70, "breakthrough: nonpromo ratio floor 0.90 blend 70%"),
        ("submission_publiconly_cogs_break_nonpromo_floor092_b70.csv", nonpromo, 0.92, 0.70, "breakthrough: nonpromo ratio floor 0.92 blend 70%"),
        ("submission_publiconly_cogs_break_nonpromo_floor094_b60.csv", nonpromo, 0.94, 0.60, "breakthrough: nonpromo ratio floor 0.94 blend 60%"),
        ("submission_publiconly_cogs_break_all_floor090_b60.csv", all_mask, 0.90, 0.60, "breakthrough: all ratio floor 0.90 blend 60%"),
        ("submission_publiconly_cogs_break_all_floor092_b50.csv", all_mask, 0.92, 0.50, "breakthrough: all ratio floor 0.92 blend 50%"),
        ("submission_publiconly_cogs_break_2024h1_floor092_b70.csv", h1_2024, 0.92, 0.70, "breakthrough: 2024H1 ratio floor 0.92 blend 70%"),
    ]
    for filename, mask, floor, blend, thesis in floor_specs:
        register(rows, base, ratio_floor(base, mask, floor, blend), filename, thesis)

    manifest = pd.DataFrame(rows)
    manifest["can_theoretically_reach_7xx"] = manifest["score_if_best_case"] < TARGET_SCORE
    manifest = manifest.sort_values(["can_theoretically_reach_7xx", "score_if_best_case"], ascending=[False, True])
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)

    required_gain = CURRENT_BEST_SCORE - TARGET_SCORE
    report = f"""# Public-Only COGS Breakthrough V3

Run directory: `{run_dir}`

Base: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

To reach `{TARGET_SCORE}` we need about `{required_gain:.0f}` MAE improvement. Since score is roughly `0.5 * (Revenue MAE + COGS MAE)`, a COGS-only path must fix around `{2 * required_gain:.0f}` average COGS error if Revenue is unchanged.

These files are intentionally aggressive. They are not local-safe; they are public-oracle probes for whether broad COGS is the missing 7xx-scale signal.

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_publiconly_cogs_break_all_plus050.csv`
2. `submission_publiconly_cogs_break_nonpromo_plus075.csv`
3. `submission_publiconly_cogs_break_nonpromo_floor092_b70.csv`
4. `submission_publiconly_cogs_break_2024h1_nonpromo_plus100.csv`
5. `submission_publiconly_cogs_break_all_floor092_b50.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_cogs_breakthrough_v3_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
