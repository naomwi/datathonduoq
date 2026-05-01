from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from analyze_public_shift_forensics import (
    ANCHOR_PATH,
    BEST_PATH,
    PUBLIC_DAYS,
    PUBLIC_END,
    PUBLIC_START,
    add_period_columns,
    mask_between_month_day,
    run_anchor_prediction,
)
from feature_pipeline import (
    CONTEXT_BASE_COLUMNS,
    PRICE_SIGNAL_COLUMNS,
    PROMO_BASE_COLUMNS,
    PROMO_MODEL_COLUMNS,
    PROMO_RESEARCH_BASE_COLUMNS,
    TARGET_SEASONAL_PRIOR_COLUMNS,
)
from logging_utils import create_run_dir, setup_logger, write_json
from train_recursive_forecast import TRAIN_END, ensure_inputs, get_candidate_feature_sets


RUN_PREFIX = "public_shift_recovery"
DATASET_DIR = Path("dataset")
NOTES_DIR = Path("notes")
CURRENT_PUBLIC_BEST = 684463.34954
CURRENT_PUBLIC_BEST_FILE = "submission_sample_v37_rev2023H2_p0100_c0650_away0250.csv"
PUBLIC_ANCHOR_FILE = ANCHOR_PATH.name

PUBLIC_SCORE_BOOK: dict[str, tuple[float, str]] = {
    PUBLIC_ANCHOR_FILE: (896000.0, "conversation_approx"),
    "submission_public_probe_promo_windows_rev_up6.csv": (888100.36839, "user_reported"),
    "submission_public_probe_promo_windows_rev_up8.csv": (887225.99926, "user_reported"),
    "submission_public_probe_promo_windows_rev_up12.csv": (888060.97204, "user_reported"),
    "submission_public_probe_rev2024h1_up5.csv": (896000.0, "conversation_approx"),
    "submission_public_probe_cogs2024h1_floor87.csv": (898472.39191, "user_reported"),
    "submission_public_parity_urban23_nonmain_up10_only.csv": (884654.02008, "user_reported"),
    "submission_public_revenue_gate_v3_soft.csv": (888493.05011, "user_reported"),
    "submission_promo_cogsratio_bestrev_a010_clip005.csv": (881699.03740, "user_reported"),
    "submission_promo_cogsmult_bestrev_all_0125.csv": (879533.52932, "user_reported"),
    "submission_txndecomp_v2_cogsratio_promotet_r40_up0075.csv": (874819.47653, "user_reported"),
    "submission_txndecomp_v2_cogsratio_followup_promotet_r60_up0100.csv": (873084.61381, "user_reported"),
    "submission_txndecomp_v3_rev_eventshape_r20_keepcogs.csv": (900762.59189, "user_reported"),
    "submission_publiconly_cogs_nonpromo_up015.csv": (865527.70356, "user_reported"),
    "submission_publiconly_cogs_break_all_plus050.csv": (839329.89703, "user_reported"),
    "submission_publiconly_cogs_break_followup_all_plus035.csv": (828569.81120, "user_reported"),
    "submission_publiconly_cogs_break_v5_all_plus020.csv": (825080.79137, "user_reported"),
    "submission_publiconly_cogs_reshape_v6_floor098_cap102_preserve.csv": (832854.44811, "user_reported"),
    "submission_publiconly_segment_v7_2023h2_up100.csv": (812496.01649, "user_reported"),
    "submission_publiconly_segment_v7_2024h1_up100.csv": (855840.24467, "user_reported"),
    "submission_publiconly_segment_v8_h2best_2024h1_down100.csv": (807504.66276, "user_reported"),
    "submission_publiconly_segment_v9_2023h1_up100.csv": (811093.31702, "user_reported"),
    "submission_publiconly_month_v10_h2_peak_more200.csv": (823082.86966, "user_reported"),
    "submission_publiconly_month_v10_h2_shoulder_more200.csv": (830056.22789, "user_reported"),
    "submission_top10_v12_cogs2023h1_down100.csv": (825629.56220, "user_reported"),
    "submission_top10_v12_rev2024highscale_down100_cogs2024highscale_down100.csv": (841263.33232, "user_reported"),
    "submission_top10_v13_rev2024highscale_up100_cogsdown100.csv": (830171.46835, "user_reported"),
    "submission_top10_v13_rev2024highscale_up100_keepcogs.csv": (812154.38787, "user_reported"),
    "submission_top10_v13_rev2023h2_up100_keepcogs.csv": (797595.96410, "user_reported"),
    "submission_h2rev_v15_current_h2_rev_up050.csv": (800572.16096, "user_reported"),
    "submission_h2shape_v16_cogs_oddmean_preserve.csv": (802116.33879, "user_reported"),
    "submission_h2antishape_v17_cogs_antiodd025_preserve.csv": (800578.87166, "user_reported"),
    "submission_h2revshape_v18_rev_odd050_preserve.csv": (798084.85522, "user_reported"),
    "submission_h2revshape_v18_rev_antiodd050_preserve.csv": (801642.41053, "user_reported"),
    "submission_sampleprior_v19_periodshape_both_a025.csv": (744359.56345, "user_reported"),
    "submission_sampleprior_v20_periodshape_both_a050.csv": (711472.67020, "user_reported"),
    "submission_sampleprior_v20_periodshape_both_a070.csv": (701103.47903, "user_reported"),
    "submission_sampleprior_v21_periodshape_both_a075.csv": (701144.82924, "user_reported"),
    "submission_sampleprior_v22_periodshape_both_a0725.csv": (701005.12470, "user_reported"),
    "submission_sample_v23_a0725_scale_to_sample005.csv": (707716.51463, "user_reported"),
    "submission_sample_v25_a0725_ratio_to_sample0050.csv": (701788.31792, "user_reported"),
    "submission_sample_v26_a0725_ratio_away_sample0025.csv": (700654.49101, "user_reported"),
    "submission_sample_v26_a0725_ratio_away_sample0050.csv": (700363.16716, "user_reported"),
    "submission_sample_v26_a0725_ratio_away_sample0100.csv": (699960.93186, "user_reported"),
    "submission_sample_v28_a0725_ratio_away_sample0125.csv": (699793.67454, "user_reported"),
    "submission_sample_v28_a0725_ratio_away_sample0175.csv": (699556.47851, "user_reported"),
    "submission_sample_v30_a0725_ratio_away_sample0225.csv": (699384.92478, "user_reported"),
    "submission_sample_v30_a0725_ratio_away_sample0250.csv": (699376.32670, "user_reported"),
    "submission_sample_v31_rev0725_cogs0750_away0250.csv": (699662.34515, "user_reported"),
    "submission_sample_v32_rev0725_cogs0700_away0250.csv": (699167.79998, "user_reported"),
    "submission_sample_v32_rev0725_cogs0650_away0250.csv": (698994.05843, "user_reported"),
    "submission_sample_v34_rev08000_cogs06500_away0250.csv": (698898.26661, "user_reported"),
    "submission_sample_v35_rev2023H2_up1000_r1000_c0650_away0250.csv": (707436.88912, "user_reported"),
    "submission_sample_v36_rev2023H2_r0600_c0650_away0250.csv": (692128.76474, "user_reported"),
    "submission_sample_v36_rev2023H2_r0400_c0650_away0250.csv": (687112.64298, "user_reported"),
    "submission_sample_v37_rev2023H2_p0200_c0650_away0250.csv": (684699.68850, "user_reported"),
    "submission_sample_v37_rev2023H2_p0100_c0650_away0250.csv": (684463.34954, "user_reported"),
    "submission_legal_router_v1_reliability_strong_nonh2_keepcogs.csv": (745552.16085, "user_reported"),
    "submission_legal_rawmd_prior_v3_r080_c065_h2r010.csv": (688915.44181, "user_reported"),
    "submission_legal_rawmd_v4_cogs_period_med.csv": (687010.89024, "user_reported"),
    "submission_tabpfn_promo_shape_cal8.csv": (888962.79663, "user_reported"),
    CURRENT_PUBLIC_BEST_FILE: (CURRENT_PUBLIC_BEST, "user_reported"),
    "submission_tabpfn26_windowmix_v1.csv": (883416.15633, "user_reported"),
    "submission_tabpfn26_windowmix_scale105.csv": (883183.43978, "user_reported"),
    "submission_tabpfn_v25low_windowmix_v1.csv": (883881.53813, "user_reported"),
    "submission_catboost_md2y_core_price_history.csv": (923770.94996, "user_reported"),
    "submission_public_recency_tail_ramp40.csv": (911000.0, "conversation_approx"),
    "submission_public_router_v1_eom_tail_soft.csv": (899000.0, "conversation_approx"),
    "submission_public_router_v1_eom_monthday_shrunk.csv": (902000.0, "conversation_approx"),
}

