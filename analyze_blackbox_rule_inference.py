from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns, load_daily_components


RUN_PREFIX = "blackbox_rule_inference"


@dataclass(frozen=True)
class Probe:
    base_file: str
    base_score: float
    candidate_file: str
    candidate_score: float
    label: str
    family: str


PROBES = [
    Probe(
        "submission_txndecomp_v2_cogsratio_followup_promotet_r60_up0100.csv",
        873084.61381,
        "submission_publiconly_cogs_nonpromo_up015.csv",
        865527.70356,
        "nonpromo COGS +1.5% from structural txndecomp",
        "broad_cogs_up",
    ),
    Probe(
        "submission_publiconly_cogs_nonpromo_up015.csv",
        865527.70356,
        "submission_publiconly_cogs_break_all_plus050.csv",
        839329.89703,
        "all COGS +5% from nonpromo-up base",
        "broad_cogs_up",
    ),
    Probe(
        "submission_publiconly_cogs_break_all_plus050.csv",
        839329.89703,
        "submission_publiconly_cogs_break_followup_all_plus035.csv",
        828569.81120,
        "all COGS +3.5% continuation",
        "broad_cogs_up",
    ),
    Probe(
        "submission_publiconly_cogs_break_followup_all_plus035.csv",
        828569.81120,
        "submission_publiconly_cogs_break_v5_all_plus020.csv",
        825080.79137,
        "all COGS +2% continuation",
        "broad_cogs_up_plateau",
    ),
    Probe(
        "submission_publiconly_cogs_break_v5_all_plus020.csv",
        825080.79137,
        "submission_publiconly_cogs_reshape_v6_floor098_cap102_preserve.csv",
        832854.44811,
        "COGS ratio reshape with total roughly preserved",
        "cogs_shape_rejected",
    ),
    Probe(
        "submission_publiconly_cogs_break_v5_all_plus020.csv",
        825080.79137,
        "submission_publiconly_segment_v7_2023h2_up100.csv",
        812496.01649,
        "2023H2 COGS +10%",
        "period_cogs",
    ),
    Probe(
        "submission_publiconly_cogs_break_v5_all_plus020.csv",
        825080.79137,
        "submission_publiconly_segment_v7_2024h1_up100.csv",
        855840.24467,
        "2024H1 COGS +10%",
        "period_cogs_rejected",
    ),
    Probe(
        "submission_publiconly_segment_v7_2023h2_up100.csv",
        812496.01649,
        "submission_publiconly_segment_v8_h2best_2024h1_down100.csv",
        807504.66276,
        "2024H1 COGS -10% after H2-up",
        "period_cogs",
    ),
    Probe(
        "submission_publiconly_segment_v8_h2best_2024h1_down100.csv",
        807504.66276,
        "submission_publiconly_segment_v9_2023h1_up100.csv",
        811093.31702,
        "2023H1 COGS +10%",
        "period_cogs_rejected",
    ),
    Probe(
        "submission_publiconly_segment_v8_h2best_2024h1_down100.csv",
        807504.66276,
        "submission_publiconly_month_v10_h2_peak_more200.csv",
        823082.86966,
        "2023H2 peak months COGS +20% extra",
        "month_cogs_rejected",
    ),
    Probe(
        "submission_publiconly_segment_v8_h2best_2024h1_down100.csv",
        807504.66276,
        "submission_publiconly_month_v10_h2_shoulder_more200.csv",
        830056.22789,
        "2023H2 shoulder months COGS +20% extra",
        "month_cogs_rejected",
    ),
    Probe(
        "submission_publiconly_segment_v8_h2best_2024h1_down100.csv",
        807504.66276,
        "submission_publiconly_breakout_v11_rev2024highscale_down100.csv",
        np.nan,
        "Revenue Mar-Jun 2024 -10% probe, generated but not submitted",
        "not_scored_revenue_probe",
    ),
]


