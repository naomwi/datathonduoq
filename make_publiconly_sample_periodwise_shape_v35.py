from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_cogs_inverse_v26 import cogs_ratio_away_from_sample
from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, align_sample_shape, period_summary
from make_publiconly_sample_targetwise_v31 import BASE_COGS_AWAY_ALPHA, PRE_SAMPLE_BEST_FILE
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "publiconly_sample_periodwise_shape_v35"
CURRENT_BEST_FILE = "submission_sample_v34_rev08000_cogs06500_away0250.csv"
CURRENT_BEST_SCORE = 698898.26661
BASE_REV_ALPHA = 0.800
BASE_COGS_ALPHA = 0.650

KNOWN_RESULTS = {
    "submission_sample_v32_rev0725_cogs0650_away0250.csv": 698994.05843,
    CURRENT_BEST_FILE: CURRENT_BEST_SCORE,
    "submission_sample_v35_rev2023H2_up1000_r1000_c0650_away0250.csv": 707436.88912,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def alpha_token(alpha: float) -> str:
    return f"{int(round(alpha * 1000)):04d}"


def periodwise_shape(
    base: pd.DataFrame,
    shape_both: pd.DataFrame,
    rev_alphas: dict[str, float],
    cogs_alphas: dict[str, float],
) -> pd.DataFrame:
    base_seg = add_segments(base)
    shape_seg = add_segments(shape_both)
    out = base[["Date", "Revenue", "COGS"]].copy()
    for period, idx in base_seg.groupby("period").groups.items():
        idx_list = list(idx)
        rev_alpha = rev_alphas.get(period, BASE_REV_ALPHA)
        cogs_alpha = cogs_alphas.get(period, BASE_COGS_ALPHA)
        out.loc[idx_list, "Revenue"] = (
            (1.0 - rev_alpha) * base_seg.loc[idx_list, "Revenue"].to_numpy()
            + rev_alpha * shape_seg.loc[idx_list, "Revenue"].to_numpy()
        )
        out.loc[idx_list, "COGS"] = (
            (1.0 - cogs_alpha) * base_seg.loc[idx_list, "COGS"].to_numpy()
            + cogs_alpha * shape_seg.loc[idx_list, "COGS"].to_numpy()
        )
    return out


def with_cogs_away(frame: pd.DataFrame, sample: pd.DataFrame) -> pd.DataFrame:
    return cogs_ratio_away_from_sample(add_segments(frame), sample, BASE_COGS_AWAY_ALPHA)


def summarize(
    rows: list[dict[str, object]],
    current: pd.DataFrame,
    frame: pd.DataFrame,
    filename: str,
    thesis: str,
    priority: int,
    changed_period: str,
    rev_alpha: float,
    cogs_alpha: float,
) -> None:
    write_submission(frame, DATASET_DIR / filename)
    delta_rev = frame["Revenue"] - current["Revenue"]
    delta_cogs = frame["COGS"] - current["COGS"]
    cur_seg = add_segments(current)
    frame_seg = add_segments(frame)
    period_mask = cur_seg["period"].eq(changed_period)
    prof = period_summary(frame)
    rows.append(
        {
            "priority": priority,
            "filename": filename,
            "path": str(DATASET_DIR / filename),
            "thesis": thesis,
            "changed_period": changed_period,
            "period_rev_alpha": rev_alpha,
            "period_cogs_alpha": cogs_alpha,
            "base_rev_alpha_other_periods": BASE_REV_ALPHA,
            "base_cogs_alpha_other_periods": BASE_COGS_ALPHA,
            "rev_rows_changed_vs_current": int(delta_rev.abs().gt(1e-6).sum()),
            "cogs_rows_changed_vs_current": int(delta_cogs.abs().gt(1e-6).sum()),
            "period_rows": int(period_mask.sum()),
            "mean_abs_rev_delta_vs_current": delta_rev.abs().mean(),
            "mean_abs_cogs_delta_vs_current": delta_cogs.abs().mean(),
            "period_mean_abs_rev_delta": (
                frame_seg.loc[period_mask, "Revenue"] - cur_seg.loc[period_mask, "Revenue"]
            ).abs().mean(),
            "period_mean_abs_cogs_delta": (
                frame_seg.loc[period_mask, "COGS"] - cur_seg.loc[period_mask, "COGS"]
            ).abs().mean(),
            "directional_best_case_gain_vs_current": 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
            "revenue_total_ratio_vs_current": frame["Revenue"].sum() / current["Revenue"].sum(),
            "cogs_total_ratio_vs_current": frame["COGS"].sum() / current["COGS"].sum(),
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
    shape_both = align_sample_shape(pre_base, sample, ("Revenue", "COGS"))

    specs: list[tuple[str, str, dict[str, float], dict[str, float], str, int]] = []
    for period in ["2023H1", "2023H2", "2024H1"]:
        specs.extend(
            [
                (
                    f"rev{period}_up1000",
                    period,
                    {period: 1.000},
                    {},
                    f"Revenue sample-shape alpha up to 1.000 only in {period}",
                    len(specs) + 1,
                ),
                (
                    f"rev{period}_down0600",
                    period,
                    {period: 0.600},
                    {},
                    f"Revenue sample-shape alpha down to 0.600 only in {period}",
                    len(specs) + 2,
                ),
            ]
        )
    for period in ["2023H1", "2023H2", "2024H1"]:
        specs.extend(
            [
                (
                    f"cogs{period}_down0450",
                    period,
                    {},
                    {period: 0.450},
                    f"COGS sample-shape alpha down to 0.450 only in {period}",
                    len(specs) + 1,
                ),
                (
                    f"cogs{period}_up0850",
                    period,
                    {},
                    {period: 0.850},
                    f"COGS sample-shape alpha up to 0.850 only in {period}",
                    len(specs) + 2,
                ),
            ]
        )

    rows: list[dict[str, object]] = []
    for label, period, rev_overrides, cogs_overrides, thesis, priority in specs:
        rev_alpha = rev_overrides.get(period, BASE_REV_ALPHA)
        cogs_alpha = cogs_overrides.get(period, BASE_COGS_ALPHA)
        filename = (
            "submission_sample_v35_"
            f"{label}_r{alpha_token(rev_alpha)}_c{alpha_token(cogs_alpha)}_away0250.csv"
        )
        shaped = periodwise_shape(pre_base, shape_both, rev_overrides, cogs_overrides)
        frame = with_cogs_away(shaped, sample)
        summarize(rows, current, frame, filename, thesis, priority, period, rev_alpha, cogs_alpha)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest["best_case_score_if_direction_correct"] = CURRENT_BEST_SCORE - manifest[
        "directional_best_case_gain_vs_current"
    ]
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_best_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)

    report = f"""# Public-Only Sample Periodwise Shape V35

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known results:

{pd.Series(KNOWN_RESULTS, name="public_score").to_markdown()}

Interpretation:

- Global Revenue alpha `0.800` improved by only `{698994.05843 - CURRENT_BEST_SCORE:.5f}`.
- The next possible big source is period heterogeneity: one half-year may want much more sample shape while another wants less.
- All candidates preserve period totals. They only alter intra-period daily shape for one target and one period.

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. Submit `submission_sample_v35_rev2023H2_up1000_r1000_c0650_away0250.csv` first.
2. If it improves, test `submission_sample_v35_rev2023H1_up1000_r1000_c0650_away0250.csv` and `submission_sample_v35_rev2024H1_up1000_r1000_c0650_away0250.csv`.
3. If Revenue period-up fails, test period-down with `submission_sample_v35_rev2023H2_down0600_r0600_c0650_away0250.csv`.
4. If Revenue period axis is weak, move to COGS period-specific candidates.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_periodwise_shape_v35_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
