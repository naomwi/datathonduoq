from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from feature_pipeline import TRAIN_END, get_ablation_feature_groups
from logging_utils import create_run_dir, setup_logger, write_json
from run_ablation import MODEL_PARAMS, load_training_frame


FIT_PARAMS = MODEL_PARAMS.copy()
FIT_PARAMS.pop("early_stopping_rounds", None)
OUTER_FOLDS = [
    ("2020-01-01", "2020-12-31"),
    ("2021-01-01", "2021-12-31"),
    ("2022-01-01", "2022-12-31"),
]
MIN_STAGE1_TRAIN_DAYS = 365
DEFAULT_TARGET = "order_count"


def get_control_features(df: pd.DataFrame) -> list[str]:
    groups = get_ablation_feature_groups(df)
    return sorted(set(groups["calendar"]).union(groups["revenue_history"]).union(groups["promo"]))


def get_stage1_target_features(df: pd.DataFrame, target_col: str) -> list[str]:
    groups = get_ablation_feature_groups(df)
    target_history = [col for col in df.columns if col.startswith(f"{target_col}_")]
    return sorted(set(groups["calendar"]).union(groups["promo"]).union(target_history))


def yearly_inner_windows(train_df: pd.DataFrame) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    years = sorted(train_df["Date"].dt.year.unique())
    if len(years) <= 2:
        return []
    windows = []
    for year in years:
        start = pd.Timestamp(f"{year}-01-01")
        end = pd.Timestamp(f"{year}-12-31")
        history_days = int((train_df["Date"] < start).sum())
        if history_days >= MIN_STAGE1_TRAIN_DAYS and (train_df["Date"] >= start).any():
            windows.append((start, end))
    return windows


def fit_predict_stage1_oof(
    train_df: pd.DataFrame,
    valid_df: pd.DataFrame,
    stage1_features: list[str],
    target_col: str,
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, object]]]:
    inner_windows = yearly_inner_windows(train_df)
    stage1_rows = []
    inner_logs: list[dict[str, object]] = []
    predicted_col = f"predicted_{target_col}"
    actual_col = f"actual_{target_col}"

    for fold_id, (start_ts, end_ts) in enumerate(inner_windows, start=1):
        inner_train = train_df[train_df["Date"] < start_ts].copy()
        inner_valid = train_df[(train_df["Date"] >= start_ts) & (train_df["Date"] <= end_ts)].copy()
        if inner_train.empty or inner_valid.empty:
            continue

        model = xgb.XGBRegressor(**FIT_PARAMS)
        model.fit(inner_train[stage1_features], inner_train[target_col], verbose=False)
        preds = model.predict(inner_valid[stage1_features])

        stage1_rows.append(
            pd.DataFrame(
                {
                    "Date": inner_valid["Date"].values,
                    predicted_col: preds,
                    actual_col: inner_valid[target_col].values,
                }
            )
        )
        inner_logs.append(
            {
                "inner_fold": fold_id,
                "start_date": start_ts,
                "end_date": end_ts,
                "stage1_mae": mean_absolute_error(inner_valid[target_col], preds),
                "stage1_rmse": np.sqrt(mean_squared_error(inner_valid[target_col], preds)),
                "stage1_r2": r2_score(inner_valid[target_col], preds),
            }
        )

    if stage1_rows:
        oof_df = pd.concat(stage1_rows, ignore_index=True)
    else:
        oof_df = pd.DataFrame(columns=["Date", predicted_col, actual_col])

    final_model = xgb.XGBRegressor(**FIT_PARAMS)
    final_model.fit(train_df[stage1_features], train_df[target_col], verbose=False)
    valid_pred = valid_df[["Date", target_col]].copy()
    valid_pred[predicted_col] = final_model.predict(valid_df[stage1_features])
    valid_pred = valid_pred.rename(columns={target_col: actual_col})

    return oof_df, valid_pred, inner_logs


