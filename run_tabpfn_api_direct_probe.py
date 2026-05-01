from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json
from train_recursive_forecast import TRAIN_END, apply_future_promo_policy, ensure_inputs
from feature_pipeline import PROMO_BASE_COLUMNS, PROMO_TARGET_ENCODING_COLUMNS


RUN_PREFIX = "tabpfn_api_direct_probe"
DATASET_DIR = Path("dataset")
ANCHOR_PATH = DATASET_DIR / "submission_catboost_md2y_core_recencyexp20.csv"
FORECAST_START = pd.Timestamp("2023-01-01")
FORECAST_END = pd.Timestamp("2024-07-01")


def authorize_api() -> None:
    token = os.getenv("PRIORLABS_TABPFN_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Set PRIORLABS_TABPFN_TOKEN before running this script.")

    # Avoid tabpfn_client.set_access_token(), because it writes the token to package cache.
    from tabpfn_client.client import ServiceClient
    from tabpfn_client.config import Config

    ServiceClient.authorize(token)
    Config.use_server = True
    Config.is_initialized = True


def add_safe_calendar_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    dates = pd.to_datetime(out["Date"])
    out["month"] = dates.dt.month.astype(float)
    out["day"] = dates.dt.day.astype(float)
    out["dayofweek"] = dates.dt.dayofweek.astype(float)
    out["weekofyear"] = dates.dt.isocalendar().week.astype(float)
    out["dayofyear"] = dates.dt.dayofyear.astype(float)
    out["quarter"] = dates.dt.quarter.astype(float)
    out["is_weekend"] = dates.dt.dayofweek.isin([5, 6]).astype(float)
    out["is_month_start"] = dates.dt.is_month_start.astype(float)
    out["is_month_end"] = dates.dt.is_month_end.astype(float)
    out["sin_dayofyear"] = np.sin(2.0 * np.pi * out["dayofyear"] / 365.25)
    out["cos_dayofyear"] = np.cos(2.0 * np.pi * out["dayofyear"] / 365.25)
    out["sin_dayofweek"] = np.sin(2.0 * np.pi * out["dayofweek"] / 7.0)
    out["cos_dayofweek"] = np.cos(2.0 * np.pi * out["dayofweek"] / 7.0)

    month_day = dates.dt.strftime("%m-%d")
    out["promo_win_marapr"] = month_day.between("03-18", "04-17").astype(float)
    out["promo_win_junjul"] = month_day.between("06-23", "07-22").astype(float)
    out["promo_win_augoct"] = month_day.between("08-30", "10-02").astype(float)
    out["promo_win_novjan"] = (
        month_day.between("11-18", "12-31") | month_day.between("01-01", "01-02")
    ).astype(float)
    out["promo_window_any"] = (
        out["promo_win_marapr"]
        + out["promo_win_junjul"]
        + out["promo_win_augoct"]
        + out["promo_win_novjan"]
    ).clip(0.0, 1.0)
    out["is_2024"] = (dates.dt.year == 2024).astype(float)
    return out


def feature_columns(train_frame: pd.DataFrame, future_frame: pd.DataFrame) -> list[str]:
    base_cols = [
        col
        for col in list(PROMO_BASE_COLUMNS) + list(PROMO_TARGET_ENCODING_COLUMNS)
        if col in train_frame.columns and col in future_frame.columns
    ]
    calendar_cols = [
        "month",
        "day",
        "dayofweek",
        "weekofyear",
        "dayofyear",
        "quarter",
        "is_weekend",
        "is_month_start",
        "is_month_end",
        "sin_dayofyear",
        "cos_dayofyear",
        "sin_dayofweek",
        "cos_dayofweek",
        "promo_win_marapr",
        "promo_win_junjul",
        "promo_win_augoct",
        "promo_win_novjan",
        "promo_window_any",
        "is_2024",
    ]
    cols = [col for col in calendar_cols + base_cols if col in train_frame.columns and col in future_frame.columns]
    return list(dict.fromkeys(cols))


def clamp_around_anchor(values: pd.Series, anchor: pd.Series, rel: float, abs_cap: float) -> pd.Series:
    lower = np.maximum(anchor * (1.0 - rel), anchor - abs_cap)
    upper = np.minimum(anchor * (1.0 + rel), anchor + abs_cap)
    return pd.Series(np.clip(values, lower, upper), index=values.index)


