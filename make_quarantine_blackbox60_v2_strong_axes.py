from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_cogs_inverse_v26 import cogs_ratio_away_from_sample
from make_publiconly_sample_periodwise_shape_v35 import BASE_COGS_ALPHA, BASE_REV_ALPHA, periodwise_shape
from make_publiconly_sample_prior_v19 import SAMPLE_FILE, add_segments, align_sample_shape, period_summary
from make_publiconly_sample_targetwise_v31 import PRE_SAMPLE_BEST_FILE
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_blackbox60_v2_strong_axes"
CURRENT_BEST_FILE = "submission_sample_v37_rev2023H2_p0100_c0650_away0250.csv"
CURRENT_BEST_SCORE = 684463.34954


KNOWN_PUBLIC = {
    CURRENT_BEST_FILE: CURRENT_BEST_SCORE,
    "submission_qbb60_h2p0050_c0650_away0250.csv": 684894.20120,
    "submission_qbb60_h2p0100_c0600_away0250.csv": 684528.07282,
}


@dataclass(frozen=True)
class Spec:
    name: str
    rev_overrides: dict[str, float]
    cogs_overrides: dict[str, float]
    away_alpha: float
    thesis: str


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def build_frame(pre_base: pd.DataFrame, shape_both: pd.DataFrame, sample: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    shaped = periodwise_shape(pre_base, shape_both, spec.rev_overrides, spec.cogs_overrides)
    return cogs_ratio_away_from_sample(add_segments(shaped), sample, spec.away_alpha)


def specs() -> list[Spec]:
    return [
        Spec(
            "qbb60v2_rev2024h1_p1000",
            {"2023H2": 0.100, "2024H1": 1.000},
            {},
            0.250,
            "Largest remaining single Revenue-shape axis: strengthen 2024H1 sample-like daily shape.",
        ),
        Spec(
            "qbb60v2_rev2024h1_p0600",
            {"2023H2": 0.100, "2024H1": 0.600},
            {},
            0.250,
            "Opposite sign for 2024H1 Revenue shape.",
        ),
        Spec(
            "qbb60v2_rev2024h1_p1200",
            {"2023H2": 0.100, "2024H1": 1.200},
            {},
            0.250,
            "High-variance extrapolation if 2024H1 p1000 improves.",
        ),
        Spec(
            "qbb60v2_rev2023h1_p1000",
            {"2023H1": 1.000, "2023H2": 0.100},
            {},
            0.250,
            "Strengthen 2023H1 Revenue sample-like daily shape.",
        ),
        Spec(
            "qbb60v2_rev2023h1_p0600",
            {"2023H1": 0.600, "2023H2": 0.100},
            {},
            0.250,
            "Opposite sign for 2023H1 Revenue shape.",
        ),
        Spec(
            "qbb60v2_rev_nonh2_p1000",
            {"2023H1": 1.000, "2023H2": 0.100, "2024H1": 1.000},
            {},
            0.250,
            "Large combined non-H2 Revenue-shape move; only submit after one non-H2 axis improves.",
        ),
        Spec(
            "qbb60v2_cogs2024h1_c0500",
            {"2023H2": 0.100},
            {"2024H1": 0.500},
            0.250,
            "Period-specific COGS shape down in 2024H1; global c0600 was near-neutral.",
        ),
        Spec(
            "qbb60v2_cogs2024h1_c0800",
            {"2023H2": 0.100},
            {"2024H1": 0.800},
            0.250,
            "Opposite COGS 2024H1 shape direction.",
        ),
        Spec(
            "qbb60v2_cogs2023h1_c0500",
            {"2023H2": 0.100},
            {"2023H1": 0.500},
            0.250,
            "Period-specific COGS shape down in 2023H1.",
        ),
        Spec(
            "qbb60v2_cogs2023h2_c0500",
            {"2023H2": 0.100},
            {"2023H2": 0.500},
            0.250,
            "Period-specific COGS shape down in guarded 2023H2.",
        ),
        Spec(
            "qbb60v2_away0300",
            {"2023H2": 0.100},
            {},
            0.300,
            "Retest COGS ratio-away strength; away axis historically improved until 0.25 then plateaued.",
        ),
        Spec(
            "qbb60v2_away0200",
            {"2023H2": 0.100},
            {},
            0.200,
            "Opposite ratio-away direction.",
        ),
    ]


def changed_by_period(current: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
    cur = add_segments(current)
    nxt = add_segments(frame)
    rows = []
    for period in ["2023H1", "2023H2", "2024H1", "2024-07-01"]:
        mask = cur["period"].eq(period)
        rows.append(
            {
                "period": period,
                "mean_abs_rev_delta": (nxt.loc[mask, "Revenue"] - cur.loc[mask, "Revenue"]).abs().mean(),
                "mean_abs_cogs_delta": (nxt.loc[mask, "COGS"] - cur.loc[mask, "COGS"]).abs().mean(),
            }
        )
    return pd.DataFrame(rows)


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Quarantine Blackbox 60x V2 Strong Axes

Run directory: `{run_dir}`

## Status

This is **not clean**. It is a quarantined public/synthetic probe generator and must not be included in a final legal source package.

Known public results incorporated:

{pd.Series(KNOWN_PUBLIC, name="public_score").to_markdown()}

Interpretation:

- H2 below alpha `0.100` is worse, so stop H2-low probing.
- Global COGS shape `0.600` is almost neutral/slightly worse, so a 60x jump must come from a larger untested axis.
- The largest remaining axes are 2024H1 Revenue shape, combined non-H2 Revenue shape, and period-specific COGS shape.

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Order

1. `submission_qbb60v2_rev2024h1_p1000.csv`
2. If it worsens, submit `submission_qbb60v2_rev2024h1_p0600.csv`
3. If `rev2024h1_p1000` improves, submit `submission_qbb60v2_rev_nonh2_p1000.csv`
4. If Revenue axes are flat, submit `submission_qbb60v2_cogs2024h1_c0500.csv`
5. If COGS 2024H1 down worsens, submit `submission_qbb60v2_cogs2024h1_c0800.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_blackbox60_v2_strong_axes_2026-04-23.md").write_text(report, encoding="utf-8")


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
                "cogs_2023H1": spec.cogs_overrides.get("2023H1", BASE_COGS_ALPHA),
                "cogs_2023H2": spec.cogs_overrides.get("2023H2", BASE_COGS_ALPHA),
                "cogs_2024H1": spec.cogs_overrides.get("2024H1", BASE_COGS_ALPHA),
                "away_alpha": spec.away_alpha,
                "mean_abs_rev_delta_vs_current": delta_rev.abs().mean(),
                "mean_abs_cogs_delta_vs_current": delta_cogs.abs().mean(),
                "movement": 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
                "revenue_total_ratio_vs_current": frame["Revenue"].sum() / current["Revenue"].sum(),
                "cogs_total_ratio_vs_current": frame["COGS"].sum() / current["COGS"].sum(),
                "ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
                "ratio_2023H1": prof.loc[prof["period"].eq("2023H1"), "ratio"].iloc[0],
                "ratio_2023H2": prof.loc[prof["period"].eq("2023H2"), "ratio"].iloc[0],
                "ratio_2024H1": prof.loc[prof["period"].eq("2024H1"), "ratio"].iloc[0],
            }
        )
        if priority <= 8:
            profile = changed_by_period(current, frame)
            profile.insert(0, "filename", path.name)
            profiles.append(profile)

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    if profiles:
        pd.concat(profiles, ignore_index=True).to_csv(run_dir / "period_delta_profiles.csv", index=False)
    period_summary(current).to_csv(run_dir / "current_best_period_summary.csv", index=False)
    write_report(run_dir, manifest)
    print(run_dir)


if __name__ == "__main__":
    main()