def evaluate_stage2(
    train_df: pd.DataFrame,
    valid_df: pd.DataFrame,
    features: list[str],
    model_name: str,
) -> dict[str, object]:
    model = xgb.XGBRegressor(**MODEL_PARAMS)
    model.fit(train_df[features], train_df["Revenue"], eval_set=[(valid_df[features], valid_df["Revenue"])], verbose=False)
    preds = model.predict(valid_df[features])
    return {
        "model_name": model_name,
        "n_features": len(features),
        "mae": mean_absolute_error(valid_df["Revenue"], preds),
        "rmse": np.sqrt(mean_squared_error(valid_df["Revenue"], preds)),
        "r2": r2_score(valid_df["Revenue"], preds),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default=DEFAULT_TARGET)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target_col = args.target
    predicted_col = f"predicted_{target_col}"
    run_prefix = f"stage1_{target_col}_ablation"

    run_dir = create_run_dir(run_prefix)
    logger = setup_logger(run_prefix, run_dir)
    logger.info("Starting stage-1 %s ablation in %s", target_col, run_dir)

    df = load_training_frame()
    if target_col not in df.columns:
        raise KeyError(f"Target column '{target_col}' not found in feature store.")
    control_features = get_control_features(df)
    stage1_features = get_stage1_target_features(df, target_col)
    challenger_features = control_features + [predicted_col]

    write_json(
        run_dir / "config.json",
        {
            "target_col": target_col,
            "train_end": TRAIN_END,
            "outer_folds": OUTER_FOLDS,
            "protocol": "one_step_orthodox_then_recursive_ab",
            "comparison_rule": (
                "Both control and challenger use the same stage-2 train rows, "
                f"restricted to dates with OOF {predicted_col} available."
            ),
            "min_stage1_train_days": MIN_STAGE1_TRAIN_DAYS,
            "control_feature_count": len(control_features),
            "stage1_feature_count": len(stage1_features),
            "control_features": control_features,
            "stage1_features": stage1_features,
            "stage2_added_feature": predicted_col,
        },
    )

    fold_rows: list[dict[str, object]] = []
    inner_rows: list[dict[str, object]] = []

    for outer_fold_id, (start_date, end_date) in enumerate(OUTER_FOLDS, start=1):
        logger.info("Outer fold %s | valid %s -> %s", outer_fold_id, start_date, end_date)
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        outer_train = df[df["Date"] < start_ts].copy()
        outer_valid = df[(df["Date"] >= start_ts) & (df["Date"] <= end_ts)].copy()
        inner_windows = yearly_inner_windows(outer_train)
        logger.info(
            "Outer fold %s | stage1 inner windows: %s",
            outer_fold_id,
            len(inner_windows),
        )

        oof_stage1, valid_stage1, inner_logs = fit_predict_stage1_oof(
            outer_train,
            outer_valid,
            stage1_features,
            target_col,
        )
        for row in inner_logs:
            row["outer_fold"] = outer_fold_id
        inner_rows.extend(inner_logs)

        stage2_train = outer_train.merge(oof_stage1[["Date", predicted_col]], on="Date", how="left")
        stage2_train = stage2_train.dropna(subset=[predicted_col]).copy()
        stage2_valid = outer_valid.merge(valid_stage1[["Date", predicted_col]], on="Date", how="left")
        if stage2_train.empty:
            raise RuntimeError(f"Outer fold {outer_fold_id} has no OOF rows for stage-2 training.")

        logger.info(
            "Outer fold %s | stage2 train rows with OOF %s: %s / %s",
            outer_fold_id,
            predicted_col,
            len(stage2_train),
            len(outer_train),
        )

        control_result = evaluate_stage2(stage2_train, stage2_valid, control_features, "control")
        challenger_result = evaluate_stage2(stage2_train, stage2_valid, challenger_features, f"control_plus_{predicted_col}")

        fold_rows.append(
            {
                "outer_fold": outer_fold_id,
                "start_date": start_date,
                "end_date": end_date,
                **control_result,
            }
        )
        fold_rows.append(
            {
                "outer_fold": outer_fold_id,
                "start_date": start_date,
                "end_date": end_date,
                **challenger_result,
            }
        )

        logger.info(
            "Outer fold %s | control MAE %.3f | challenger MAE %.3f | delta %.3f",
            outer_fold_id,
            control_result["mae"],
            challenger_result["mae"],
            challenger_result["mae"] - control_result["mae"],
        )

    fold_df = pd.DataFrame(fold_rows)
    inner_df = pd.DataFrame(inner_rows)
    fold_df.to_csv(run_dir / "outer_fold_results.csv", index=False)
    inner_df.to_csv(run_dir / "stage1_inner_fold_results.csv", index=False)

    summary = (
        fold_df.groupby("model_name")
        .agg(
            n_features=("n_features", "mean"),
            mae_mean=("mae", "mean"),
            mae_std=("mae", "std"),
            rmse_mean=("rmse", "mean"),
            r2_mean=("r2", "mean"),
        )
        .reset_index()
        .sort_values("mae_mean")
        .reset_index(drop=True)
    )
    control_mae = float(summary.loc[summary["model_name"] == "control", "mae_mean"].iloc[0])
    challenger_mae = float(
        summary.loc[summary["model_name"] == f"control_plus_{predicted_col}", "mae_mean"].iloc[0]
    )
    summary["delta_mae_vs_control"] = summary["mae_mean"] - control_mae
    summary.to_csv(run_dir / "summary.csv", index=False)

    best_name = str(summary.iloc[0]["model_name"])
    better_than_control = challenger_mae < control_mae
    decision = "accept" if better_than_control else "reject"
    write_json(
        run_dir / "decision.json",
        {
            "protocol_gate": "one_step_orthodox",
            "decision": decision,
            "best_model": best_name,
            "better_than_control": better_than_control,
            "control_mae_mean": control_mae,
            "challenger_mae_mean": challenger_mae,
            "delta_mae_vs_control": challenger_mae - control_mae,
        },
    )

    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write(f"# Stage-1 {target_col} Ablation\n\n")
        f.write("## Protocol Notes\n")
        f.write("- Gate: `one-step orthodox` before any recursive A/B\n")
        f.write("- Comparison is row-matched: control and challenger train on the same rows with OOF stage-1 predictions\n")
        f.write(f"- Candidate added feature: `{predicted_col}`\n")
        f.write(f"- Decision: `{decision}`\n\n")
        f.write("## Summary\n")
        f.write(summary.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Outer Fold Results\n")
        f.write(fold_df.to_markdown(index=False))
        f.write("\n\n")
        if not inner_df.empty:
            f.write("## Stage-1 Inner Fold Results\n")
            f.write(inner_df.to_markdown(index=False))
            f.write("\n")

    logger.info("Finished run. Best model: %s", best_name)
    logger.info("Artifacts written to %s", run_dir)


if __name__ == "__main__":
    main()
