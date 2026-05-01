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
    ROUTER_BASE_FEATURE_COLUMNS,
    _rmse,
    build_router_feature_base,
    invalid_row_count,
    predict_candidate,
)
from train_recursive_forecast import ensure_inputs, get_candidate_feature_sets


RUN_PREFIX = "public_revenue_gate_v3"
DATASET_DIR = Path("dataset")
LOGS_DIR = Path("logs")
V1_RUN_DIR = LOGS_DIR / "20260420_185314_public_revenue_router_v1"
V1_OOF_PATH = V1_RUN_DIR / "oof_daily_predictions.csv"

PUBLIC_RECENCY_PATH = DATASET_DIR / "submission_catboost_md2y_core_recencyexp20.csv"
PUBLIC_ROUTER_V1_PATH = DATASET_DIR / "submission_public_revenue_router_v1_clip.csv"
PUBLIC_EOM_SOFT_PATH = DATASET_DIR / "submission_public_router_v1_eom_tail_soft.csv"

RECENCY_CANDIDATE = {
    "candidate_id": "catboost_md2y_core_recencyexp20",
    "kind": "model",
    "model_family": "catboost",
    "revenue_experiment": "curated_promo_cogs",
    "cogs_experiment": "curated_promo_cogs",
    "promo_future_policy": "seasonal_month_day_recent_2y",
    "context_future_policy": "zero",
    "cogs_postprocess_variant": "blend60_clip_q99",
    "sample_weight_mode": "exp_years",
    "sample_weight_decay": 0.20,
}

DONOR_COLUMNS = ["recencyexp20", "router_v1_clip", "router_eom_tail_soft"]
CLASS_TO_DONOR = {0: "recencyexp20", 1: "router_v1_clip", 2: "router_eom_tail_soft"}
DONOR_TO_CLASS = {value: key for key, value in CLASS_TO_DONOR.items()}
FOLD_WEIGHT_MAP = {1: 1.0, 2: 1.5, 3: 2.0}

CLASSIFIER_PARAMS = {
    "loss_function": "MultiClass",
    "iterations": 600,
    "learning_rate": 0.03,
    "depth": 4,
    "l2_leaf_reg": 10.0,
    "bootstrap_type": "Bernoulli",
    "subsample": 0.8,
    "random_seed": 42,
    "verbose": False,
    "allow_writing_files": False,
}

GATE_VARIANTS = [
    {
        "candidate_id": "public_revenue_gate_v3_hard",
        "priority": 1,
        "mode": "hard",
        "thesis": "hard gate across recencyexp20, router_v1_clip, and router_eom_tail_soft.",
    },
    {
        "candidate_id": "public_revenue_gate_v3_margin55",
        "priority": 2,
        "mode": "margin",
        "confidence_threshold": 0.55,
        "thesis": "fallback to recencyexp20 unless the gate is confident.",
    },
    {
        "candidate_id": "public_revenue_gate_v3_soft",
        "priority": 3,
        "mode": "soft",
        "thesis": "probability blend across recencyexp20 and structural router donors.",
    },
]


def load_submission(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)


def add_date_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out["month"] = out["Date"].dt.month
    out["days_to_eom"] = (out["Date"] + pd.offsets.MonthEnd(0) - out["Date"]).dt.days
    return out


def load_router_v1_oof() -> pd.DataFrame:
    df = pd.read_csv(V1_OOF_PATH, parse_dates=["Date"])
    df = df.loc[
        df["candidate_id"] == "public_revenue_router_v1_clip",
        ["fold", "Date", "Revenue_true", "Revenue_pred", "COGS_true", "COGS_pred"],
    ].copy()
    df = add_date_features(df)
    df["ratio_true_pred"] = df["Revenue_true"] / df["Revenue_pred"].replace(0.0, np.nan)
    return df.sort_values(["fold", "Date"]).reset_index(drop=True)


def build_eom_day_ratio(router_training_df: pd.DataFrame) -> dict[int, float]:
    eom = router_training_df.loc[router_training_df["days_to_eom"] <= 2].copy()
    day_ratio = (
        eom.groupby("days_to_eom")["ratio_true_pred"]
        .median()
        .clip(lower=1.0, upper=1.30)
        .to_dict()
    )
    return {int(key): float(value) for key, value in day_ratio.items()}