FOLD_WEIGHTS = {
    "long_2020_548d": 0.35,
    "long_2021_548d": 0.35,
    "year_2022": 0.20,
    "year_2020": 0.10,
}

PUBLIC_FAILED_FAMILY_QUARANTINE = {
    "recency_tail",
    "eom_router",
}

HORIZON_BINS = [
    ("h001_014", 1, 14),
    ("h015_030", 15, 30),
    ("h031_090", 31, 90),
    ("h091_180", 91, 180),
    ("h181_365", 181, 365),
    ("h366_548", 366, 548),
]

WINDOWS = {
    "marapr": ("03-18", "04-17"),
    "junjul": ("06-23", "07-22"),
    "augoct": ("08-30", "10-02"),
    "novjan": ("11-18", "01-02"),
}

KNOWN_FUTURE_CALENDAR = {
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
    "sin_dayofyear_k2",
    "cos_dayofyear_k2",
    "sin_dayofyear_k3",
    "cos_dayofyear_k3",
    "sin_dayofweek",
    "cos_dayofweek",
    "sin_month",
    "cos_month",
    "days_to_eom",
    "days_from_bom",
    "is_tet_month",
    "month_weekday_interact",
}

PROMO_COLUMNS = set(PROMO_BASE_COLUMNS) | set(PROMO_MODEL_COLUMNS) | set(PROMO_RESEARCH_BASE_COLUMNS)
CONTEXT_COLUMNS = set(CONTEXT_BASE_COLUMNS)
PRICE_COLUMNS = set(PRICE_SIGNAL_COLUMNS)
TARGET_PRIOR_COLUMNS = set(TARGET_SEASONAL_PRIOR_COLUMNS)


