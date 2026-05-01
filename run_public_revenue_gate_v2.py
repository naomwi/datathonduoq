from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import mean_absolute_error, r2_score

from feature_pipeline import CALENDAR_COLUMNS
from logging_utils import create_run_dir, setup_logger, write_json
from run_leaderboard_sprint import SPRINT_FOLDS
from run_public_revenue_router_v1 import (
    PROMO_POLICY,
    ROUTER_BASE_FEATURE_COLUMNS,
    SWITCH_PROXY_WEIGHT,
    _rmse,
    build_router_feature_base,
    candidate_by_id,
    invalid_row_count,
    predict_candidate,
    zscore_align,
)
from train_recursive_forecast import ensure_inputs, get_candidate_feature_sets


RUN_PREFIX = "public_revenue_gate_v2"
DATASET_DIR = Path("dataset")
V1_RUN_DIR = Path("logs") / "20260420_185314_public_revenue_router_v1"

PUBLIC_ANCHOR_PATH = DATASET_DIR / "submission_blend_catboost_core_lightgbm_context_rev70_cogs100.csv"
PUBLIC_REVSWITCH_PATH = DATASET_DIR / "submission_public_structural_revswitch_z20_cogs100.csv"
PUBLIC_ROUTER_V1_PATH = DATASET_DIR / "submission_public_revenue_router_v1_clip.csv"
V1_OOF_PATH = V1_RUN_DIR / "oof_daily_predictions.csv"

DONOR_COLUMNS = ["anchor_rev70", "revswitch_z20", "router_v1_clip"]
CLASS_TO_DONOR = {0: "anchor_rev70", 1: "revswitch_z20", 2: "router_v1_clip"}
DONOR_TO_CLASS = {value: key for key, value in CLASS_TO_DONOR.items()}
BASELINE_FOLD_WEIGHT_MAP = {1: 1.0, 2: 1.5, 3: 2.0}

CLASSIFIER_PARAMS = {
    "loss_function": "MultiClass",
    "iterations": 600,
    "learning_rate": 0.03,
    "depth": 4,
    "l2_leaf_reg": 10.0,
    "subsample": 0.8,
    "random_seed": 42,
    "verbose": False,
    "allow_writing_files": False,
}

GATE_VARIANTS = [
    {
        "candidate_id": "public_revenue_gate_v2_hard",
        "priority": 1,
        "mode": "hard",
        "thesis": "hard regime gate across anchor, revswitch, and router_v1_clip.",
    },
    {
        "candidate_id": "public_revenue_gate_v2_margin55",
        "priority": 2,
        "mode": "margin",
        "confidence_threshold": 0.55,
        "thesis": "only leave router_v1_clip when the gate is confident enough.",
    },
    {
        "candidate_id": "public_revenue_gate_v2_soft",
        "priority": 3,
        "mode": "soft",
        "thesis": "probability blend across the three revenue paths.",
    },
]


def load_submission(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["Date"])
    return df.sort_values("Date").reset_index(drop=True)


def load_router_v1_oof() -> pd.DataFrame:
    df = pd.read_csv(V1_OOF_PATH, parse_dates=["Date"])
    df = df.loc[df["candidate_id"] == "public_revenue_router_v1_clip", ["fold", "Date", "Revenue_pred", "Revenue_true", "COGS_true", "COGS_pred"]].copy()
    return df.sort_values(["fold", "Date"]).reset_index(drop=True)