def apply_eom_tail_soft(
    df: pd.DataFrame,
    day_ratio: dict[int, float],
    blend_strength: float = 0.60,
    min_ratio: float = 1.0,
    max_ratio: float = 1.25,
) -> pd.DataFrame:
    out = add_date_features(df)
    ratio = out["days_to_eom"].map(day_ratio).fillna(1.0).astype(float)
    ratio = 1.0 + blend_strength * (ratio - 1.0)
    ratio = ratio.clip(lower=min_ratio, upper=max_ratio)
    out["Revenue_pred"] = (out["Revenue_pred"] * ratio).clip(lower=0.0)
    return out


def build_fold_frame(
    *,
    fold_id: int,
    truth_df: pd.DataFrame,
    feature_base: pd.DataFrame,
    recency_df: pd.DataFrame,
    router_df: pd.DataFrame,
    router_eom_df: pd.DataFrame,
) -> pd.DataFrame:
    merged = truth_df.rename(columns={"Revenue": "Revenue_true", "COGS": "COGS_true"}).copy()
    merged = add_date_features(merged)
    merged = merged.merge(
        recency_df.rename(columns={"Revenue_pred": "recencyexp20", "COGS_pred": "cogs_anchor"})[
            ["Date", "recencyexp20", "cogs_anchor"]
        ],
        on="Date",
        how="left",
    )
    merged = merged.merge(
        router_df.rename(columns={"Revenue_pred": "router_v1_clip"})[["Date", "router_v1_clip"]],
        on="Date",
        how="left",
    )
    merged = merged.merge(
        router_eom_df.rename(columns={"Revenue_pred": "router_eom_tail_soft"})[
            ["Date", "router_eom_tail_soft"]
        ],
        on="Date",
        how="left",
    )
    merged = merged.merge(feature_base, on="Date", how="left")
    merged["month"] = pd.to_datetime(merged["Date"]).dt.month
    merged["days_to_eom"] = (pd.to_datetime(merged["Date"]) + pd.offsets.MonthEnd(0) - pd.to_datetime(merged["Date"])).dt.days

    merged["delta_router_vs_recency"] = merged["router_v1_clip"] - merged["recencyexp20"]
    merged["delta_routereom_vs_recency"] = merged["router_eom_tail_soft"] - merged["recencyexp20"]
    merged["delta_routereom_vs_router"] = merged["router_eom_tail_soft"] - merged["router_v1_clip"]
    merged["donor_min"] = merged[DONOR_COLUMNS].min(axis=1)
    merged["donor_max"] = merged[DONOR_COLUMNS].max(axis=1)
    merged["donor_mean"] = merged[DONOR_COLUMNS].mean(axis=1)
    merged["donor_std"] = merged[DONOR_COLUMNS].std(axis=1)
    merged["donor_span"] = merged["donor_max"] - merged["donor_min"]
    merged["recency_is_highest"] = (merged["recencyexp20"] >= merged["donor_max"] - 1e-9).astype(int)
    merged["router_is_highest"] = (merged["router_v1_clip"] >= merged["donor_max"] - 1e-9).astype(int)
    merged["routereom_is_highest"] = (merged["router_eom_tail_soft"] >= merged["donor_max"] - 1e-9).astype(int)

    error_map = {donor: (merged["Revenue_true"] - merged[donor]).abs() for donor in DONOR_COLUMNS}
    error_df = pd.DataFrame(error_map)
    best_donor = error_df.idxmin(axis=1)
    best_error = error_df.min(axis=1)
    anchor_error = error_df["recencyexp20"]
    gain_vs_anchor = (anchor_error - best_error).clip(lower=0.0)

    merged["label_best_donor"] = best_donor
    merged["label_class"] = merged["label_best_donor"].map(DONOR_TO_CLASS).astype(int)
    merged["gain_vs_anchor"] = gain_vs_anchor
    merged["fold"] = fold_id
    merged["sample_weight"] = FOLD_WEIGHT_MAP.get(fold_id, 1.0) * (1.0 + gain_vs_anchor / 50000.0)
    return merged