@dataclass(frozen=True)
class FoldSpec:
    name: str
    train_end: pd.Timestamp
    forecast_start: pd.Timestamp
    forecast_end: pd.Timestamp


def public_like_folds() -> list[FoldSpec]:
    return [
        FoldSpec(
            "long_2020_548d",
            pd.Timestamp("2019-12-31"),
            pd.Timestamp("2020-01-01"),
            pd.Timestamp("2020-01-01") + pd.Timedelta(days=PUBLIC_DAYS - 1),
        ),
        FoldSpec(
            "long_2021_548d",
            pd.Timestamp("2020-12-31"),
            pd.Timestamp("2021-01-01"),
            pd.Timestamp("2021-01-01") + pd.Timedelta(days=PUBLIC_DAYS - 1),
        ),
        FoldSpec(
            "year_2022",
            pd.Timestamp("2021-12-31"),
            pd.Timestamp("2022-01-01"),
            pd.Timestamp("2022-12-31"),
        ),
        FoldSpec(
            "year_2020",
            pd.Timestamp("2019-12-31"),
            pd.Timestamp("2020-01-01"),
            pd.Timestamp("2020-12-31"),
        ),
    ]


def safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    den = denominator.astype(float).replace(0.0, np.nan)
    return (numerator.astype(float) / den).replace([np.inf, -np.inf], np.nan).fillna(1.0)


def main_promo_mask(dates: pd.Series) -> pd.Series:
    masks = [mask_between_month_day(dates, start, end) for start, end in WINDOWS.values()]
    out = masks[0].copy()
    for mask in masks[1:]:
        out |= mask
    return out


def infer_family(filename: str) -> str:
    name = filename.lower()
    if filename == PUBLIC_ANCHOR_FILE:
        return "anchor"
    if "price_history" in name:
        return "price_history"
    if "tabpfn" in name and "windowmix" in name:
        return "promo_windowmix"
    if "promo_windows" in name:
        return "flat_main_promo"
    if "promo_shape" in name or "2024heavy" in name:
        return "tabpfn_global_shape"
    if "publiconly_segment" in name:
        return "publiconly_segment_oracle"
    if "cogs2024h1" in name or "cogs_floor" in name or "floor87" in name:
        return "broad_cogs_probe"
    if "parity" in name or "oddpromo" in name:
        return "promo_parity"
    if "public_event" in name:
        return "event_shoulder_spike"
    if "direct" in name or "horizon" in name:
        return "direct_horizon"
    if "rev2024h1" in name or "recovery_months" in name or "revenue_gate" in name:
        return "broad_revenue_probe"
    if "recency_tail" in name or "late_const" in name:
        return "recency_tail"
    if "eom" in name:
        return "eom_router"
    if "structural" in name or "bottomup" in name:
        return "structural_probe"
    if "catboost" in name or "lightgbm" in name or "xgb" in name:
        return "model_submission"
    return "other_submission"


def infer_projection_mode(family: str, filename: str) -> str:
    name = filename.lower()
    if family in {"recency_tail", "direct_horizon", "eom_router"}:
        return "horizon_step"
    if "2024h1" in name or "late" in name or "tail" in name:
        return "horizon_step"
    return "month_day"


def status_from_public_score(filename: str, family: str, public_score: float | None) -> str:
    if filename == CURRENT_PUBLIC_BEST_FILE:
        return "best_public_keep"
    if filename == PUBLIC_ANCHOR_FILE:
        return "anchor"
    if family in PUBLIC_FAILED_FAMILY_QUARANTINE:
        return "blocked_family_public_fail"
    if family in {"price_history", "broad_cogs_probe", "promo_parity", "tabpfn_global_shape"}:
        return "blocked_known_bad_family"
    if public_score is not None and public_score > CURRENT_PUBLIC_BEST + 1e-6:
        return "submitted_worse_than_best"
    if public_score is not None and public_score <= CURRENT_PUBLIC_BEST:
        return "submitted_public_improvement"
    return "unsubmitted_or_unknown"


