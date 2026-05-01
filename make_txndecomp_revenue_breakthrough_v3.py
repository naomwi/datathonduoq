from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_transaction_decomposition_v2 import (
    DATASET_DIR,
    LOG_ROOT,
    NOTES_DIR,
    add_event_columns,
    build_component_shape_donor,
    build_tet_profile,
    compensate_month_total,
    load_daily_components,
    write_submission,
)


RUN_PREFIX = "txndecomp_revenue_breakthrough_v3"
CURRENT_BEST_FILE = "submission_txndecomp_v2_cogsratio_followup_promotet_r60_up0100.csv"


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def _clip_multiplier(candidate: pd.Series, base: pd.Series, lower: float, upper: float) -> pd.Series:
    multiplier = (candidate / base.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    return base * multiplier.clip(lower, upper)


def register(
    rows: list[dict[str, object]],
    base: pd.DataFrame,
    frame: pd.DataFrame,
    filename: str,
    thesis: str,
) -> None:
    path = DATASET_DIR / filename
    write_submission(frame, path)
    rev_delta = frame["Revenue"] - base["Revenue"]
    cogs_delta = frame["COGS"] - base["COGS"]
    rows.append(
        {
            "filename": filename,
            "path": str(path),
            "thesis": thesis,
            "revenue_total_ratio_vs_best": frame["Revenue"].sum() / base["Revenue"].sum(),
            "cogs_total_ratio_vs_best": frame["COGS"].sum() / base["COGS"].sum(),
            "mean_abs_revenue_delta": rev_delta.abs().mean(),
            "max_abs_revenue_delta": rev_delta.abs().max(),
            "mean_revenue_delta": rev_delta.mean(),
            "mean_abs_cogs_delta": cogs_delta.abs().mean(),
            "changed_cogs": bool((cogs_delta.abs() > 1e-6).any()),
        }
    )


def main() -> None:
    run_dir = make_run_dir()
    base = pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"])
    base = add_event_columns(base).reset_index(drop=True)
    history = load_daily_components()
    donor = build_component_shape_donor(history, base).reset_index(drop=True)
    tet_profile = build_tet_profile(history)

    event_mask = base["win_event"].astype(bool)
    promo_mask = base["win_main_promo"].astype(bool)
    tet_mask = base["win_tet_wide"].astype(bool)
    dates = base["Date"]

    rows: list[dict[str, object]] = []

    def candidate_from_shape(
        name: str,
        mask: pd.Series,
        shape: pd.Series,
        weight: float,
        compensate: bool,
        clip: tuple[float, float] | None,
        thesis: str,
    ) -> None:
        frame = base[["Date", "Revenue", "COGS"]].copy()
        rev = base["Revenue"].copy()
        shaped = base["Revenue"] * (1.0 + weight * (shape - 1.0))
        if clip is not None:
            shaped = _clip_multiplier(shaped, base["Revenue"], clip[0], clip[1])
        rev.loc[mask] = shaped.loc[mask]
        if compensate:
            rev = compensate_month_total(base["Revenue"], rev, dates, mask)
        frame["Revenue"] = rev.clip(lower=0.0)
        register(rows, base, frame, name, thesis)

    # These variants are intentionally large enough to matter for a 7xx jump.
    candidate_from_shape(
        "submission_txndecomp_v3_rev_eventshape_r12_keepcogs.csv",
        event_mask,
        donor["revenue_shape"],
        0.12,
        True,
        (0.72, 1.38),
        "Revenue-only event/promo/Tet transaction shape, monthly total preserved, COGS fixed",
    )
    candidate_from_shape(
        "submission_txndecomp_v3_rev_eventshape_r20_keepcogs.csv",
        event_mask,
        donor["revenue_shape"],
        0.20,
        True,
        (0.65, 1.55),
        "High-upside Revenue-only event/promo/Tet transaction shape, monthly total preserved, COGS fixed",
    )
    candidate_from_shape(
        "submission_txndecomp_v3_rev_eventshape_r28_clip_keepcogs.csv",
        event_mask,
        donor["revenue_shape"],
        0.28,
        True,
        (0.60, 1.65),
        "Aggressive but clipped Revenue-only event/promo/Tet transaction shape, monthly total preserved, COGS fixed",
    )
    candidate_from_shape(
        "submission_txndecomp_v3_rev_promoshape_r25_nocomp_keepcogs.csv",
        promo_mask,
        donor["revenue_shape"],
        0.25,
        False,
        (0.65, 1.60),
        "Revenue-only promo shape without nonpromo compensation; tests whether promo total itself is wrong",
    )
    candidate_from_shape(
        "submission_txndecomp_v3_rev_promoshape_r40_nocomp_keepcogs.csv",
        promo_mask,
        donor["revenue_shape"],
        0.40,
        False,
        (0.55, 1.80),
        "Aggressive Revenue-only promo shape without nonpromo compensation",
    )
    candidate_from_shape(
        "submission_txndecomp_v3_rev_monthshape_r08_keepcogs.csv",
        pd.Series(True, index=base.index),
        donor["revenue_shape"],
        0.08,
        True,
        (0.72, 1.38),
        "All-day transaction intra-month Revenue shape, monthly totals preserved, COGS fixed",
    )
    candidate_from_shape(
        "submission_txndecomp_v3_rev_monthshape_r14_keepcogs.csv",
        pd.Series(True, index=base.index),
        donor["revenue_shape"],
        0.14,
        True,
        (0.62, 1.55),
        "Aggressive all-day transaction intra-month Revenue shape, monthly totals preserved, COGS fixed",
    )

    # Exact lunar Tet profile, separated because it is a targeted calendar hypothesis.
    tet = base[["Date", "tet_offset"]].merge(tet_profile, on="tet_offset", how="left")
    tet_shape = tet["tet_rev_shape"].fillna(1.0)
    candidate_from_shape(
        "submission_txndecomp_v3_rev_tetshift_r70_keepcogs.csv",
        tet_mask,
        tet_shape,
        0.70,
        True,
        (0.72, 1.35),
        "Exact lunar Tet Revenue profile, monthly total preserved, COGS fixed",
    )

    manifest = pd.DataFrame(rows).sort_values("mean_abs_revenue_delta")
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    donor.to_csv(run_dir / "component_shape_donor.csv", index=False)

    report = f"""# Transaction Revenue Breakthrough V3

Run directory: `{run_dir}`

Base: `{CURRENT_BEST_FILE}` scored `873084.61381`.

## Why This Exists
COGS-only has improved public, but it is too small to reach 7xx. A 7xx jump requires Revenue daily-shape improvement on the order of `100k+` average absolute movement. These candidates keep current-best COGS fixed and only test Revenue shape from transaction decomposition.

## Candidate Manifest
{manifest.to_markdown(index=False)}

## Suggested Order
1. `submission_txndecomp_v3_rev_eventshape_r20_keepcogs.csv`
2. `submission_txndecomp_v3_rev_eventshape_r12_keepcogs.csv`
3. `submission_txndecomp_v3_rev_monthshape_r08_keepcogs.csv`
4. `submission_txndecomp_v3_rev_promoshape_r25_nocomp_keepcogs.csv`
5. `submission_txndecomp_v3_rev_eventshape_r28_clip_keepcogs.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "txndecomp_revenue_breakthrough_v3_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
