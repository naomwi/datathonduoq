from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_prior_v19 import add_segments, period_summary
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_blackbox60_v17_jul_aug_only"
CURRENT_BEST_FILE = "submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv"
CURRENT_BEST_SCORE = 662759.87577


@dataclass(frozen=True)
class Spec:
    name: str
    jul_scale: float = 1.0
    aug_scale: float = 1.0
    sep_scale: float = 1.0
    thesis: str = ""


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def specs() -> list[Spec]:
    return [
        Spec(
            name="qbb60v17_augup050_only",
            aug_scale=1.050,
            thesis="August has the single highest ratio distortion in H2; test whether the missing signal is mostly August only.",
        ),
        Spec(
            name="qbb60v17_augup075_only",
            aug_scale=1.075,
            thesis="If August is the main miss, a stronger one-month correction should show a clearer public jump.",
        ),
        Spec(
            name="qbb60v17_julup050_only",
            jul_scale=1.050,
            thesis="Check whether July is the more important undercalled month instead of August.",
        ),
        Spec(
            name="qbb60v17_augup050_sepdown025",
            aug_scale=1.050,
            sep_scale=0.975,
            thesis="Reallocate within Q3: lift August but trim September, since broad Q3-up likely overmoved September.",
        ),
    ]


def apply_spec(frame: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    out = add_segments(frame.copy())
    mask_2023 = out["Date"].dt.year.eq(2023)
    if spec.jul_scale != 1.0:
        out.loc[mask_2023 & out["Date"].dt.month.eq(7), "Revenue"] *= spec.jul_scale
    if spec.aug_scale != 1.0:
        out.loc[mask_2023 & out["Date"].dt.month.eq(8), "Revenue"] *= spec.aug_scale
    if spec.sep_scale != 1.0:
        out.loc[mask_2023 & out["Date"].dt.month.eq(9), "Revenue"] *= spec.sep_scale
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


def month_summary(frame: pd.DataFrame) -> dict[str, float]:
    out = add_segments(frame.copy())
    mask_2023 = out["Date"].dt.year.eq(2023)
    result: dict[str, float] = {}
    for month, label in [(7, "jul"), (8, "aug"), (9, "sep")]:
        sub = out.loc[mask_2023 & out["Date"].dt.month.eq(month)]
        result[f"rev_{label}"] = sub["Revenue"].sum()
        result[f"ratio_{label}"] = sub["COGS"].sum() / sub["Revenue"].sum()
    q3 = out.loc[mask_2023 & out["Date"].dt.month.isin([7, 8, 9])]
    result["rev_q3"] = q3["Revenue"].sum()
    result["ratio_q3"] = q3["COGS"].sum() / q3["Revenue"].sum()
    return result


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Quarantine Blackbox 60x V17 Jul-Aug Only

Run directory: `{run_dir}`

## Status

This branch is **not clean**. It builds directly on the current blackbox best and public-leaderboard feedback.

Current anchor:

- `{CURRENT_BEST_FILE}` = `{CURRENT_BEST_SCORE}`

## Why This Batch Exists

- Broad `Q3 up / Q4 down` failed.
- `Jul-Aug up / Q4 down` also failed harder, which makes the `Q4 down` leg suspect.
- The next branch drops `Q4 down` entirely and isolates `Jul`, `Aug`, and `Sep` inside `Q3`.

## Candidate Manifest

{manifest.to_markdown(index=False)}
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_blackbox60_v17_jul_aug_only_2026-04-24.md").write_text(report, encoding="utf-8")


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
        months = month_summary(frame)
        rows.append(
            {
                "priority": priority,
                "filename": path.name,
                "thesis": spec.thesis,
                "jul_scale": spec.jul_scale,
                "aug_scale": spec.aug_scale,
                "sep_scale": spec.sep_scale,
                "mean_abs_rev_delta_vs_current": delta_rev.abs().mean(),
                "mean_abs_cogs_delta_vs_current": delta_cogs.abs().mean(),
                "movement": 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean()),
                "revenue_total_ratio_vs_current": frame["Revenue"].sum() / current["Revenue"].sum(),
                "cogs_total_ratio_vs_current": frame["COGS"].sum() / current["COGS"].sum(),
                "ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
                "ratio_2023H1": prof.loc[prof["period"].eq("2023H1"), "ratio"].iloc[0],
                "ratio_2023H2": prof.loc[prof["period"].eq("2023H2"), "ratio"].iloc[0],
                "ratio_2024H1": prof.loc[prof["period"].eq("2024H1"), "ratio"].iloc[0],
                **months,
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
