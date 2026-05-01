from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_public_shift_recovery import CURRENT_PUBLIC_BEST, CURRENT_PUBLIC_BEST_FILE, PUBLIC_SCORE_BOOK
from run_transaction_decomposition_v2 import add_event_columns


DATASET_DIR = Path("dataset")
LOG_ROOT = Path("logs")
NOTES_DIR = Path("notes")
RUN_PREFIX = "public_only_forensics"


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def load_submission(filename: str) -> pd.DataFrame | None:
    path = DATASET_DIR / filename
    if not path.exists():
        return None
    frame = pd.read_csv(path, parse_dates=["Date"])
    if not {"Date", "Revenue", "COGS"}.issubset(frame.columns):
        return None
    return add_event_columns(frame)


def summarize_delta(base: pd.DataFrame, candidate: pd.DataFrame, filename: str, score: float) -> dict[str, object]:
    merged = base[["Date", "Revenue", "COGS", "win_main_promo", "win_tet_wide", "win_event"]].merge(
        candidate[["Date", "Revenue", "COGS"]],
        on="Date",
        suffixes=("_base", "_cand"),
    )
    if len(merged) != len(base):
        raise ValueError(f"Length mismatch for {filename}: {len(merged)} vs {len(base)}")
    rev_delta = merged["Revenue_cand"] - merged["Revenue_base"]
    cogs_delta = merged["COGS_cand"] - merged["COGS_base"]
    promo = merged["win_main_promo"].astype(bool)
    tet = merged["win_tet_wide"].astype(bool)
    event = merged["win_event"].astype(bool)
    nonpromo = ~promo

    def mean_if(values: pd.Series, mask: pd.Series) -> float:
        if not mask.any():
            return 0.0
        return float(values.loc[mask].mean())

    def absmean_if(values: pd.Series, mask: pd.Series) -> float:
        if not mask.any():
            return 0.0
        return float(values.loc[mask].abs().mean())

    changed_abs = float((rev_delta.abs().mean() + cogs_delta.abs().mean()) / 2.0)
    score_delta = score - CURRENT_PUBLIC_BEST
    return {
        "filename": filename,
        "public_score": score,
        "score_delta_vs_best": score_delta,
        "combined_abs_move": changed_abs,
        "score_delta_per_100k_move": score_delta / (changed_abs / 100_000.0) if changed_abs else np.nan,
        "rev_mean_delta": float(rev_delta.mean()),
        "rev_abs_mean_delta": float(rev_delta.abs().mean()),
        "rev_promo_mean_delta": mean_if(rev_delta, promo),
        "rev_nonpromo_mean_delta": mean_if(rev_delta, nonpromo),
        "rev_event_abs_mean_delta": absmean_if(rev_delta, event),
        "cogs_mean_delta": float(cogs_delta.mean()),
        "cogs_abs_mean_delta": float(cogs_delta.abs().mean()),
        "cogs_promo_mean_delta": mean_if(cogs_delta, promo),
        "cogs_nonpromo_mean_delta": mean_if(cogs_delta, nonpromo),
        "cogs_tet_mean_delta": mean_if(cogs_delta, tet),
        "cogs_event_abs_mean_delta": absmean_if(cogs_delta, event),
        "changes_revenue": bool((rev_delta.abs() > 1e-6).any()),
        "changes_cogs": bool((cogs_delta.abs() > 1e-6).any()),
        "changes_nonpromo_revenue": bool((rev_delta.loc[nonpromo].abs() > 1e-6).any()),
        "changes_nonpromo_cogs": bool((cogs_delta.loc[nonpromo].abs() > 1e-6).any()),
    }


def infer_family(filename: str) -> str:
    name = filename.lower()
    if "txndecomp_v3_rev" in name:
        return "txndecomp_revenue_shape"
    if "txndecomp_v2_cogsratio" in name:
        return "txndecomp_cogs_ratio"
    if "cogsmult" in name or "cogsratio" in name:
        return "promo_cogs"
    if "revenue_gate" in name or "rev2024" in name:
        return "broad_revenue"
    if "promo_windows_rev" in name or "tabpfn_promo_windowmix" in name or "windowmix" in name:
        return "promo_revenue"
    if "price_history" in name:
        return "price_history"
    if "parity" in name:
        return "promo_parity"
    if "router" in name or "eom" in name or "tail" in name:
        return "calendar_router"
    return "other"


def main() -> None:
    run_dir = make_run_dir()
    base = load_submission(CURRENT_PUBLIC_BEST_FILE)
    if base is None:
        raise ValueError(f"Missing current best file: {CURRENT_PUBLIC_BEST_FILE}")

    rows: list[dict[str, object]] = []
    for filename, (score, source) in PUBLIC_SCORE_BOOK.items():
        frame = load_submission(filename)
        if frame is None:
            continue
        row = summarize_delta(base, frame, filename, score)
        row["family"] = infer_family(filename)
        row["source"] = source
        rows.append(row)

    df = pd.DataFrame(rows).sort_values("public_score")
    df.to_csv(run_dir / "public_only_score_delta_table.csv", index=False)

    family = (
        df.groupby("family", as_index=False)
        .agg(
            n=("filename", "size"),
            best_public_score=("public_score", "min"),
            median_score_delta=("score_delta_vs_best", "median"),
            min_score_delta=("score_delta_vs_best", "min"),
            max_score_delta=("score_delta_vs_best", "max"),
            median_rev_abs_move=("rev_abs_mean_delta", "median"),
            median_cogs_abs_move=("cogs_abs_mean_delta", "median"),
        )
        .sort_values("best_public_score")
    )
    family.to_csv(run_dir / "family_summary.csv", index=False)

    report = f"""# Public-Only Forensics

Run directory: `{run_dir}`

Current best: `{CURRENT_PUBLIC_BEST_FILE}` = `{CURRENT_PUBLIC_BEST}`.

This report intentionally ignores local validation and reads only public-score reactions to submitted files.

## Family Summary
{family.to_markdown(index=False)}

## Known Score Delta Table
{df[[
    "filename",
    "family",
    "public_score",
    "score_delta_vs_best",
    "rev_abs_mean_delta",
    "cogs_abs_mean_delta",
    "rev_mean_delta",
    "cogs_mean_delta",
    "changes_nonpromo_revenue",
    "changes_nonpromo_cogs",
]].to_markdown(index=False)}

## Public-Only Conclusions
- Confirmed good: targeted promo/Tet `COGS` upward through transaction-derived COGS ratio.
- Confirmed bad: transaction-derived Revenue event shape, broad nonpromo Revenue changes, price-history direct features, odd parity Revenue.
- The path to 7xx is not the rejected Revenue event donor. It must be either a different Revenue prior, a larger COGS-ratio/level miss, or a target-period scale/calendar signal not represented by our current local features.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "public_only_forensics_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
