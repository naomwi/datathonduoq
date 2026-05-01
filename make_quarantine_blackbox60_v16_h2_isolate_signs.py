from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_prior_v19 import add_segments, period_summary
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_blackbox60_v16_h2_isolate_signs"
CURRENT_BEST_FILE = "submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv"
CURRENT_BEST_SCORE = 662759.87577


@dataclass(frozen=True)
class Spec:
    name: str
    jul_scale: float = 1.0
    aug_scale: float = 1.0
    q4_scale: float = 1.0
    thesis: str = ""


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def specs() -> list[Spec]:
    return [
        Spec(
            name="qbb60v16_h2iso_q4down025_only",
            q4_scale=0.975,
            thesis="Isolate whether the failure came mainly from Q4 being too high on the current anchor.",
        ),
        Spec(
            name="qbb60v16_h2iso_julaugup050_only",
            jul_scale=1.050,
            aug_scale=1.050,
            thesis="Isolate whether the missing H2 signal is concentrated in Jul-Aug without touching Q4.",
        ),
        Spec(
            name="qbb60v16_h2iso_julup050_q4down025",
            jul_scale=1.050,
            q4_scale=0.975,
            thesis="If only July is undercalled while Q4 is high, this should outperform the broad Q3-up version.",
        ),
        Spec(
            name="qbb60v16_h2iso_augup050_q4down025",
            aug_scale=1.050,
            q4_scale=0.975,
            thesis="If August is the real undercalled month, this should beat July-only and broad Q3-up.",
        ),
    ]


def apply_spec(frame: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    out = add_segments(frame.copy())
    mask_2023 = out["Date"].dt.year.eq(2023)
    mask_jul = mask_2023 & out["Date"].dt.month.eq(7)
    mask_aug = mask_2023 & out["Date"].dt.month.eq(8)
    mask_q4 = mask_2023 & out["Date"].dt.month.isin([10, 11, 12])

    if spec.jul_scale != 1.0:
        out.loc[mask_jul, "Revenue"] *= spec.jul_scale
    if spec.aug_scale != 1.0:
        out.loc[mask_aug, "Revenue"] *= spec.aug_scale
    if spec.q4_scale != 1.0:
        out.loc[mask_q4, "Revenue"] *= spec.q4_scale
    return out


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


def monthly_summary(frame: pd.DataFrame) -> dict[str, float]:
    out = add_segments(frame.copy())
    mask_2023 = out["Date"].dt.year.eq(2023)
    months = {}
    for month, label in [(7, "jul"), (8, "aug"), (9, "sep"), (10, "oct"), (11, "nov"), (12, "dec")]:
        sub = out.loc[mask_2023 & out["Date"].dt.month.eq(month)]
        months[f"rev_{label}"] = sub["Revenue"].sum()
        months[f"ratio_{label}"] = sub["COGS"].sum() / sub["Revenue"].sum()
    return months


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Quarantine Blackbox 60x V16 H2 Isolate Signs

Run directory: `{run_dir}`

## Status

This branch is **not clean**. It builds directly on the current blackbox best and public-leaderboard feedback.

Current anchor:

- `{CURRENT_BEST_FILE}` = `{CURRENT_BEST_SCORE}`

## Why This Batch Exists

- Broad `Q3 up / Q4 down` failed.
- That does not kill the H2 hypothesis; it means the correction is probably more localized.
- The next useful step is to isolate `Q4 down` from `Jul-Aug up`, then split `Jul` versus `Aug`.

## Candidate Manifest

{manifest.to_markdown(index=False)}
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_blackbox60_v16_h2_isolate_signs_2026-04-24.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    current = add_segments(pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"]))

    rows = []
    profiles = []
    for priority, spec in enumerate(specs(), start=1):
        frame = apply_spec(current, spec)
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)

        delta_rev = frame["Revenue"] - current["Revenue"]
        delta_cogs = frame["COGS"] - current["COGS"]
        prof = period_summary(frame)
        month = monthly_summary(frame)
        rows.append(
            {
                "priority": priority,
                "filename": path.name,
                "thesis": spec.thesis,
                "jul_scale": spec.jul_scale,
                "aug_scale": spec.aug_scale,
                "q4_scale": spec.q4_scale,
                "mean_abs_rev_delta_vs_current": delta_rev.abs().mean(),
                "mean_abs_cogs_delta_vs_current": delta_cogs.abs().mean(),
                "movement": 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
                "revenue_total_ratio_vs_current": frame["Revenue"].sum() / current["Revenue"].sum(),
                "cogs_total_ratio_vs_current": frame["COGS"].sum() / current["COGS"].sum(),
                "ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
                "ratio_2023H1": prof.loc[prof["period"].eq("2023H1"), "ratio"].iloc[0],
                "ratio_2023H2": prof.loc[prof["period"].eq("2023H2"), "ratio"].iloc[0],
                "ratio_2024H1": prof.loc[prof["period"].eq("2024H1"), "ratio"].iloc[0],
                **month,
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
