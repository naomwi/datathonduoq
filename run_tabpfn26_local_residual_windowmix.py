from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from huggingface_hub import hf_hub_download
from sklearn.metrics import mean_absolute_error
from tabpfn import TabPFNRegressor

from logging_utils import create_run_dir, setup_logger, write_json
from make_tabpfn_windowmix_followup import build_windowmix_uplift, export_candidate, write_report


SOURCE_RUN_DIR = Path("logs/20260421_181237_tabpfn_api_optimized_sprint")
RUN_PREFIX = "tabpfn26_local_residual_windowmix"
HF_REPO_ID = "Prior-Labs/tabpfn_2_6"
HF_REGRESSOR_CKPT = "tabpfn-v2.6-regressor-v2.6_default.ckpt"
BASE_TARGETS = {"marapr": 0.08, "junjul": 0.10, "augoct": 0.08, "novjan": 0.06}


def load_source_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    oof = pd.read_csv(SOURCE_RUN_DIR / "anchor_oof_table.csv", parse_dates=["Date"])
    public_frame = pd.read_csv(SOURCE_RUN_DIR / "public_feature_frame.csv", parse_dates=["Date"])
    features = pd.read_csv(SOURCE_RUN_DIR / "features.csv")["feature"].astype(str).tolist()
    if "target_log_residual" not in oof.columns:
        raise ValueError("anchor_oof_table.csv is missing target_log_residual")
    return oof, public_frame, features


def download_tabpfn26_checkpoint() -> Path:
    return Path(hf_hub_download(repo_id=HF_REPO_ID, filename=HF_REGRESSOR_CKPT))


def fit_predict_tabpfn26(
    ckpt_path: Path,
    oof: pd.DataFrame,
    public_frame: pd.DataFrame,
    feature_cols: list[str],
    logger,
) -> tuple[pd.Series, pd.Series, dict[str, object]]:
    X_oof = oof[feature_cols].fillna(0.0).astype(float)
    y_oof = oof["target_log_residual"].astype(float)
    X_public = public_frame[feature_cols].fillna(0.0).astype(float)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    logger.info("Fitting local TabPFN 2.6 checkpoint=%s rows=%s cols=%s device=%s", ckpt_path, len(X_oof), len(feature_cols), device)
    model = TabPFNRegressor(
        model_path=ckpt_path,
        n_estimators=8,
        device=device,
        random_state=42,
    )
    model.fit(X_oof, y_oof)
    oof_pred = pd.Series(np.asarray(model.predict(X_oof), dtype=float), index=oof.index)
    public_pred = pd.Series(np.asarray(model.predict(X_public), dtype=float), index=public_frame.index)

    promo_mask = oof["promo_window_any"].astype(float) > 0
    metrics = {
        "model": "tabpfn_2_6_local",
        "checkpoint": str(ckpt_path),
        "device": device,
        "n_estimators": 8,
        "n_features": len(feature_cols),
        "n_oof_rows": len(oof),
        "n_public_rows": len(public_frame),
        "residual_mae_all": float(mean_absolute_error(y_oof, oof_pred)),
        "zero_residual_mae_all": float(np.abs(y_oof).mean()),
        "residual_mae_promo": float(mean_absolute_error(y_oof[promo_mask], oof_pred.loc[promo_mask])),
        "zero_residual_mae_promo": float(np.abs(y_oof[promo_mask]).mean()),
        "residual_mae_nonpromo": float(mean_absolute_error(y_oof[~promo_mask], oof_pred.loc[~promo_mask])),
        "zero_residual_mae_nonpromo": float(np.abs(y_oof[~promo_mask]).mean()),
    }
    return oof_pred, public_pred, metrics


def build_candidates(run_dir: Path, public_frame: pd.DataFrame, scores: pd.Series) -> pd.DataFrame:
    base = build_windowmix_uplift(public_frame, scores, BASE_TARGETS, weighted_mean_target=0.08, sharpness=1.4)
    variants: list[tuple[str, pd.Series, float]] = [
        ("tabpfn26_windowmix_v1", base, 0.0),
        ("tabpfn26_windowmix_scale095", base * 0.95, 0.0),
        ("tabpfn26_windowmix_scale105", base * 1.05, 0.0),
        ("tabpfn26_windowmix_scale110", base * 1.10, 0.0),
        ("tabpfn26_windowmix_soft_v1", build_windowmix_uplift(public_frame, scores, BASE_TARGETS, 0.08, sharpness=0.8), 0.0),
        ("tabpfn26_windowmix_sharp_v1", build_windowmix_uplift(public_frame, scores, BASE_TARGETS, 0.08, sharpness=2.2), 0.0),
        (
            "tabpfn26_windowmix_junjul12_v1",
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
            "tabpfn26_windowmix_augoct10_v1",
            build_windowmix_uplift(
                public_frame,
                scores,
                {"marapr": 0.075, "junjul": 0.10, "augoct": 0.10, "novjan": 0.05},
                0.08,
                sharpness=1.4,
            ),
            0.0,
        ),
        ("tabpfn26_windowmix_cogs2", base, 0.02),
    ]
    return pd.DataFrame(
        [export_candidate(run_dir, public_frame, candidate_id, uplift, cogs_pct) for candidate_id, uplift, cogs_pct in variants]
    )


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    oof, public_frame, feature_cols = load_source_frames()
    ckpt_path = download_tabpfn26_checkpoint()

    oof_pred, public_pred, metrics = fit_predict_tabpfn26(ckpt_path, oof, public_frame, feature_cols, logger)
    pd.DataFrame(
        {
            "Date": oof["Date"],
            "fold": oof["fold"],
            "target_log_residual": oof["target_log_residual"],
            "tabpfn26_residual": oof_pred,
        }
    ).to_csv(run_dir / "oof_residual_predictions.csv", index=False)
    pd.DataFrame({"Date": public_frame["Date"], "tabpfn26_residual": public_pred}).to_csv(
        run_dir / "raw_residual_predictions.csv",
        index=False,
    )
    pd.DataFrame([metrics]).to_csv(run_dir / "model_metrics.csv", index=False)
    write_json(
        run_dir / "config.json",
        {
            "hf_repo_id": HF_REPO_ID,
            "hf_checkpoint": HF_REGRESSOR_CKPT,
            "checkpoint_path": str(ckpt_path),
            "note": "Uses local Hugging Face TabPFN 2.6 regressor checkpoint; no API token is used.",
        },
    )

    summary = build_candidates(run_dir, public_frame, public_pred)
    summary.to_csv(run_dir / "summary.csv", index=False)
    write_report(run_dir, summary)
    logger.info("Saved local TabPFN 2.6 windowmix run to %s", run_dir)
    print(pd.DataFrame([metrics]).to_string(index=False))
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
