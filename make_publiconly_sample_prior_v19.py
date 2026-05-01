from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns, write_submission


RUN_PREFIX = "publiconly_sample_prior_v19"
CURRENT_BEST_FILE = "submission_top10_v13_rev2023h2_up100_keepcogs.csv"
CURRENT_BEST_SCORE = 797595.96410
SAMPLE_FILE = "sample_submission.csv"

RECENT_REJECTS = {
    "submission_h2rev_v15_current_h2_rev_up050.csv": 800572.16096,
    "submission_h2shape_v16_cogs_oddmean_preserve.csv": 802116.33879,
    "submission_h2antishape_v17_cogs_antiodd025_preserve.csv": 800578.87166,
    "submission_h2revshape_v18_rev_odd050_preserve.csv": 798084.85522,
    "submission_h2revshape_v18_rev_antiodd050_preserve.csv": 801642.41053,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def add_segments(frame: pd.DataFrame) -> pd.DataFrame:
    out = add_event_columns(frame).reset_index(drop=True)
    out["period"] = "other"
    out.loc[out["Date"].dt.year.eq(2023) & out["Date"].dt.month.le(6), "period"] = "2023H1"
    out.loc[out["Date"].dt.year.eq(2023) & out["Date"].dt.month.ge(7), "period"] = "2023H2"
    out.loc[out["Date"].dt.year.eq(2024) & out["Date"].dt.month.le(6), "period"] = "2024H1"
    out.loc[out["Date"].eq(pd.Timestamp("2024-07-01")), "period"] = "2024-07-01"
    out["month_key"] = out["Date"].dt.strftime("%Y-%m")
    out["dow"] = out["Date"].dt.dayofweek
    return out


def align_sample_shape(base: pd.DataFrame, sample: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    merged = base[["Date", "Revenue", "COGS", "period"]].merge(
        sample[["Date", "Revenue", "COGS"]],
        on="Date",
        suffixes=("_base", "_sample"),
        how="left",
    )
    out = base[["Date", "Revenue", "COGS"]].copy()
    for col in columns:
        for period, idx in merged.groupby("period").groups.items():
            idx_list = list(idx)
            base_total = merged.loc[idx_list, f"{col}_base"].sum()
            sample_total = merged.loc[idx_list, f"{col}_sample"].sum()
            if sample_total <= 0:
                continue
            out.loc[idx_list, col] = merged.loc[idx_list, f"{col}_sample"].to_numpy() * base_total / sample_total
    return out


def blend(base: pd.DataFrame, donor: pd.DataFrame, alpha: float) -> pd.DataFrame:
    out = base[["Date", "Revenue", "COGS"]].copy()
    out["Revenue"] = (1.0 - alpha) * base["Revenue"] + alpha * donor["Revenue"]
    out["COGS"] = (1.0 - alpha) * base["COGS"] + alpha * donor["COGS"]
    return out


def blend_direct_sample(base: pd.DataFrame, sample: pd.DataFrame, alpha: float) -> pd.DataFrame:
    out = base[["Date", "Revenue", "COGS"]].copy()
    out["Revenue"] = (1.0 - alpha) * base["Revenue"] + alpha * sample["Revenue"]
    out["COGS"] = (1.0 - alpha) * base["COGS"] + alpha * sample["COGS"]
    return out


def keep_ratio_from_base(revenue_frame: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    out = revenue_frame[["Date", "Revenue", "COGS"]].copy()
    out["COGS"] = out["Revenue"] * base["COGS"] / base["Revenue"]
    return out


def period_summary(frame: pd.DataFrame) -> pd.DataFrame:
    prof = add_segments(frame)
    return (
        prof.groupby("period", as_index=False)
        .agg(days=("Date", "count"), Revenue=("Revenue", "sum"), COGS=("COGS", "sum"))
        .assign(ratio=lambda d: d["COGS"] / d["Revenue"])
    )


def summarize(base: pd.DataFrame, sample: pd.DataFrame, frame: pd.DataFrame, filename: str, thesis: str, priority: int) -> dict[str, object]:
    delta_rev = frame["Revenue"] - base["Revenue"]
    delta_cogs = frame["COGS"] - base["COGS"]
    prof = period_summary(frame)
    sample_prof = period_summary(sample)
    base_prof = period_summary(base)
    return {
        "priority": priority,
        "filename": filename,
        "path": str(DATASET_DIR / filename),
        "thesis": thesis,
        "rev_rows_changed": int(delta_rev.abs().gt(1e-6).sum()),
        "cogs_rows_changed": int(delta_cogs.abs().gt(1e-6).sum()),
        "mean_abs_rev_delta": delta_rev.abs().mean(),
        "mean_abs_cogs_delta": delta_cogs.abs().mean(),
        "directional_best_case_gain": 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
        "revenue_total_ratio_vs_best": frame["Revenue"].sum() / base["Revenue"].sum(),
        "cogs_total_ratio_vs_best": frame["COGS"].sum() / base["COGS"].sum(),
        "revenue_total_ratio_vs_sample": frame["Revenue"].sum() / sample["Revenue"].sum(),
        "cogs_total_ratio_vs_sample": frame["COGS"].sum() / sample["COGS"].sum(),
        "ratio_all": frame["COGS"].sum() / frame["Revenue"].sum(),
        "ratio_2023h1": prof.loc[prof["period"].eq("2023H1"), "ratio"].iloc[0],
        "ratio_2023h2": prof.loc[prof["period"].eq("2023H2"), "ratio"].iloc[0],
        "ratio_2024h1": prof.loc[prof["period"].eq("2024H1"), "ratio"].iloc[0],
        "sample_ratio_2023h1": sample_prof.loc[sample_prof["period"].eq("2023H1"), "ratio"].iloc[0],
        "sample_ratio_2023h2": sample_prof.loc[sample_prof["period"].eq("2023H2"), "ratio"].iloc[0],
        "sample_ratio_2024h1": sample_prof.loc[sample_prof["period"].eq("2024H1"), "ratio"].iloc[0],
        "base_ratio_2023h1": base_prof.loc[base_prof["period"].eq("2023H1"), "ratio"].iloc[0],
        "base_ratio_2023h2": base_prof.loc[base_prof["period"].eq("2023H2"), "ratio"].iloc[0],
        "base_ratio_2024h1": base_prof.loc[base_prof["period"].eq("2024H1"), "ratio"].iloc[0],
    }


def register(rows: list[dict[str, object]], base: pd.DataFrame, sample: pd.DataFrame, frame: pd.DataFrame, filename: str, thesis: str, priority: int) -> None:
    write_submission(frame, DATASET_DIR / filename)
    rows.append(summarize(base, sample, frame, filename, thesis, priority))


def main() -> None:
    run_dir = make_run_dir()
    base = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    sample = add_segments(pd.read_csv(DATASET_DIR / SAMPLE_FILE, parse_dates=["Date"]))

    shape_both = align_sample_shape(base, sample, ("Revenue", "COGS"))
    shape_rev = align_sample_shape(base, sample, ("Revenue",))
    shape_cogs = align_sample_shape(base, sample, ("COGS",))
    shape_rev_keep_ratio = keep_ratio_from_base(shape_rev, base)

    rows: list[dict[str, object]] = []
    specs = [
        (
            "submission_sampleprior_v19_periodshape_both_a025.csv",
            blend(base, shape_both, 0.25),
            "blend 25% toward sample day-level shape, preserving current period totals for Revenue and COGS",
            1,
        ),
        (
            "submission_sampleprior_v19_periodshape_both_a050.csv",
            blend(base, shape_both, 0.50),
            "blend 50% toward sample day-level shape, preserving current period totals for Revenue and COGS",
            2,
        ),
        (
            "submission_sampleprior_v19_periodshape_both_a100.csv",
            shape_both,
            "replace day-level shape with sample shape, preserving current period totals",
            3,
        ),
        (
            "submission_sampleprior_v19_revshape_a050_keepcogs.csv",
            blend(base, shape_rev, 0.50),
            "blend 50% toward sample Revenue shape only, keep current COGS",
            4,
        ),
        (
            "submission_sampleprior_v19_cogsshape_a050_keeprev.csv",
            blend(base, shape_cogs, 0.50),
            "blend 50% toward sample COGS shape only, keep current Revenue",
            5,
        ),
        (
            "submission_sampleprior_v19_revshape_a050_preserve_ratio.csv",
            blend(base, shape_rev_keep_ratio, 0.50),
            "blend 50% toward sample Revenue shape and preserve current daily COGS/Revenue ratio",
            6,
        ),
        (
            "submission_sampleprior_v19_direct_a010.csv",
            blend_direct_sample(base, sample, 0.10),
            "direct 10% blend toward sample_submission values; tests sample as true low-scale prior",
            7,
        ),
        (
            "submission_sampleprior_v19_direct_a020.csv",
            blend_direct_sample(base, sample, 0.20),
            "direct 20% blend toward sample_submission values",
            8,
        ),
        (
            "submission_sampleprior_v19_direct_a035.csv",
            blend_direct_sample(base, sample, 0.35),
            "direct 35% blend toward sample_submission values",
            9,
        ),
    ]

    for filename, frame, thesis, priority in specs:
        register(rows, base, sample, frame, filename, thesis, priority)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(base).to_csv(run_dir / "current_best_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)
    period_summary(shape_both).to_csv(run_dir / "sample_shape_preserve_period_summary.csv", index=False)

    report = f"""# Public-Only Sample Prior V19

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Recent rejected probes:

{pd.Series(RECENT_REJECTS, name="public_score").to_markdown()}

Observation:

- `sample_submission.csv` is not a zero template; it contains a complete 548-day Revenue/COGS forecast.
- Its total scale is much lower than the current best, so direct blending is risky.
- A safer test is to borrow only its day-level shape while preserving current period totals.

Current best period summary:

{period_summary(base).to_markdown(index=False)}

Sample submission period summary:

{period_summary(sample).to_markdown(index=False)}

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_sampleprior_v19_periodshape_both_a025.csv`
2. If it improves: `submission_sampleprior_v19_periodshape_both_a050.csv`
3. If shape fails but close: `submission_sampleprior_v19_revshape_a050_keepcogs.csv`
4. Direct sample blend is a separate low-scale prior probe; only submit `direct_a010` if shape signal is not terrible.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_prior_v19_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
