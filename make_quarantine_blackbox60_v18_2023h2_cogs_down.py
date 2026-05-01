from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_prior_v19 import add_segments, period_summary
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_blackbox60_v18_2023h2_cogs_down"
CURRENT_BEST_FILE = "submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv"
CURRENT_BEST_SCORE = 662759.87577


@dataclass(frozen=True)
class Spec:
    name: str
    cogs_scale_2023h2: float
    thesis: str


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def specs() -> list[Spec]:
    return [
        Spec(
            "qbb60v18_cogs2023h2_down010",
            0.99,
            "Small H2 cost-ratio correction: current 2023H2 ratio is still high, but with 3 submissions left the first probe should be conservative.",
        ),
        Spec(
            "qbb60v18_cogs2023h2_down020",
            0.98,
            "Medium H2 cost-ratio correction if the H2 error is materially in COGS rather than Revenue.",
        ),
        Spec(
            "qbb60v18_cogs2023h2_down030",
            0.97,
            "Stronger H2 COGS reduction if the hidden public regime wants a large step down in late-2023 costs.",
        ),
    ]


def apply_spec(frame: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    out = add_segments(frame.copy())
    mask = out["period"].eq("2023H2")
    out.loc[mask, "COGS"] *= spec.cogs_scale_2023h2
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


def h2_summary(frame: pd.DataFrame) -> dict[str, float]:
    out = add_segments(frame.copy())
    h2 = out.loc[out["period"].eq("2023H2")]
    q3 = out.loc[out["Date"].dt.year.eq(2023) & out["Date"].dt.month.isin([7, 8, 9])]
    q4 = out.loc[out["Date"].dt.year.eq(2023) & out["Date"].dt.month.isin([10, 11, 12])]
    return {
        "rev_2023H2": h2["Revenue"].sum(),
        "cogs_2023H2": h2["COGS"].sum(),
        "ratio_2023H2": h2["COGS"].sum() / h2["Revenue"].sum(),
        "ratio_q3": q3["COGS"].sum() / q3["Revenue"].sum(),
        "ratio_q4": q4["COGS"].sum() / q4["Revenue"].sum(),
    }


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Quarantine Blackbox 60x V18 2023H2 COGS Down

Run directory: `{run_dir}`

## Status

This branch is **not clean**. It builds directly on the current blackbox best and public-leaderboard feedback.

Current anchor:

- `{CURRENT_BEST_FILE}` = `{CURRENT_BEST_SCORE}`

## Why This Batch Exists

- `2023H2 Revenue up` failed.
- `2023H2 Revenue down` also failed.
- `Q3/Q4` revenue reallocations also failed.
- The remaining plausible H2 axis is therefore `COGS`, not `Revenue`: current 2023H2 cost ratio is still high while revenue moves keep hurting.

## Candidate Manifest

{manifest.to_markdown(index=False)}
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_blackbox60_v18_2023h2_cogs_down_2026-04-24.md").write_text(report, encoding="utf-8")


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
        h2 = h2_summary(frame)
        rows.append(
            {
                "priority": priority,
                "filename": path.name,
                "thesis": spec.thesis,
                "cogs_scale_2023H2": spec.cogs_scale_2023h2,
                "mean_abs_rev_delta_vs_current": delta_rev.abs().mean(),
                "mean_abs_cogs_delta_vs_current": delta_cogs.abs().mean(),
                "movement": 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
                "revenue_total_ratio_vs_current": frame["Revenue"].sum() / current["Revenue"].sum(),
                "cogs_total_ratio_vs_current": frame["COGS"].sum() / current["COGS"].sum(),
                "ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
                "ratio_2023H1": prof.loc[prof["period"].eq("2023H1"), "ratio"].iloc[0],
                "ratio_2023H2": h2["ratio_2023H2"],
                "ratio_2024H1": prof.loc[prof["period"].eq("2024H1"), "ratio"].iloc[0],
                "ratio_q3": h2["ratio_q3"],
                "ratio_q4": h2["ratio_q4"],
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