def export_candidate(
    run_dir: Path,
    anchor: pd.DataFrame,
    candidate_id: str,
    revenue: pd.Series,
    publish: bool = False,
) -> dict:
    submission = pd.DataFrame(
        {
            "Date": pd.to_datetime(anchor["Date"]).dt.strftime("%Y-%m-%d"),
            "Revenue": np.clip(revenue, 0.0, None),
            "COGS": anchor["COGS"],
        }
    )
    run_path = run_dir / f"submission_{candidate_id}.csv"
    dataset_path = DATASET_DIR / f"submission_{candidate_id}.csv"
    submission.to_csv(run_path, index=False)
    if publish:
        submission.to_csv(dataset_path, index=False)

    delta = submission["Revenue"] - anchor["Revenue"]
    return {
        "candidate_id": candidate_id,
        "run_path": str(run_path),
        "dataset_path": str(dataset_path) if publish else "",
        "revenue_delta_mean": float(delta.mean()),
        "revenue_delta_abs_mean": float(delta.abs().mean()),
        "revenue_delta_max_abs": float(delta.abs().max()),
        "revenue_total_ratio": float(submission["Revenue"].sum() / anchor["Revenue"].sum()),
    }


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    authorize_api()

    feature_store, base = ensure_inputs()
    adjusted_base = apply_future_promo_policy(base, TRAIN_END, "seasonal_month_day_recent_2y")
    train_frame = add_safe_calendar_features(feature_store.loc[feature_store["Date"] <= TRAIN_END].copy())
    future_frame = add_safe_calendar_features(
        adjusted_base.loc[
            (adjusted_base["Date"] >= FORECAST_START) & (adjusted_base["Date"] <= FORECAST_END)
        ].copy()
    )
    anchor = pd.read_csv(ANCHOR_PATH, parse_dates=["Date"])

    cols = feature_columns(train_frame, future_frame)
    X_train = train_frame[cols].fillna(0.0)
    y_train = train_frame["Revenue"].astype(float)
    X_future = future_frame[cols].fillna(0.0)

    from tabpfn_client import TabPFNRegressor

    n_estimators = int(os.getenv("TABPFN_API_N_ESTIMATORS", "8"))
    model_path = os.getenv("TABPFN_API_MODEL_PATH", "default")
    logger.info("Fitting TabPFN API regressor model_path=%s n_estimators=%s rows=%s cols=%s", model_path, n_estimators, len(X_train), len(cols))
    model = TabPFNRegressor(model_path=model_path, n_estimators=n_estimators, random_state=42)
    model.fit(X_train, y_train)
    raw_pred = pd.Series(model.predict(X_future), index=anchor.index).clip(lower=0.0)
    raw_pred.to_frame("tabpfn_api_revenue_pred").to_csv(run_dir / "raw_predictions.csv", index=False)

    promo_mask = (
        future_frame["promo_window_any"].reset_index(drop=True).astype(float) > 0
    )
    anchor_rev = anchor["Revenue"].astype(float)
    donor = clamp_around_anchor(raw_pred, anchor_rev, rel=0.30, abs_cap=1_500_000.0)

    rows = []
    rows.append(export_candidate(run_dir, anchor, "tabpfn_api_direct_full_w20", 0.8 * anchor_rev + 0.2 * donor))
    rows.append(export_candidate(run_dir, anchor, "tabpfn_api_direct_full_w40", 0.6 * anchor_rev + 0.4 * donor))

    for weight in [0.20, 0.40, 0.60]:
        blended = anchor_rev.copy()
        blended.loc[promo_mask] = (1.0 - weight) * anchor_rev.loc[promo_mask] + weight * donor.loc[promo_mask]
        rows.append(export_candidate(run_dir, anchor, f"tabpfn_api_promo_donor_w{int(weight * 100)}", blended))

    summary = pd.DataFrame(rows)
    summary.to_csv(run_dir / "summary.csv", index=False)
    pd.Series(cols, name="feature").to_csv(run_dir / "features.csv", index=False)
    write_json(
        run_dir / "config.json",
        {
            "model_path": model_path,
            "n_estimators": n_estimators,
            "n_train_rows": len(X_train),
            "n_features": len(cols),
            "note": "API token is not stored in this run directory.",
        },
    )

    logger.info("Saved summary to %s", run_dir / "summary.csv")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