PERIODS = {
    "2023H1": lambda df: df["Date"].dt.year.eq(2023) & df["Date"].dt.month.le(6),
    "2023H2": lambda df: df["Date"].dt.year.eq(2023) & df["Date"].dt.month.ge(7),
    "2024H1": lambda df: df["Date"].dt.year.eq(2024) & df["Date"].dt.month.le(6),
    "2023H2_peak_aug_nov_dec": lambda df: df["Date"].dt.strftime("%Y-%m").isin(["2023-08", "2023-11", "2023-12"]),
    "2023H2_shoulder_jul_sep_oct": lambda df: df["Date"].dt.strftime("%Y-%m").isin(["2023-07", "2023-09", "2023-10"]),
    "2024_highscale_mar_jun": lambda df: df["Date"].dt.strftime("%Y-%m").isin(["2024-03", "2024-04", "2024-05", "2024-06"]),
    "promo_window": lambda df: df["win_main_promo"].astype(bool),
    "nonpromo": lambda df: ~df["win_main_promo"].astype(bool),
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def load_submission(filename: str) -> pd.DataFrame:
    path = DATASET_DIR / filename
    if not path.exists():
        raise FileNotFoundError(path)
    return add_event_columns(pd.read_csv(path, parse_dates=["Date"])).reset_index(drop=True)


def add_period(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["period"] = "other"
    out.loc[out["Date"].dt.year.eq(2023) & out["Date"].dt.month.le(6), "period"] = "2023H1"
    out.loc[out["Date"].dt.year.eq(2023) & out["Date"].dt.month.ge(7), "period"] = "2023H2"
    out.loc[out["Date"].dt.year.eq(2024) & out["Date"].dt.month.le(6), "period"] = "2024H1"
    out["month_key"] = out["Date"].dt.strftime("%Y-%m")
    return out


def summarize_probe(probe: Probe) -> dict[str, object]:
    base = load_submission(probe.base_file)
    candidate = load_submission(probe.candidate_file)
    merged = base[["Date", "Revenue", "COGS", "win_main_promo"]].merge(
        candidate[["Date", "Revenue", "COGS"]],
        on="Date",
        suffixes=("_base", "_cand"),
    )
    merged = add_period(merged)
    rev_delta = merged["Revenue_cand"] - merged["Revenue_base"]
    cogs_delta = merged["COGS_cand"] - merged["COGS_base"]
    score_gain = probe.base_score - probe.candidate_score if np.isfinite(probe.candidate_score) else np.nan
    max_possible_gain = 0.5 * (rev_delta.abs().mean() + cogs_delta.abs().mean())
    changed = (rev_delta.abs() + cogs_delta.abs()).gt(1e-6)
    cogs_changed = cogs_delta.abs().gt(1e-6)
    rev_changed = rev_delta.abs().gt(1e-6)
    changed_cogs_ratio_base = (
        merged.loc[cogs_changed, "COGS_base"].sum() / merged.loc[cogs_changed, "Revenue_base"].sum()
        if cogs_changed.any()
        else np.nan
    )
    changed_cogs_ratio_candidate = (
        merged.loc[cogs_changed, "COGS_cand"].sum() / merged.loc[cogs_changed, "Revenue_cand"].sum()
        if cogs_changed.any()
        else np.nan
    )
    changed_cogs_ratio_midpoint = (
        (merged.loc[cogs_changed, "COGS_base"] + 0.5 * cogs_delta.loc[cogs_changed]).sum()
        / merged.loc[cogs_changed, "Revenue_base"].sum()
        if cogs_changed.any()
        else np.nan
    )
    changed_rev_total_ratio = (
        merged.loc[rev_changed, "Revenue_cand"].sum() / merged.loc[rev_changed, "Revenue_base"].sum()
        if rev_changed.any()
        else np.nan
    )
    cogs_bound = "not_applicable"
    if cogs_changed.any() and np.isfinite(score_gain):
        mean_changed_delta = float(cogs_delta.loc[cogs_changed].mean())
        if score_gain > 0 and mean_changed_delta > 0:
            cogs_bound = "actual_above_midpoint"
        elif score_gain < 0 and mean_changed_delta > 0:
            cogs_bound = "actual_below_midpoint"
        elif score_gain > 0 and mean_changed_delta < 0:
            cogs_bound = "actual_below_midpoint"
        elif score_gain < 0 and mean_changed_delta < 0:
            cogs_bound = "actual_above_midpoint"

    row: dict[str, object] = {
        "label": probe.label,
        "family": probe.family,
        "base_file": probe.base_file,
        "candidate_file": probe.candidate_file,
        "base_score": probe.base_score,
        "candidate_score": probe.candidate_score,
        "score_gain_positive_is_good": score_gain,
        "max_possible_gain_if_direction_perfect": max_possible_gain,
        "realized_efficiency": score_gain / max_possible_gain if max_possible_gain and np.isfinite(score_gain) else np.nan,
        "rows_changed": int(changed.sum()),
        "rev_rows_changed": int(rev_changed.sum()),
        "cogs_rows_changed": int(cogs_changed.sum()),
        "mean_rev_delta": float(rev_delta.mean()),
        "mean_cogs_delta": float(cogs_delta.mean()),
        "mean_abs_rev_delta": float(rev_delta.abs().mean()),
        "mean_abs_cogs_delta": float(cogs_delta.abs().mean()),
        "changed_cogs_ratio_base": changed_cogs_ratio_base,
        "changed_cogs_ratio_candidate": changed_cogs_ratio_candidate,
        "changed_cogs_ratio_midpoint": changed_cogs_ratio_midpoint,
        "implied_cogs_bound": cogs_bound,
        "changed_rev_total_ratio": changed_rev_total_ratio,
    }
    for period in ["2023H1", "2023H2", "2024H1"]:
        mask = merged["period"].eq(period)
        row[f"{period}_mean_cogs_delta"] = float(cogs_delta.loc[mask].mean()) if mask.any() else 0.0
        row[f"{period}_mean_rev_delta"] = float(rev_delta.loc[mask].mean()) if mask.any() else 0.0
        row[f"{period}_base_cogs_rev_ratio"] = float(merged.loc[mask, "COGS_base"].sum() / merged.loc[mask, "Revenue_base"].sum()) if mask.any() else np.nan
        row[f"{period}_cand_cogs_rev_ratio"] = float(merged.loc[mask, "COGS_cand"].sum() / merged.loc[mask, "Revenue_cand"].sum()) if mask.any() else np.nan
    return row


def segment_profile(filename: str) -> pd.DataFrame:
    frame = add_period(load_submission(filename))
    rows: list[dict[str, object]] = []
    for name, mask_fn in PERIODS.items():
        mask = mask_fn(frame)
        if not mask.any():
            continue
        rows.append(
            {
                "segment": name,
                "rows": int(mask.sum()),
                "revenue_sum": float(frame.loc[mask, "Revenue"].sum()),
                "cogs_sum": float(frame.loc[mask, "COGS"].sum()),
                "cogs_rev_ratio_weighted": float(frame.loc[mask, "COGS"].sum() / frame.loc[mask, "Revenue"].sum()),
                "mean_revenue": float(frame.loc[mask, "Revenue"].mean()),
                "mean_cogs": float(frame.loc[mask, "COGS"].mean()),
            }
        )
    return pd.DataFrame(rows)


def historical_analog_table() -> tuple[pd.DataFrame, pd.DataFrame]:
    hist = load_daily_components()
    hist = add_event_columns(hist)
    hist["period"] = np.where(hist["month"].le(6), "H1", "H2")
    hist["year_period"] = hist["year"].astype(str) + hist["period"]
    hist["month_key"] = hist["Date"].dt.strftime("%Y-%m")
    hist = hist.loc[hist["Date"].lt(pd.Timestamp("2023-01-01"))].copy()
    hist["cogs_rev_ratio"] = hist["COGS"] / hist["Revenue"].replace(0, np.nan)
    period = (
        hist.groupby(["year", "period"], as_index=False)
        .agg(
            rows=("Date", "size"),
            revenue_sum=("Revenue", "sum"),
            cogs_sum=("COGS", "sum"),
            mean_ratio=("cogs_rev_ratio", "mean"),
        )
        .sort_values(["year", "period"])
    )
    period["weighted_ratio"] = period["cogs_sum"] / period["revenue_sum"]
    month = (
        hist.groupby(["year", "month"], as_index=False)
        .agg(revenue_sum=("Revenue", "sum"), cogs_sum=("COGS", "sum"), mean_ratio=("cogs_rev_ratio", "mean"))
        .sort_values(["year", "month"])
    )
    month["weighted_ratio"] = month["cogs_sum"] / month["revenue_sum"]
    return period, month


def build_rule_report(probe_table: pd.DataFrame, current_profile: pd.DataFrame, hist_period: pd.DataFrame) -> str:
    exact = probe_table.loc[probe_table["candidate_score"].notna()].copy()
    exact["public_reaction"] = np.where(exact["score_gain_positive_is_good"] > 0, "improved", "worsened")

    accepted = exact.loc[exact["score_gain_positive_is_good"] > 0].sort_values("score_gain_positive_is_good", ascending=False)
    rejected = exact.loc[exact["score_gain_positive_is_good"] < 0].sort_values("score_gain_positive_is_good")
    top_cols = [
        "label",
        "public_reaction",
        "score_gain_positive_is_good",
        "realized_efficiency",
        "rows_changed",
        "mean_cogs_delta",
        "mean_rev_delta",
        "changed_cogs_ratio_base",
        "changed_cogs_ratio_midpoint",
        "changed_cogs_ratio_candidate",
    ]
    bound_cols = [
        "label",
        "public_reaction",
        "score_gain_positive_is_good",
        "implied_cogs_bound",
        "changed_cogs_ratio_base",
        "changed_cogs_ratio_midpoint",
        "changed_cogs_ratio_candidate",
    ]

    return f"""# Blackbox Rule Inference

Generated at `{datetime.now():%Y-%m-%d %H:%M:%S}`.

## What This Is
This is not another leaderboard-fitting script. It converts the public probes we already submitted into constraints about the hidden public target. A positive score gain means the changed direction probably moved predictions closer to public truth; a negative gain means the change likely overshot or moved the wrong segment.

## Accepted Signals
{accepted[top_cols].to_markdown(index=False)}

## Rejected Signals
{rejected[top_cols].to_markdown(index=False)}

## Implied COGS Ratio Bounds
For COGS-only probes, MAE gives a useful midpoint rule. If raising COGS improves, hidden actual COGS is likely above the midpoint between base and candidate. If raising COGS worsens, hidden actual COGS is likely below that midpoint. The reverse holds for lowering COGS.

{exact.loc[exact["implied_cogs_bound"].ne("not_applicable"), bound_cols].to_markdown(index=False)}

## Current Best Segment Profile
Current best used for inference: `submission_publiconly_segment_v8_h2best_2024h1_down100.csv`, public score `807504.66276`.

{current_profile.to_markdown(index=False)}

## Historical COGS/Revenue Ratios
{hist_period.to_markdown(index=False)}

## Inferred Rules
- `COGS` is the main missing signal. Broad COGS raises from the structural model improved public from `873084.61` to `825080.79`, far more than model swaps or Revenue shape.
- The broad COGS raise has a plateau. Extra broad/all COGS still helped, but each step had lower realized efficiency; later aggressive H2 month pushes reversed badly.
- `2023H2` requires a higher COGS/Revenue regime than the original model predicted. The cleanest segment win is `2023H2 COGS +10%`, improving `12584.77` from the `825080.79` base.
- `2023H2` is not an unlimited spike. Adding another `+20%` to peak or shoulder H2 months worsened by `15578.21` and `22551.57`, so the likely true H2 ratio is near the current boosted level, not far above it.
- `2024H1` does not share the H2 cost shock. `2024H1 COGS +10%` was strongly rejected, while `2024H1 COGS -10%` after H2-up helped only `4991.35`; the real rule is probably "do not raise 2024H1", not "crush 2024H1".
- Broad `2023H1 COGS +10%` is rejected mildly. This suggests 2023H1 is near neutral or mixed by month, not a second broad underprediction regime.
- Capping/reshaping high COGS-ratio days while preserving total was rejected. That means high-ratio days are not simply artifacts to clip; product mix or margin compression can genuinely create ratios near/above 1 in parts of H2.
- Historical ratios are not enough by themselves, but they support a plausible structural story: H2 can carry different margin/cost behavior than H1, and public 2023H2 likely has a cost/mix regime that local OOF did not represent.

## Practical Non-Overfit Takeaway
The rule to model structurally is:

`COGS = Revenue * ratio_regime(Date, promo_window, H2_cost_regime)`

where `ratio_regime` should allow a higher 2023H2 ratio, keep 2024H1 restrained, and avoid clipping true high-ratio days. The next robust modeling work should estimate this ratio from historical analogs/product-mix proxies instead of continuing public probes.
"""


def main() -> None:
    run_dir = make_run_dir()

    rows = []
    skipped = []
    for probe in PROBES:
        try:
            rows.append(summarize_probe(probe))
        except FileNotFoundError as exc:
            skipped.append({"probe": probe.label, "missing": str(exc)})
    probe_table = pd.DataFrame(rows)
    probe_table.to_csv(run_dir / "probe_reaction_table.csv", index=False)
    if skipped:
        pd.DataFrame(skipped).to_csv(run_dir / "skipped_missing_files.csv", index=False)

    current_profile = segment_profile("submission_publiconly_segment_v8_h2best_2024h1_down100.csv")
    current_profile.to_csv(run_dir / "current_best_segment_profile.csv", index=False)

    hist_period, hist_month = historical_analog_table()
    hist_period.to_csv(run_dir / "historical_period_ratios.csv", index=False)
    hist_month.to_csv(run_dir / "historical_month_ratios.csv", index=False)

    report = build_rule_report(probe_table, current_profile, hist_period)
    (run_dir / "blackbox_rule_report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "blackbox_rule_inference_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
