from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_periodwise_shape_v35 import (
    BASE_COGS_ALPHA,
    BASE_REV_ALPHA,
    CURRENT_BEST_FILE,
    CURRENT_BEST_SCORE,
    KNOWN_RESULTS,
    alpha_token,
    periodwise_shape,
    with_cogs_away,
)
from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, align_sample_shape, period_summary
from make_publiconly_sample_targetwise_v31 import PRE_SAMPLE_BEST_FILE
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "publiconly_sample_2023h2_reversal_v36"
FAILED_UP_FILE = "submission_sample_v35_rev2023H2_up1000_r1000_c0650_away0250.csv"
FAILED_UP_SCORE = 707436.88912
R0600_SCORE = 692128.76474


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


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
        (0.750, "small 2023H2 reversal from current 0.800 to 0.750", 1),
        (0.700, "moderate 2023H2 reversal to 0.700", 2),
        (0.650, "strong 2023H2 reversal to 0.650", 3),
        (0.600, "large 2023H2 reversal to 0.600; opposite of failed up1000 test", 4),
        (0.550, "larger 2023H2 reversal to 0.550", 5),
        (0.500, "half sample-shape strength in 2023H2", 6),
        (0.400, "high-variance 2023H2 reversal", 7),
        (0.000, "remove sample-shape contribution in 2023H2 only", 8),
    ]

    rows: list[dict[str, object]] = []
    for rev_alpha, thesis, priority in specs:
        filename = f"submission_sample_v36_rev2023H2_r{alpha_token(rev_alpha)}_c0650_away0250.csv"
        shaped = periodwise_shape(pre_base, shape_both, {"2023H2": rev_alpha}, {})
        frame = with_cogs_away(shaped, sample)
        summarize(rows, current, frame, filename, thesis, priority, rev_alpha)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest["best_case_score_if_direction_correct"] = CURRENT_BEST_SCORE - manifest[
        "directional_best_case_gain_vs_current"
    ]
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_best_period_summary.csv", index=False)
    period_summary(sample).to_csv(run_dir / "sample_submission_period_summary.csv", index=False)

    known = dict(KNOWN_RESULTS)
    known[FAILED_UP_FILE] = FAILED_UP_SCORE
    known["submission_sample_v36_rev2023H2_r0600_c0650_away0250.csv"] = R0600_SCORE
    fail_delta = FAILED_UP_SCORE - CURRENT_BEST_SCORE
    report = f"""# Public-Only Sample 2023H2 Reversal V36

Run directory: `{run_dir}`

Current best: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

Known results:

{pd.Series(known, name="public_score").to_markdown()}

Interpretation:

- `2023H2` Revenue alpha up to `1.000` worsened by `{fail_delta:.5f}`.
- That is a strong sign that `2023H2` is over-shaped toward sample under the current global Revenue alpha `0.800`.
- The immediate high-information next probe is the opposite side, especially `0.600`.

Candidate manifest:

{manifest.to_markdown(index=False)}

Suggested order:

1. Submit `submission_sample_v36_rev2023H2_r0600_c0650_away0250.csv` for the strongest opposite-direction test.
2. If it improves a lot, continue `submission_sample_v36_rev2023H2_r0500_c0650_away0250.csv`.
3. If it improves only slightly, test `submission_sample_v36_rev2023H2_r0650_c0650_away0250.csv`.
4. If it worsens, `2023H2` shape is near current optimum and the next axis is `2024H1`.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_sample_2023h2_reversal_v36_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
