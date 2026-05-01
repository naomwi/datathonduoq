from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path
from threading import Event, Thread

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("TABPFN_DISABLE_TELEMETRY", "1")

import numpy as np
import pandas as pd
import torch
import xgboost as xgb
from lightning.pytorch import Trainer, seed_everything
from lightning.pytorch.callbacks import Callback, EarlyStopping
from pytorch_forecasting import GroupNormalizer, TemporalFusionTransformer, TimeSeriesDataSet
from pytorch_forecasting.metrics import MAE
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from tabpfn import TabPFNRegressor
from tabpfn.constants import ModelVersion
from tabpfn.regressor import ModelSource

from logging_utils import create_run_dir, setup_logger, write_json
from train_recursive_forecast import (

    PROMO_RAW_COLUMNS,
    SYSTEMS,
    _apply_cogs_postprocess,
    _compute_ratio_stats,
    _trailing_ratio,
    build_feature_row,
    ensure_inputs,
    get_candidate_feature_sets,
    recursive_forecast,
    zero_unknown_promo_signals,
)


RUN_PREFIX = "revenue_family_screen"
SCREEN_FOLD = ("2021-01-01", "2022-07-02")
CURRENT_WINNER = "system_promo_plus_cogs_blend60_clip_q99"
TFT_ENCODER_LENGTH = 365
TFT_MAX_EPOCHS = 100
TFT_BATCH_SIZE = 64
USE_CUDA = torch.cuda.is_available()
TABPFN_VERSION = ModelVersion.V2_6 if hasattr(ModelVersion, "V2_6") else ModelVersion.V2_5
TABPFN_VERSION_LABEL = "v2.6" if TABPFN_VERSION == ModelVersion.V2_6 else "v2.5"
TABPFN_MODEL_FILENAME = (
    ModelSource.get_regressor_v2_6().default_filename
    if TABPFN_VERSION == ModelVersion.V2_6
    else ModelSource.get_regressor_v2_5().default_filename
)
TABPFN_MODEL_PATH = Path.home() / "AppData" / "Roaming" / "tabpfn" / TABPFN_MODEL_FILENAME


