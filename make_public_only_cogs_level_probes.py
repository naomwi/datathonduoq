from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns, write_submission


RUN_PREFIX = "public_only_cogs_level_probes"
CURRENT_BEST_FILE = "submission_txndecomp_v2_cogsratio_followup_promotet_r60_up0100.csv"


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def register(rows: list[dict[str, object]], base: pd.DataFrame, frame: pd.DataFrame, filename: str, thesis: str) -> None:
    path = DATASET_DIR / filename
    write_submission(frame, path)
    delta = frame["COGS"] - base["COGS"]
    rows.append(
        {
            "filename": filename,
            "path": str(path),
            "thesis": thesis,
            "revenue_total_ratio_vs_best": frame["Revenue"].sum() / base["Revenue"].sum(),
            "cogs_total_ratio_vs_best": frame["COGS"].sum() / base["COGS"].sum(),
            "mean_cogs_delta": delta.mean(),
            "mean_abs_cogs_delta": delta.abs().mean(),
            "max_abs_cogs_delta": delta.abs().max(),
            "pred_cogs_ratio_mean": float((frame["COGS"] / frame["Revenue"]).mean()),
            "pred_cogs_ratio_promo": float((frame.loc[base["win_main_promo"], "COGS"] / frame.loc[base["win_main_promo"], "Revenue"]).mean()),
            "pred_cogs_ratio_nonpromo": float((frame.loc[~base["win_main_promo"], "COGS"] / frame.loc[~base["win_main_promo"], "Revenue"]).mean()),
        }
    )


def apply_multiplier(base: pd.DataFrame, mask: pd.Series, multiplier: float) -> pd.DataFrame:
    frame = base[["Date", "Revenue", "COGS"]].copy()
    frame.loc[mask, "COGS"] = frame.loc[mask, "COGS"] * multiplier
    return frame


def apply_ratio_floor(base: pd.DataFrame, mask: pd.Series, floor: float, blend: float = 1.0) -> pd.DataFrame:
    frame = base[["Date", "Revenue", "COGS"]].copy()
    target = (frame["Revenue"] * floor).where(mask, frame["COGS"])
    lifted = frame["COGS"].where(frame["COGS"] >= target, (1.0 - blend) * frame["COGS"] + blend * target)
    frame["COGS"] = lifted
    return frame


def main() -> None:
    run_dir = make_run_dir()
    base = pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"])
    base = add_event_columns(base).reset_index(drop=True)
    dates = base["Date"]
    promo = base["win_main_promo"].astype(bool)
    tet = base["win_tet_wide"].astype(bool)
    nonpromo = ~promo
    y2024 = dates.dt.year.eq(2024)
    y2023 = dates.dt.year.eq(2023)
    h1_2024 = y2024 & dates.dt.month.le(6)
    h2_2023 = y2023 & dates.dt.month.ge(7)
    nonpromo_2024h1 = nonpromo & h1_2024
    nonpromo_all = nonpromo
    promotet = promo | tet

    rows: list[dict[str, object]] = []
    specs = [
        ("submission_publiconly_cogs_all_up010.csv", pd.Series(True, index=base.index), 1.010, "all COGS +1%, pure level test"),
        ("submission_publiconly_cogs_all_up020.csv", pd.Series(True, index=base.index), 1.020, "all COGS +2%, tests broad COGS underprediction"),
        ("submission_publiconly_cogs_nonpromo_up015.csv", nonpromo_all, 1.015, "nonpromo COGS +1.5%, checks whether COGS miss is broader than promo/Tet"),
        ("submission_publiconly_cogs_nonpromo_up030.csv", nonpromo_all, 1.030, "nonpromo COGS +3%, bigger broad COGS level probe"),
        ("submission_publiconly_cogs_2024h1_nonpromo_up030.csv", nonpromo_2024h1, 1.030, "2024H1 nonpromo COGS +3%, tests high-scale future COGS level"),
        ("submission_publiconly_cogs_2024h1_nonpromo_up050.csv", nonpromo_2024h1, 1.050, "2024H1 nonpromo COGS +5%, aggressive high-scale future COGS level"),
        ("submission_publiconly_cogs_2023h2_up025.csv", h2_2023, 1.025, "2023H2 COGS +2.5%, checks year-2 seasonal COGS underprediction"),
        ("submission_publiconly_cogs_promotet_up020.csv", promotet, 1.020, "continue confirmed promo/Tet COGS gradient by simple multiplier"),
    ]
    for filename, mask, mult, thesis in specs:
        register(rows, base, apply_multiplier(base, mask, mult), filename, thesis)

    floor_specs = [
        ("submission_publiconly_cogs_nonpromo_floor086_b50.csv", nonpromo_all, 0.86, 0.50, "nonpromo COGS ratio floor 0.86 blended 50%"),
        ("submission_publiconly_cogs_nonpromo_floor088_b50.csv", nonpromo_all, 0.88, 0.50, "nonpromo COGS ratio floor 0.88 blended 50%"),
        ("submission_publiconly_cogs_2024h1_floor088_b50.csv", h1_2024, 0.88, 0.50, "2024H1 COGS ratio floor 0.88 blended 50%"),
        ("submission_publiconly_cogs_2024h1_floor090_b35.csv", h1_2024, 0.90, 0.35, "2024H1 COGS ratio floor 0.90 blended 35%"),
    ]
    for filename, mask, floor, blend, thesis in floor_specs:
        register(rows, base, apply_ratio_floor(base, mask, floor, blend), filename, thesis)

    manifest = pd.DataFrame(rows).sort_values("mean_abs_cogs_delta")
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    report = f"""# Public-Only COGS Level Probes

Run directory: `{run_dir}`

Base: `{CURRENT_BEST_FILE}` scored `873084.61381`.

These probes deliberately ignore local validation and keep Revenue fixed. They test whether the COGS miss that public rewarded in promo/Tet also exists in broader test segments.

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_publiconly_cogs_nonpromo_up015.csv`
2. `submission_publiconly_cogs_all_up010.csv`
3. `submission_publiconly_cogs_2024h1_nonpromo_up030.csv`
4. `submission_publiconly_cogs_nonpromo_floor086_b50.csv`
5. `submission_publiconly_cogs_promotet_up020.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "public_only_cogs_level_probes_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
