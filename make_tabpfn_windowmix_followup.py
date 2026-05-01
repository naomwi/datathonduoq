from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from logging_utils import create_run_dir, setup_logger


SOURCE_RUN_DIR = Path("logs/20260421_181237_tabpfn_api_optimized_sprint")
DATASET_DIR = Path("dataset")
RUN_PREFIX = "tabpfn_windowmix_followup"
BASE_TARGETS = {"marapr": 0.08, "junjul": 0.10, "augoct": 0.08, "novjan": 0.06}


def load_inputs() -> tuple[pd.DataFrame, pd.Series]:
    public_frame_path = SOURCE_RUN_DIR / "public_feature_frame.csv"
    scores_path = SOURCE_RUN_DIR / "tabpfn_residual_ensemble.csv"
    if not public_frame_path.exists():
        raise FileNotFoundError(f"Missing public frame: {public_frame_path}")
    if not scores_path.exists():
        raise FileNotFoundError(f"Missing TabPFN scores: {scores_path}")

    public_frame = pd.read_csv(public_frame_path, parse_dates=["Date"])
    scores = pd.read_csv(scores_path).iloc[:, 0].astype(float)
    if len(public_frame) != len(scores):
        raise ValueError(f"Length mismatch: public_frame={len(public_frame)} scores={len(scores)}")
    return public_frame, pd.Series(scores.to_numpy(), index=public_frame.index)


def window_masks(frame: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        "marapr": frame["promo_win_marapr"].astype(float) > 0,
        "junjul": frame["promo_win_junjul"].astype(float) > 0,
        "augoct": frame["promo_win_augoct"].astype(float) > 0,
        "novjan": frame["promo_win_novjan"].astype(float) > 0,
    }


def uplift_shape_from_scores(
    scores: pd.Series,
    mask: pd.Series,
    target_mean: float,
    sharpness: float,
) -> pd.Series:
    out = pd.Series(0.0, index=scores.index)
    if not mask.any():
        return out

    subset = scores.loc[mask].astype(float)
    ranks = subset.rank(method="average", pct=True).fillna(0.5)
    weights = np.exp((ranks - 0.5) * sharpness)
    weights = weights / weights.mean()
    uplift = np.clip(target_mean * weights, 0.015, 0.22)
    uplift = uplift * (target_mean / max(float(uplift.mean()), 1e-9))
    out.loc[mask] = uplift
    return out


def build_windowmix_uplift(
    public_frame: pd.DataFrame,
    scores: pd.Series,
    targets: dict[str, float],
    weighted_mean_target: float = 0.08,
    sharpness: float = 1.4,
) -> pd.Series:
    masks = window_masks(public_frame)
    uplift = pd.Series(0.0, index=public_frame.index)
    for name, mask in masks.items():
        uplift += uplift_shape_from_scores(scores, mask, targets[name], sharpness)

    promo_mask = public_frame["promo_window_any"].astype(float) > 0
    if promo_mask.any():
        anchor_rev = public_frame["Revenue_pred"].astype(float)
        weighted_mean = float((uplift.loc[promo_mask] * anchor_rev.loc[promo_mask]).sum() / anchor_rev.loc[promo_mask].sum())
        uplift.loc[promo_mask] *= weighted_mean_target / max(weighted_mean, 1e-9)
    return uplift


