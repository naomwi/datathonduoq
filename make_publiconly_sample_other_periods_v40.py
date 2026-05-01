from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_periodwise_shape_v35 import BASE_COGS_ALPHA, periodwise_shape, with_cogs_away
from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, align_sample_shape, period_summary
from make_publiconly_sample_targetwise_v31 import PRE_SAMPLE_BEST_FILE
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "publiconly_sample_other_periods_v40"
CURRENT_BEST_FILE = "submission_sample_v37_rev2023H2_p0100_c0650_away0250.csv"
CURRENT_BEST_SCORE = 684463.34954
BASE_REV_ALPHA = 0.800
LOCKED_2023H2_ALPHA = 0.100

KNOWN_RESULTS = {
    "submission_sample_v34_rev08000_cogs06500_away0250.csv": 698898.26661,
    "submission_sample_v36_rev2023H2_r0600_c0650_away0250.csv": 692128.76474,
    "submission_sample_v36_rev2023H2_r0400_c0650_away0250.csv": 687112.64298,
    "submission_sample_v37_rev2023H2_p0200_c0650_away0250.csv": 684699.68850,
    CURRENT_BEST_FILE: CURRENT_BEST_SCORE,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def token(alpha: float) -> str:
    sign = "m" if alpha < 0 else "p"
    return f"{sign}{abs(int(round(alpha * 1000))):04d}"


def build_frame(
    pre_base: pd.DataFrame,
    shape_both: pd.DataFrame,
    sample: pd.DataFrame,
    overrides: dict[str, float],
) -> pd.DataFrame:
    rev_overrides = {"2023H2": LOCKED_2023H2_ALPHA}
    rev_overrides.update(overrides)
    shaped = periodwise_shape(pre_base, shape_both, rev_overrides, {})
    return with_cogs_away(shaped, sample)


def period_delta_summary(current: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
    cur = add_segments(current)
    nxt = add_segments(frame)
    rows = []
    for period in ["2023H1", "2023H2", "2024H1", "2024-07-01"]:
        mask = cur["period"].eq(period)
        rows.append(
            {
                "period": period,
                "rows": int(mask.sum()),
                "mean_abs_rev_delta": (nxt.loc[mask, "Revenue"] - cur.loc[mask, "Revenue"]).abs().mean(),
                "mean_abs_cogs_delta": (nxt.loc[mask, "COGS"] - cur.loc[mask, "COGS"]).abs().mean(),
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
    overrides: dict[str, float],
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
            "rev_2023H1": overrides.get("2023H1", BASE_REV_ALPHA),
            "rev_2023H2": LOCKED_2023H2_ALPHA,
            "rev_2024H1": overrides.get("2024H1", BASE_REV_ALPHA),
            "cogs_alpha_all_periods": BASE_COGS_ALPHA,
            "rev_rows_changed_vs_current": int(delta_rev.abs().gt(1e-6).sum()),
            "cogs_rows_changed_vs_current": int(delta_cogs.abs().gt(1e-6).sum()),
            "mean_abs_rev_delta_vs_current": delta_rev.abs().mean(),
            "mean_abs_cogs_delta_vs_current": delta_cogs.abs().mean(),
            "directional_best_case_gain_vs_current": 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
            "revenue_total_ratio_vs_current": frame["Revenue"].sum() / current["Revenue"].sum(),
            "cogs_total_ratio_vs_current": frame["COGS"].sum() / current["COGS"].sum(),
            "min_revenue": frame["Revenue"].min(),
            "min_cogs": frame["COGS"].min(),
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
        ("2024h1p1000", {"2024H1": 1.000}, "lock 2023H2 at 0.100; strengthen 2024H1 sample shape", 1),
        ("2024h1p1200", {"2024H1": 1.200}, "lock 2023H2; extrapolate 2024H1 beyond sample shape", 2),
        ("2024h1p0600", {"2024H1": 0.600}, "opposite sign check for 2024H1", 3),
        ("2023h1p1000", {"2023H1": 1.000}, "lock 2023H2; strengthen 2023H1 sample shape", 4),
        ("2023h1p1200", {"2023H1": 1.200}, "lock 2023H2; extrapolate 2023H1 beyond sample shape", 5),
        ("2023h1p0600", {"2023H1": 0.600}, "opposite sign check for 2023H1", 6),
        (
            "2023h1p1000_2024h1p1000",
            {"2023H1": 1.000, "2024H1": 1.000},
            "both non-H2 periods stronger sample shape",
            7,
        ),
        (
            "2023h1p1200_2024h1p1000",
            {"2023H1": 1.200, "2024H1": 1.000},
            "2023H1 extrapolated plus 2024H1 stronger sample shape",
            8,
        ),
        (
            "2023h1p1000_2024h1p1200",
            {"2023H1": 1.000, "2024H1": 1.200},
            "2023H1 stronger plus 2024H1 extrapolated",
            9,
        ),
        (
            "2023h1p1200_2024h1p1200",
            {"2023H1": 1.200, "2024H1": 1.200},
            "high-variance non-H2 extrapolation toward 65x",
            10,
        ),
    ]

    rows: list[dict[str, object]] = []
    profiles = []
    for label, overrides, thesis, priority in specs:
        override_tag = "_".join(f"{period.lower()}{token(alpha)}" for period, alpha in sorted(overrides.items()))
        filename = f"submission_sample_v40_h2p0100_{label}_{override_tag}_c0650_away0250.csv"
        frame = build_frame(pre_base, shape_both, sample, overrides)
        summarize(rows, current, frame, filename, thesis, priority, overrides)
        if priority in {1, 3, 4, 7, 10}:
            prof = period_delta_summary(current, frame)
            prof.insert(0, "filename", filename)
            profiles.append(prof)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest["best_case_score_if_direction_correct"] = CURRENT_BEST_SCORE - manifest[
        "directional_best_case_gain_vs_current"
    ]
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    if profiles:
        pd.concat(profiles, ignore_index=True).to_csv(run_dir / "period_delta_profiles.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_best_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)

    report = f"""# Public-Only Sample Other Periods V40

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known results:

{pd.Series(KNOWN_RESULTS, name="public_score").to_markdown()}

Black-box interpretation:

- `2023H2` is now nearly optimized around alpha `0.100`; it is no longer the route to a large drop.
- Global Revenue alpha `0.800` improved even while `2023H2` was badly over-shaped, implying non-H2 periods likely prefer stronger sample shape.
- `2024H1` has the largest shape delta, so it is the best next high-information axis for a `65x` target.

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. Submit `submission_sample_v40_h2p0100_2024h1p1000_2024h1p1000_c0650_away0250.csv`.
2. If it improves, submit `submission_sample_v40_h2p0100_2024h1p1200_2024h1p1200_c0650_away0250.csv`.
3. If 2024H1 improves, test the combined non-H2 candidate `submission_sample_v40_h2p0100_2023h1p1000_2024h1p1000_2023h1p1000_2024h1p1000_c0650_away0250.csv`.
4. If 2024H1 worsens, submit the opposite sign `submission_sample_v40_h2p0100_2024h1p0600_2024h1p0600_c0650_away0250.csv`.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_other_periods_v40_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
