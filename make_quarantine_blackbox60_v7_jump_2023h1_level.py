from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_cogs_inverse_v26 import cogs_ratio_away_from_sample
from make_publiconly_sample_periodwise_shape_v35 import BASE_REV_ALPHA, periodwise_shape
from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, align_sample_shape, period_summary
from make_publiconly_sample_targetwise_v31 import PRE_SAMPLE_BEST_FILE
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_blackbox60_v7_jump_2023h1_level"
CURRENT_BEST_FILE = "submission_qbb60v6_shape_nonh2_2023h1p0900_2024h1p1100_level103.csv"
CURRENT_BEST_SCORE = 679112.88021


@dataclass(frozen=True)
class Spec:
    name: str
    rev_overrides: dict[str, float]
    away_alpha: float
    rev_scale_2023h1: float
    rev_scale_2024h1: float
    cogs_scale_2024h1: float
    thesis: str


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def build_frame(
    pre_base: pd.DataFrame,
    shape_both: pd.DataFrame,
    sample: pd.DataFrame,
    spec: Spec,
) -> pd.DataFrame:
    shaped = periodwise_shape(pre_base, shape_both, spec.rev_overrides, {})
    shaped = cogs_ratio_away_from_sample(add_segments(shaped), sample, spec.away_alpha)
    out = add_segments(shaped)
    out.loc[out["period"].eq("2023H1"), "Revenue"] *= spec.rev_scale_2023h1
    out.loc[out["period"].eq("2024H1"), "Revenue"] *= spec.rev_scale_2024h1
    out.loc[out["period"].eq("2024H1"), "COGS"] *= spec.cogs_scale_2024h1
    return out[["Date", "Revenue", "COGS", "period"]]


def specs() -> list[Spec]:
    base_rev = {"2023H1": 0.900, "2023H2": 0.100, "2024H1": 1.100}
    return [
        Spec(
            "qbb60v7_nonh2shape_2023h1level103",
            base_rev,
            0.250,
            1.030,
            1.030,
            1.000,
            "Main jump hypothesis: after fixing non-H2 shape, 2023H1 Revenue is still under-level by about +3%.",
        ),
        Spec(
            "qbb60v7_nonh2shape_2023h1level105",
            base_rev,
            0.250,
            1.050,
            1.030,
            1.000,
            "Aggressive continuation if 2023H1 really has a hidden level gap, not just a shape gap.",
        ),
        Spec(
            "qbb60v7_nonh2shape_away0300",
            base_rev,
            0.300,
            1.000,
            1.030,
            1.000,
            "Existing shape winner plus stronger COGS ratio-away; tests whether cost regime is still under-shifted.",
        ),
        Spec(
            "qbb60v7_nonh2shape_2023h1level103_away0300",
            base_rev,
            0.300,
            1.030,
            1.030,
            1.000,
            "Full jump attempt: combine the new 2023H1 level hypothesis with stronger COGS ratio-away.",
        ),
        Spec(
            "qbb60v7_nonh2shape_2023h1level103_2024h1p1200",
            {"2023H1": 0.900, "2023H2": 0.100, "2024H1": 1.200},
            0.250,
            1.030,
            1.030,
            1.000,
            "Revenue-only jump attempt: if both non-H2 periods still want even stronger sample-like shape plus 2023H1 level.",
        ),
    ]


def summarize_period_deltas(current: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
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


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Quarantine Blackbox 60x V7 Jump 2023H1 Level

Run directory: `{run_dir}`

## Status

This branch is **not clean**. It uses `sample_submission.csv` and public-leaderboard feedback.

Current blackbox best:

- `{CURRENT_BEST_FILE}` = `{CURRENT_BEST_SCORE}`

## Why This Batch Exists

- `2023H1 p0.900 + 2024H1 p1.100 + 2024H1 level +3%` improved strongly to `679112.88021`.
- Pushing `2023H1` shape to `1.000` worsened slightly, so the next likely jump is not more `2023H1` shape.
- The larger remaining hypothesis is that `2023H1` is still under-level, similar to how `2024H1 level +3%` helped earlier.

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Order

1. `submission_qbb60v7_nonh2shape_2023h1level103.csv`
2. If it improves, submit `submission_qbb60v7_nonh2shape_2023h1level103_away0300.csv`
3. If step 1 improves strongly, try `submission_qbb60v7_nonh2shape_2023h1level105.csv`
4. If step 1 worsens, fall back to the orthogonal big jump `submission_qbb60v7_nonh2shape_away0300.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_blackbox60_v7_jump_2023h1_level_2026-04-24.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    pre_base = add_segments(pd.read_csv(DATASET_DIR / PRE_SAMPLE_BEST_FILE, parse_dates=["Date"]))
    current = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))
    sample = add_segments(pd.read_csv(DATASET_DIR / SAMPLE_FILE, parse_dates=["Date"]))
    shape_both = align_sample_shape(pre_base, sample, ("Revenue", "COGS"))

    rows = []
    profiles = []
    for priority, spec in enumerate(specs(), start=1):
        frame = build_frame(pre_base, shape_both, sample, spec)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)
        delta_rev = frame["Revenue"] - current["Revenue"]
        delta_cogs = frame["COGS"] - current["COGS"]
        prof = period_summary(frame)
        rows.append(
            {
                "priority": priority,
                "filename": path.name,
                "thesis": spec.thesis,
                "rev_2023H1": spec.rev_overrides.get("2023H1", BASE_REV_ALPHA),
                "rev_2023H2": spec.rev_overrides.get("2023H2", BASE_REV_ALPHA),
                "rev_2024H1": spec.rev_overrides.get("2024H1", BASE_REV_ALPHA),
                "away_alpha": spec.away_alpha,
                "rev_scale_2023H1": spec.rev_scale_2023h1,
                "rev_scale_2024H1": spec.rev_scale_2024h1,
                "mean_abs_rev_delta_vs_current": delta_rev.abs().mean(),
                "mean_abs_cogs_delta_vs_current": delta_cogs.abs().mean(),
                "movement": 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
                "revenue_total_ratio_vs_current": frame["Revenue"].sum() / current["Revenue"].sum(),
                "cogs_total_ratio_vs_current": frame["COGS"].sum() / current["COGS"].sum(),
                "ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
                "ratio_2023H1": prof.loc[prof["period"].eq("2023H1"), "ratio"].iloc[0],
                "ratio_2023H2": prof.loc[prof["period"].eq("2023H2"), "ratio"].iloc[0],
                "ratio_2024H1": prof.loc[prof["period"].eq("2024H1"), "ratio"].iloc[0],
                "max_revenue": frame["Revenue"].max(),
                "max_cogs": frame["COGS"].max(),
            }
        )
        profile = summarize_period_deltas(current, frame)
        profile.insert(0, "filename", path.name)
        profiles.append(profile)

    manifest = pd.DataFrame(rows).sort_values("priority")
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    pd.concat(profiles, ignore_index=True).to_csv(run_dir / "period_delta_profiles.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_best_period_summary.csv", index=False)
    write_report(run_dir, manifest)
    print(run_dir)


if __name__ == "__main__":
    main()
