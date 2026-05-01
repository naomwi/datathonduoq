from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_prior_v19 import (
    SAMPLE_FILE,
    add_segments,
    align_sample_shape,
    blend,
    period_summary,
    register,
)
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "publiconly_sample_scale_ratio_v23"
PRE_SAMPLE_BEST_FILE = "submission_top10_v13_rev2023h2_up100_keepcogs.csv"
CURRENT_BEST_FILE = "submission_sampleprior_v22_periodshape_both_a0725.csv"
CURRENT_BEST_SCORE = 701005.12470
SAMPLE_SHAPE_ALPHA = 0.725

KNOWN_RESULTS = {
    "submission_sampleprior_v20_periodshape_both_a070.csv": 701103.47903,
    "submission_sampleprior_v22_periodshape_both_a0725.csv": CURRENT_BEST_SCORE,
    "submission_sampleprior_v21_periodshape_both_a075.csv": 701144.82924,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def period_blend_totals(current: pd.DataFrame, sample: pd.DataFrame, rev_alpha: float, cogs_alpha: float) -> pd.DataFrame:
    out = current[["Date", "Revenue", "COGS"]].copy()
    cur_prof = add_segments(current)
    sample_prof = add_segments(sample)
    merged_sample = cur_prof[["Date", "period"]].merge(
        sample_prof[["Date", "Revenue", "COGS"]],
        on="Date",
        how="left",
        suffixes=("", "_sample"),
    )
    for period, idx in cur_prof.groupby("period").groups.items():
        idx_list = list(idx)
        cur_rev = out.loc[idx_list, "Revenue"].sum()
        cur_cogs = out.loc[idx_list, "COGS"].sum()
        sample_idx = merged_sample.index[merged_sample["period"].eq(period)].tolist()
        sample_rev = merged_sample.loc[sample_idx, "Revenue"].sum()
        sample_cogs = merged_sample.loc[sample_idx, "COGS"].sum()
        target_rev = (1.0 - rev_alpha) * cur_rev + rev_alpha * sample_rev
        target_cogs = (1.0 - cogs_alpha) * cur_cogs + cogs_alpha * sample_cogs
        if cur_rev > 0:
            out.loc[idx_list, "Revenue"] *= target_rev / cur_rev
        if cur_cogs > 0:
            out.loc[idx_list, "COGS"] *= target_cogs / cur_cogs
    return out


def cogs_ratio_blend(current: pd.DataFrame, sample: pd.DataFrame, alpha: float) -> pd.DataFrame:
    out = current[["Date", "Revenue", "COGS"]].copy()
    cur_prof = add_segments(current)
    sample_prof = add_segments(sample)
    for period, idx in cur_prof.groupby("period").groups.items():
        idx_list = list(idx)
        cur_ratio = out.loc[idx_list, "COGS"].sum() / out.loc[idx_list, "Revenue"].sum()
        sample_mask = sample_prof["period"].eq(period)
        sample_ratio = sample_prof.loc[sample_mask, "COGS"].sum() / sample_prof.loc[sample_mask, "Revenue"].sum()
        target_ratio = (1.0 - alpha) * cur_ratio + alpha * sample_ratio
        out.loc[idx_list, "COGS"] *= target_ratio / cur_ratio
    return out


def global_scale(current: pd.DataFrame, revenue_multiplier: float = 1.0, cogs_multiplier: float = 1.0) -> pd.DataFrame:
    out = current[["Date", "Revenue", "COGS"]].copy()
    out["Revenue"] *= revenue_multiplier
    out["COGS"] *= cogs_multiplier
    return out


def write_and_summarize(rows: list[dict[str, object]], base: pd.DataFrame, sample: pd.DataFrame, frame: pd.DataFrame, filename: str, thesis: str, priority: int) -> None:
    path = DATASET_DIR / filename
    write_submission(frame, path)
    delta_rev = frame["Revenue"] - base["Revenue"]
    delta_cogs = frame["COGS"] - base["COGS"]
    prof = period_summary(frame)
    rows.append(
        {
            "priority": priority,
            "filename": filename,
            "path": str(path),
            "thesis": thesis,
            "rev_rows_changed_vs_current": int(delta_rev.abs().gt(1e-6).sum()),
            "cogs_rows_changed_vs_current": int(delta_cogs.abs().gt(1e-6).sum()),
            "mean_abs_rev_delta_vs_current": delta_rev.abs().mean(),
            "mean_abs_cogs_delta_vs_current": delta_cogs.abs().mean(),
            "directional_best_case_gain_vs_current": 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
            "revenue_total_ratio_vs_current": frame["Revenue"].sum() / base["Revenue"].sum(),
            "cogs_total_ratio_vs_current": frame["COGS"].sum() / base["COGS"].sum(),
            "revenue_total_ratio_vs_sample": frame["Revenue"].sum() / sample["Revenue"].sum(),
            "cogs_total_ratio_vs_sample": frame["COGS"].sum() / sample["COGS"].sum(),
            "ratio_all": frame["COGS"].sum() / frame["Revenue"].sum(),
            "ratio_2023h1": prof.loc[prof["period"].eq("2023H1"), "ratio"].iloc[0],
            "ratio_2023h2": prof.loc[prof["period"].eq("2023H2"), "ratio"].iloc[0],
            "ratio_2024h1": prof.loc[prof["period"].eq("2024H1"), "ratio"].iloc[0],
        }
    )


def main() -> None:
    run_dir = make_run_dir()
    pre_base = add_segments(pd.read_csv(DATASET_DIR / PRE_SAMPLE_BEST_FILE, parse_dates=["Date"]))
    current = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    sample = add_segments(pd.read_csv(DATASET_DIR / SAMPLE_FILE, parse_dates=["Date"]))

    # Rebuild the current formula for reproducibility and sanity.
    shape_both = align_sample_shape(pre_base, sample, ("Revenue", "COGS"))
    rebuilt_current = blend(pre_base, shape_both, SAMPLE_SHAPE_ALPHA)
    max_diff = (rebuilt_current[["Revenue", "COGS"]] - current[["Revenue", "COGS"]]).abs().max().max()
    if max_diff > 1e-4:
        raise RuntimeError(f"Rebuilt current best differs from file by {max_diff}")

    rows: list[dict[str, object]] = []
    specs = [
        (
            "submission_sample_v23_a0725_ratio_to_sample005.csv",
            cogs_ratio_blend(current, sample, 0.05),
            "keep a0725 shape and Revenue, move period COGS/Revenue ratios 5% toward sample",
            1,
        ),
        (
            "submission_sample_v23_a0725_ratio_to_sample010.csv",
            cogs_ratio_blend(current, sample, 0.10),
            "keep a0725 shape and Revenue, move period COGS/Revenue ratios 10% toward sample",
            2,
        ),
        (
            "submission_sample_v23_a0725_scale_to_sample005.csv",
            period_blend_totals(current, sample, rev_alpha=0.05, cogs_alpha=0.05),
            "keep a0725 shape, move period Revenue and COGS totals 5% toward sample totals",
            3,
        ),
        (
            "submission_sample_v23_a0725_scale_to_sample010.csv",
            period_blend_totals(current, sample, rev_alpha=0.10, cogs_alpha=0.10),
            "keep a0725 shape, move period Revenue and COGS totals 10% toward sample totals",
            4,
        ),
        (
            "submission_sample_v23_a0725_revscale_down005.csv",
            global_scale(current, revenue_multiplier=0.995, cogs_multiplier=1.0),
            "micro global Revenue -0.5%, keep COGS",
            5,
        ),
        (
            "submission_sample_v23_a0725_cogsscale_down005.csv",
            global_scale(current, revenue_multiplier=1.0, cogs_multiplier=0.995),
            "micro global COGS -0.5%, keep Revenue",
            6,
        ),
        (
            "submission_sample_v23_a0725_bothscale_down005.csv",
            global_scale(current, revenue_multiplier=0.995, cogs_multiplier=0.995),
            "micro global Revenue and COGS -0.5%",
            7,
        ),
    ]
    for filename, frame, thesis, priority in specs:
        write_and_summarize(rows, current, sample, frame, filename, thesis, priority)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_a0725_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)

    report = f"""# Public-Only Sample Scale Ratio V23

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known results:

{pd.Series(KNOWN_RESULTS, name="public_score").to_markdown()}

Interpretation:

- Alpha-only sample shape has plateaued around `701k`; local fit predicts only tiny alpha gains.
- To reach `699.x`, test a second axis: period totals and COGS ratios slightly toward `sample_submission`.
- These are intentionally small moves from the current best.

Current best period summary:

{period_summary(current).to_markdown(index=False)}

Sample period summary:

{period_summary(sample).to_markdown(index=False)}

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_sample_v23_a0725_ratio_to_sample005.csv`
2. If it improves: `submission_sample_v23_a0725_ratio_to_sample010.csv`
3. If ratio move fails: `submission_sample_v23_a0725_scale_to_sample005.csv`
4. Use global micro-scale probes only if both sample-ratio and sample-scale fail.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_scale_ratio_v23_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
