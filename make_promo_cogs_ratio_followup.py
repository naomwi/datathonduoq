from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json


RUN_PREFIX = "promo_cogs_ratio_followup"
DATASET_DIR = Path("dataset")
BEST_PATH = DATASET_DIR / "submission_tabpfn_promo_windowmix_v1.csv"
ANCHOR_PATH = DATASET_DIR / "submission_catboost_md2y_core_recencyexp20.csv"
SOURCE_FRAME_PATH = Path("logs/20260421_205129_promo_window_core_v2/public_feature_frame_scored.csv")
PUBLIC_WINNER = "submission_promo_cogsratio_bestrev_a010_clip005.csv"
PUBLIC_WINNER_SCORE = 881699.03740


def load_frame() -> pd.DataFrame:
    if not SOURCE_FRAME_PATH.exists():
        raise FileNotFoundError(f"Missing source frame: {SOURCE_FRAME_PATH}")
    frame = pd.read_csv(SOURCE_FRAME_PATH, parse_dates=["Date"])
    best = pd.read_csv(BEST_PATH, parse_dates=["Date"]).rename(columns={"Revenue": "Best_Revenue", "COGS": "Best_COGS"})
    anchor = pd.read_csv(ANCHOR_PATH, parse_dates=["Date"]).rename(columns={"Revenue": "Anchor_Revenue", "COGS": "Anchor_COGS"})
    return frame.merge(best, on="Date", how="left").merge(anchor, on="Date", how="left")


def export_candidate(
    run_dir: Path,
    frame: pd.DataFrame,
    candidate_id: str,
    promo_cogs_multiplier: float,
    windows: set[str] | None = None,
) -> dict[str, object]:
    promo_mask = frame["core_is_promo_window"].astype(float) > 0
    active_mask = promo_mask.copy()
    if windows is not None:
        active_mask &= frame["core_window_id"].astype(str).isin(windows)

    revenue = frame["Best_Revenue"].astype(float).copy()
    cogs = frame["Anchor_COGS"].astype(float).copy()
    cogs.loc[active_mask] *= promo_cogs_multiplier

    out = pd.DataFrame(
        {
            "Date": pd.to_datetime(frame["Date"]).dt.strftime("%Y-%m-%d"),
            "Revenue": revenue.clip(lower=0.0),
            "COGS": cogs.clip(lower=0.0),
        }
    )
    run_path = run_dir / f"submission_{candidate_id}.csv"
    dataset_path = DATASET_DIR / f"submission_{candidate_id}.csv"
    out.to_csv(run_path, index=False)
    out.to_csv(dataset_path, index=False)

    anchor_rev = frame["Anchor_Revenue"].astype(float)
    anchor_cogs = frame["Anchor_COGS"].astype(float)
    rev_delta = out["Revenue"] - anchor_rev
    cogs_delta = out["COGS"] - anchor_cogs
    row: dict[str, object] = {
        "candidate_id": candidate_id,
        "run_path": str(run_path),
        "dataset_path": str(dataset_path),
        "promo_cogs_multiplier": promo_cogs_multiplier,
        "windows": ",".join(sorted(windows)) if windows else "all",
        "changed_rows": int(active_mask.sum()),
        "revenue_total_ratio_vs_anchor": float(out["Revenue"].sum() / anchor_rev.sum()),
        "revenue_delta_promo_mean": float(rev_delta.loc[promo_mask].mean()),
        "revenue_delta_nonpromo_max_abs": float(rev_delta.loc[~promo_mask].abs().max()),
        "cogs_total_ratio_vs_anchor": float(out["COGS"].sum() / anchor_cogs.sum()),
        "cogs_delta_mean": float(cogs_delta.mean()),
        "cogs_delta_active_mean": float(cogs_delta.loc[active_mask].mean()) if active_mask.any() else 0.0,
        "cogs_delta_promo_mean": float(cogs_delta.loc[promo_mask].mean()),
        "cogs_delta_nonpromo_max_abs": float(cogs_delta.loc[~promo_mask].abs().max()),
    }
    for window in ["marapr", "junjul", "augoct", "novjan"]:
        mask = frame["core_window_id"].astype(str).eq(window)
        row[f"{window}_cogs_delta_mean"] = float(cogs_delta.loc[mask].mean()) if mask.any() else 0.0
    return row


def write_report(run_dir: Path, summary: pd.DataFrame) -> None:
    with (run_dir / "report.md").open("w", encoding="utf-8") as f:
        f.write("# Promo COGS Ratio Follow-Up\n\n")
        f.write(f"Public winner so far: `{PUBLIC_WINNER}` = `{PUBLIC_WINNER_SCORE}`.\n\n")
        f.write("Frame: keep current best Revenue exactly and test simple promo COGS multipliers around the winning +0.5% move.\n\n")
        f.write(summary.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    frame = load_frame()
    specs = [
        ("promo_cogsmult_bestrev_all_0025", 1.0025, None),
        ("promo_cogsmult_bestrev_all_0075", 1.0075, None),
        ("promo_cogsmult_bestrev_all_0100", 1.0100, None),
        ("promo_cogsmult_bestrev_all_0125", 1.0125, None),
        ("promo_cogsmult_bestrev_all_0150", 1.0150, None),
        ("promo_cogsmult_bestrev_all_0200", 1.0200, None),
        ("promo_cogsmult_bestrev_noaugoct_0050", 1.0050, {"marapr", "junjul", "novjan"}),
        ("promo_cogsmult_bestrev_noaugoct_0075", 1.0075, {"marapr", "junjul", "novjan"}),
        ("promo_cogsmult_bestrev_noaugoct_0125", 1.0125, {"marapr", "junjul", "novjan"}),
        ("promo_cogsmult_bestrev_mar_jun_nov_0100", 1.0100, {"marapr", "junjul", "novjan"}),
        ("promo_cogsmult_bestrev_junjul_novjan_0075", 1.0075, {"junjul", "novjan"}),
        ("promo_cogsmult_bestrev_marapr_only_0075", 1.0075, {"marapr"}),
    ]
    rows = [export_candidate(run_dir, frame, candidate_id, multiplier, windows) for candidate_id, multiplier, windows in specs]
    summary = pd.DataFrame(rows)
    summary.to_csv(run_dir / "summary.csv", index=False)
    write_json(
        run_dir / "config.json",
        {
            "source_frame_path": str(SOURCE_FRAME_PATH),
            "best_path": str(BEST_PATH),
            "anchor_path": str(ANCHOR_PATH),
            "public_winner": PUBLIC_WINNER,
            "public_winner_score": PUBLIC_WINNER_SCORE,
        },
    )
    write_report(run_dir, summary)
    logger.info("Saved %s promo COGS follow-up candidates to %s", len(summary), run_dir)
    print(summary.to_string(index=False))
    print(f"\nSaved outputs to {run_dir}")


if __name__ == "__main__":
    main()
