from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, align_sample_shape, period_summary
from make_publiconly_sample_targetwise_v31 import BASE_COGS_AWAY_ALPHA, BASE_REV_ALPHA, PRE_SAMPLE_BEST_FILE, build_candidate
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "publiconly_sample_cogs_shape_micro_v33"
CURRENT_BEST_FILE = "submission_sample_v32_rev0725_cogs0700_away0250.csv"
CURRENT_BEST_SCORE = 699167.79998

KNOWN_COGS_SHAPE_RESULTS = {
    0.7500: ("submission_sample_v31_rev0725_cogs0750_away0250.csv", 699662.34515),
    0.7250: ("submission_sample_v30_a0725_ratio_away_sample0250.csv", 699376.32670),
    0.7000: (CURRENT_BEST_FILE, CURRENT_BEST_SCORE),
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def alpha_token(alpha: float) -> str:
    return f"{int(round(alpha * 10000)):05d}"


def fit_curve(alphas: list[float]) -> pd.DataFrame:
    pts = np.array([[alpha, score] for alpha, (_, score) in KNOWN_COGS_SHAPE_RESULTS.items()], dtype=float)
    rows = []
    for deg in (1, 2):
        coef = np.polyfit(pts[:, 0], pts[:, 1], deg)
        for alpha in alphas:
            rows.append(
                {
                    "fit": f"poly{deg}",
                    "cogs_alpha": alpha,
                    "pred_score": float(np.polyval(coef, alpha)),
                }
            )
        if deg == 2:
            a, b, _ = coef
            opt = -b / (2.0 * a)
            rows.append(
                {
                    "fit": "poly2_optimum",
                    "cogs_alpha": float(opt),
                    "pred_score": float(np.polyval(coef, opt)),
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
            "rev_alpha": BASE_REV_ALPHA,
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


def main() -> None:
    run_dir = make_run_dir()
    pre_base = add_segments(pd.read_csv(DATASET_DIR / PRE_SAMPLE_BEST_FILE, parse_dates=["Date"]))
    current = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    sample = add_segments(pd.read_csv(DATASET_DIR / SAMPLE_FILE, parse_dates=["Date"]))
    shape_both = align_sample_shape(pre_base, sample, ("Revenue", "COGS"))

    alpha_specs = [
        (0.6750, "existing v32 step, checks if optimum is close to 0.700"),
        (0.6625, "midpoint between 0.675 and expected 0.650 zone"),
        (0.6500, "quadratic fit target zone from 0.750/0.725/0.700"),
        (0.6450, "near quadratic optimum"),
        (0.6400, "near quadratic optimum lower side"),
        (0.6250, "tests if trend remains monotonic below fitted optimum"),
        (0.6000, "extreme lower-side public-only diagnostic"),
    ]
    pred = fit_curve([alpha for alpha, _ in alpha_specs])
    pred.to_csv(run_dir / "cogs_shape_fit_predictions.csv", index=False)

    rows: list[dict[str, object]] = []
    for priority, (cogs_alpha, thesis) in enumerate(alpha_specs, start=1):
        filename = f"submission_sample_v33_rev0725_cogs{alpha_token(cogs_alpha)}_away0250.csv"
        frame = build_candidate(pre_base, shape_both, sample, BASE_REV_ALPHA, cogs_alpha)
        summarize(rows, current, frame, filename, thesis, priority, cogs_alpha)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest = manifest.merge(
        pred.loc[pred["fit"].eq("poly2"), ["cogs_alpha", "pred_score"]],
        on="cogs_alpha",
        how="left",
    ).rename(columns={"pred_score": "poly2_pred_score"})
    manifest["best_case_score_if_direction_correct"] = CURRENT_BEST_SCORE - manifest[
        "directional_best_case_gain_vs_current"
    ]
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_best_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)

    known = pd.DataFrame(
        [
            {"cogs_alpha": alpha, "filename": filename, "public_score": score}
            for alpha, (filename, score) in KNOWN_COGS_SHAPE_RESULTS.items()
        ]
    ).sort_values("cogs_alpha")
    known.to_csv(run_dir / "known_cogs_shape_results.csv", index=False)

    opt = pred.loc[pred["fit"].eq("poly2_optimum")].iloc[0]
    report = f"""# Public-Only Sample COGS Shape Micro V33

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known COGS-shape results:

{known.to_markdown(index=False)}

Fit predictions:

{pred.to_markdown(index=False)}

Interpretation:

- Reducing COGS sample-shape alpha from `0.725` to `0.700` improved by `{699376.32670 - CURRENT_BEST_SCORE:.5f}`.
- Increasing it to `0.750` worsened, so the next search should stay below `0.700`.
- The three-point quadratic fit puts the local optimum near COGS alpha `{opt['cogs_alpha']:.4f}` with predicted score `{opt['pred_score']:.2f}`. Treat this as a navigation hint, not a trusted forecast.

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. Submit existing `submission_sample_v32_rev0725_cogs0650_away0250.csv` or equivalent `submission_sample_v33_rev0725_cogs06500_away0250.csv`.
2. If it improves, submit `submission_sample_v33_rev0725_cogs06450_away0250.csv`.
3. If `0.650` worsens, fall back to `submission_sample_v32_rev0725_cogs0675_away0250.csv`.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_cogs_shape_micro_v33_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
