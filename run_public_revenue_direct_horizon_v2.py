"""
Direct Multi-Horizon CatBoost v2 — FIXED Frozen Origin Bug
Training: Direct (unrolled) — model learns f(X_t, Covariates_{t+h}, h) = Y_{t+h}
Inference: Recursive feature update — origin features refresh each day using predicted values.
This hybrid avoids both problems:
  - Training gradient is clean (no recursive error accumulation in the loss)
  - Inference features stay fresh (no frozen lags at day 300)
"""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error

from logging_utils import create_run_dir, setup_logger, write_json
from train_recursive_forecast import (
    ensure_inputs, get_candidate_feature_sets, apply_future_promo_policy,
    BACKTEST_FOLDS, TRAIN_END, PROMO_RAW_COLUMNS, make_regressor, fit_regressor,
    build_feature_row, build_sample_weights,
    _transform_target_series, recursive_forecast, _inverse_transform_scalar
)

RUN_PREFIX = "public_revenue_direct_horizon_v2_fixed"
DATASET_DIR = Path("dataset")

CANDIDATES = [
    {"candidate_id": "direct_v2_cut15", "cut": 15},
    {"candidate_id": "direct_v2_cut30", "cut": 30},
    {"candidate_id": "direct_v2_cut45", "cut": 45},
]


def evaluate_anchor(feature_store, base, feature_sets):
    """RecencyExp20 anchor for COGS and gating."""
    results = []
    rev_features = feature_sets["curated_promo_cogs"]
    cogs_features = feature_sets["curated_promo_cogs"]
    for fold_id, (start_date, end_date) in enumerate(BACKTEST_FOLDS, start=1):
        start_ts, end_ts = pd.Timestamp(start_date), pd.Timestamp(end_date)
        cutoff = start_ts - pd.Timedelta(days=1)
        adj_base = apply_future_promo_policy(base, cutoff, "seasonal_month_day_recent_2y")
        preds = recursive_forecast(
            feature_store=feature_store, full_base=adj_base,
            train_end_date=cutoff, forecast_start=start_ts, forecast_end=end_ts,
            revenue_features=rev_features, cogs_features=cogs_features,
            model_family="catboost", cogs_postprocess_variant="blend60_clip_q99",
            sample_weight_mode="exp_years", sample_weight_decay=0.20,
        )
        preds["fold"] = fold_id
        results.append(preds)
    return pd.concat(results, ignore_index=True)


def build_unrolled_dataset(feature_store, base, features, max_h):
    """Unroll to (origin_date, horizon) pairs for direct training."""
    future_indicators = PROMO_RAW_COLUMNS + ["sin_", "cos_", "is_", "year", "month", "day"]
    future_cols = [
        f for f in features
        if any(x in f for x in future_indicators)
        and "lag_" not in f and "rollmean" not in f and "ewm_" not in f
    ]
    origin_cols = [f for f in features if f not in future_cols]

    fs_idx = feature_store.set_index("Date").sort_index()
    base_idx = base.set_index("Date").sort_index()

    dfs = []
    for h in range(1, max_h + 1):
        df_h = fs_idx[origin_cols].copy()
        future_dates = pd.to_datetime(df_h.index) + pd.Timedelta(days=h)
        df_h["y_target"] = fs_idx["Revenue"].reindex(future_dates).values
        df_h["forecast_step"] = h
        df_h["target_date"] = future_dates
        for c in future_cols:
            if c in base_idx.columns:
                df_h[c] = base_idx.reindex(future_dates)[c].values
            elif c in fs_idx.columns:
                df_h[c] = fs_idx.reindex(future_dates)[c].values
        df_h = df_h.dropna(subset=["y_target"])
        dfs.append(df_h)

    unrolled = pd.concat(dfs, ignore_index=False)
    for c in unrolled.columns:
        if fs_idx.get(c) is not None and fs_idx[c].dtype == object:
            unrolled[c] = unrolled[c].astype(str)
        elif base_idx.get(c) is not None and base_idx[c].dtype == object:
            unrolled[c] = unrolled[c].astype(str)
    return unrolled, origin_cols, future_cols


