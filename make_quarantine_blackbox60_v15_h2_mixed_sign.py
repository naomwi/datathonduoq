from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_prior_v19 import add_segments, period_summary
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_blackbox60_v15_h2_mixed_sign"
CURRENT_BEST_FILE = "submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv"
CURRENT_BEST_SCORE = 662759.87577


@dataclass(frozen=True)
class Spec:
    name: str
    q3_scale: float = 1.0
    q4_scale: float = 1.0
    jul_aug_scale: float = 1.0
    thesis: str = ""


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def specs() -> list[Spec]:
    return [
        Spec(
            name="qbb60v15_h2split_q3up050_q4down025",
            q3_scale=1.050,
            q4_scale=0.975,
            thesis="Primary mixed-sign test: Q3 looks undercalled while Q4 looks overcalled on the current best anchor.",
        ),
        Spec(
            name="qbb60v15_h2split_q3up075_q4down050",
            q3_scale=1.075,
            q4_scale=0.950,
            thesis="Stronger mixed-sign continuation toward the sample-like H2 internal split.",
        ),
        Spec(
            name="qbb60v15_h2split_julaugup050_q4down025",
            jul_aug_scale=1.050,
            q4_scale=0.975,
            thesis="Localize the H2-up sign to Jul-Aug only, where both share and ratio look most misaligned.",
        ),
        Spec(
            name="qbb60v15_h2split_julaugup075_q4down050",
            jul_aug_scale=1.075,
            q4_scale=0.950,
            thesis="Aggressive Jul-Aug recovery with Q4 down, if the real error is concentrated in summer shoulder months.",
        ),
    ]


def apply_spec(frame: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    out = add_segments(frame.copy())
    mask_2023 = out["Date"].dt.year.eq(2023)
    mask_q3 = mask_2023 & out["Date"].dt.month.isin([7, 8, 9])
    mask_q4 = mask_2023 & out["Date"].dt.month.isin([10, 11, 12])
    mask_jul_aug = mask_2023 & out["Date"].dt.month.isin([7, 8])

    if spec.q3_scale != 1.0:
        out.loc[mask_q3, "Revenue"] *= spec.q3_scale
    if spec.q4_scale != 1.0:
        out.loc[mask_q4, "Revenue"] *= spec.q4_scale
    if spec.jul_aug_scale != 1.0:
        out.loc[mask_jul_aug, "Revenue"] *= spec.jul_aug_scale
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


def q3_q4_summary(frame: pd.DataFrame) -> dict[str, float]:
    out = add_segments(frame.copy())
    mask_2023 = out["Date"].dt.year.eq(2023)
    q3 = out.loc[mask_2023 & out["Date"].dt.month.isin([7, 8, 9])]
    q4 = out.loc[mask_2023 & out["Date"].dt.month.isin([10, 11, 12])]
    h2 = out.loc[mask_2023 & out["Date"].dt.month.isin([7, 8, 9, 10, 11, 12])]
    return {
        "rev_q3": q3["Revenue"].sum(),
        "rev_q4": q4["Revenue"].sum(),
        "ratio_q3": q3["COGS"].sum() / q3["Revenue"].sum(),
        "ratio_q4": q4["COGS"].sum() / q4["Revenue"].sum(),
        "q3_share_of_h2": q3["Revenue"].sum() / h2["Revenue"].sum(),
        "q4_share_of_h2": q4["Revenue"].sum() / h2["Revenue"].sum(),
    }


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Quarantine Blackbox 60x V15 H2 Mixed Sign

Run directory: `{run_dir}`

## Status

This branch is **not clean**. It builds directly on the current blackbox best and public-leaderboard feedback.

Current anchor:

- `{CURRENT_BEST_FILE}` = `{CURRENT_BEST_SCORE}`

## Why This Batch Exists

- `2023H2 +2.5%` failed.
- `2023H2 -2.5%` also failed.
- That strongly suggests `2023H2` is not a one-sign mistake.
- The current best still looks low in `Q3` but high in `Q4`, so the next real jump hypothesis is a mixed-sign H2 split: `Q3 up / Q4 down`.

## Candidate Manifest

{manifest.to_markdown(index=False)}
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_blackbox60_v15_h2_mixed_sign_2026-04-24.md").write_text(report, encoding="utf-8")


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
        h2 = q3_q4_summary(frame)
        rows.append(
            {
                "priority": priority,
                "filename": path.name,
                "thesis": spec.thesis,
                "q3_scale": spec.q3_scale,
                "q4_scale": spec.q4_scale,
                "jul_aug_scale": spec.jul_aug_scale,
                "mean_abs_rev_delta_vs_current": delta_rev.abs().mean(),
                "mean_abs_cogs_delta_vs_current": delta_cogs.abs().mean(),
                "movement": 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
                "revenue_total_ratio_vs_current": frame["Revenue"].sum() / current["Revenue"].sum(),
                "cogs_total_ratio_vs_current": frame["COGS"].sum() / current["COGS"].sum(),
                "ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
                "ratio_2023H1": prof.loc[prof["period"].eq("2023H1"), "ratio"].iloc[0],
                "ratio_2023H2": prof.loc[prof["period"].eq("2023H2"), "ratio"].iloc[0],
                "ratio_2024H1": prof.loc[prof["period"].eq("2024H1"), "ratio"].iloc[0],
                "rev_q3": h2["rev_q3"],
                "rev_q4": h2["rev_q4"],
                "ratio_q3": h2["ratio_q3"],
                "ratio_q4": h2["ratio_q4"],
                "q3_share_of_h2": h2["q3_share_of_h2"],
                "q4_share_of_h2": h2["q4_share_of_h2"],
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
