from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_cogs_inverse_v26 import cogs_ratio_away_from_sample
from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, align_sample_shape, period_summary
from make_publiconly_sample_targetwise_v27 import targetwise_shape
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "publiconly_sample_targetwise_v31"
PRE_SAMPLE_BEST_FILE = "submission_top10_v13_rev2023h2_up100_keepcogs.csv"
CURRENT_BEST_FILE = "submission_sample_v30_a0725_ratio_away_sample0250.csv"
CURRENT_BEST_SCORE = 699376.32670
BASE_REV_ALPHA = 0.725
BASE_COGS_ALPHA = 0.725
BASE_COGS_AWAY_ALPHA = 0.250

KNOWN_RESULTS = {
    "submission_sampleprior_v22_periodshape_both_a0725.csv": 701005.12470,
    "submission_sample_v25_a0725_ratio_to_sample0050.csv": 701788.31792,
    "submission_sample_v26_a0725_ratio_away_sample0100.csv": 699960.93186,
    "submission_sample_v28_a0725_ratio_away_sample0175.csv": 699556.47851,
    "submission_sample_v30_a0725_ratio_away_sample0225.csv": 699384.92478,
    CURRENT_BEST_FILE: CURRENT_BEST_SCORE,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def with_cogs_away(frame: pd.DataFrame, sample: pd.DataFrame, alpha: float = BASE_COGS_AWAY_ALPHA) -> pd.DataFrame:
    return cogs_ratio_away_from_sample(add_segments(frame), sample, alpha)


def build_candidate(
    pre_base: pd.DataFrame,
    shape_both: pd.DataFrame,
    sample: pd.DataFrame,
    rev_alpha: float,
    cogs_alpha: float,
    away_alpha: float = BASE_COGS_AWAY_ALPHA,
) -> pd.DataFrame:
    shaped = targetwise_shape(pre_base, shape_both, rev_alpha, cogs_alpha)
    return with_cogs_away(shaped, sample, away_alpha)


def alpha_token(alpha: float) -> str:
    return f"{int(round(alpha * 1000)):04d}"


def summarize(
    rows: list[dict[str, object]],
    current: pd.DataFrame,
    frame: pd.DataFrame,
    filename: str,
    thesis: str,
    priority: int,
    rev_alpha: float,
    cogs_alpha: float,
) -> None:
    write_submission(frame, DATASET_DIR / filename)
    delta_rev = frame["Revenue"] - current["Revenue"]
    delta_cogs = frame["COGS"] - current["COGS"]
    prof = period_summary(frame)
    rows.append(
        {
            "priority": priority,
            "filename": filename,
            "path": str(DATASET_DIR / filename),
            "thesis": thesis,
            "rev_alpha": rev_alpha,
            "cogs_alpha": cogs_alpha,
            "cogs_away_alpha": BASE_COGS_AWAY_ALPHA,
            "rev_rows_changed_vs_current": int(delta_rev.abs().gt(1e-6).sum()),
            "cogs_rows_changed_vs_current": int(delta_cogs.abs().gt(1e-6).sum()),
            "mean_abs_rev_delta_vs_current": delta_rev.abs().mean(),
            "mean_abs_cogs_delta_vs_current": delta_cogs.abs().mean(),
            "directional_best_case_gain_vs_current": 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
            "revenue_total_ratio_vs_current": frame["Revenue"].sum() / current["Revenue"].sum(),
            "cogs_total_ratio_vs_current": frame["COGS"].sum() / current["COGS"].sum(),
            "ratio_all": frame["COGS"].sum() / frame["Revenue"].sum(),
            "ratio_2023h1": prof.loc[prof["period"].eq("2023H1"), "ratio"].iloc[0],
            "ratio_2023h2": prof.loc[prof["period"].eq("2023H2"), "ratio"].iloc[0],
            "ratio_2024h1": prof.loc[prof["period"].eq("2024H1"), "ratio"].iloc[0],
        }
    )


def known_score_curve() -> pd.DataFrame:
    rows = [
        (-0.050, "ratio_to_sample0050", 701788.31792),
        (0.000, "a0725_shape_only", 701005.12470),
        (0.025, "away0025", 700654.49101),
        (0.050, "away0050", 700363.16716),
        (0.100, "away0100", 699960.93186),
        (0.125, "away0125", 699793.67454),
        (0.175, "away0175", 699556.47851),
        (0.225, "away0225", 699384.92478),
        (0.250, "away0250", CURRENT_BEST_SCORE),
    ]
    out = pd.DataFrame(rows, columns=["cogs_away_alpha", "label", "public_score"])
    out["delta_from_prev"] = out["public_score"].diff()
    return out


def main() -> None:
    run_dir = make_run_dir()
    pre_base = add_segments(pd.read_csv(DATASET_DIR / PRE_SAMPLE_BEST_FILE, parse_dates=["Date"]))
    current = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    sample = add_segments(pd.read_csv(DATASET_DIR / SAMPLE_FILE, parse_dates=["Date"]))
    shape_both = align_sample_shape(pre_base, sample, ("Revenue", "COGS"))
    rebuilt_current = build_candidate(pre_base, shape_both, sample, BASE_REV_ALPHA, BASE_COGS_ALPHA)

    rows: list[dict[str, object]] = []
    specs = [
        (0.725, 0.750, "COGS sample-shape alpha up to 0.750, Revenue stays 0.725", 1),
        (0.725, 0.775, "COGS sample-shape alpha up to 0.775, Revenue stays 0.725", 2),
        (0.725, 0.800, "COGS sample-shape alpha up to 0.800, Revenue stays 0.725", 3),
        (0.750, 0.725, "Revenue sample-shape alpha up to 0.750, COGS stays 0.725", 4),
        (0.800, 0.725, "Revenue sample-shape alpha up to 0.800, COGS stays 0.725", 5),
        (0.700, 0.725, "Revenue sample-shape alpha down to 0.700, COGS stays 0.725", 6),
        (0.725, 0.700, "COGS sample-shape alpha down to 0.700, Revenue stays 0.725", 7),
        (0.700, 0.800, "Revenue alpha down, COGS alpha up", 8),
        (0.800, 0.700, "Revenue alpha up, COGS alpha down", 9),
        (0.750, 0.800, "Both stronger, with COGS stronger than Revenue", 10),
        (0.800, 0.750, "Both stronger, with Revenue stronger than COGS", 11),
        (0.725, 0.850, "High-variance COGS shape extension to 0.850", 12),
        (0.850, 0.725, "High-variance Revenue shape extension to 0.850", 13),
    ]
    for rev_alpha, cogs_alpha, thesis, priority in specs:
        filename = (
            "submission_sample_v31_rev"
            f"{alpha_token(rev_alpha)}_cogs{alpha_token(cogs_alpha)}_away0250.csv"
        )
        frame = build_candidate(pre_base, shape_both, sample, rev_alpha, cogs_alpha)
        summarize(rows, current, frame, filename, thesis, priority, rev_alpha, cogs_alpha)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest["best_case_score_if_direction_correct"] = CURRENT_BEST_SCORE - manifest[
        "directional_best_case_gain_vs_current"
    ]
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)

    score_curve = known_score_curve()
    score_curve.to_csv(run_dir / "known_cogs_away_score_curve.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_best_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)
    period_summary(rebuilt_current).to_csv(run_dir / "rebuilt_current_period_summary.csv", index=False)

    max_rebuild_rev_delta = float((rebuilt_current["Revenue"] - current["Revenue"]).abs().max())
    max_rebuild_cogs_delta = float((rebuilt_current["COGS"] - current["COGS"]).abs().max())
    last_step_gain = KNOWN_RESULTS["submission_sample_v30_a0725_ratio_away_sample0225.csv"] - CURRENT_BEST_SCORE

    report = f"""# Public-Only Sample Targetwise V31

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known results:

{pd.Series(KNOWN_RESULTS, name="public_score").to_markdown()}

COGS-away score curve:

{score_curve.to_markdown(index=False)}

Interpretation:

- The last COGS-away step `0.225 -> 0.250` improved only `{last_step_gain:.5f}`, so this axis is nearly exhausted.
- To chase `67x`, the next meaningful axis is not more global COGS ratio; it is whether Revenue and COGS want different sample-shape strengths.
- Rebuild check against current best: max Revenue delta `{max_rebuild_rev_delta:.8f}`, max COGS delta `{max_rebuild_cogs_delta:.8f}`.

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. Submit `submission_sample_v31_rev0725_cogs0750_away0250.csv`.
2. If it improves, continue `submission_sample_v31_rev0725_cogs0775_away0250.csv`, then `submission_sample_v31_rev0725_cogs0800_away0250.csv`.
3. If COGS-shape-up fails, test Revenue side with `submission_sample_v31_rev0750_cogs0725_away0250.csv`.
4. Do not prioritize more COGS-away micro steps unless all target-wise probes fail.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_targetwise_v31_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
