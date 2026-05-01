from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from logging_utils import create_run_dir
from run_public_shift_recovery import (
    ANCHOR_PATH,
    FOLD_WEIGHTS,
    PUBLIC_ANCHOR_FILE,
    apply_candidate_transform,
    build_anchor_fold_predictions,
    candidate_manifest,
    read_submission,
)
from run_transaction_decomposition_v2 import NOTES_DIR
from train_recursive_forecast import ensure_inputs, get_candidate_feature_sets


RUN_PREFIX = "multimetric_publiclike_research"
LOG_ROOT = Path("logs")
CURRENT_CLEAN_BEST_FILE = "submission_cleanv19_v17_ratio_monthsmooth_h2_recenteven_a150.csv"
CURRENT_CLEAN_BEST_SCORE = 667139.04897


KNOWN_PUBLIC_SCORES = {
    PUBLIC_ANCHOR_FILE: 896000.0,
    "submission_clean_regime_recovery_yoy125.csv": 1850907.55136,
    "submission_clean_regime_recovery_v3_h2strong_cogsp95.csv": 732768.71351,
    "submission_cleaninput_pubguided_v4_h2max_2024h1max.csv": 731445.92334,
    "submission_cleaninput_rawmdshape_v5_v4main_cogs2024gap0545.csv": 691281.03681,
    "submission_cleaninput_rawmdshape_v6_finalday_down_h1cogs_mid.csv": 694303.78793,
    "submission_cleanroom_rawmd_r080_c065_h2r010_cogsmed.csv": 934406.02470,
    "submission_reasonable_final_sourceclean_pubcal.csv": 695415.79121,
    "submission_reasonable_final_sourceclean_pubcal_soft.csv": 716547.39412,
    "submission_reasonable_v2_shape_doublepass.csv": 698523.05526,
    "submission_strictlegal_tv_selected.csv": 1269623.95048,
    "submission_cleanv2_h1funnel_b045_r0876.csv": 673785.31754,
    "submission_cleanv2_h1funnel_b050_r0876.csv": 676153.29609,
    "submission_cleanv2_h1fine_b046_r0876.csv": 673951.68734,
    CURRENT_CLEAN_BEST_FILE: CURRENT_CLEAN_BEST_SCORE,
    "submission_cleanv3_head_funnel_last_c10_h1only_r0876.csv": 674590.42937,
    "submission_cleanv3_funnel_c110_h1r0876.csv": 673759.96838,
    "submission_cleanv4_opratio_g020.csv": 677137.31895,
    "submission_cleanv6_merch_revshape_g010.csv": 674337.07653,
    "submission_cleanv7_source_h1_s020_r0870.csv": 673720.88479,
    "submission_cleanv7_sourcefine_s0190_r0870.csv": 674415.02000,
    "submission_cleanv9_big_h1_keeprev_cogs_r0820.csv": 678484.18208,
    "submission_cleanv10_h1_shape141617_ratio1719_a075.csv": 668492.34671,
    "submission_cleanv10_h1_ratio1719_keeprev_a100.csv": 674778.63531,
    "submission_cleanv11_trainselected_revrecovery_141617_ratioall_median_a025.csv": 671492.88376,
    "submission_cleanv12_v10ops_h1_ratio_discount_a075.csv": 669972.24260,
    "submission_cleanv12_monthfunnel_h1_ratio_discount_a050.csv": 672391.67763,
    "submission_cleanv13_v12month_all_mddow_a015.csv": 671121.37456,
    "submission_cleanv14_v12_month_all_mddow_both_a300.csv": 672156.87781,
    "submission_cleanv14_v10_all_mddow_both_a300.csv": 667774.94896,
    "submission_cleanv14_v10_all_mddow_both_a350.csv": 668661.10196,
    "submission_cleanv14_v10_all_mddow_r300_c400.csv": 669329.78461,
    "submission_cleanv15_v10_ratiofirst_mddow_r500_q500.csv": 669985.88759,
    "submission_cleanv16_v10_boundary_both_c500_a300.csv": 667551.14004,
    "submission_cleanv16_v10_boundary_both_c750_a300.csv": 668194.03025,
    "submission_cleanv17_v16_h2ratio_recent_weighted_c400.csv": 667263.90843,
    "submission_cleanv17_v16_h2ratio_recent_weighted_c550.csv": 668159.83655,
    "submission_cleanv19_v17_combo_h2smooth_h1c250.csv": 667369.76606,
    "submission_cleanv19_v17_ratio_monthsmooth_h2_recenteven_a150.csv": 667139.04897,
    "submission_cleanv19_v17_ratio_monthsmooth_h2_recenteven_a160.csv": 667141.31420,
    "submission_cleanv19_v17_ratio_monthsmooth_h2_recenteven_a200.csv": 667150.69988,
    "submission_cleanv5_r2_level_to_txnmonth_a400.csv": 708303.49686,
    "submission_qbb60v7_nonh2shape_2023h1level103_away0300.csv": 671930.79214,
    "submission_qbb60v8_nonh2shape_2023h1level105_away0300.csv": 668570.18037,
    "submission_qbb60v9_nonh2shape_2023h1level107_away0300.csv": 665868.08869,
    "submission_qbb60v9_nonh2shape_2023h1level110_away0300.csv": 663346.24664,
    "submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv": 662759.87577,
    "submission_qbb60v18_cogs2023h2_down010.csv": 662607.08245,
    "submission_qbb60v20_lastshot_cogs23h2_down010_cogs24h1_down016.csv": 664159.16954,
    "submission_qbb61v21_shape_preserve_nonh2_g030.csv": 664937.71763,
    "submission_qbb61v21_extrap_clean_to_best_g010.csv": 663007.39829,
    "submission_qbb62_h1_frontload_preserve_total_q1up050.csv": 667597.86978,
    "submission_qbb62_h1_backload_preserve_total_q2up040.csv": 661327.00240,
    "submission_qbb63_h1_mayjun_up060_janfebfund.csv": 666579.35776,
    "submission_qbb64_apr_cogs_from_mayjun_q2preserve_cogs_apr080.csv": 667484.97219,
    "submission_qbb64_apr_from_mayjun_q2preserve_apr080.csv": 667631.42258,
    "submission_qbb65_h2_highratio_cogs_down060_keeprev.csv": 659211.90870,
    "submission_qbb65_h2_highratio_cogs_down100_keeprev.csv": 660345.33116,
    "submission_qbb66_2024h1_recency_revshape_a030_keep_h2cogs.csv": 661604.13161,
    "submission_qbb66_2024h1_frontload_q1up030_keep_h2cogs.csv": 659485.66889,
    "submission_qbb67_h2_aug_extra_cogs_down040_keeprev.csv": 661165.47840,
    "submission_qbb67_h2_highratio_shape_preserve_down040.csv": 659804.99207,
    "submission_qbb68_h1_q1_cogs_down040_keeprev.csv": 657443.28137,
    "submission_qbb68_h1_q1_cogs_down080_keeprev.csv": 656301.72926,
    "submission_qbb69_h1_q1_cogs_down120_keeprev.csv": 655838.51372,
}


