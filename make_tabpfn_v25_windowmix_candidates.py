from __future__ import annotations

from pathlib import Path

import pandas as pd

from logging_utils import create_run_dir, setup_logger
from make_tabpfn_windowmix_followup import build_windowmix_uplift, export_candidate, write_report


SOURCE_RUN_DIR = Path("logs/20260421_181237_tabpfn_api_optimized_sprint")
RUN_PREFIX = "tabpfn_v25_windowmix_candidates"
BASE_TARGETS = {"marapr": 0.08, "junjul": 0.10, "augoct": 0.08, "novjan": 0.06}


def load_source() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    public_frame = pd.read_csv(SOURCE_RUN_DIR / "public_feature_frame.csv", parse_dates=["Date"])
    raw_preds = pd.read_csv(SOURCE_RUN_DIR / "raw_residual_predictions.csv", parse_dates=["Date"])
    metrics = pd.read_csv(SOURCE_RUN_DIR / "model_path_metrics.csv")
    return public_frame, raw_preds, metrics


def v25_weighted_scores(raw_preds: pd.DataFrame, metrics: pd.DataFrame) -> pd.Series:
    ok = metrics.loc[(metrics["status"] == "ok") & metrics["model_path"].astype(str).str.startswith("v2.5")].copy()
    if ok.empty:
        raise RuntimeError("No successful v2.5 model paths found.")
    weights = 1.0 / ok["residual_mae_promo"].astype(float).clip(lower=1e-6)
    weights = weights / weights.sum()
    scores = pd.Series(0.0, index=raw_preds.index)
    for weight, col in zip(weights, ok["column"], strict=False):
        scores += float(weight) * raw_preds[col].astype(float)
    return scores


def export_from_scores(
    run_dir: Path,
    public_frame: pd.DataFrame,
    candidate_id: str,
    scores: pd.Series,
    scale: float = 1.0,
    sharpness: float = 1.4,
) -> dict[str, object]:
    uplift = build_windowmix_uplift(public_frame, scores, BASE_TARGETS, weighted_mean_target=0.08, sharpness=sharpness)
    return export_candidate(run_dir, public_frame, candidate_id, uplift * scale)


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    public_frame, raw_preds, metrics = load_source()
    logger.info("Loaded raw TabPFN residual predictions from %s", SOURCE_RUN_DIR)

    score_sets: dict[str, pd.Series] = {
        "v25ens": v25_weighted_scores(raw_preds, metrics),
        "v25low": raw_preds["resid_v2_5_low_skew"].astype(float),
        "v25real": raw_preds["resid_v2_5_real"].astype(float),
        "v25default": raw_preds["resid_v2_5_default"].astype(float),
        "v25small": raw_preds["resid_v2_5_small_samples"].astype(float),
    }

    rows: list[dict[str, object]] = []
    for name, scores in score_sets.items():
        rows.append(export_from_scores(run_dir, public_frame, f"tabpfn_{name}_windowmix_v1", scores))

    rows.append(export_from_scores(run_dir, public_frame, "tabpfn_v25ens_windowmix_scale105", score_sets["v25ens"], scale=1.05))
    rows.append(export_from_scores(run_dir, public_frame, "tabpfn_v25low_windowmix_scale105", score_sets["v25low"], scale=1.05))
    rows.append(export_from_scores(run_dir, public_frame, "tabpfn_v25ens_windowmix_soft", score_sets["v25ens"], sharpness=0.8))
    rows.append(export_from_scores(run_dir, public_frame, "tabpfn_v25low_windowmix_soft", score_sets["v25low"], sharpness=0.8))

    summary = pd.DataFrame(rows)
    summary.to_csv(run_dir / "summary.csv", index=False)
    write_report(run_dir, summary)
    logger.info("Saved %s v2.5-only candidates to %s", len(summary), run_dir)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