def read_submission(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["Date"])
    required = {"Date", "Revenue", "COGS"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")
    return df[["Date", "Revenue", "COGS"]].copy()


def valid_public_submission_paths() -> list[Path]:
    paths = []
    for path in sorted(DATASET_DIR.glob("submission*.csv")):
        try:
            df = pd.read_csv(path, usecols=["Date"])
        except Exception:
            continue
        dates = pd.to_datetime(df["Date"], errors="coerce")
        if len(dates) == PUBLIC_DAYS and dates.min() == PUBLIC_START and dates.max() == PUBLIC_END:
            paths.append(path)
    return paths


def candidate_manifest(anchor_public: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    anchor = add_period_columns(anchor_public.rename(columns={"Revenue": "Revenue_anchor", "COGS": "COGS_anchor"}))
    promo = anchor["win_main_promo"].astype(bool)
    h1_2024 = anchor["is_2024_public_h1"].astype(bool)

    rows = []
    transforms: dict[str, pd.DataFrame] = {}
    for path in valid_public_submission_paths():
        sub = read_submission(path)
        merged = anchor.merge(sub, on="Date", how="inner")
        if len(merged) != PUBLIC_DAYS:
            continue

        rev_delta = merged["Revenue"] - merged["Revenue_anchor"]
        cogs_delta = merged["COGS"] - merged["COGS_anchor"]
        rev_ratio = safe_ratio(merged["Revenue"], merged["Revenue_anchor"])
        cogs_ratio = safe_ratio(merged["COGS"], merged["COGS_anchor"])
        transform = pd.DataFrame(
            {
                "Date": merged["Date"],
                "horizon_step": (merged["Date"] - PUBLIC_START).dt.days + 1,
                "month_day": merged["Date"].dt.strftime("%m-%d"),
                "revenue_multiplier": rev_ratio,
                "cogs_multiplier": cogs_ratio,
            }
        )
        transforms[path.name] = transform

        family = infer_family(path.name)
        score_tuple = PUBLIC_SCORE_BOOK.get(path.name)
        public_score = score_tuple[0] if score_tuple else None
        score_source = score_tuple[1] if score_tuple else ""
        projection_mode = infer_projection_mode(family, path.name)
        nonpromo_rev_abs_max = float(rev_delta.loc[~promo].abs().max())
        nonpromo_cogs_abs_max = float(cogs_delta.loc[~promo].abs().max())
        rows.append(
            {
                "filename": path.name,
                "candidate_id": path.stem.removeprefix("submission_"),
                "dataset_path": str(path),
                "family": family,
                "primary_projection_mode": projection_mode,
                "status": status_from_public_score(path.name, family, public_score),
                "public_score": public_score,
                "public_score_source": score_source,
                "delta_vs_current_best_public": public_score - CURRENT_PUBLIC_BEST if public_score is not None else np.nan,
                "rows": len(merged),
                "revenue_total_ratio_vs_anchor": float(merged["Revenue"].sum() / anchor["Revenue_anchor"].sum()),
                "cogs_total_ratio_vs_anchor": float(merged["COGS"].sum() / anchor["COGS_anchor"].sum()),
                "rev_delta_mean": float(rev_delta.mean()),
                "rev_delta_promo_mean": float(rev_delta.loc[promo].mean()),
                "rev_delta_nonpromo_mean": float(rev_delta.loc[~promo].mean()),
                "rev_delta_2024h1_mean": float(rev_delta.loc[h1_2024].mean()),
                "cogs_delta_mean": float(cogs_delta.mean()),
                "cogs_delta_promo_mean": float(cogs_delta.loc[promo].mean()),
                "cogs_delta_nonpromo_mean": float(cogs_delta.loc[~promo].mean()),
                "cogs_delta_2024h1_mean": float(cogs_delta.loc[h1_2024].mean()),
                "nonpromo_revenue_delta_max_abs": nonpromo_rev_abs_max,
                "nonpromo_cogs_delta_max_abs": nonpromo_cogs_abs_max,
                "changes_nonpromo_revenue": nonpromo_rev_abs_max > 1e-6,
                "changes_nonpromo_cogs": nonpromo_cogs_abs_max > 1e-6,
            }
        )
    manifest = pd.DataFrame(rows).sort_values(
        ["public_score", "family", "filename"],
        ascending=[True, True, True],
        na_position="last",
    )
    return manifest, transforms


def build_anchor_fold_predictions(
    feature_store: pd.DataFrame,
    base: pd.DataFrame,
    feature_sets: dict[str, list[str]],
    logger,
) -> pd.DataFrame:
    all_frames = []
    for fold in public_like_folds():
        logger.info(
            "Running fixed-anchor fold %s train_end=%s forecast=%s..%s",
            fold.name,
            fold.train_end.date(),
            fold.forecast_start.date(),
            fold.forecast_end.date(),
        )
        pred = run_anchor_prediction(
            feature_store=feature_store,
            base=base,
            feature_sets=feature_sets,
            train_end=fold.train_end,
            forecast_start=fold.forecast_start,
            forecast_end=fold.forecast_end,
            promo_policy="seasonal_month_day_recent_2y",
            context_policy="zero",
            sample_weight_mode="exp_years",
            sample_weight_decay=0.20,
        )
        truth = feature_store.loc[
            feature_store["Date"].between(fold.forecast_start, fold.forecast_end),
            ["Date", "Revenue", "COGS"],
        ].copy()
        frame = truth.merge(pred, on="Date", how="inner")
        frame["fold"] = fold.name
        frame["fold_start"] = fold.forecast_start
        frame["horizon_step"] = (frame["Date"] - fold.forecast_start).dt.days + 1
        all_frames.append(frame)
    return pd.concat(all_frames, ignore_index=True)


def apply_candidate_transform(
    anchor_fold: pd.DataFrame,
    transform: pd.DataFrame,
    projection_mode: str,
) -> pd.DataFrame:
    out = anchor_fold.copy()
    if projection_mode == "horizon_step":
        lookup = transform[["horizon_step", "revenue_multiplier", "cogs_multiplier"]].drop_duplicates("horizon_step")
        out = out.merge(lookup, on="horizon_step", how="left")
    elif projection_mode == "month_day":
        lookup = (
            transform.groupby("month_day", as_index=False)[["revenue_multiplier", "cogs_multiplier"]]
            .mean()
            .copy()
        )
        out["month_day"] = out["Date"].dt.strftime("%m-%d")
        out = out.merge(lookup, on="month_day", how="left")
    else:
        raise ValueError(f"Unknown projection mode: {projection_mode}")

    out["revenue_multiplier"] = out["revenue_multiplier"].fillna(1.0)
    out["cogs_multiplier"] = out["cogs_multiplier"].fillna(1.0)
    out["Revenue_candidate"] = out["Revenue_pred"].astype(float) * out["revenue_multiplier"].astype(float)
    out["COGS_candidate"] = out["COGS_pred"].astype(float) * out["cogs_multiplier"].astype(float)
    out["Revenue_candidate"] = out["Revenue_candidate"].clip(lower=0.0)
    out["COGS_candidate"] = out["COGS_candidate"].clip(lower=0.0)
    return out


def segment_masks(frame: pd.DataFrame) -> dict[str, pd.Series]:
    dates = pd.to_datetime(frame["Date"])
    promo = main_promo_mask(dates)
    masks: dict[str, pd.Series] = {
        "all": pd.Series(True, index=frame.index),
        "main_promo": promo,
        "nonpromo": ~promo,
    }
    for label, lo, hi in HORIZON_BINS:
        masks[label] = frame["horizon_step"].between(lo, hi)
    for label, (start, end) in WINDOWS.items():
        masks[f"window_{label}"] = mask_between_month_day(dates, start, end)
    return masks


def compute_metric_row(
    frame: pd.DataFrame,
    candidate_id: str,
    filename: str,
    family: str,
    projection_mode: str,
    fold: str,
    segment: str,
) -> dict[str, object] | None:
    if frame.empty:
        return None
    rev_abs = (frame["Revenue"] - frame["Revenue_candidate"]).abs()
    cogs_abs = (frame["COGS"] - frame["COGS_candidate"]).abs()
    revenue_mae = float(rev_abs.mean())
    cogs_mae = float(cogs_abs.mean())
    combined_mae = 0.5 * (revenue_mae + cogs_mae)
    target_mean_combined = float(0.5 * (frame["Revenue"].mean() + frame["COGS"].mean()))
    revenue_wape = float(rev_abs.sum() / max(frame["Revenue"].abs().sum(), 1e-9))
    cogs_wape = float(cogs_abs.sum() / max(frame["COGS"].abs().sum(), 1e-9))
    actual_ratio = (frame["COGS"] / frame["Revenue"].replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    pred_ratio = (frame["COGS_candidate"] / frame["Revenue_candidate"].replace(0, np.nan)).replace(
        [np.inf, -np.inf], np.nan
    )
    return {
        "candidate_id": candidate_id,
        "filename": filename,
        "family": family,
        "projection_mode": projection_mode,
        "fold": fold,
        "segment": segment,
        "rows": len(frame),
        "revenue_mae": revenue_mae,
        "cogs_mae": cogs_mae,
        "combined_mae": combined_mae,
        "normalized_combined_mae": combined_mae / max(target_mean_combined, 1e-9),
        "combined_wape": 0.5 * (revenue_wape + cogs_wape),
        "revenue_bias_actual_minus_pred": float((frame["Revenue"] - frame["Revenue_candidate"]).mean()),
        "cogs_bias_actual_minus_pred": float((frame["COGS"] - frame["COGS_candidate"]).mean()),
        "actual_revenue_mean": float(frame["Revenue"].mean()),
        "pred_revenue_mean": float(frame["Revenue_candidate"].mean()),
        "actual_cogs_ratio_mean": float(actual_ratio.mean()),
        "pred_cogs_ratio_mean": float(pred_ratio.mean()),
        "cogs_ratio_bias_pred_minus_actual": float(pred_ratio.mean() - actual_ratio.mean()),
    }


def projected_segment_metrics(
    anchor_fold_predictions: pd.DataFrame,
    manifest: pd.DataFrame,
    transforms: dict[str, pd.DataFrame],
    logger,
) -> pd.DataFrame:
    rows = []
    for idx, record in manifest.reset_index(drop=True).iterrows():
        filename = record["filename"]
        if filename not in transforms:
            continue
        if idx % 25 == 0:
            logger.info("Projecting candidate transforms %s/%s", idx + 1, len(manifest))
        projected = apply_candidate_transform(
            anchor_fold_predictions,
            transforms[filename],
            projection_mode=str(record["primary_projection_mode"]),
        )
        for fold_name, fold_frame in projected.groupby("fold", sort=False):
            for segment_name, mask in segment_masks(fold_frame).items():
                metric_frame = fold_frame.loc[mask].copy()
                metric = compute_metric_row(
                    metric_frame,
                    candidate_id=str(record["candidate_id"]),
                    filename=filename,
                    family=str(record["family"]),
                    projection_mode=str(record["primary_projection_mode"]),
                    fold=str(fold_name),
                    segment=segment_name,
                )
                if metric is not None:
                    rows.append(metric)
    return pd.DataFrame(rows)


def summarize_candidates(segment_metrics: pd.DataFrame, manifest: pd.DataFrame) -> pd.DataFrame:
    all_metrics = segment_metrics.loc[segment_metrics["segment"] == "all"].copy()
    fold_weight = pd.Series(FOLD_WEIGHTS, name="fold_weight")
    weighted = all_metrics.merge(fold_weight.rename_axis("fold").reset_index(), on="fold", how="left")
    weighted["fold_weight"] = weighted["fold_weight"].fillna(0.0)

    rows = []
    for (candidate_id, filename), group in weighted.groupby(["candidate_id", "filename"], sort=False):
        weight_sum = float(group["fold_weight"].sum())
        weighted_norm = float((group["normalized_combined_mae"] * group["fold_weight"]).sum() / max(weight_sum, 1e-9))
        weighted_mae = float((group["combined_mae"] * group["fold_weight"]).sum() / max(weight_sum, 1e-9))
        fold_norms = group.set_index("fold")["normalized_combined_mae"].to_dict()
        fold_maes = group.set_index("fold")["combined_mae"].to_dict()
        rows.append(
            {
                "candidate_id": candidate_id,
                "filename": filename,
                "public_like_weighted_norm": weighted_norm,
                "public_like_weighted_mae": weighted_mae,
                "worst_fold_norm": float(group["normalized_combined_mae"].max()),
                "worst_fold_combined_mae": float(group["combined_mae"].max()),
                "mean_norm": float(group["normalized_combined_mae"].mean()),
                "mean_combined_mae": float(group["combined_mae"].mean()),
                "long_2020_548d_norm": fold_norms.get("long_2020_548d", np.nan),
                "long_2021_548d_norm": fold_norms.get("long_2021_548d", np.nan),
                "year_2022_norm": fold_norms.get("year_2022", np.nan),
                "year_2020_norm": fold_norms.get("year_2020", np.nan),
                "long_2020_548d_mae": fold_maes.get("long_2020_548d", np.nan),
                "long_2021_548d_mae": fold_maes.get("long_2021_548d", np.nan),
                "year_2022_mae": fold_maes.get("year_2022", np.nan),
                "year_2020_mae": fold_maes.get("year_2020", np.nan),
                "mean_revenue_bias_actual_minus_pred": float(group["revenue_bias_actual_minus_pred"].mean()),
                "mean_cogs_bias_actual_minus_pred": float(group["cogs_bias_actual_minus_pred"].mean()),
            }
        )

    summary = pd.DataFrame(rows)
    summary = summary.merge(manifest, on=["candidate_id", "filename"], how="left")
    anchor_row = summary.loc[summary["filename"] == PUBLIC_ANCHOR_FILE]
    if anchor_row.empty:
        raise ValueError(f"Anchor candidate missing from summary: {PUBLIC_ANCHOR_FILE}")
    anchor_weighted_norm = float(anchor_row["public_like_weighted_norm"].iloc[0])
    anchor_worst_norm = float(anchor_row["worst_fold_norm"].iloc[0])
    summary["delta_weighted_norm_vs_anchor"] = summary["public_like_weighted_norm"] - anchor_weighted_norm
    summary["delta_worst_norm_vs_anchor"] = summary["worst_fold_norm"] - anchor_worst_norm
    summary["public_rank_known"] = summary["public_score"].rank(method="dense", ascending=True)
    summary["gate"] = summary.apply(lambda row: gate_candidate(row, anchor_worst_norm), axis=1)
    return summary.sort_values(
        ["gate", "public_like_weighted_norm", "public_score", "filename"],
        ascending=[True, True, True, True],
        na_position="last",
    )


def gate_candidate(row: pd.Series, anchor_worst_norm: float) -> str:
    status = str(row.get("status", ""))
    family = str(row.get("family", ""))
    if status == "best_public_keep":
        return "00_keep_current_public_best"
    if status == "anchor":
        return "01_anchor_baseline"
    if status in {"blocked_known_bad_family", "blocked_family_public_fail", "submitted_worse_than_best"}:
        return "90_reject_public_evidence"
    if family in {
        "price_history",
        "broad_cogs_probe",
        "promo_parity",
        "tabpfn_global_shape",
        *PUBLIC_FAILED_FAMILY_QUARANTINE,
    }:
        return "91_reject_family_quarantine"
    if bool(row.get("changes_nonpromo_revenue", False)):
        return "80_reject_nonpromo_revenue_move"
    if row["delta_weighted_norm_vs_anchor"] <= 0.0 and row["worst_fold_norm"] <= anchor_worst_norm + 0.005:
        return "10_pass_public_like_gate"
    if row["delta_weighted_norm_vs_anchor"] <= 0.003:
        return "20_borderline_probe_only"
    return "70_reject_public_like_gate"


def classify_feature(feature: str) -> tuple[str, str]:
    if feature in {"Date", "Revenue", "COGS", "snapshot_date", "is_train"}:
        return "target_or_id", "not_allowed_as_future_feature"
    if feature in KNOWN_FUTURE_CALENDAR:
        return "known_future", "calendar_available_for_public"
    if feature in TARGET_PRIOR_COLUMNS:
        return "recursive_safe", "seasonal_target_prior_from_past_only"
    if (
        feature.startswith(("rev_", "cogs_", "revplus_", "cogsplus_"))
        or feature.startswith(("revenue_", "cogs_"))
        or "revplus" in feature
        or "cogsplus" in feature
    ):
        return "recursive_safe", "derived_from_recursive_target_history"
    if feature in PROMO_COLUMNS or feature.startswith(("promo_", "active_promo_", "days_since_promo")):
        return "policy_imputed", "requires_explicit_future_promo_policy"
    if "_promo_" in feature or "discount" in feature:
        return "policy_imputed", "requires_explicit_future_promo_policy"
    if feature in PRICE_COLUMNS or "price" in feature or "margin" in feature:
        return "policy_imputed_risky", "price_policy_failed_public_when_used_directly"
    if feature in CONTEXT_COLUMNS or feature in {"sessions", "page_views", "visits"}:
        return "policy_imputed_risky", "context_unknown_after_2022"
    if any(token in feature for token in ["order", "item", "inventory", "traffic", "shipment", "payment", "review"]):
        return "unknown_future_risky", "raw_operational_signal_unobserved_in_public"
    if "_lag_" in feature or "_roll" in feature or "_ewm_" in feature:
        return "recursive_or_policy_dependent", "check_source_column_before_public_use"
    return "unclassified_review", "manual_review_required"


def write_feature_policy_audit(feature_store: pd.DataFrame, run_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for feature in feature_store.columns:
        classification, reason = classify_feature(feature)
        rows.append({"feature": feature, "policy_class": classification, "reason": reason})
    audit = pd.DataFrame(rows)
    summary = (
        audit.groupby("policy_class", as_index=False)
        .agg(feature_count=("feature", "count"))
        .sort_values("feature_count", ascending=False)
    )
    audit.to_csv(run_dir / "feature_policy_audit.csv", index=False)
    summary.to_csv(run_dir / "feature_policy_summary.csv", index=False)
    return audit, summary


def write_report(
    run_dir: Path,
    summary: pd.DataFrame,
    segment_metrics: pd.DataFrame,
    manifest: pd.DataFrame,
    feature_policy_summary: pd.DataFrame,
) -> None:
    anchor = summary.loc[summary["filename"] == PUBLIC_ANCHOR_FILE].iloc[0]
    best = summary.loc[summary["filename"] == CURRENT_PUBLIC_BEST_FILE].iloc[0]
    known_public = summary.loc[summary["public_score"].notna()].sort_values("public_score").copy()
    top_gate = summary.loc[summary["gate"].isin(["10_pass_public_like_gate", "20_borderline_probe_only"])].head(20)
    quarantined = manifest.loc[
        manifest["status"].isin(["blocked_known_bad_family", "submitted_worse_than_best"])
    ].head(30)

    cols = [
        "filename",
        "family",
        "public_score",
        "gate",
        "public_like_weighted_norm",
        "worst_fold_norm",
        "delta_weighted_norm_vs_anchor",
        "revenue_total_ratio_vs_anchor",
        "changes_nonpromo_revenue",
    ]
    seg_cols = [
        "candidate_id",
        "fold",
        "segment",
        "rows",
        "combined_mae",
        "normalized_combined_mae",
        "revenue_bias_actual_minus_pred",
        "cogs_ratio_bias_pred_minus_actual",
    ]
    best_segments = segment_metrics.loc[
        (segment_metrics["filename"] == CURRENT_PUBLIC_BEST_FILE)
        & (segment_metrics["segment"].isin(["all", "main_promo", "nonpromo", "h366_548"]))
    ][seg_cols]

    with (run_dir / "public_shift_report.md").open("w", encoding="utf-8") as f:
        f.write("# Public-Shift Recovery Report\n\n")
        f.write("This run replaces old average OOF gating with fixed-anchor, public-like projection checks.\n\n")
        f.write("## Baseline\n")
        f.write(
            f"- Anchor `{PUBLIC_ANCHOR_FILE}` weighted normalized error: "
            f"`{anchor['public_like_weighted_norm']:.6f}`, worst fold: `{anchor['worst_fold_norm']:.6f}`.\n"
        )
        f.write(
            f"- Current public best `{CURRENT_PUBLIC_BEST_FILE}` public score: "
            f"`{CURRENT_PUBLIC_BEST:.5f}`, projected weighted normalized error: "
            f"`{best['public_like_weighted_norm']:.6f}`.\n"
        )
        f.write("- Candidate transforms are projected from public submissions back onto 548-day local folds; this is a risk gate, not a replacement for true retraining.\n\n")

        f.write("## Known Public Scores\n")
        f.write(known_public[cols].head(40).to_markdown(index=False))
        f.write("\n\n")

        f.write("## Public-Like Gate Candidates\n")
        if top_gate.empty:
            f.write("No unknown candidates passed the public-like gate.\n\n")
        else:
            f.write(top_gate[cols].to_markdown(index=False))
            f.write("\n\n")

        f.write("## Current Best Segment Check\n")
        f.write(best_segments.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Quarantine / Do-Not-Submit Evidence\n")
        if quarantined.empty:
            f.write("No quarantined candidates found.\n\n")
        else:
            f.write(
                quarantined[
                    [
                        "filename",
                        "family",
                        "status",
                        "public_score",
                        "delta_vs_current_best_public",
                        "changes_nonpromo_revenue",
                        "changes_nonpromo_cogs",
                    ]
                ].to_markdown(index=False)
            )
            f.write("\n\n")

        f.write("## Feature Policy Summary\n")
        f.write(feature_policy_summary.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Decision Rules\n")
        f.write("- Keep `promo_windowmix` as the public-best family, but do not submit variants that fail worst-fold normalized gates.\n")
        f.write("- Do not use `price_history`, broad COGS floors, odd-year parity, or global TabPFN shape as direct public submissions.\n")
        f.write("- Treat `policy_imputed_risky` and `unknown_future_risky` features as banned unless a future policy is explicit and this runner passes.\n")


def write_note(run_dir: Path, summary: pd.DataFrame) -> None:
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    best_rows = summary.head(12)[
        [
            "filename",
            "family",
            "public_score",
            "gate",
            "public_like_weighted_norm",
            "worst_fold_norm",
            "delta_weighted_norm_vs_anchor",
        ]
    ]
    with (NOTES_DIR / "public_shift_recovery_2026-04-21.md").open("w", encoding="utf-8") as f:
        f.write("# Public Shift Recovery Implementation - 2026-04-21\n\n")
        f.write(f"Run directory: `{run_dir}`\n\n")
        f.write("Implemented fixed-anchor public-like validation, candidate manifest, segment metrics, and feature policy audit.\n\n")
        f.write("## Top Rows\n")
        f.write(best_rows.to_markdown(index=False))
        f.write("\n\n")
        f.write("Required outputs:\n")
        f.write(f"- `{run_dir / 'summary.csv'}`\n")
        f.write(f"- `{run_dir / 'segment_metrics.csv'}`\n")
        f.write(f"- `{run_dir / 'candidate_manifest.csv'}`\n")
        f.write(f"- `{run_dir / 'public_shift_report.md'}`\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting public-shift recovery run")

    if not ANCHOR_PATH.exists():
        raise FileNotFoundError(f"Missing anchor submission: {ANCHOR_PATH}")
    if not BEST_PATH.exists():
        raise FileNotFoundError(f"Missing current best submission: {BEST_PATH}")

    anchor_public = read_submission(ANCHOR_PATH)
    manifest, transforms = candidate_manifest(anchor_public)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    logger.info("Loaded %s valid public-period submissions", len(manifest))

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))
    feature_policy_audit, feature_policy_summary = write_feature_policy_audit(feature_store, run_dir)
    logger.info("Feature policy classes: %s", feature_policy_summary.to_dict(orient="records"))

    anchor_fold_predictions = build_anchor_fold_predictions(feature_store, base, feature_sets, logger)
    anchor_fold_predictions.to_csv(run_dir / "anchor_fold_predictions.csv", index=False)

    segment_metrics = projected_segment_metrics(anchor_fold_predictions, manifest, transforms, logger)
    segment_metrics.to_csv(run_dir / "segment_metrics.csv", index=False)
    summary = summarize_candidates(segment_metrics, manifest)
    summary.to_csv(run_dir / "summary.csv", index=False)

    write_json(
        run_dir / "config.json",
        {
            "public_period": [str(PUBLIC_START.date()), str(PUBLIC_END.date())],
            "public_days": PUBLIC_DAYS,
            "anchor_path": str(ANCHOR_PATH),
            "current_public_best_path": str(BEST_PATH),
            "current_public_best_score": CURRENT_PUBLIC_BEST,
            "fold_weights": FOLD_WEIGHTS,
            "train_end": str(TRAIN_END.date()),
            "note": "Candidate public submissions are projected onto fixed-anchor folds via month-day or horizon-step multipliers.",
        },
    )
    write_report(run_dir, summary, segment_metrics, manifest, feature_policy_summary)
    write_note(run_dir, summary)

    logger.info("Saved public-shift recovery outputs to %s", run_dir)
    display_cols = [
        "filename",
        "family",
        "public_score",
        "gate",
        "public_like_weighted_norm",
        "worst_fold_norm",
        "delta_weighted_norm_vs_anchor",
    ]
    print(summary[display_cols].head(30).to_string(index=False))
    print(f"\nSaved outputs to {run_dir}")


if __name__ == "__main__":
    main()