def _rmse(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def write_status(
    run_dir: Path,
    stage: str,
    current_model: str | None = None,
    current_step: int | None = None,
    total_steps: int | None = None,
    extra: dict[str, object] | None = None,
) -> None:
    payload: dict[str, object] = {
        "stage": stage,
        "current_model": current_model,
        "current_step": current_step,
        "total_steps": total_steps,
        "timestamp": pd.Timestamp.utcnow().isoformat(),
    }
    if extra:
        payload.update(extra)
    write_json(run_dir / "status.json", payload)


@contextmanager
def heartbeat(
    run_dir: Path,
    stage: str,
    current_model: str,
    interval_sec: int = 30,
    extra: dict[str, object] | None = None,
):
    stop_event = Event()

    def _beat() -> None:
        beat = 0
        while not stop_event.wait(interval_sec):
            beat += 1
            payload = {"heartbeat_count": beat}
            if extra:
                payload.update(extra)
            write_status(run_dir, stage=stage, current_model=current_model, extra=payload)

    worker = Thread(target=_beat, daemon=True)
    worker.start()
    try:
        yield
    finally:
        stop_event.set()
        worker.join(timeout=1)


class TFTStatusCallback(Callback):
    def __init__(self, run_dir: Path, total_epochs: int) -> None:
        self.run_dir = run_dir
        self.total_epochs = total_epochs

    def on_train_epoch_end(self, trainer: Trainer, pl_module) -> None:  # pragma: no cover - runtime callback
        write_status(
            run_dir=self.run_dir,
            stage="running_tft_epoch",
            current_model="tft_revenue_direct",
            current_step=trainer.current_epoch + 1,
            total_steps=self.total_epochs,
            extra={"latest_val_loss": float(trainer.callback_metrics.get("val_loss", np.nan))},
        )


def _merge_truth(
    feature_store: pd.DataFrame,
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
    preds: pd.DataFrame,
) -> pd.DataFrame:
    truth = feature_store.loc[
        (feature_store["Date"] >= start_ts) & (feature_store["Date"] <= end_ts),
        ["Date", "Revenue"],
    ].copy()
    merged = truth.merge(preds, on="Date", how="left").sort_values("Date").reset_index(drop=True)
    return merged


def evaluate_current_winner(
    feature_store: pd.DataFrame,
    base: pd.DataFrame,
    feature_sets: dict[str, list[str]],
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
) -> pd.DataFrame:
    config = SYSTEMS[CURRENT_WINNER]
    preds = recursive_forecast(
        feature_store=feature_store,
        full_base=zero_unknown_promo_signals(base, start_ts - pd.Timedelta(days=1)),
        train_end_date=start_ts - pd.Timedelta(days=1),
        forecast_start=start_ts,
        forecast_end=end_ts,
        revenue_features=feature_sets[config["revenue_experiment"]],
        cogs_features=feature_sets[config["cogs_experiment"]],
        cogs_postprocess_variant=config["cogs_postprocess_variant"],
    )
    return preds[["Date", "Revenue_pred"]].copy()


def evaluate_tabpfn(
    feature_store: pd.DataFrame,
    base: pd.DataFrame,
    feature_sets: dict[str, list[str]],
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
    run_dir: Path,
) -> pd.DataFrame:
    if not TABPFN_MODEL_PATH.exists() and not os.environ.get("TABPFN_TOKEN"):
        raise RuntimeError(
            f"TabPFN {TABPFN_VERSION_LABEL} requires one-time license acceptance or a TABPFN_TOKEN. "
            "Visit https://ux.priorlabs.ai, accept the license, or provide TABPFN_TOKEN, "
            f"then rerun. Expected cached model path: {TABPFN_MODEL_PATH}"
        )

    config = SYSTEMS[CURRENT_WINNER]
    revenue_features = feature_sets[config["revenue_experiment"]]
    cogs_features = feature_sets[config["cogs_experiment"]]
    cutoff = start_ts - pd.Timedelta(days=1)
    train_df = feature_store.loc[feature_store["Date"] <= cutoff].copy()
    valid_dates = base.loc[(base["Date"] >= start_ts) & (base["Date"] <= end_ts), "Date"].copy()
    adjusted_base = zero_unknown_promo_signals(base, cutoff)
    promo_indexed = adjusted_base[["Date"] + PROMO_RAW_COLUMNS].copy().set_index("Date")

    revenue_model = TabPFNRegressor.create_default_for_version(
        TABPFN_VERSION,
        device="cuda" if USE_CUDA else "cpu",
        n_preprocessing_jobs=1,
    )
    with heartbeat(
        run_dir,
        stage="running_tabpfn_fit",
        current_model=f"tabpfn_{TABPFN_VERSION_LABEL.replace('.', '_')}_revenue",
        extra={"tabpfn_version": TABPFN_VERSION_LABEL},
    ):
        revenue_model.fit(train_df[revenue_features], train_df["Revenue"])

    cogs_model = xgb.XGBRegressor(**FIT_MODEL_PARAMS)
    cogs_model.fit(train_df[cogs_features], train_df["COGS"], verbose=False)

    history = train_df[["Date", "Revenue", "COGS"]].copy().set_index("Date").sort_index()
    ratio_stats = _compute_ratio_stats(train_df)
    results: list[dict[str, object]] = []

    total_dates = len(valid_dates)
    with heartbeat(
        run_dir,
        stage="running_tabpfn_predict",
        current_model=f"tabpfn_{TABPFN_VERSION_LABEL.replace('.', '_')}_revenue",
        extra={"tabpfn_version": TABPFN_VERSION_LABEL, "prediction_days": total_dates},
    ):
        for idx, current_date in enumerate(valid_dates, start=1):
            if idx == 1 or idx % 25 == 0 or idx == total_dates:
                write_status(
                    run_dir,
                    stage="running_tabpfn_predict",
                    current_model=f"tabpfn_{TABPFN_VERSION_LABEL.replace('.', '_')}_revenue",
                    current_step=idx,
                    total_steps=total_dates,
                    extra={"tabpfn_version": TABPFN_VERSION_LABEL},
                )

            revenue_row = build_feature_row(current_date, history, promo_indexed, revenue_features)
            cogs_row = build_feature_row(current_date, history, promo_indexed, cogs_features)
            pred_revenue = float(revenue_model.predict(revenue_row)[0])
            pred_cogs_raw = float(cogs_model.predict(cogs_row)[0])
            hist_ratio = _trailing_ratio(history, fallback=ratio_stats["median"])
            pred_cogs = _apply_cogs_postprocess(
                config["cogs_postprocess_variant"],
                pred_revenue,
                pred_cogs_raw,
                hist_ratio,
                ratio_stats,
            )
            pred_revenue = max(pred_revenue, 0.0)
            pred_cogs = max(pred_cogs, 0.0)
            history.loc[current_date, ["Revenue", "COGS"]] = [pred_revenue, pred_cogs]
            results.append({"Date": current_date, "Revenue_pred": pred_revenue})

    return pd.DataFrame(results)


def evaluate_tft(
    feature_store: pd.DataFrame,
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
    run_dir: Path,
) -> pd.DataFrame:
    cutoff = start_ts - pd.Timedelta(days=1)
    prediction_length = int((end_ts - start_ts).days + 1)
    tft_cols = [
        "Date",
        "Revenue",
        "COGS",
        "year",
        "month",
        "day",
        "dayofweek",
        "weekofyear",
        "quarter",
        "dayofyear",
        "is_weekend",
        "is_month_start",
        "is_month_end",
        "is_quarter_start",
        "is_quarter_end",
        "sin_dayofyear",
        "cos_dayofyear",
        "sin_dayofweek",
        "cos_dayofweek",
        "sin_month",
        "cos_month",
    ] + PROMO_RAW_COLUMNS
    data = feature_store[tft_cols].copy()
    future_mask = data["Date"] > cutoff
    for col in PROMO_RAW_COLUMNS:
        data.loc[future_mask, col] = 0.0

    data["series_id"] = "retail"
    data = data.sort_values("Date").reset_index(drop=True)
    data["time_idx"] = np.arange(len(data))

    known_reals = [
        "time_idx",
        "year",
        "month",
        "day",
        "dayofweek",
        "weekofyear",
        "quarter",
        "dayofyear",
        "is_weekend",
        "is_month_start",
        "is_month_end",
        "is_quarter_start",
        "is_quarter_end",
        "sin_dayofyear",
        "cos_dayofyear",
        "sin_dayofweek",
        "cos_dayofweek",
        "sin_month",
        "cos_month",
    ] + PROMO_RAW_COLUMNS
    cutoff_idx = int(data.loc[data["Date"] == cutoff, "time_idx"].iloc[0])
    start_idx = int(data.loc[data["Date"] == start_ts, "time_idx"].iloc[0])
    end_idx = int(data.loc[data["Date"] == end_ts, "time_idx"].iloc[0])

    training = TimeSeriesDataSet(
        data[data["time_idx"] <= cutoff_idx].copy(),
        time_idx="time_idx",
        target="Revenue",
        group_ids=["series_id"],
        static_categoricals=["series_id"],
        min_encoder_length=TFT_ENCODER_LENGTH,
        max_encoder_length=TFT_ENCODER_LENGTH,
        min_prediction_length=prediction_length,
        max_prediction_length=prediction_length,
        time_varying_known_reals=known_reals,
        time_varying_unknown_reals=["Revenue", "COGS"],
        target_normalizer=GroupNormalizer(groups=["series_id"]),
        add_relative_time_idx=True,
        add_target_scales=True,
        add_encoder_length=True,
    )

    validation = TimeSeriesDataSet.from_dataset(
        training,
        data[data["time_idx"] <= end_idx].copy(),
        min_prediction_idx=start_idx,
        predict=True,
        stop_randomization=True,
    )

    train_loader = training.to_dataloader(train=True, batch_size=TFT_BATCH_SIZE, num_workers=0)
    valid_loader = validation.to_dataloader(train=False, batch_size=1, num_workers=0)

    import torch
    torch.use_deterministic_algorithms(False)
    seed_everything(42, workers=False)
    early_stop = EarlyStopping(monitor="val_loss", min_delta=1e-4, patience=10, mode="min")
    status_callback = TFTStatusCallback(run_dir=run_dir, total_epochs=TFT_MAX_EPOCHS)
    trainer = Trainer(
        accelerator="gpu" if USE_CUDA else "cpu",
        devices=1,
        max_epochs=TFT_MAX_EPOCHS,
        callbacks=[early_stop, status_callback],
        enable_progress_bar=False,
        enable_model_summary=False,
        logger=False,
        deterministic=False,
    )
    tft = TemporalFusionTransformer.from_dataset(
        training,
        learning_rate=0.03,
        hidden_size=16,
        attention_head_size=1,
        dropout=0.1,
        hidden_continuous_size=8,
        loss=MAE(),
        output_size=1,
        reduce_on_plateau_patience=2,
        log_interval=-1,
    )
    trainer.fit(tft, train_dataloaders=train_loader, val_dataloaders=valid_loader)

    pred_tensor = tft.predict(valid_loader)
    pred_values = pred_tensor.detach().cpu().numpy().reshape(-1)
    pred_dates = data.loc[(data["Date"] >= start_ts) & (data["Date"] <= end_ts), "Date"].reset_index(drop=True)
    return pd.DataFrame({"Date": pred_dates, "Revenue_pred": pred_values[: len(pred_dates)]})


def summarize_result(name: str, merged: pd.DataFrame, duration_sec: float) -> dict[str, object]:
    return {
        "model_family": name,
        "n_days": len(merged),
        "revenue_mae": mean_absolute_error(merged["Revenue"], merged["Revenue_pred"]),
        "revenue_rmse": _rmse(merged["Revenue"], merged["Revenue_pred"]),
        "revenue_r2": r2_score(merged["Revenue"], merged["Revenue_pred"]),
        "duration_sec": duration_sec,
    }


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting revenue family screen in %s", run_dir)

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    start_ts = pd.Timestamp(SCREEN_FOLD[0])
    end_ts = pd.Timestamp(SCREEN_FOLD[1])

    write_json(
        run_dir / "config.json",
        {
            "screen_fold": SCREEN_FOLD,
            "current_winner": CURRENT_WINNER,
            "tft_encoder_length": TFT_ENCODER_LENGTH,
            "tft_max_epochs": TFT_MAX_EPOCHS,
            "use_cuda": USE_CUDA,
            "tabpfn_version": TABPFN_VERSION_LABEL,
            "tabpfn_model_path": str(TABPFN_MODEL_PATH),
        },
    )

    result_rows: list[dict[str, object]] = []
    predictions: dict[str, pd.DataFrame] = {}
    errors: list[dict[str, str]] = []

    write_status(run_dir, stage="starting", current_step=0, total_steps=3)
    tabpfn_candidate_name = f"tabpfn_{TABPFN_VERSION_LABEL.replace('.', '_')}_revenue"
    candidates = [
        ("xgb_current_winner", lambda: evaluate_current_winner(feature_store, base, feature_sets, start_ts, end_ts)),
        # (tabpfn_candidate_name, lambda: evaluate_tabpfn(feature_store, base, feature_sets, start_ts, end_ts, run_dir)),
        ("tft_revenue_direct", lambda: evaluate_tft(feature_store, start_ts, end_ts, run_dir)),
    ]

    for idx, (name, fn) in enumerate(candidates, start=1):
        logger.info("Running candidate %s", name)
        write_status(run_dir, stage="running_candidate", current_model=name, current_step=idx, total_steps=len(candidates))
        started = time.perf_counter()
        try:
            preds = fn()
            duration_sec = time.perf_counter() - started
            merged = _merge_truth(feature_store, start_ts, end_ts, preds)
            result_rows.append(summarize_result(name, merged, duration_sec))
            predictions[name] = merged
            merged.to_csv(run_dir / f"{name}_predictions.csv", index=False)
            write_status(
                run_dir,
                stage="candidate_completed",
                current_model=name,
                current_step=idx,
                total_steps=len(candidates),
                extra={
                    "duration_sec": duration_sec,
                    "revenue_mae": result_rows[-1]["revenue_mae"],
                },
            )
            logger.info(
                "Candidate %s | revenue MAE %.3f | duration %.1fs",
                name,
                result_rows[-1]["revenue_mae"],
                duration_sec,
            )
        except Exception as exc:  # pragma: no cover - experiment runner
            errors.append({"model_family": name, "error": repr(exc)})
            write_status(
                run_dir,
                stage="candidate_failed",
                current_model=name,
                current_step=idx,
                total_steps=len(candidates),
                extra={"error": repr(exc)},
            )
            logger.exception("Candidate %s failed", name)

    summary_df = pd.DataFrame(result_rows).sort_values("revenue_mae").reset_index(drop=True)
    summary_df.to_csv(run_dir / "summary.csv", index=False)
    if errors:
        pd.DataFrame(errors).to_csv(run_dir / "errors.csv", index=False)

    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Revenue Family Screen\n\n")
        f.write("## Goal\n")
        f.write(
            f"- Quick screen on the latest 548-day pseudo-test fold to see whether TFT or TabPFN {TABPFN_VERSION_LABEL} look promising relative to the current XGB winner.\n\n"
        )
        f.write("## Fold\n")
        f.write(f"- Start: `{SCREEN_FOLD[0]}`\n")
        f.write(f"- End: `{SCREEN_FOLD[1]}`\n")
        f.write(f"- Current winner reference: `{CURRENT_WINNER}`\n\n")
        f.write("## Summary\n")
        if summary_df.empty:
            f.write("- No candidate completed successfully.\n\n")
        else:
            f.write(summary_df.to_markdown(index=False))
            f.write("\n\n")
        if errors:
            f.write("## Errors\n")
            f.write(pd.DataFrame(errors).to_markdown(index=False))
            f.write("\n")

    write_status(
        run_dir,
        stage="completed",
        current_step=len(candidates),
        total_steps=len(candidates),
        extra={"n_success": len(result_rows), "n_failed": len(errors)},
    )
    logger.info("Saved report to %s", report_path)


if __name__ == "__main__":
    main()