def build_prediction_frame(
    *,
    feature_base: pd.DataFrame,
    recency_df: pd.DataFrame,
    router_df: pd.DataFrame,
    router_eom_df: pd.DataFrame,
) -> pd.DataFrame:
    merged = add_date_features(recency_df.rename(columns={"Revenue": "recencyexp20", "COGS": "cogs_anchor"}))
    merged = merged.merge(
        router_df.rename(columns={"Revenue": "router_v1_clip"})[["Date", "router_v1_clip"]],
        on="Date",
        how="left",
    )
    merged = merged.merge(
        router_eom_df.rename(columns={"Revenue": "router_eom_tail_soft"})[
            ["Date", "router_eom_tail_soft"]
        ],
        on="Date",
        how="left",
    )
    merged = merged.merge(feature_base, on="Date", how="left")
    merged["month"] = pd.to_datetime(merged["Date"]).dt.month
    merged["days_to_eom"] = (pd.to_datetime(merged["Date"]) + pd.offsets.MonthEnd(0) - pd.to_datetime(merged["Date"])).dt.days
    merged["delta_router_vs_recency"] = merged["router_v1_clip"] - merged["recencyexp20"]
    merged["delta_routereom_vs_recency"] = merged["router_eom_tail_soft"] - merged["recencyexp20"]
    merged["delta_routereom_vs_router"] = merged["router_eom_tail_soft"] - merged["router_v1_clip"]
    merged["donor_min"] = merged[DONOR_COLUMNS].min(axis=1)
    merged["donor_max"] = merged[DONOR_COLUMNS].max(axis=1)
    merged["donor_mean"] = merged[DONOR_COLUMNS].mean(axis=1)
    merged["donor_std"] = merged[DONOR_COLUMNS].std(axis=1)
    merged["donor_span"] = merged["donor_max"] - merged["donor_min"]
    merged["recency_is_highest"] = (merged["recencyexp20"] >= merged["donor_max"] - 1e-9).astype(int)
    merged["router_is_highest"] = (merged["router_v1_clip"] >= merged["donor_max"] - 1e-9).astype(int)
    merged["routereom_is_highest"] = (merged["router_eom_tail_soft"] >= merged["donor_max"] - 1e-9).astype(int)
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
        fallback = frame["recencyexp20"].to_numpy()
        chosen = donor_matrix[np.arange(len(frame)), class_idx]
        output = np.where(max_prob >= float(variant["confidence_threshold"]), chosen, fallback)
        return pd.Series(output, index=frame.index)
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
        f.write("# Public Revenue Gate V3\n\n")
        f.write("## Framing\n")
        f.write("- Goal: route Revenue between the best full public donor and the structural router family.\n")
        f.write("- Revenue donors: `recencyexp20`, `router_v1_clip`, `router_eom_tail_soft`.\n")
        f.write("- COGS stays frozen from `recencyexp20`, because that is the current best full public submission.\n")
        f.write("- Gate objective is best daily Revenue donor, with weights emphasizing days where recencyexp20 is clearly not best.\n\n")
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
    logger.info("Starting public revenue gate v3 in %s", run_dir)

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    router_v1_oof = load_router_v1_oof()

    frames: list[pd.DataFrame] = []
    baseline_rows: list[dict[str, object]] = []

    for fold_id, (start_date, end_date) in enumerate(SPRINT_FOLDS, start=1):
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        cutoff = start_ts - pd.Timedelta(days=1)
        logger.info("Generating fold donors for fold %s", fold_id)

        recency_preds = predict_candidate(RECENCY_CANDIDATE, feature_store, base, feature_sets, start_ts, end_ts, cutoff)
        router_fold = router_v1_oof.loc[router_v1_oof["fold"] == fold_id, ["Date", "Revenue_pred"]].copy()
        router_train = router_v1_oof.loc[router_v1_oof["fold"] != fold_id].copy()
        day_ratio = build_eom_day_ratio(router_train)
        router_eom_fold = apply_eom_tail_soft(router_fold, day_ratio=day_ratio)

        truth_df = base.loc[(base["Date"] >= start_ts) & (base["Date"] <= end_ts), ["Date", "Revenue", "COGS"]].copy()
        feature_base = build_router_feature_base(base, cutoff)
        feature_base = add_date_features(feature_base)
        feature_base = feature_base.loc[(feature_base["Date"] >= start_ts) & (feature_base["Date"] <= end_ts)].copy()
        frame = build_fold_frame(
            fold_id=fold_id,
            truth_df=truth_df,
            feature_base=feature_base,
            recency_df=recency_preds[["Date", "Revenue_pred", "COGS_pred"]],
            router_df=router_fold,
            router_eom_df=router_eom_fold[["Date", "Revenue_pred"]],
        )
        frames.append(frame)

        for donor in DONOR_COLUMNS:
            merged = frame[["Date", "Revenue_true", "COGS_true"]].copy()
            merged["Revenue_pred"] = frame[donor]
            merged["COGS_pred"] = frame["cogs_anchor"]
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
        "recencyexp20",
        "router_v1_clip",
        "router_eom_tail_soft",
        "delta_router_vs_recency",
        "delta_routereom_vs_recency",
        "delta_routereom_vs_router",
        "donor_min",
        "donor_max",
        "donor_mean",
        "donor_std",
        "donor_span",
        "recency_is_highest",
        "router_is_highest",
        "routereom_is_highest",
        "month",
        "days_to_eom",
    ]
    feature_cols += [col for col in ROUTER_BASE_FEATURE_COLUMNS if col in full_df.columns]
    feature_cols += [col for col in CALENDAR_COLUMNS if col in full_df.columns]
    feature_cols = list(dict.fromkeys(feature_cols))

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
                        "COGS_pred": valid_df["cogs_anchor"],
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
    final_recency = add_date_features(load_submission(PUBLIC_RECENCY_PATH))
    final_router = add_date_features(load_submission(PUBLIC_ROUTER_V1_PATH))
    final_router_eom = add_date_features(load_submission(PUBLIC_EOM_SOFT_PATH))
    final_feature_base = add_date_features(build_router_feature_base(base, pd.Timestamp("2022-12-31")))
    final_feature_base = final_feature_base.loc[
        (final_feature_base["Date"] >= final_recency["Date"].min()) & (final_feature_base["Date"] <= final_recency["Date"].max())
    ].copy()

    final_frame = build_prediction_frame(
        feature_base=final_feature_base,
        recency_df=final_recency[["Date", "Revenue", "COGS"]],
        router_df=final_router[["Date", "Revenue"]],
        router_eom_df=final_router_eom[["Date", "Revenue"]],
    )
    final_probabilities = final_model.predict_proba(final_frame[feature_cols])

    final_manifest_rows: list[dict[str, object]] = []
    for variant in GATE_VARIANTS:
        revenue_pred = apply_gate_variant(final_frame, final_probabilities, variant)
        submission = pd.DataFrame(
            {
                "Date": pd.to_datetime(final_frame["Date"]).dt.strftime("%Y-%m-%d"),
                "Revenue": revenue_pred,
                "COGS": final_recency["COGS"].to_numpy(),
            }
        )
        output_name = f"submission_{variant['candidate_id']}.csv"
        dataset_path = DATASET_DIR / output_name
        run_path = run_dir / output_name
        submission.to_csv(dataset_path, index=False)
        submission.to_csv(run_path, index=False)
        logger.info("Exported %s", output_name)

        revenue_abs_diff = (submission["Revenue"] - final_recency["Revenue"]).abs()
        final_manifest_rows.append(
            {
                "priority": variant["priority"],
                "candidate_id": variant["candidate_id"],
                "rows_changed_revenue": int((revenue_abs_diff > 1e-9).sum()),
                "rows_changed_cogs": 0,
                "anchor_invalid_rows": invalid_row_count(final_recency),
                "candidate_invalid_rows": invalid_row_count(submission),
                "mean_abs_diff_revenue_vs_recencyexp20": float(revenue_abs_diff.mean()),
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