def build_fold_frame(
    *,
    fold_id: int,
    truth_df: pd.DataFrame,
    feature_base: pd.DataFrame,
    anchor_df: pd.DataFrame,
    revswitch_df: pd.DataFrame,
    router_v1_df: pd.DataFrame,
) -> pd.DataFrame:
    merged = truth_df.rename(columns={"Revenue": "Revenue_true", "COGS": "COGS_true"}).copy()
    merged = merged.merge(
        anchor_df.rename(columns={"Revenue_pred": "anchor_rev70", "COGS_pred": "cogs_anchor"})[
            ["Date", "anchor_rev70", "cogs_anchor"]
        ],
        on="Date",
        how="left",
    )
    merged = merged.merge(revswitch_df.rename(columns={"Revenue_pred": "revswitch_z20"})[["Date", "revswitch_z20"]], on="Date", how="left")
    merged = merged.merge(router_v1_df.rename(columns={"Revenue_pred": "router_v1_clip"})[["Date", "router_v1_clip"]], on="Date", how="left")
    merged = merged.merge(feature_base, on="Date", how="left")

    merged["delta_revswitch_vs_anchor"] = merged["revswitch_z20"] - merged["anchor_rev70"]
    merged["delta_router_v1_vs_anchor"] = merged["router_v1_clip"] - merged["anchor_rev70"]
    merged["delta_router_v1_vs_revswitch"] = merged["router_v1_clip"] - merged["revswitch_z20"]
    merged["donor_min"] = merged[DONOR_COLUMNS].min(axis=1)
    merged["donor_max"] = merged[DONOR_COLUMNS].max(axis=1)
    merged["donor_mean"] = merged[DONOR_COLUMNS].mean(axis=1)
    merged["donor_std"] = merged[DONOR_COLUMNS].std(axis=1)
    merged["donor_span"] = merged["donor_max"] - merged["donor_min"]
    merged["router_is_highest"] = (merged["router_v1_clip"] >= merged["donor_max"] - 1e-9).astype(int)
    merged["router_is_lowest"] = (merged["router_v1_clip"] <= merged["donor_min"] + 1e-9).astype(int)

    error_map = {
        donor: (merged["Revenue_true"] - merged[donor]).abs()
        for donor in DONOR_COLUMNS
    }
    error_df = pd.DataFrame(error_map)
    best_donor = error_df.idxmin(axis=1)
    best_error = error_df.min(axis=1)
    router_error = error_df["router_v1_clip"]
    gain_vs_router = (router_error - best_error).clip(lower=0.0)

    merged["label_best_donor"] = best_donor
    merged["label_class"] = merged["label_best_donor"].map(DONOR_TO_CLASS).astype(int)
    merged["gain_vs_router"] = gain_vs_router
    merged["fold"] = fold_id
    merged["sample_weight"] = BASELINE_FOLD_WEIGHT_MAP.get(fold_id, 1.0) * (1.0 + gain_vs_router / 50000.0)
    return merged


def apply_gate_variant(frame: pd.DataFrame, probabilities: np.ndarray, variant: dict[str, object]) -> pd.Series:
    donor_matrix = frame[DONOR_COLUMNS].to_numpy()
    mode = str(variant["mode"])
    if mode == "hard":
        class_idx = probabilities.argmax(axis=1)
        return pd.Series(donor_matrix[np.arange(len(frame)), class_idx], index=frame.index)
    if mode == "soft":
        weighted = (probabilities * donor_matrix).sum(axis=1)
        return pd.Series(weighted, index=frame.index)
    if mode == "margin":
        class_idx = probabilities.argmax(axis=1)
        max_prob = probabilities.max(axis=1)
        router_clip = frame["router_v1_clip"].to_numpy()
        chosen = donor_matrix[np.arange(len(frame)), class_idx]
        fallback = np.where(max_prob >= float(variant["confidence_threshold"]), chosen, router_clip)
        return pd.Series(fallback, index=frame.index)
    raise ValueError(f"Unknown gate mode: {mode}")


def build_summary(fold_metrics_df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        fold_metrics_df.groupby("candidate_id", as_index=False)
        .agg(
            revenue_mae_mean=("revenue_mae", "mean"),
            revenue_rmse_mean=("revenue_rmse", "mean"),
            revenue_r2_mean=("revenue_r2", "mean"),
            cogs_mae_mean=("cogs_mae", "mean"),
            cogs_rmse_mean=("cogs_rmse", "mean"),
            cogs_r2_mean=("cogs_r2", "mean"),
            combined_mae_mean=("combined_mae", "mean"),
        )
        .sort_values(["combined_mae_mean", "revenue_mae_mean"])
        .reset_index(drop=True)
    )
    return summary


