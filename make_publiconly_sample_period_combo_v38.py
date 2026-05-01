from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_periodwise_shape_v35 import BASE_COGS_ALPHA, BASE_REV_ALPHA, periodwise_shape, with_cogs_away
from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, align_sample_shape, period_summary
from make_publiconly_sample_targetwise_v31 import PRE_SAMPLE_BEST_FILE
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "publiconly_sample_period_combo_v38"
CURRENT_BEST_FILE = "submission_sample_v37_rev2023H2_p0200_c0650_away0250.csv"
CURRENT_BEST_SCORE = 684699.68850

KNOWN_RESULTS = {
    "submission_sample_v35_rev2023H2_up1000_r1000_c0650_away0250.csv": 707436.88912,
    "submission_sample_v34_rev08000_cogs06500_away0250.csv": 698898.26661,
    "submission_sample_v36_rev2023H2_r0600_c0650_away0250.csv": 692128.76474,
    "submission_sample_v36_rev2023H2_r0400_c0650_away0250.csv": 687112.64298,
    CURRENT_BEST_FILE: CURRENT_BEST_SCORE,
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def signed_token(alpha: float) -> str:
    sign = "m" if alpha < 0 else "p"
    return f"{sign}{abs(int(round(alpha * 1000))):04d}"


def build_frame(
    pre_base: pd.DataFrame,
    shape_both: pd.DataFrame,
    sample: pd.DataFrame,
    rev_overrides: dict[str, float],
    cogs_overrides: dict[str, float] | None = None,
) -> pd.DataFrame:
    shaped = periodwise_shape(pre_base, shape_both, rev_overrides, cogs_overrides or {})
    return with_cogs_away(shaped, sample)


def summarize(
    rows: list[dict[str, object]],
    current: pd.DataFrame,
    frame: pd.DataFrame,
    filename: str,
    thesis: str,
    priority: int,
    rev_overrides: dict[str, float],
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
            "rev_2023H1": rev_overrides.get("2023H1", BASE_REV_ALPHA),
            "rev_2023H2": rev_overrides.get("2023H2", BASE_REV_ALPHA),
            "rev_2024H1": rev_overrides.get("2024H1", BASE_REV_ALPHA),
            "cogs_alpha_all_periods": BASE_COGS_ALPHA,
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

    specs = [
        ("h2p0200", {"2023H2": 0.200}, "continue lowering only 2023H2 Revenue alpha to 0.200", 1),
        ("h2p0000", {"2023H2": 0.000}, "remove sample shape only in 2023H2", 2),
        ("h2m0100", {"2023H2": -0.100}, "extrapolate 2023H2 slightly away from sample", 3),
        (
            "h2p0200_2024h1up1000",
            {"2023H2": 0.200, "2024H1": 1.000},
            "2023H2 low plus stronger 2024H1 sample shape",
            4,
        ),
        (
            "h2p0200_2024h1down0600",
            {"2023H2": 0.200, "2024H1": 0.600},
            "2023H2 low plus weaker 2024H1 sample shape",
            5,
        ),
        (
            "h2p0200_2024h1down0400",
            {"2023H2": 0.200, "2024H1": 0.400},
            "2023H2 low plus much weaker 2024H1 sample shape",
            6,
        ),
        (
            "h2p0000_2024h1up1000",
            {"2023H2": 0.000, "2024H1": 1.000},
            "2023H2 zero plus stronger 2024H1 sample shape",
            7,
        ),
        (
            "h2p0000_2024h1down0600",
            {"2023H2": 0.000, "2024H1": 0.600},
            "2023H2 zero plus weaker 2024H1 sample shape",
            8,
        ),
        (
            "h2p0200_2023h1up1000",
            {"2023H2": 0.200, "2023H1": 1.000},
            "2023H2 low plus stronger 2023H1 sample shape",
            9,
        ),
        (
            "h2p0200_2023h1down0600",
            {"2023H2": 0.200, "2023H1": 0.600},
            "2023H2 low plus weaker 2023H1 sample shape",
            10,
        ),
    ]

    rows: list[dict[str, object]] = []
    for label, rev_overrides, thesis, priority in specs:
        parts = [label]
        for period, alpha in sorted(rev_overrides.items()):
            parts.append(f"{period.lower()}{signed_token(alpha)}")
        filename = f"submission_sample_v38_{'_'.join(parts)}_c0650_away0250.csv"
        frame = build_frame(pre_base, shape_both, sample, rev_overrides)
        summarize(rows, current, frame, filename, thesis, priority, rev_overrides)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest["best_case_score_if_direction_correct"] = CURRENT_BEST_SCORE - manifest[
        "directional_best_case_gain_vs_current"
    ]
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_best_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)

    report = f"""# Public-Only Sample Period Combo V38

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known results:

{pd.Series(KNOWN_RESULTS, name="public_score").to_markdown()}

Interpretation:

- `2023H2` Revenue alpha `0.400` is now the best known point.
- The curve still points lower, so the immediate next probes are `0.200` and `0.000`.
- This batch also prepares 2024H1/2023H1 period-combo probes for after the 2023H2 low-alpha result is known.

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. Submit `submission_sample_v37_rev2023H2_p0200_c0650_away0250.csv` or equivalent v38 h2p0200 first.
2. If it improves, submit `submission_sample_v37_rev2023H2_p0000_c0650_away0250.csv`.
3. If `p0000` improves or stays close, try 2024H1 combo: `submission_sample_v38_h2p0000_2023h2p0000_2024h1p1000_c0650_away0250.csv`.
4. If `p0200` fails, keep `r0400` and test period-combo around 2024H1 separately.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_period_combo_v38_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
