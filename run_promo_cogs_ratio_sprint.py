from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json


RUN_PREFIX = "promo_cogs_ratio_sprint"
DATASET_DIR = Path("dataset")
BEST_PATH = DATASET_DIR / "submission_tabpfn_promo_windowmix_v1.csv"
ANCHOR_PATH = DATASET_DIR / "submission_catboost_md2y_core_recencyexp20.csv"
SOURCE_RUN_DIR = Path("logs/20260421_205129_promo_window_core_v2")


WINDOW_ORDER = ["marapr", "junjul", "augoct", "novjan"]


def load_public_scored() -> pd.DataFrame:
    path = SOURCE_RUN_DIR / "public_feature_frame_scored.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing scored public frame: {path}")
    frame = pd.read_csv(path, parse_dates=["Date"])
    required = {
        "Date",
        "Revenue_pred",
        "COGS_pred",
        "core_is_promo_window",
        "core_window_id",
        "score_cogs_ratio_delta",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")
    return frame


def load_best_and_anchor(frame: pd.DataFrame) -> pd.DataFrame:
    if not BEST_PATH.exists():
        raise FileNotFoundError(f"Missing best submission: {BEST_PATH}")
    if not ANCHOR_PATH.exists():
        raise FileNotFoundError(f"Missing anchor submission: {ANCHOR_PATH}")
    best = pd.read_csv(BEST_PATH, parse_dates=["Date"]).rename(columns={"Revenue": "Best_Revenue", "COGS": "Best_COGS"})
    anchor = pd.read_csv(ANCHOR_PATH, parse_dates=["Date"]).rename(columns={"Revenue": "Anchor_Revenue", "COGS": "Anchor_COGS"})
    out = frame.merge(best, on="Date", how="left").merge(anchor, on="Date", how="left")
    if out[["Best_Revenue", "Best_COGS", "Anchor_Revenue", "Anchor_COGS"]].isna().any().any():
        raise ValueError("Best/anchor merge produced nulls")
    return out


def adjusted_cogs(
    frame: pd.DataFrame,
    alpha: float,
    clip: float,
    positive_only: bool = False,
    allowed_windows: set[str] | None = None,
    ratio_delta_cap: float = 0.08,
) -> pd.Series:
    promo_mask = frame["core_is_promo_window"].astype(float) > 0
    if allowed_windows is not None:
        promo_mask &= frame["core_window_id"].astype(str).isin(allowed_windows)

    anchor_rev = frame["Anchor_Revenue"].astype(float).clip(lower=1.0)
    anchor_cogs = frame["Anchor_COGS"].astype(float).clip(lower=1.0)
    best_rev = frame["Best_Revenue"].astype(float).clip(lower=1.0)
    delta = frame["score_cogs_ratio_delta"].astype(float).clip(-ratio_delta_cap, ratio_delta_cap)
    if positive_only:
        delta = delta.clip(lower=0.0)

    anchor_ratio = (anchor_cogs / anchor_rev).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    desired_ratio = (anchor_ratio + alpha * delta).clip(0.65, 0.98)
    proposed_cogs = best_rev * desired_ratio
    multiplier = (proposed_cogs / anchor_cogs).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    multiplier = multiplier.clip(1.0 - clip, 1.0 + clip)

    cogs = anchor_cogs.copy()
    cogs.loc[promo_mask] = anchor_cogs.loc[promo_mask] * multiplier.loc[promo_mask]
    return cogs


def export_candidate(
    run_dir: Path,
    frame: pd.DataFrame,
    candidate_id: str,
    alpha: float,
    clip: float,
    positive_only: bool = False,
    allowed_windows: set[str] | None = None,
) -> dict[str, object]:
    dates = pd.to_datetime(frame["Date"])
    promo_mask = frame["core_is_promo_window"].astype(float) > 0
    active_mask = promo_mask.copy()
    if allowed_windows is not None:
        active_mask &= frame["core_window_id"].astype(str).isin(allowed_windows)
    cogs = adjusted_cogs(frame, alpha=alpha, clip=clip, positive_only=positive_only, allowed_windows=allowed_windows)
    submission = pd.DataFrame(
        {
            "Date": dates.dt.strftime("%Y-%m-%d"),
            "Revenue": frame["Best_Revenue"].astype(float).clip(lower=0.0),
            "COGS": cogs.clip(lower=0.0),
        }
    )

    run_path = run_dir / f"submission_{candidate_id}.csv"
    dataset_path = DATASET_DIR / f"submission_{candidate_id}.csv"
    submission.to_csv(run_path, index=False)
    submission.to_csv(dataset_path, index=False)

    anchor_rev = frame["Anchor_Revenue"].astype(float)
    anchor_cogs = frame["Anchor_COGS"].astype(float)
    best_rev = frame["Best_Revenue"].astype(float)
    rev_delta = submission["Revenue"] - anchor_rev
    cogs_delta = submission["COGS"] - anchor_cogs
    row: dict[str, object] = {
        "candidate_id": candidate_id,
        "run_path": str(run_path),
        "dataset_path": str(dataset_path),
        "alpha": alpha,
        "clip": clip,
        "positive_only": positive_only,
        "allowed_windows": ",".join(sorted(allowed_windows)) if allowed_windows else "all",
        "changed_rows": int(active_mask.sum()),
        "revenue_total_ratio_vs_anchor": float(submission["Revenue"].sum() / anchor_rev.sum()),
        "revenue_delta_promo_mean": float(rev_delta.loc[promo_mask].mean()),
        "revenue_delta_nonpromo_max_abs": float(rev_delta.loc[~promo_mask].abs().max()),
        "cogs_total_ratio_vs_anchor": float(submission["COGS"].sum() / anchor_cogs.sum()),
        "cogs_delta_mean": float(cogs_delta.mean()),
        "cogs_delta_active_mean": float(cogs_delta.loc[active_mask].mean()) if active_mask.any() else 0.0,
        "cogs_delta_promo_mean": float(cogs_delta.loc[promo_mask].mean()),
        "cogs_delta_nonpromo_max_abs": float(cogs_delta.loc[~promo_mask].abs().max()),
        "best_revenue_preserved": bool(np.allclose(submission["Revenue"], best_rev)),
    }
    for window in WINDOW_ORDER:
        mask = frame["core_window_id"].astype(str).eq(window)
        row[f"{window}_rows"] = int(mask.sum())
        row[f"{window}_cogs_delta_mean"] = float(cogs_delta.loc[mask].mean()) if mask.any() else 0.0
        row[f"{window}_score_delta_mean"] = float(frame.loc[mask, "score_cogs_ratio_delta"].mean()) if mask.any() else 0.0
    return row


def write_report(run_dir: Path, summary: pd.DataFrame, diagnostics: pd.DataFrame) -> None:
    with (run_dir / "report.md").open("w", encoding="utf-8") as f:
        f.write("# Promo COGS Ratio Sprint\n\n")
        f.write("Frame: keep current best Revenue exactly, adjust only promo-window COGS with small ratio-delta priors.\n\n")
        f.write("## Window Diagnostics\n")
        f.write(diagnostics.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Candidate Summary\n")
        f.write(summary.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    frame = load_best_and_anchor(load_public_scored())
    promo = frame.loc[frame["core_is_promo_window"].astype(float) > 0].copy()
    diagnostics = (
        promo.groupby("core_window_id", as_index=False)
        .agg(
            rows=("Date", "count"),
            score_cogs_ratio_delta_mean=("score_cogs_ratio_delta", "mean"),
            score_cogs_ratio_delta_median=("score_cogs_ratio_delta", "median"),
            score_cogs_ratio_delta_min=("score_cogs_ratio_delta", "min"),
            score_cogs_ratio_delta_max=("score_cogs_ratio_delta", "max"),
            anchor_cogs_mean=("Anchor_COGS", "mean"),
            best_revenue_mean=("Best_Revenue", "mean"),
        )
        .sort_values("core_window_id")
    )

    specs = [
        ("promo_cogsratio_bestrev_a005_clip005", 0.05, 0.005, False, None),
        ("promo_cogsratio_bestrev_a010_clip005", 0.10, 0.005, False, None),
        ("promo_cogsratio_bestrev_a015_clip010", 0.15, 0.010, False, None),
        ("promo_cogsratio_bestrev_pos_a010_clip005", 0.10, 0.005, True, None),
        ("promo_cogsratio_bestrev_pos_a020_clip010", 0.20, 0.010, True, None),
        ("promo_cogsratio_bestrev_noaugoct_a010_clip005", 0.10, 0.005, True, {"marapr", "junjul", "novjan"}),
        ("promo_cogsratio_bestrev_junjul_novjan_a015_clip010", 0.15, 0.010, True, {"junjul", "novjan"}),
    ]
    rows = [
        export_candidate(
            run_dir,
            frame,
            candidate_id=candidate_id,
            alpha=alpha,
            clip=clip,
            positive_only=positive_only,
            allowed_windows=allowed_windows,
        )
        for candidate_id, alpha, clip, positive_only, allowed_windows in specs
    ]
    summary = pd.DataFrame(rows)
    summary.to_csv(run_dir / "summary.csv", index=False)
    diagnostics.to_csv(run_dir / "window_diagnostics.csv", index=False)
    write_json(
        run_dir / "config.json",
        {
            "source_run_dir": str(SOURCE_RUN_DIR),
            "best_path": str(BEST_PATH),
            "anchor_path": str(ANCHOR_PATH),
            "hypothesis": "Public may need promo-specific COGS ratio adjustment while Revenue stays at current best.",
            "safety": "Revenue is exactly current best; non-promo COGS unchanged.",
        },
    )
    write_report(run_dir, summary, diagnostics)
    logger.info("Saved %s COGS-ratio candidates to %s", len(summary), run_dir)
    print(diagnostics.to_string(index=False))
    print(summary.to_string(index=False))
    print(f"\nSaved outputs to {run_dir}")


if __name__ == "__main__":
    main()