def export_candidate(
    run_dir: Path,
    public_frame: pd.DataFrame,
    candidate_id: str,
    uplift: pd.Series,
    cogs_pct: float = 0.0,
) -> dict[str, object]:
    promo_mask = public_frame["promo_window_any"].astype(float) > 0
    revenue = public_frame["Revenue_pred"].astype(float) * (1.0 + uplift.astype(float))
    cogs = public_frame["COGS_pred"].astype(float).copy()
    if cogs_pct:
        cogs.loc[promo_mask] *= 1.0 + cogs_pct

    submission = pd.DataFrame(
        {
            "Date": pd.to_datetime(public_frame["Date"]).dt.strftime("%Y-%m-%d"),
            "Revenue": np.clip(revenue, 0.0, None),
            "COGS": np.clip(cogs, 0.0, None),
        }
    )
    run_path = run_dir / f"submission_{candidate_id}.csv"
    dataset_path = DATASET_DIR / f"submission_{candidate_id}.csv"
    submission.to_csv(run_path, index=False)
    submission.to_csv(dataset_path, index=False)

    rev_delta = submission["Revenue"] - public_frame["Revenue_pred"]
    cogs_delta = submission["COGS"] - public_frame["COGS_pred"]
    anchor_rev = public_frame["Revenue_pred"].astype(float)
    promo_anchor_rev = anchor_rev.loc[promo_mask]
    promo_uplift = uplift.loc[promo_mask]
    weighted_promo_mean = float((promo_uplift * promo_anchor_rev).sum() / promo_anchor_rev.sum())

    row: dict[str, object] = {
        "candidate_id": candidate_id,
        "run_path": str(run_path),
        "dataset_path": str(dataset_path),
        "changed_rows": int(promo_mask.sum()),
        "promo_uplift_mean": float(promo_uplift.mean()),
        "promo_uplift_weighted_mean": weighted_promo_mean,
        "promo_uplift_min": float(promo_uplift.min()),
        "promo_uplift_max": float(promo_uplift.max()),
        "revenue_total_ratio": float(submission["Revenue"].sum() / public_frame["Revenue_pred"].sum()),
        "revenue_delta_mean": float(rev_delta.mean()),
        "revenue_delta_max_abs": float(rev_delta.abs().max()),
        "cogs_pct": cogs_pct,
        "cogs_total_ratio": float(submission["COGS"].sum() / public_frame["COGS_pred"].sum()),
        "cogs_delta_mean": float(cogs_delta.mean()),
        "nonpromo_revenue_delta_max_abs": float(rev_delta.loc[~promo_mask].abs().max()),
    }
    for name, mask in window_masks(public_frame).items():
        if mask.any():
            row[f"{name}_uplift_mean"] = float(uplift.loc[mask].mean())
            row[f"{name}_uplift_weighted_mean"] = float((uplift.loc[mask] * anchor_rev.loc[mask]).sum() / anchor_rev.loc[mask].sum())
    return row


def write_report(run_dir: Path, summary: pd.DataFrame) -> None:
    with (run_dir / "report.md").open("w", encoding="utf-8") as f:
        f.write("# TabPFN Windowmix Follow-Up\n\n")
        f.write("Uses the successful `tabpfn_promo_windowmix_v1` frame and only varies windowmix scale, within-window sharpness, window target allocation, or promo COGS co-move.\n\n")
        f.write(summary.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    public_frame, scores = load_inputs()
    logger.info("Loaded public frame rows=%s from %s", len(public_frame), SOURCE_RUN_DIR)

    base = build_windowmix_uplift(public_frame, scores, BASE_TARGETS, weighted_mean_target=0.08, sharpness=1.4)
    variants: list[tuple[str, pd.Series, float]] = [
        ("tabpfn_windowmix_scale095", base * 0.95, 0.0),
        ("tabpfn_windowmix_scale105", base * 1.05, 0.0),
        ("tabpfn_windowmix_scale110", base * 1.10, 0.0),
        ("tabpfn_windowmix_soft_v1", build_windowmix_uplift(public_frame, scores, BASE_TARGETS, 0.08, sharpness=0.8), 0.0),
        ("tabpfn_windowmix_sharp_v1", build_windowmix_uplift(public_frame, scores, BASE_TARGETS, 0.08, sharpness=2.2), 0.0),
        (
            "tabpfn_windowmix_junjul12_v1",
            build_windowmix_uplift(
                public_frame,
                scores,
                {"marapr": 0.075, "junjul": 0.12, "augoct": 0.08, "novjan": 0.05},
                0.08,
                sharpness=1.4,
            ),
            0.0,
        ),
        (
            "tabpfn_windowmix_augoct10_v1",
            build_windowmix_uplift(
                public_frame,
                scores,
                {"marapr": 0.075, "junjul": 0.10, "augoct": 0.10, "novjan": 0.05},
                0.08,
                sharpness=1.4,
            ),
            0.0,
        ),
        (
            "tabpfn_windowmix_novjan04_v1",
            build_windowmix_uplift(
                public_frame,
                scores,
                {"marapr": 0.085, "junjul": 0.105, "augoct": 0.085, "novjan": 0.04},
                0.08,
                sharpness=1.4,
            ),
            0.0,
        ),
        ("tabpfn_windowmix_cogs2", base, 0.02),
        ("tabpfn_windowmix_cogs4", base, 0.04),
    ]

    rows = [export_candidate(run_dir, public_frame, candidate_id, uplift, cogs_pct) for candidate_id, uplift, cogs_pct in variants]
    summary = pd.DataFrame(rows)
    summary.to_csv(run_dir / "summary.csv", index=False)
    write_report(run_dir, summary)
    logger.info("Saved %s windowmix follow-up candidates to %s", len(summary), run_dir)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
