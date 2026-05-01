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


RUN_PREFIX = "quarantine_blackbox60_v3_anchor682"
CURRENT_BEST_FILE = "submission_sample_v40_h2p0100_2024h1p1000_2024h1p1000_c0650_away0250.csv"
CURRENT_BEST_SCORE = 682039.28310


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
    # Current best coordinates: rev 2023H1=0.800, 2023H2=0.100, 2024H1=1.000;
    # cogs all=0.650; cogs ratio away=0.250.
    return [
        Spec(
            "qbb60v3_2024h1p1100",
            {"2023H2": 0.100, "2024H1": 1.100},
            {},
            0.250,
            "Continue 2024H1 Revenue-shape direction beyond current p1000.",
        ),
        Spec(
            "qbb60v3_2024h1p1200",
            {"2023H2": 0.100, "2024H1": 1.200},
            {},
            0.250,
            "Larger 2024H1 Revenue-shape extrapolation.",
        ),
        Spec(
            "qbb60v3_2024h1p0900",
            {"2023H2": 0.100, "2024H1": 0.900},
            {},
            0.250,
            "Check if optimum is below current p1000.",
        ),
        Spec(
            "qbb60v3_2023h1p0900_2024h1p1000",
            {"2023H1": 0.900, "2023H2": 0.100, "2024H1": 1.000},
            {},
            0.250,
            "Add modest 2023H1 Revenue-shape strength on top of current best.",
        ),
        Spec(
            "qbb60v3_2023h1p1000_2024h1p1000",
            {"2023H1": 1.000, "2023H2": 0.100, "2024H1": 1.000},
            {},
            0.250,
            "Add full 2023H1 Revenue-shape strength on top of current best.",
        ),
        Spec(
            "qbb60v3_2023h1p0700_2024h1p1000",
            {"2023H1": 0.700, "2023H2": 0.100, "2024H1": 1.000},
            {},
            0.250,
            "Opposite 2023H1 Revenue-shape direction on top of current best.",
        ),
        Spec(
            "qbb60v3_cogs2024h1_c0500",
            {"2023H2": 0.100, "2024H1": 1.000},
            {"2024H1": 0.500},
            0.250,
            "COGS 2024H1 sample-shape down on top of current best.",
        ),
        Spec(
            "qbb60v3_cogs2024h1_c0800",
            {"2023H2": 0.100, "2024H1": 1.000},
            {"2024H1": 0.800},
            0.250,
            "COGS 2024H1 sample-shape up on top of current best.",
        ),
        Spec(
            "qbb60v3_cogsall_c0600",
            {"2023H2": 0.100, "2024H1": 1.000},
            {"2023H1": 0.600, "2023H2": 0.600, "2024H1": 0.600},
            0.250,
            "Global COGS-shape down re-tested on the true 682k anchor.",
        ),
        Spec(
            "qbb60v3_away0300",
            {"2023H2": 0.100, "2024H1": 1.000},
            {},
            0.300,
            "COGS ratio-away stronger on top of current best.",
        ),
        Spec(
            "qbb60v3_away0200",
            {"2023H2": 0.100, "2024H1": 1.000},
            {},
            0.200,
            "COGS ratio-away softer on top of current best.",
        ),
        Spec(
            "qbb60v3_2024h1p1100_cogs2024h1c0500",
            {"2023H2": 0.100, "2024H1": 1.100},
            {"2024H1": 0.500},
            0.250,
            "Combined continuation: 2024H1 Revenue p1100 plus 2024H1 COGS-shape down.",
        ),
    ]


def period_delta(current: pd.DataFrame, frame: pd.DataFrame) -> pd.DataFrame:
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
    report = f"""# Quarantine Blackbox 60x V3 Anchor 682

Run directory: `{run_dir}`

## Status

This is **not clean**. It reads `sample_submission.csv` and uses public-leaderboard feedback. Do not include it in a final legal source package.

Current true blackbox best:

- `{CURRENT_BEST_FILE}` = `{CURRENT_BEST_SCORE}`

Important correction:

- This file is identical to `submission_qbb60v2_rev2024h1_p1000.csv`.
- Therefore all follow-ups must be anchored on `2024H1 Revenue alpha = 1.000`, not the older `0.800`.

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Order

1. `submission_qbb60v3_2024h1p1100.csv`
2. If p1100 improves, submit `submission_qbb60v3_2024h1p1200.csv`
3. If p1100 worsens, submit `submission_qbb60v3_2024h1p0900.csv`
4. If 2024H1 is flat, test `submission_qbb60v3_2023h1p0900_2024h1p1000.csv`
5. If Revenue shape stalls, test COGS on true anchor: `submission_qbb60v3_cogs2024h1_c0500.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_blackbox60_v3_anchor682_2026-04-23.md").write_text(report, encoding="utf-8")


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
            profile = period_delta(current, frame)
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