def write_report(
    run_dir: Path,
    summary_df: pd.DataFrame,
    fold_metrics_df: pd.DataFrame,
    final_manifest_df: pd.DataFrame,
    feature_importance_df: pd.DataFrame,
) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Public Revenue Gate V2\n\n")
        f.write("## Framing\n")
        f.write("- Goal: search for a higher-variance public jump by gating between three proven Revenue paths.\n")
        f.write("- Revenue donors: `anchor_rev70`, `revswitch_z20`, `router_v1_clip`.\n")
        f.write("- COGS stays frozen from the current public winner path.\n")
        f.write("- Gate objective is best daily Revenue donor, with weights emphasizing days where router_v1_clip is clearly not best.\n\n")
        f.write("## OOF Ranking\n")
        f.write(summary_df.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Fold Metrics\n")
        f.write(fold_metrics_df.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Final Manifest\n")
        f.write(final_manifest_df.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Feature Importance\n")
        f.write(feature_importance_df.head(20).to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting public revenue gate v2 in %s", run_dir)

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    router_v1_oof = load_router_v1_oof()

    candidate_catboost = candidate_by_id("catboost_md2y_core")
    candidate_lgbm_context = candidate_by_id("lightgbm_md2y_context")
    candidate_switch = {
        "candidate_id": "catboost_md2y_revenue_switch_proxy",
        "kind": "model",
        "model_family": "catboost",
        "revenue_experiment": "curated_promo_cogs",
        "secondary_revenue_experiment": "baseline_plus_promo",
        "revenue_regime_variant": "promo_heavy_switch",
        "cogs_experiment": "curated_promo_cogs",
        "promo_future_policy": PROMO_POLICY,
        "context_future_policy": "zero",
        "price_future_policy": "zero",
        "hierarchy_future_policy": "zero",
        "cogs_postprocess_variant": "blend60_clip_q99",
    }

    frames: list[pd.DataFrame] = []
    baseline_rows: list[dict[str, object]] = []

    for fold_id, (start_date, end_date) in enumerate(SPRINT_FOLDS, start=1):
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        cutoff = start_ts - pd.Timedelta(days=1)
        logger.info("Generating fold donors for fold %s", fold_id)

        catboost_preds = predict_candidate(candidate_catboost, feature_store, base, feature_sets, start_ts, end_ts, cutoff)
        lgbm_context_preds = predict_candidate(candidate_lgbm_context, feature_store, base, feature_sets, start_ts, end_ts, cutoff)
        switch_preds = predict_candidate(candidate_switch, feature_store, base, feature_sets, start_ts, end_ts, cutoff)

        anchor_preds = pd.DataFrame(
            {
                "Date": catboost_preds["Date"],
                "Revenue_pred": 0.7 * catboost_preds["Revenue_pred"] + 0.3 * lgbm_context_preds["Revenue_pred"],
                "COGS_pred": catboost_preds["COGS_pred"],
            }
        )
        switch_anchor = pd.DataFrame(
            {
                "Date": anchor_preds["Date"],
                "Revenue_pred": 0.6 * anchor_preds["Revenue_pred"] + SWITCH_PROXY_WEIGHT * switch_preds["Revenue_pred"],
            }
        )
        switch_aligned = switch_anchor.copy()
        switch_aligned["Revenue_pred"] = zscore_align(anchor_preds["Revenue_pred"], switch_anchor["Revenue_pred"])
        revswitch_z20 = pd.DataFrame(
            {
                "Date": anchor_preds["Date"],
                "Revenue_pred": 0.8 * anchor_preds["Revenue_pred"] + 0.2 * switch_aligned["Revenue_pred"],
            }
        )

        truth_df = base.loc[(base["Date"] >= start_ts) & (base["Date"] <= end_ts), ["Date", "Revenue", "COGS"]].copy()
        feature_base = build_router_feature_base(base, cutoff)
        feature_base = feature_base.loc[(feature_base["Date"] >= start_ts) & (feature_base["Date"] <= end_ts)].copy()
        router_v1_fold = router_v1_oof.loc[router_v1_oof["fold"] == fold_id, ["Date", "Revenue_pred"]].copy()
        frame = build_fold_frame(
            fold_id=fold_id,
            truth_df=truth_df,
            feature_base=feature_base,
            anchor_df=anchor_preds[["Date", "Revenue_pred", "COGS_pred"]],
            revswitch_df=revswitch_z20,
            router_v1_df=router_v1_fold,
        )
        frames.append(frame)

        for donor in DONOR_COLUMNS:
            merged = frame[["Date", "Revenue_true", "COGS_true"]].copy()
            merged["Revenue_pred"] = frame[donor]
            merged["COGS_pred"] = anchor_preds["COGS_pred"].to_numpy()
            baseline_rows.append(
                {
                    "candidate_id": donor,
                    "fold": fold_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "revenue_mae": mean_absolute_error(merged["Revenue_true"], merged["Revenue_pred"]),
                    "revenue_rmse": _rmse(merged["Revenue_true"], merged["Revenue_pred"]),
                    "revenue_r2": r2_score(merged["Revenue_true"], merged["Revenue_pred"]),
                    "cogs_mae": mean_absolute_error(merged["COGS_true"], merged["COGS_pred"]),
                    "cogs_rmse": _rmse(merged["COGS_true"], merged["COGS_pred"]),
                    "cogs_r2": r2_score(merged["COGS_true"], merged["COGS_pred"]),
                    "combined_mae": 0.5
                    * (
                        mean_absolute_error(merged["Revenue_true"], merged["Revenue_pred"])
                        + mean_absolute_error(merged["COGS_true"], merged["COGS_pred"])
                    ),
                }
            )

    full_df = pd.concat(frames, ignore_index=True)
    feature_cols = [
        "anchor_rev70",
        "revswitch_z20",
        "router_v1_clip",
        "delta_revswitch_vs_anchor",
        "delta_router_v1_vs_anchor",
        "delta_router_v1_vs_revswitch",
        "donor_min",
        "donor_max",
        "donor_mean",
        "donor_std",
        "donor_span",
        "router_is_highest",
        "router_is_lowest",
    ]
    feature_cols += [col for col in ROUTER_BASE_FEATURE_COLUMNS if col in full_df.columns]
    feature_cols += [col for col in CALENDAR_COLUMNS if col in full_df.columns]
    write_json(
        run_dir / "config.json",
        {
            "feature_cols": feature_cols,
            "gate_variants": GATE_VARIANTS,
            "donor_columns": DONOR_COLUMNS,
        },
    )

    gate_rows: list[dict[str, object]] = []
    oof_rows: list[pd.DataFrame] = []
    for fold_id, (start_date, end_date) in enumerate(SPRINT_FOLDS, start=1):
        train_df = full_df.loc[full_df["fold"] != fold_id].copy()
        valid_df = full_df.loc[full_df["fold"] == fold_id].copy()

        model = CatBoostClassifier(**CLASSIFIER_PARAMS)
        model.fit(
            train_df[feature_cols],
            train_df["label_class"],
            sample_weight=train_df["sample_weight"],
        )
        probabilities = model.predict_proba(valid_df[feature_cols])

        for variant in GATE_VARIANTS:
            revenue_pred = apply_gate_variant(valid_df, probabilities, variant)
            merged = valid_df[["Date", "Revenue_true", "COGS_true"]].copy()
            merged["Revenue_pred"] = revenue_pred
            merged["COGS_pred"] = valid_df["cogs_anchor"].to_numpy()
            oof_rows.append(
                pd.DataFrame(
                    {
                        "candidate_id": variant["candidate_id"],
                        "fold": fold_id,
                        "Date": valid_df["Date"],
                        "Revenue_true": valid_df["Revenue_true"],
                        "Revenue_pred": revenue_pred,
                        "COGS_true": valid_df["COGS_true"],
                        "COGS_pred": valid_df["COGS_true"],
                    }
                )
            )
            gate_rows.append(
                {
                    "candidate_id": variant["candidate_id"],
                    "fold": fold_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "revenue_mae": mean_absolute_error(merged["Revenue_true"], merged["Revenue_pred"]),
                    "revenue_rmse": _rmse(merged["Revenue_true"], merged["Revenue_pred"]),
                    "revenue_r2": r2_score(merged["Revenue_true"], merged["Revenue_pred"]),
                    "cogs_mae": mean_absolute_error(merged["COGS_true"], merged["COGS_pred"]),
                    "cogs_rmse": _rmse(merged["COGS_true"], merged["COGS_pred"]),
                    "cogs_r2": r2_score(merged["COGS_true"], merged["COGS_pred"]),
                    "combined_mae": 0.5
                    * (
                        mean_absolute_error(merged["Revenue_true"], merged["Revenue_pred"])
                        + mean_absolute_error(merged["COGS_true"], merged["COGS_pred"])
                    ),
                }
            )

    fold_metrics_df = pd.DataFrame(baseline_rows + gate_rows).sort_values(["candidate_id", "fold"]).reset_index(drop=True)
    fold_metrics_df.to_csv(run_dir / "fold_metrics.csv", index=False)
    pd.concat(oof_rows, ignore_index=True).to_csv(run_dir / "oof_daily_predictions.csv", index=False)
    summary_df = build_summary(fold_metrics_df)
    summary_df.to_csv(run_dir / "summary.csv", index=False)

    logger.info("Training final gate on all folds")
    final_model = CatBoostClassifier(**CLASSIFIER_PARAMS)
    final_model.fit(
        full_df[feature_cols],
        full_df["label_class"],
        sample_weight=full_df["sample_weight"],
    )
    feature_importance_df = final_model.get_feature_importance(prettified=True)
    feature_importance_df.to_csv(run_dir / "feature_importance.csv", index=False)

    logger.info("Preparing final public donor frame")
    final_anchor = load_submission(PUBLIC_ANCHOR_PATH)
    final_revswitch = load_submission(PUBLIC_REVSWITCH_PATH)
    final_router_v1 = load_submission(PUBLIC_ROUTER_V1_PATH)
    final_feature_base = build_router_feature_base(base, pd.Timestamp("2022-12-31"))
    final_feature_base = final_feature_base.loc[
        (final_feature_base["Date"] >= final_anchor["Date"].min()) & (final_feature_base["Date"] <= final_anchor["Date"].max())
    ].copy()

    final_frame = pd.DataFrame({"Date": final_anchor["Date"]})
    final_frame["Revenue_true"] = np.nan
    final_frame["COGS_true"] = np.nan
    final_frame = build_fold_frame(
        fold_id=0,
        truth_df=final_frame.rename(columns={"Revenue_true": "Revenue", "COGS_true": "COGS"}),
        feature_base=final_feature_base,
        anchor_df=final_anchor.rename(columns={"Revenue": "Revenue_pred", "COGS": "COGS_pred"})[
            ["Date", "Revenue_pred", "COGS_pred"]
        ],
        revswitch_df=final_revswitch.rename(columns={"Revenue": "Revenue_pred"})[["Date", "Revenue_pred"]],
        router_v1_df=final_router_v1.rename(columns={"Revenue": "Revenue_pred"})[["Date", "Revenue_pred"]],
    )
    final_probabilities = final_model.predict_proba(final_frame[feature_cols])

    final_manifest_rows: list[dict[str, object]] = []
    for variant in GATE_VARIANTS:
        revenue_pred = apply_gate_variant(final_frame, final_probabilities, variant)
        submission = pd.DataFrame(
            {
                "Date": pd.to_datetime(final_frame["Date"]).dt.strftime("%Y-%m-%d"),
                "Revenue": revenue_pred,
                "COGS": final_router_v1["COGS"].to_numpy(),
            }
        )
        output_name = f"submission_{variant['candidate_id']}.csv"
        dataset_path = DATASET_DIR / output_name
        run_path = run_dir / output_name
        submission.to_csv(dataset_path, index=False)
        submission.to_csv(run_path, index=False)
        logger.info("Exported %s", output_name)

        revenue_abs_diff = (submission["Revenue"] - final_router_v1["Revenue"]).abs()
        final_manifest_rows.append(
            {
                "priority": variant["priority"],
                "candidate_id": variant["candidate_id"],
                "rows_changed_revenue": int((revenue_abs_diff > 1e-9).sum()),
                "rows_changed_cogs": 0,
                "anchor_invalid_rows": invalid_row_count(final_router_v1),
                "candidate_invalid_rows": invalid_row_count(submission),
                "mean_abs_diff_revenue_vs_router_v1": float(revenue_abs_diff.mean()),
                "thesis": variant["thesis"],
                "dataset_file": str(dataset_path),
            }
        )

    final_manifest_df = pd.DataFrame(final_manifest_rows).sort_values(["priority"]).reset_index(drop=True)
    final_manifest_df.to_csv(run_dir / "final_manifest.csv", index=False)
    write_json(run_dir / "final_manifest.json", {"candidates": final_manifest_rows})

    write_report(run_dir, summary_df, fold_metrics_df, final_manifest_df, feature_importance_df)
    logger.info("Saved summary to %s", run_dir / "summary.csv")
    if not summary_df.empty:
        logger.info("Top OOF candidate: %s", summary_df.iloc[0]["candidate_id"])


if __name__ == "__main__":
    main()
