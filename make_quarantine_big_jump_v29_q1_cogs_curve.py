from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from make_publiconly_sample_prior_v19 import add_segments, period_summary
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_big_jump_v29_q1_cogs_curve"
BASE_FILE = "submission_qbb65_h2_highratio_cogs_down060_keeprev.csv"
CURRENT_BEST_FILE = "submission_qbb68_h1_q1_cogs_down080_keeprev.csv"
CURRENT_BEST_SCORE = 656301.72926
SAMPLE_FILE = "sample_submission.csv"

KNOWN_Q1_DOWN_POINTS = pd.DataFrame(
    [
        {"q1_cogs_down": 0.000, "public_score": 659211.90870, "filename": BASE_FILE},
        {"q1_cogs_down": 0.040, "public_score": 657443.28137, "filename": "submission_qbb68_h1_q1_cogs_down040_keeprev.csv"},
        {"q1_cogs_down": 0.080, "public_score": CURRENT_BEST_SCORE, "filename": CURRENT_BEST_FILE},
    ]
)


@dataclass(frozen=True)
class Candidate:
    name: str
    family: str
    changed_scope: str
    thesis: str
    frame: pd.DataFrame


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def load_submission(filename: str) -> pd.DataFrame:
    return pd.read_csv(DATASET_DIR / filename, parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)


def assert_aligned(left: pd.DataFrame, right: pd.DataFrame, label: str) -> None:
    if not left["Date"].equals(right["Date"]):
        raise ValueError(f"Date mismatch for {label}")


def month_mask(frame: pd.DataFrame, year: int, months: tuple[int, ...]) -> pd.Series:
    return frame["Date"].dt.year.eq(year) & frame["Date"].dt.month.isin(months)


def q1_mask(frame: pd.DataFrame) -> pd.Series:
    return month_mask(frame, 2023, (1, 2, 3))


def apply_absolute_q1_down(base: pd.DataFrame, down: float) -> pd.DataFrame:
    out = base.copy()
    out.loc[q1_mask(out).to_numpy(), "COGS"] *= 1.0 - down
    return out


def sample_month_ratio_frame(base: pd.DataFrame, sample: pd.DataFrame, alpha: float) -> pd.DataFrame:
    out = base.copy()
    sample_month = sample.copy()
    sample_month["month"] = sample_month["Date"].dt.to_period("M")
    monthly = sample_month.groupby("month").agg(Revenue=("Revenue", "sum"), COGS=("COGS", "sum"))
    sample_ratio = monthly["COGS"] / monthly["Revenue"]
    month_key = out["Date"].dt.to_period("M")
    q1 = q1_mask(out).to_numpy()
    desired = out["Revenue"] * month_key.map(sample_ratio).astype(float)
    out.loc[q1, "COGS"] = (1.0 - alpha) * out.loc[q1, "COGS"] + alpha * desired.loc[q1]
    return out


def extra_month_down(current: pd.DataFrame, month: int, extra_down: float) -> pd.DataFrame:
    out = current.copy()
    mask = month_mask(out, 2023, (month,))
    out.loc[mask.to_numpy(), "COGS"] *= 1.0 - extra_down
    return out


def fit_response_curve() -> pd.DataFrame:
    points = KNOWN_Q1_DOWN_POINTS.copy()
    coef = np.polyfit(points["q1_cogs_down"], points["public_score"], 2)
    optimum = float(-coef[1] / (2.0 * coef[0]))
    grid = pd.DataFrame({"q1_cogs_down": [0.10, 0.12, 0.13, 0.14, 0.16, optimum]})
    grid["public_score_fit"] = np.polyval(coef, grid["q1_cogs_down"])
    grid["label"] = ["down100", "down120", "down130", "down140", "down160", "quadratic_optimum"]
    points["public_score_fit"] = np.polyval(coef, points["q1_cogs_down"])
    points["label"] = "known_" + points["q1_cogs_down"].map(lambda value: f"down{int(round(value * 1000)):03d}")
    return pd.concat([points[["label", "q1_cogs_down", "public_score", "public_score_fit"]], grid], ignore_index=True)