def latest_cached_anchor_folds() -> tuple[pd.DataFrame | None, Path | None]:
    required = {"Date", "Revenue", "COGS", "Revenue_pred", "COGS_pred", "fold", "horizon_step"}
    candidates = sorted(
        LOG_ROOT.rglob("anchor_fold_predictions.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        try:
            frame = pd.read_csv(path, parse_dates=["Date", "fold_start"])
        except Exception:
            continue
        if required.issubset(frame.columns):
            return frame, path
    return None, None


def load_or_build_anchor_folds(run_dir: Path) -> tuple[pd.DataFrame, str]:
    cached, cached_path = latest_cached_anchor_folds()
    if cached is not None and cached_path is not None:
        return cached, str(cached_path)

    feature_store, base = ensure_inputs()
    feature_sets = get_candidate_feature_sets(feature_store.head(1))

    class PrintLogger:
        def info(self, message: str, *args: object) -> None:
            print(message % args if args else message)

    frame = build_anchor_fold_predictions(feature_store, base, feature_sets, PrintLogger())
    out_path = run_dir / "anchor_fold_predictions.csv"
    frame.to_csv(out_path, index=False)
    return frame, str(out_path)


def refine_family(filename: str, family: str) -> str:
    name = filename.lower()
    if "qbb" in name or "sample" in name or "publiconly" in name or "top10" in name:
        return "quarantine_blackbox"
    if (
        "cleanv" in name
        or "cleaninput" in name
        or "cleanroom" in name
        or "strictlegal" in name
        or "clean_regime_recovery" in name
    ):
        return "clean_input"
    if "legal_" in name or "reasonable" in name or "sourceclean" in name:
        return "clean_input_public_guided"
    return family


def r2_score_np(actual: pd.Series, pred: pd.Series) -> float:
    actual_np = actual.to_numpy(dtype=float)
    pred_np = pred.to_numpy(dtype=float)
    sst = float(np.sum((actual_np - actual_np.mean()) ** 2))
    if sst <= 1e-12:
        return np.nan
    sse = float(np.sum((actual_np - pred_np) ** 2))
    return 1.0 - sse / sst


def metric_row(frame: pd.DataFrame, record: pd.Series, fold: str) -> dict[str, object]:
    rev_err = frame["Revenue"] - frame["Revenue_candidate"]
    cogs_err = frame["COGS"] - frame["COGS_candidate"]
    rev_abs = rev_err.abs()
    cogs_abs = cogs_err.abs()
    rev_sq = rev_err**2
    cogs_sq = cogs_err**2
    day_abs = 0.5 * (rev_abs + cogs_abs)

    revenue_mae = float(rev_abs.mean())
    cogs_mae = float(cogs_abs.mean())
    revenue_rmse = float(np.sqrt(rev_sq.mean()))
    cogs_rmse = float(np.sqrt(cogs_sq.mean()))
    revenue_r2 = r2_score_np(frame["Revenue"], frame["Revenue_candidate"])
    cogs_r2 = r2_score_np(frame["COGS"], frame["COGS_candidate"])

    pooled_actual = pd.concat([frame["Revenue"], frame["COGS"]], ignore_index=True)
    pooled_pred = pd.concat([frame["Revenue_candidate"], frame["COGS_candidate"]], ignore_index=True)
    pooled_r2 = r2_score_np(pooled_actual, pooled_pred)

    combined_mae = 0.5 * (revenue_mae + cogs_mae)
    combined_rmse = 0.5 * (revenue_rmse + cogs_rmse)
    target_mean = 0.5 * (float(frame["Revenue"].mean()) + float(frame["COGS"].mean()))
    return {
        "candidate_id": record["candidate_id"],
        "filename": record["filename"],
        "family": record["family"],
        "projection_mode": record["primary_projection_mode"],
        "fold": fold,
        "rows": len(frame),
        "revenue_mae": revenue_mae,
        "cogs_mae": cogs_mae,
        "combined_mae": combined_mae,
        "revenue_rmse": revenue_rmse,
        "cogs_rmse": cogs_rmse,
        "combined_rmse": combined_rmse,
        "revenue_r2": revenue_r2,
        "cogs_r2": cogs_r2,
        "macro_r2": 0.5 * (revenue_r2 + cogs_r2),
        "pooled_r2": pooled_r2,
        "normalized_combined_mae": combined_mae / max(target_mean, 1e-9),
        "normalized_combined_rmse": combined_rmse / max(target_mean, 1e-9),
        "rmse_mae_ratio": combined_rmse / max(combined_mae, 1e-9),
        "max_day_combined_abs": float(day_abs.max()),
        "p95_day_combined_abs": float(day_abs.quantile(0.95)),
        "revenue_bias_actual_minus_pred": float(rev_err.mean()),
        "cogs_bias_actual_minus_pred": float(cogs_err.mean()),
    }


def fold_metrics(
    anchor_folds: pd.DataFrame,
    manifest: pd.DataFrame,
    transforms: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    rows = []
    for _, record in manifest.iterrows():
        filename = str(record["filename"])
        transform = transforms.get(filename)
        if transform is None:
            continue
        projected = apply_candidate_transform(
            anchor_folds,
            transform,
            projection_mode=str(record["primary_projection_mode"]),
        )
        for fold, group in projected.groupby("fold", sort=False):
            rows.append(metric_row(group, record, str(fold)))
    return pd.DataFrame(rows)


def weighted_average(group: pd.DataFrame, column: str) -> float:
    weights = group["fold_weight"].to_numpy(dtype=float)
    values = group[column].to_numpy(dtype=float)
    mask = ~np.isnan(values)
    if not mask.any():
        return np.nan
    return float(np.average(values[mask], weights=weights[mask]))


def summarize(metrics: pd.DataFrame, manifest: pd.DataFrame) -> pd.DataFrame:
    weighted = metrics.copy()
    fold_weights = pd.Series(FOLD_WEIGHTS, name="fold_weight").rename_axis("fold").reset_index()
    weighted = weighted.merge(fold_weights, on="fold", how="left")
    weighted["fold_weight"] = weighted["fold_weight"].fillna(0.0)

    rows = []
    for (candidate_id, filename), group in weighted.groupby(["candidate_id", "filename"], sort=False):
        rows.append(
            {
                "candidate_id": candidate_id,
                "filename": filename,
                "weighted_norm_mae": weighted_average(group, "normalized_combined_mae"),
                "weighted_norm_rmse": weighted_average(group, "normalized_combined_rmse"),
                "weighted_combined_mae": weighted_average(group, "combined_mae"),
                "weighted_combined_rmse": weighted_average(group, "combined_rmse"),
                "weighted_macro_r2": weighted_average(group, "macro_r2"),
                "weighted_pooled_r2": weighted_average(group, "pooled_r2"),
                "worst_norm_mae": float(group["normalized_combined_mae"].max()),
                "worst_norm_rmse": float(group["normalized_combined_rmse"].max()),
                "worst_macro_r2": float(group["macro_r2"].min()),
                "worst_pooled_r2": float(group["pooled_r2"].min()),
                "worst_target_r2": float(group[["revenue_r2", "cogs_r2"]].min(axis=1).min()),
                "worst_rmse_mae_ratio": float(group["rmse_mae_ratio"].max()),
                "worst_day_combined_abs": float(group["max_day_combined_abs"].max()),
                "p95_day_combined_abs_mean": float(group["p95_day_combined_abs"].mean()),
                "mean_revenue_bias_actual_minus_pred": float(group["revenue_bias_actual_minus_pred"].mean()),
                "mean_cogs_bias_actual_minus_pred": float(group["cogs_bias_actual_minus_pred"].mean()),
            }
        )

    summary = pd.DataFrame(rows)
    summary = summary.merge(manifest, on=["candidate_id", "filename"], how="left")
    anchor = summary.loc[summary["filename"].eq(PUBLIC_ANCHOR_FILE)].iloc[0]
    clean_best = summary.loc[summary["filename"].eq(CURRENT_CLEAN_BEST_FILE)]
    clean_best_row = clean_best.iloc[0] if not clean_best.empty else anchor

    for col in ["weighted_norm_mae", "weighted_norm_rmse", "weighted_macro_r2", "weighted_pooled_r2"]:
        summary[f"delta_{col}_vs_anchor"] = summary[col] - float(anchor[col])
        summary[f"delta_{col}_vs_clean_best"] = summary[col] - float(clean_best_row[col])
    summary["public_score_known"] = summary["filename"].map(KNOWN_PUBLIC_SCORES).combine_first(summary["public_score"])
    summary["public_delta_vs_clean_best"] = summary["public_score_known"] - CURRENT_CLEAN_BEST_SCORE
    summary["multi_metric_gate"] = summary.apply(lambda row: gate_row(row, anchor, clean_best_row), axis=1)
    return summary.sort_values(
        ["multi_metric_gate", "weighted_norm_mae", "weighted_norm_rmse", "filename"],
        ascending=[True, True, True, True],
        na_position="last",
    )


def gate_row(row: pd.Series, anchor: pd.Series, clean_best: pd.Series) -> str:
    if row["filename"] == CURRENT_CLEAN_BEST_FILE:
        return "00_keep_current_clean_best"
    if row["filename"] == PUBLIC_ANCHOR_FILE:
        return "01_anchor_reference"

    family = str(row.get("family", ""))
    public_score = row.get("public_score_known", np.nan)
    has_public = not pd.isna(public_score)
    if has_public and float(public_score) > CURRENT_CLEAN_BEST_SCORE + 5000.0:
        return "85_reject_public_mae_regression"

    near_public_best = has_public and float(public_score) <= CURRENT_CLEAN_BEST_SCORE + 1000.0
    rmse_safe_vs_clean = row["weighted_norm_rmse"] <= float(clean_best["weighted_norm_rmse"]) + 0.0005
    r2_safe_vs_clean = row["worst_pooled_r2"] >= float(clean_best["worst_pooled_r2"]) - 0.005
    if near_public_best and rmse_safe_vs_clean and r2_safe_vs_clean:
        if family == "quarantine_blackbox":
            return "35_quarantine_public_good_rmse_r2_safe"
        return "05_public_near_best_rmse_r2_safe"

    good_mae = row["weighted_norm_mae"] <= float(anchor["weighted_norm_mae"]) + 0.001
    safe_rmse = row["weighted_norm_rmse"] <= float(anchor["weighted_norm_rmse"]) + 0.0015
    safe_r2_relative = row["worst_pooled_r2"] >= float(anchor["worst_pooled_r2"]) - 0.02
    strict_r2_ok = row["worst_pooled_r2"] >= 0.0 and row["worst_target_r2"] >= -0.10

    if family == "quarantine_blackbox":
        if good_mae and safe_rmse and safe_r2_relative:
            return "40_quarantine_metric_safe_not_clean"
        return "80_quarantine_metric_risk"
    if good_mae and safe_rmse and strict_r2_ok:
        return "10_local_only_pass_strict_multimetric"
    if good_mae and safe_rmse and safe_r2_relative:
        return "20_local_only_pass_relative_multimetric"
    if good_mae and not safe_rmse:
        return "70_reject_rmse_tail_risk"
    if good_mae and not safe_r2_relative:
        return "71_reject_r2_fold_risk"
    return "90_reject_mae_gate"


def write_report(run_dir: Path, summary: pd.DataFrame, metrics: pd.DataFrame, cache_source: str) -> None:
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    known = summary.loc[summary["public_score_known"].notna()].sort_values("public_score_known")
    clean = summary.loc[summary["family"].isin(["clean_input", "clean_input_public_guided"])].copy()
    pass_rows = summary.loc[summary["multi_metric_gate"].str.startswith(("05_", "10_", "20_", "35_", "40_"))].head(30)
    risk = summary.loc[
        (summary["weighted_norm_mae"] <= summary.loc[summary["filename"].eq(PUBLIC_ANCHOR_FILE), "weighted_norm_mae"].iloc[0] + 0.001)
        & (summary["multi_metric_gate"].str.startswith(("70_", "71_")))
    ].head(30)

    display_cols = [
        "filename",
        "family",
        "public_score_known",
        "multi_metric_gate",
        "weighted_norm_mae",
        "weighted_norm_rmse",
        "worst_pooled_r2",
        "worst_target_r2",
        "worst_rmse_mae_ratio",
    ]
    report = f"""# Multi-Metric Public-Like Research

Run directory: `{run_dir}`

Anchor fold cache: `{cache_source}`

## Decision Rule

This run adds RMSE and R2 risk checks to the old public-like MAE gate. It is a research gate, not a replacement for the true hidden test labels.

- Public-near-best gate: known public MAE within 1000 of the clean best, plus RMSE/R2 no worse than the clean best on public-like folds.
- Public-regression block: known public MAE more than 5000 worse than the clean best is rejected even if local metrics look good.
- Local-only good MAE: weighted normalized MAE is no worse than the fixed anchor by more than 0.001.
- Local-only safe RMSE: weighted normalized RMSE is no worse than the fixed anchor by more than 0.0015.
- Local-only strict R2: worst pooled fold R2 >= 0 and worst target fold R2 >= -0.10.

## Known Public Rows

{known[display_cols].head(35).to_markdown(index=False)}

## Clean-Input Rows

{clean[display_cols].head(35).to_markdown(index=False)}

## Rows Passing Multi-Metric Gate

{pass_rows[display_cols].to_markdown(index=False) if not pass_rows.empty else "No rows passed."}

## MAE-Good But RMSE/R2-Risky Rows

{risk[display_cols].to_markdown(index=False) if not risk.empty else "No MAE-good rows failed only RMSE/R2 risk."}

## Interpretation

- If a candidate improves public MAE but lands in `70_reject_rmse_tail_risk`, it is likely overfitting level or sparse days and can hurt final RMSE/R2.
- If it lands in `71_reject_r2_fold_risk`, the fold-level shape is unstable even when MAE looks acceptable.
- The next safe direction should improve daily shape smoothness and target ratio stability, not only period totals.
"""
    (run_dir / "publiclike_multimetric_report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "multimetric_publiclike_research_2026-04-24.md").write_text(report, encoding="utf-8")

    risk.to_csv(run_dir / "rmse_r2_risk_table.csv", index=False)
    pass_rows.to_csv(run_dir / "multimetric_pass_table.csv", index=False)
    metrics.to_csv(run_dir / "fold_metrics.csv", index=False)
    summary.to_csv(run_dir / "summary.csv", index=False)


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    anchor_public = read_submission(ANCHOR_PATH)
    manifest, transforms = candidate_manifest(anchor_public)
    manifest = manifest.copy()
    manifest["family"] = [refine_family(str(row.filename), str(row.family)) for row in manifest.itertuples()]
    manifest["public_score"] = manifest["filename"].map(KNOWN_PUBLIC_SCORES).combine_first(manifest["public_score"])
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)

    anchor_folds, cache_source = load_or_build_anchor_folds(run_dir)
    metrics = fold_metrics(anchor_folds, manifest, transforms)
    summary = summarize(metrics, manifest)
    write_report(run_dir, summary, metrics, cache_source)

    display_cols = [
        "filename",
        "family",
        "public_score_known",
        "multi_metric_gate",
        "weighted_norm_mae",
        "weighted_norm_rmse",
        "worst_pooled_r2",
        "worst_target_r2",
    ]
    print(summary[display_cols].head(30).to_string(index=False))
    print(f"\nSaved outputs to {run_dir}")


if __name__ == "__main__":
    main()
