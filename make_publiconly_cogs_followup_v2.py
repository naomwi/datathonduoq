from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns, write_submission


RUN_PREFIX = "publiconly_cogs_followup_v2"
CURRENT_BEST_FILE = "submission_publiconly_cogs_nonpromo_up015.csv"


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
    promotet = promo | base["win_tet_wide"].astype(bool)

    rows: list[dict[str, object]] = []
    specs = [
        ("submission_publiconly_cogs_followup_nonpromo_plus0075.csv", nonpromo, 1.0075, "after winning nonpromo +1.5%, add another +0.75% nonpromo"),
        ("submission_publiconly_cogs_followup_nonpromo_plus0150.csv", nonpromo, 1.0150, "after winning nonpromo +1.5%, add another +1.5% nonpromo"),
        ("submission_publiconly_cogs_followup_nonpromo_plus0225.csv", nonpromo, 1.0225, "after winning nonpromo +1.5%, add another +2.25% nonpromo"),
        ("submission_publiconly_cogs_followup_all_plus0050.csv", all_mask, 1.0050, "global COGS +0.5% on top of current best"),
        ("submission_publiconly_cogs_followup_all_plus0100.csv", all_mask, 1.0100, "global COGS +1.0% on top of current best"),
        ("submission_publiconly_cogs_followup_2024h1_nonpromo_plus0200.csv", h1_2024_nonpromo, 1.0200, "2024H1 nonpromo +2% on top of current best"),
        ("submission_publiconly_cogs_followup_2024h1_nonpromo_plus0350.csv", h1_2024_nonpromo, 1.0350, "2024H1 nonpromo +3.5% on top of current best"),
        ("submission_publiconly_cogs_followup_2023h2_nonpromo_plus0200.csv", h2_2023_nonpromo, 1.0200, "2023H2 nonpromo +2% on top of current best"),
        ("submission_publiconly_cogs_followup_promotet_plus0100.csv", promotet, 1.0100, "continue promo/Tet COGS +1% on top of current best"),
    ]
    for filename, mask, mult, thesis in specs:
        register(rows, base, multiply(base, mask, mult), filename, thesis)

    floor_specs = [
        ("submission_publiconly_cogs_followup_nonpromo_floor088_b35.csv", nonpromo, 0.88, 0.35, "nonpromo COGS ratio floor 0.88 blended 35%"),
        ("submission_publiconly_cogs_followup_nonpromo_floor090_b35.csv", nonpromo, 0.90, 0.35, "nonpromo COGS ratio floor 0.90 blended 35%"),
        ("submission_publiconly_cogs_followup_all_floor088_b25.csv", all_mask, 0.88, 0.25, "all COGS ratio floor 0.88 blended 25%"),
        ("submission_publiconly_cogs_followup_2024h1_floor090_b35.csv", h1_2024, 0.90, 0.35, "2024H1 COGS ratio floor 0.90 blended 35%"),
    ]
    for filename, mask, floor, blend, thesis in floor_specs:
        register(rows, base, ratio_floor(base, mask, floor, blend), filename, thesis)

    manifest = pd.DataFrame(rows).sort_values("mean_abs_cogs_delta")
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    report = f"""# Public-Only COGS Followup V2

Run directory: `{run_dir}`

Base: `{CURRENT_BEST_FILE}` scored `865527.70356`.

The public accepted nonpromo COGS +1.5%, so these probes scale that confirmed direction without touching Revenue.

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_publiconly_cogs_followup_nonpromo_plus0150.csv`
2. `submission_publiconly_cogs_followup_all_plus0050.csv`
3. `submission_publiconly_cogs_followup_2024h1_nonpromo_plus0200.csv`
4. `submission_publiconly_cogs_followup_nonpromo_floor088_b35.csv`
5. `submission_publiconly_cogs_followup_nonpromo_plus0225.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_cogs_followup_v2_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