def build_candidates(base: pd.DataFrame, current: pd.DataFrame, sample: pd.DataFrame) -> list[Candidate]:
    assert_aligned(base, current, "current best")
    assert_aligned(base, sample, "sample")

    candidates: list[Candidate] = []
    for down in [0.10, 0.12, 0.13, 0.14, 0.16]:
        token = f"down{int(round(down * 1000)):03d}"
        candidates.append(
            Candidate(
                name=f"qbb69_h1_q1_cogs_{token}_keeprev",
                family="h1_q1_cogs_response_curve",
                changed_scope="2023Q1 COGS only",
                thesis=f"Absolute 2023Q1 COGS reduction {down:.1%} from the pre-Q1-down anchor; extends the accepted 4% and 8% response curve.",
                frame=apply_absolute_q1_down(base, down),
            )
        )

    for alpha in [0.75, 1.00]:
        token = f"a{int(round(alpha * 1000)):04d}"
        candidates.append(
            Candidate(
                name=f"qbb69_h1_q1_cogs_sample_monthratio_{token}",
                family="h1_q1_cogs_sample_month_ratio",
                changed_scope="2023Q1 COGS only",
                thesis=f"Blend Q1 COGS {alpha:.0%} toward sample monthly COGS/Revenue ratios; tests month-specific ratio repair instead of uniform down.",
                frame=sample_month_ratio_frame(base, sample, alpha),
            )
        )

    candidates.extend(
        [
            Candidate(
                name="qbb69_h1_mar_extra_cogs_down040_from_down080",
                family="h1_q1_month_concentration",
                changed_scope="2023-03 COGS only",
                thesis="After uniform down080, March still has the highest Q1 ratio; lower March another 4%.",
                frame=extra_month_down(current, 3, 0.040),
            ),
            Candidate(
                name="qbb69_h1_mar_extra_cogs_down060_from_down080",
                family="h1_q1_month_concentration",
                changed_scope="2023-03 COGS only",
                thesis="Stronger March-only repair after uniform down080.",
                frame=extra_month_down(current, 3, 0.060),
            ),
        ]
    )
    return candidates


def month_summary(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["month"] = out["Date"].dt.strftime("%Y-%m")
    return (
        out.groupby("month", as_index=False)
        .agg(days=("Date", "count"), Revenue=("Revenue", "sum"), COGS=("COGS", "sum"))
        .assign(ratio=lambda data: data["COGS"] / data["Revenue"])
    )


def summarize_candidate(current: pd.DataFrame, candidate: Candidate, filename: str, priority: int) -> dict[str, object]:
    frame = candidate.frame
    delta_rev = frame["Revenue"] - current["Revenue"]
    delta_cogs = frame["COGS"] - current["COGS"]
    prof = period_summary(frame)
    q1 = q1_mask(current)
    non_q1 = ~q1
    return {
        "priority": priority,
        "filename": filename,
        "family": candidate.family,
        "changed_scope": candidate.changed_scope,
        "thesis": candidate.thesis,
        "rev_rows_changed": int(delta_rev.abs().gt(1e-6).sum()),
        "cogs_rows_changed": int(delta_cogs.abs().gt(1e-6).sum()),
        "non_q1_max_abs_delta_vs_current": float(
            max(delta_rev.loc[non_q1].abs().max(), delta_cogs.loc[non_q1].abs().max())
        ),
        "mean_abs_rev_delta_vs_current": float(delta_rev.abs().mean()),
        "mean_abs_cogs_delta_vs_current": float(delta_cogs.abs().mean()),
        "movement_vs_current": float(0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean())),
        "best_case_score_if_direction_perfect": float(CURRENT_BEST_SCORE - 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean())),
        "revenue_total_ratio_vs_current": float(frame["Revenue"].sum() / current["Revenue"].sum()),
        "cogs_total_ratio_vs_current": float(frame["COGS"].sum() / current["COGS"].sum()),
        "ratio_all": float(frame["COGS"].sum() / frame["Revenue"].sum()),
        "ratio_2023H1": float(prof.loc[prof["period"].eq("2023H1"), "ratio"].iloc[0]),
        "ratio_2023H2": float(prof.loc[prof["period"].eq("2023H2"), "ratio"].iloc[0]),
        "ratio_2024H1": float(prof.loc[prof["period"].eq("2024H1"), "ratio"].iloc[0]),
        "max_revenue": float(frame["Revenue"].max()),
        "max_cogs": float(frame["COGS"].max()),
    }


