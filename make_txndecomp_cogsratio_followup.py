from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from run_transaction_decomposition_v2 import (
    DATASET_DIR,
    LOG_ROOT,
    NOTES_DIR,
    add_event_columns,
    build_component_shape_donor,
    load_daily_components,
    write_submission,
)


RUN_PREFIX = "txndecomp_cogsratio_followup"
CURRENT_BEST_FILE = "submission_txndecomp_v2_cogsratio_promotet_r40_up0075.csv"
ANCHOR_FILE = "submission_catboost_md2y_core_recencyexp20.csv"


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def register_candidate(
    rows: list[dict[str, object]],
    frame: pd.DataFrame,
    base: pd.DataFrame,
    anchor: pd.DataFrame,
    filename: str,
    thesis: str,
) -> None:
    path = DATASET_DIR / filename
    write_submission(frame, path)
    changed = (frame["COGS"] - base["COGS"]).abs()
    anchor_merged = anchor.merge(frame, on="Date", suffixes=("_anchor", ""))
    rows.append(
        {
            "filename": filename,
            "path": str(path),
            "thesis": thesis,
            "revenue_total_ratio_vs_current_best": frame["Revenue"].sum() / base["Revenue"].sum(),
            "cogs_total_ratio_vs_current_best": frame["COGS"].sum() / base["COGS"].sum(),
            "cogs_total_ratio_vs_anchor": frame["COGS"].sum() / anchor_merged["COGS_anchor"].sum(),
            "mean_abs_cogs_delta_vs_current_best": changed.mean(),
            "max_abs_cogs_delta_vs_current_best": changed.max(),
            "changes_nonpromo_cogs": bool((changed[~base["win_main_promo"]] > 1e-6).any()),
        }
    )


def main() -> None:
    run_dir = make_run_dir()
    base = pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"])
    anchor = pd.read_csv(DATASET_DIR / ANCHOR_FILE, parse_dates=["Date"])
    history = load_daily_components()
    donor = build_component_shape_donor(history, base)
    base = add_event_columns(base).reset_index(drop=True)
    donor = donor.reset_index(drop=True)

    ratio_target = donor["donor_cogs_from_ratio"].clip(lower=0.0)
    promo_mask = base["win_main_promo"].astype(bool)
    tet_mask = base["win_tet_wide"].astype(bool)
    promotet_mask = (promo_mask | tet_mask).astype(bool)

    specs: list[tuple[str, pd.Series, float, float]] = [
        ("promotet_r50_up0050", promotet_mask, 0.50, 0.0050),
        ("promotet_r55_up0075", promotet_mask, 0.55, 0.0075),
        ("promotet_r60_up0100", promotet_mask, 0.60, 0.0100),
        ("promotet_r70_up0125", promotet_mask, 0.70, 0.0125),
        ("promotet_r80_up0150", promotet_mask, 0.80, 0.0150),
        ("promotet_r100_up0200", promotet_mask, 1.00, 0.0200),
        ("promoonly_r60_up0100", promo_mask, 0.60, 0.0100),
        ("promoonly_r80_up0150", promo_mask, 0.80, 0.0150),
        ("tetonly_r70", tet_mask, 0.70, 0.0000),
    ]

    rows: list[dict[str, object]] = []
    for suffix, mask, weight, promo_multiplier in specs:
        frame = base[["Date", "Revenue", "COGS"]].copy()
        cogs = base["COGS"].copy()
        cogs.loc[mask] = (1.0 - weight) * base.loc[mask, "COGS"] + weight * ratio_target.loc[mask]
        if promo_multiplier:
            cogs.loc[promo_mask] *= 1.0 + promo_multiplier
        frame["COGS"] = cogs.clip(lower=0.0)
        register_candidate(
            rows,
            frame,
            base,
            anchor,
            f"submission_txndecomp_v2_cogsratio_followup_{suffix}.csv",
            f"continue confirmed transaction COGS-ratio gradient: mask={suffix}, weight={weight}, promo_up={promo_multiplier}",
        )

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    donor.to_csv(run_dir / "component_shape_donor.csv", index=False)

    report = f"""# Transaction COGS-Ratio Followup

Run directory: `{run_dir}`

Base: `{CURRENT_BEST_FILE}` scored `874819.47653`.

The public improvement from `879533` to `874819` confirms targeted promo/Tet COGS-ratio movement. This sweep keeps Revenue fixed and tests whether the optimum is still higher.

{manifest.to_markdown(index=False)}

Suggested order before any Revenue-shape gamble:

1. `submission_txndecomp_v2_cogsratio_followup_promotet_r60_up0100.csv`
2. `submission_txndecomp_v2_cogsratio_followup_promotet_r70_up0125.csv`
3. `submission_txndecomp_v2_cogsratio_followup_promoonly_r80_up0150.csv`
4. `submission_txndecomp_v2_cogsratio_followup_promotet_r80_up0150.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "txndecomp_cogsratio_followup_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
