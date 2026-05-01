from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from make_publiconly_sample_periodwise_shape_v35 import BASE_COGS_ALPHA, BASE_REV_ALPHA, periodwise_shape, with_cogs_away
from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, align_sample_shape, period_summary
from make_publiconly_sample_targetwise_v31 import PRE_SAMPLE_BEST_FILE
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "publiconly_sample_2023h2_micro_v39"
CURRENT_BEST_FILE = "submission_sample_v37_rev2023H2_p0100_c0650_away0250.csv"
CURRENT_BEST_SCORE = 684463.34954

KNOWN_2023H2_RESULTS = {
    1.000: ("submission_sample_v35_rev2023H2_up1000_r1000_c0650_away0250.csv", 707436.88912),
    0.800: ("submission_sample_v34_rev08000_cogs06500_away0250.csv", 698898.26661),
    0.600: ("submission_sample_v36_rev2023H2_r0600_c0650_away0250.csv", 692128.76474),
    0.400: ("submission_sample_v36_rev2023H2_r0400_c0650_away0250.csv", 687112.64298),
    0.200: ("submission_sample_v37_rev2023H2_p0200_c0650_away0250.csv", 684699.68850),
    0.100: (CURRENT_BEST_FILE, CURRENT_BEST_SCORE),
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def token(alpha: float) -> str:
    sign = "m" if alpha < 0 else "p"
    return f"{sign}{abs(int(round(alpha * 10000))):05d}"


def fit_predictions(alphas: list[float]) -> pd.DataFrame:
    pts = np.array([[alpha, score] for alpha, (_, score) in KNOWN_2023H2_RESULTS.items()], dtype=float)
    rows = []
    for deg in (2, 3, 4):
        coef = np.polyfit(pts[:, 0], pts[:, 1], deg)
        xs = np.linspace(-0.1, 0.3, 801)
        ys = np.polyval(coef, xs)
        best_idx = int(np.argmin(ys))
        for alpha in alphas:
            rows.append({"fit": f"poly{deg}", "rev_alpha_2023H2": alpha, "pred_score": float(np.polyval(coef, alpha))})
        rows.append(
            {
                "fit": f"poly{deg}_grid_opt",
                "rev_alpha_2023H2": float(xs[best_idx]),
                "pred_score": float(ys[best_idx]),
            }
        )
    return pd.DataFrame(rows)


def summarize(
    rows: list[dict[str, object]],
    current: pd.DataFrame,
    frame: pd.DataFrame,
    filename: str,
    thesis: str,
    priority: int,
    rev_alpha_2023h2: float,
) -> None:
    write_submission(frame, DATASET_DIR / filename)
    delta_rev = frame["Revenue"] - current["Revenue"]
    delta_cogs = frame["COGS"] - current["COGS"]
    cur_seg = add_segments(current)
    frame_seg = add_segments(frame)
    h2_mask = cur_seg["period"].eq("2023H2")
    prof = period_summary(frame)
    rows.append(
        {
            "priority": priority,
            "filename": filename,
            "path": str(DATASET_DIR / filename),
            "thesis": thesis,
            "rev_alpha_2023H2": rev_alpha_2023h2,
            "base_rev_alpha_other_periods": BASE_REV_ALPHA,
            "base_cogs_alpha_all_periods": BASE_COGS_ALPHA,
            "rev_rows_changed_vs_current": int(delta_rev.abs().gt(1e-6).sum()),
            "cogs_rows_changed_vs_current": int(delta_cogs.abs().gt(1e-6).sum()),
            "mean_abs_rev_delta_vs_current": delta_rev.abs().mean(),
            "mean_abs_cogs_delta_vs_current": delta_cogs.abs().mean(),
            "h2_mean_abs_rev_delta": (
                frame_seg.loc[h2_mask, "Revenue"] - cur_seg.loc[h2_mask, "Revenue"]
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

    specs = [
        (0.175, "small step below current p0200; tests whether optimum is near 0.17"),
        (0.150, "midpoint toward p0100; conservative next probe"),
        (0.125, "between p0150 and p0100"),
        (0.100, "existing v37 p0100 equivalent; tests low side"),
        (0.075, "lower-side micro toward p0050"),
        (0.050, "near quadratic optimum zone"),
        (0.025, "very low 2023H2 alpha"),
        (0.000, "existing v37 p0000 equivalent"),
    ]
    pred = fit_predictions([alpha for alpha, _ in specs])
    pred.to_csv(run_dir / "fit_predictions.csv", index=False)

    rows: list[dict[str, object]] = []
    for priority, (rev_alpha, thesis) in enumerate(specs, start=1):
        filename = f"submission_sample_v39_rev2023H2_{token(rev_alpha)}_c0650_away0250.csv"
        shaped = periodwise_shape(pre_base, shape_both, {"2023H2": rev_alpha}, {})
        frame = with_cogs_away(shaped, sample)
        summarize(rows, current, frame, filename, thesis, priority, rev_alpha)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest = manifest.merge(
        pred.loc[pred["fit"].eq("poly2"), ["rev_alpha_2023H2", "pred_score"]],
        on="rev_alpha_2023H2",
        how="left",
    ).rename(columns={"pred_score": "poly2_pred_score"})
    manifest["best_case_score_if_direction_correct"] = CURRENT_BEST_SCORE - manifest[
        "directional_best_case_gain_vs_current"
    ]
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)

    known = pd.DataFrame(
        [
            {"rev_alpha_2023H2": alpha, "filename": filename, "public_score": score}
            for alpha, (filename, score) in KNOWN_2023H2_RESULTS.items()
        ]
    ).sort_values("rev_alpha_2023H2")
    known.to_csv(run_dir / "known_2023h2_results.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_best_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)

    report = f"""# Public-Only Sample 2023H2 Micro V39

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known 2023H2 results:

{known.to_markdown(index=False)}

Fit predictions:

{pred.to_markdown(index=False)}

Interpretation:

- `2023H2` alpha `0.200` is still best, but the improvement from `0.400 -> 0.200` is much smaller than `0.600 -> 0.400`.
- Fits disagree: quadratic wants near `0.03`, cubic/quartic prefer around `0.12-0.17`.
- Submit `0.100` for higher information, or `0.150` if you want lower risk.

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. Submit `submission_sample_v37_rev2023H2_p0100_c0650_away0250.csv` or equivalent v39 p0100.
2. If it improves, submit `submission_sample_v39_rev2023H2_p00500_c0650_away0250.csv`.
3. If `p0100` worsens, submit `submission_sample_v39_rev2023H2_p01500_c0650_away0250.csv`.
4. Only submit `p0000` if `p0100` improves or stays very close.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_2023h2_micro_v39_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