def direct_multi_horizon_evaluate_v2(
    unrolled_train, origin_cols, future_cols, features, cut,
    train_end_date, forecast_start, forecast_end,
    feature_store, base, anchor_cogs
):
    """
    FIXED: Recursive feature update during inference.
    - Train two direct models (Early / Late) on unrolled data.
    - During inference, iterate day-by-day, updating history with predicted revenue,
      then build fresh origin features for the CORRECT horizon model.
    """
    train_end_date = pd.Timestamp(train_end_date)
    forecast_start = pd.Timestamp(forecast_start)
    forecast_end = pd.Timestamp(forecast_end)

    # Recency weighting (same as anchor)
    years_from_end = np.maximum(
        (train_end_date - unrolled_train["target_date"]).dt.days / 365.25, 0.0
    )
    unrolled_train["sample_weight"] = np.exp(-0.20 * years_from_end)

    early_mask = unrolled_train["forecast_step"] <= cut
    late_mask = unrolled_train["forecast_step"] > cut
    train_features = features + ["forecast_step"]

    # --- Train ---
    early_model = make_regressor("catboost")
    late_model = make_regressor("catboost")

    print(f"      Fitting Early Model (step <= {cut}) on {early_mask.sum()} rows...")
    fit_regressor(
        early_model, unrolled_train.loc[early_mask, train_features],
        _transform_target_series(unrolled_train.loc[early_mask, "y_target"], "none"),
        "catboost", sample_weight=unrolled_train.loc[early_mask, "sample_weight"],
    )
    if late_mask.any():
        print(f"      Fitting Late Model (step > {cut}) on {late_mask.sum()} rows...")
        fit_regressor(
            late_model, unrolled_train.loc[late_mask, train_features],
            _transform_target_series(unrolled_train.loc[late_mask, "y_target"], "none"),
            "catboost", sample_weight=unrolled_train.loc[late_mask, "sample_weight"],
        )

    # --- Inference: RECURSIVE feature update (THE FIX) ---
    print(f"      Inference with Recursive Feature Update...")
    forecast_dates = pd.date_range(forecast_start, forecast_end)

    # Initialize history with actual data up to cutoff
    history = (
        feature_store.loc[feature_store["Date"] <= train_end_date, ["Date", "Revenue", "COGS"]]
        .copy().set_index("Date").sort_index()
    )
    promo_indexed = base.set_index("Date")
    base_idx = base.set_index("Date")
    fs_idx = feature_store.set_index("Date")
    cogs_mapping = anchor_cogs.set_index("Date")["COGS_pred"].to_dict()

    results = []
    for step, current_date in enumerate(forecast_dates, start=1):
        # Build fresh origin features using recursive history
        row_features = build_feature_row(
            current_date, history, promo_indexed, None, origin_cols
        )

        # Add future-aware features for the target date
        for c in future_cols:
            if c in base_idx.columns:
                val = base_idx[c].get(current_date, np.nan)
            elif c in fs_idx.columns:
                val = fs_idx[c].get(current_date, np.nan)
            else:
                val = np.nan
            row_features[c] = val

        row_features["forecast_step"] = step

        # Pick the right model
        model = early_model if step <= cut else late_model
        pred_rev = float(model.predict(row_features[train_features])[0])
        pred_rev = max(pred_rev, 0.0)

        # Update history for next day's feature construction
        history.loc[current_date, "Revenue"] = pred_rev
        history.loc[current_date, "COGS"] = float(cogs_mapping.get(current_date, 0.0))

        results.append({"Date": current_date, "Revenue_pred": pred_rev})

    # Merge with frozen anchor COGS
    res = pd.DataFrame(results)
    res["COGS_pred"] = res["Date"].map(cogs_mapping).fillna(0.0)
    return res