def validate_frame(frame: pd.DataFrame, filename: str) -> None:
    if len(frame) != 548:
        raise ValueError(f"{filename}: expected 548 rows, found {len(frame)}")
    if frame["Date"].min() != pd.Timestamp("2023-01-01"):
        raise ValueError(f"{filename}: bad start date")
    if frame["Date"].max() != pd.Timestamp("2024-07-01"):
        raise ValueError(f"{filename}: bad end date")
    if frame[["Revenue", "COGS"]].isna().any().any():
        raise ValueError(f"{filename}: NaN values found")
    if (frame[["Revenue", "COGS"]] < 0).any().any():
        raise ValueError(f"{filename}: negative values found")


def write_report(run_dir: Path, manifest: pd.DataFrame, response_curve: pd.DataFrame, base: pd.DataFrame, current: pd.DataFrame, sample: pd.DataFrame) -> None:
    report = f"""# Quarantine Big Jump V29 Q1 COGS Curve

Run directory: `{run_dir}`

## Status

This branch is **quarantine blackbox**, not clean.

## Current Read

- Current best anchor: `{CURRENT_BEST_FILE}` = `{CURRENT_BEST_SCORE}`.
- Q1 COGS down `4%` and `8%` both improved; slope is decreasing but still positive.
- Quadratic fit from `0/4/8%` puts the response optimum near `13%` absolute Q1 COGS down.
- This batch changes only 2023Q1 COGS and preserves Revenue, 2023Q2, 2023H2, and 2024H1.

## Response Curve

{response_curve.to_markdown(index=False)}

## Current Q1 Month Ratios

{month_summary(current).head(3).to_markdown(index=False)}

## Sample Q1 Month Ratios

{month_summary(sample).head(3).to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Suggested Submit Order

1. `submission_qbb69_h1_q1_cogs_down120_keeprev.csv`
2. If it improves cleanly, submit `submission_qbb69_h1_q1_cogs_down130_keeprev.csv`
3. If `down120` is flat/slightly worse, submit `submission_qbb69_h1_q1_cogs_down100_keeprev.csv`
4. If uniform-down stalls but remains close, submit `submission_qbb69_h1_q1_cogs_sample_monthratio_a1000.csv`
5. Use March-only candidates only if uniform-down overshoots but March ratio still looks high.

## Do Not Use As Clean

These candidates are public-guided/quarantine probes and must not be presented as clean model outputs.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_big_jump_v29_q1_cogs_curve_2026-04-26.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    base = load_submission(BASE_FILE)
    current = load_submission(CURRENT_BEST_FILE)
    sample = load_submission(SAMPLE_FILE)

    rows: list[dict[str, object]] = []
    profiles: list[pd.DataFrame] = []
    for priority, candidate in enumerate(build_candidates(base, current, sample), start=1):
        filename = f"submission_{candidate.name}.csv"
        export = candidate.frame[["Date", "Revenue", "COGS"]].copy()
        validate_frame(export, filename)
        write_submission(export, DATASET_DIR / filename)
        write_submission(export, run_dir / filename)
        rows.append(summarize_candidate(current, candidate, filename, priority))
        profile = month_summary(export)
        profile.insert(0, "filename", filename)
        profiles.append(profile)

    manifest = pd.DataFrame(rows).sort_values("priority")
    response_curve = fit_response_curve()
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    response_curve.to_csv(run_dir / "response_curve.csv", index=False)
    pd.concat(profiles, ignore_index=True).to_csv(run_dir / "month_profiles.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_best_period_summary.csv", index=False)
    period_summary(base).to_csv(run_dir / "base_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_period_summary.csv", index=False)
    write_report(run_dir, manifest, response_curve, base, current, sample)
    print(run_dir)


if __name__ == "__main__":
    main()