def main():
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Direct Horizon v2 (FIXED recursive inference)...")

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))

    # Feature schema: strict_core + promo_detail
    features = feature_sets.get("forecast_core_plus_promo_detail", [])
    if not features:
        strict_core = feature_sets["forecast_core_strict"]
        from feature_pipeline import get_ablation_feature_groups
        groups = get_ablation_feature_groups(feature_store.head(1))
        features = sorted(list(set(strict_core).union(set(groups.get("promo_detail", [])))))

    logger.info("Step 1: Anchor OOF (recencyexp20) for COGS + gating...")
    anchor_oof = evaluate_anchor(feature_store, base, feature_sets)
    anchor_oof["Date"] = pd.to_datetime(anchor_oof["Date"])

    logger.info("Step 2: Unrolling Dataset...")
    max_h = max([(pd.Timestamp(f[1]) - pd.Timestamp(f[0])).days + 1 for f in BACKTEST_FOLDS])
    unrolled_full, origin_cols, future_cols = build_unrolled_dataset(
        feature_store, base, features, max_h=max_h
    )
    logger.info(f"Unrolled: {len(unrolled_full):,} rows. Future: {len(future_cols)}, Origin: {len(origin_cols)}")

    all_results = []
    for candidate in CANDIDATES:
        c_id = candidate["candidate_id"]
        cut = candidate["cut"]
        logger.info(f"\n--- Evaluating: {c_id} (Cut={cut}) ---")

        for fold_id, (start_date, end_date) in enumerate(BACKTEST_FOLDS, start=1):
            start_ts = pd.Timestamp(start_date)
            end_ts = pd.Timestamp(end_date)
            cutoff = start_ts - pd.Timedelta(days=1)

            print(f"  Fold {fold_id} ({start_date} -> {end_date})")
            adj_base = apply_future_promo_policy(base, cutoff, "seasonal_month_day_recent_2y")
            unrolled_train = unrolled_full[unrolled_full["target_date"] <= cutoff].copy()

            preds = direct_multi_horizon_evaluate_v2(
                unrolled_train, origin_cols, future_cols, features, cut,
                cutoff, start_ts, end_ts, feature_store, adj_base, anchor_oof
            )

            truth = feature_store.loc[
                (feature_store["Date"] >= start_ts) & (feature_store["Date"] <= end_ts),
                ["Date", "Revenue", "COGS"]
            ]
            merged = truth.merge(preds, on="Date", how="inner")
            merged["fold"] = fold_id
            merged["forecast_step"] = np.arange(1, len(merged) + 1)
            merged["candidate_id"] = c_id
            all_results.append(merged)

    # --- Gating ---
    all_df = pd.concat(all_results, ignore_index=True)
    truth_anchor = feature_store[["Date", "Revenue", "COGS"]].merge(anchor_oof, on="Date", how="inner")
    truth_anchor["forecast_step"] = truth_anchor.groupby("fold").cumcount() + 1

    def compute_metrics(df):
        rev_mae = mean_absolute_error(df["Revenue"], df["Revenue_pred"])
        cogs_mae = mean_absolute_error(df["COGS"], df["COGS_pred"])
        return (rev_mae + cogs_mae) / 2.0, rev_mae

    gate_reports = []
    for c_id in [c["candidate_id"] for c in CANDIDATES]:
        c_df = all_df[all_df["candidate_id"] == c_id]
        cut_val = next(c["cut"] for c in CANDIDATES if c["candidate_id"] == c_id)

        c_combined_oof, _ = compute_metrics(c_df)
        anc_combined_oof, _ = compute_metrics(truth_anchor)

        c_recent = c_df[c_df["fold"] >= 2]
        anc_recent = truth_anchor[truth_anchor["fold"] >= 2]
        c_recent_weighted, _ = compute_metrics(c_recent)
        anc_recent_weighted, _ = compute_metrics(anc_recent)

        c_late_recent = c_recent[c_recent["forecast_step"] > cut_val]
        anc_late_recent = anc_recent[anc_recent["forecast_step"] > cut_val]
        _, c_late_rev = compute_metrics(c_late_recent) if len(c_late_recent) > 0 else (np.nan, np.nan)
        _, anc_late_rev = compute_metrics(anc_late_recent) if len(anc_late_recent) > 0 else (np.nan, np.nan)

        beats_late = c_late_rev < anc_late_rev
        no_fail_recent = c_recent_weighted <= anc_recent_weighted * 1.01
        no_regress_oof = c_combined_oof <= anc_combined_oof * 1.02
        gate_pass = beats_late and no_fail_recent and no_regress_oof

        gate_reports.append({
            "candidate_id": c_id, "gate_pass": gate_pass,
            "c_combined_oof": c_combined_oof, "anchor_combined_oof": anc_combined_oof,
            "c_recent_weighted": c_recent_weighted, "anc_recent_weighted": anc_recent_weighted,
            "c_late_rev": c_late_rev, "anc_late_rev": anc_late_rev,
        })

    gate_df = pd.DataFrame(gate_reports)
    logger.info("\n--- GATING REPORT ---")
    logger.info("\n" + gate_df.to_string(index=False))
    gate_df.to_csv(run_dir / "summary.csv", index=False)

    # --- Export ---
    passed_ids = gate_df.loc[gate_df["gate_pass"], "candidate_id"].tolist()
    export_ids = passed_ids

    try:
        pub_cogs = pd.read_csv("dataset/submission_catboost_md2y_core_recencyexp20.csv")[["Date", "COGS"]]
        pub_cogs["Date"] = pd.to_datetime(pub_cogs["Date"])
    except FileNotFoundError:
        logger.warning("Cannot find anchor COGS submission. Using zeros.")
        pub_cogs = None

    unrolled_full_inf = unrolled_full[unrolled_full["target_date"] <= pd.Timestamp(TRAIN_END)].copy()

    for c_id in export_ids:
        cut_val = next(c["cut"] for c in CANDIDATES if c["candidate_id"] == c_id)
        adj_base = apply_future_promo_policy(base, pd.Timestamp(TRAIN_END), "seasonal_month_day_recent_2y")

        fake_anchor = (
            pub_cogs.rename(columns={"COGS": "COGS_pred"})
            if pub_cogs is not None
            else pd.DataFrame(columns=["Date", "COGS_pred"])
        )

        pub_preds = direct_multi_horizon_evaluate_v2(
            unrolled_full_inf, origin_cols, future_cols, features, cut_val,
            pd.Timestamp(TRAIN_END), "2023-01-01", "2024-07-01",
            feature_store, adj_base, fake_anchor,
        )

        submission = pub_preds.rename(columns={"Revenue_pred": "Revenue", "COGS_pred": "COGS"})[["Date", "Revenue", "COGS"]]
        submission["Date"] = pd.to_datetime(submission["Date"]).dt.strftime("%Y-%m-%d")
        out_path = DATASET_DIR / f"submission_{c_id}.csv"
        submission.to_csv(out_path, index=False)
        logger.info(f"Exported {out_path}")

    logger.info("Done.")


if __name__ == "__main__":
    main()
