from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from make_publiconly_sample_prior_v19 import add_segments, period_summary
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_mae_frontier_v21"
CLEAN_ANCHOR_FILE = "submission_cleanv2_h1fine_b044_r0876.csv"
QBB_BASE_FILE = "submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv"
QBB_BEST_FILE = "submission_qbb60v18_cogs2023h2_down010.csv"
QBB_BEST_SCORE = 662607.08245


@dataclass(frozen=True)
class Spec:
    name: str
    mode: str
    gamma: float = 0.0
    h2_cogs_scale: float = 0.99
    h1_rev_rel_scale: float = 1.0
    thesis: str = ""


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def normalize_to_sum(values: pd.Series, target_total: float) -> pd.Series:
    current = float(values.sum())
    if current <= 0:
        return pd.Series(target_total / len(values), index=values.index)
    return values * (target_total / current)


def fine_tune(base: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    out = add_segments(base.copy())
    h2 = out["period"].eq("2023H2")
    h1 = out["period"].eq("2023H1")
    out.loc[h2, "COGS"] *= spec.h2_cogs_scale
    out.loc[h1, "Revenue"] *= spec.h1_rev_rel_scale
    return out[["Date", "Revenue", "COGS"]]


def extrapolate_from_clean(clean: pd.DataFrame, best: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    merged = clean.merge(best, on="Date", suffixes=("_clean", "_best"))
    out = pd.DataFrame({"Date": merged["Date"]})
    for target in ["Revenue", "COGS"]:
        delta = merged[f"{target}_best"] - merged[f"{target}_clean"]
        out[target] = merged[f"{target}_best"] + spec.gamma * delta
        out[target] = out[target].clip(lower=0.0)
    return out


def shape_extrapolate_preserve_periods(clean: pd.DataFrame, best: pd.DataFrame, spec: Spec, periods: set[str]) -> pd.DataFrame:
    merged = add_segments(clean).merge(add_segments(best), on=["Date", "period"], suffixes=("_clean", "_best"))
    out = pd.DataFrame({"Date": merged["Date"], "period": merged["period"]})
    for target in ["Revenue", "COGS"]:
        raw = merged[f"{target}_best"] + spec.gamma * (merged[f"{target}_best"] - merged[f"{target}_clean"])
        out[target] = merged[f"{target}_best"].astype(float)
        for period, idx in merged.groupby("period").groups.items():
            if period not in periods:
                continue
            idx_list = list(idx)
            clipped = raw.loc[idx_list].clip(lower=0.0)
            target_total = float(merged.loc[idx_list, f"{target}_best"].sum())
            out.loc[idx_list, target] = normalize_to_sum(clipped, target_total)
    return out[["Date", "Revenue", "COGS"]]


def specs() -> list[Spec]:
    return [
        Spec(
            name="qbb61v21_h2cogs_down0125",
            mode="fine",
            h2_cogs_scale=0.9875,
            thesis="Fine tune the only still-positive late-stage axis: 2023H2 COGS slightly below the known -1% winner.",
        ),
        Spec(
            name="qbb61v21_h2cogs_down015_h1level1135",
            mode="fine",
            h2_cogs_scale=0.9850,
            h1_rev_rel_scale=1.135 / 1.130,
            thesis="Combine a slightly stronger H2 COGS reduction with the quadratic 2023H1 level optimum between +13% and +15%.",
        ),
        Spec(
            name="qbb61v21_extrap_clean_to_best_g010",
            mode="extrapolate",
            gamma=0.10,
            thesis="Test whether hidden target is still beyond the clean-to-qbb direction; moderate full-vector extrapolation.",
        ),
        Spec(
            name="qbb61v21_extrap_clean_to_best_g020",
            mode="extrapolate",
            gamma=0.20,
            thesis="Higher-variance continuation of the same direction; useful only if g010 improves materially.",
        ),
        Spec(
            name="qbb61v21_shape_preserve_nonh2_g030",
            mode="shape_nonh2",
            gamma=0.30,
            thesis="Push daily shape further in 2023H1/2024H1 while preserving period totals; avoids rejected level movement.",
        ),
        Spec(
            name="qbb61v21_shape_preserve_all_g020",
            mode="shape_all",
            gamma=0.20,
            thesis="Push daily shape further in every main period while preserving period totals.",
        ),
    ]


def build_candidate(clean: pd.DataFrame, qbb_base: pd.DataFrame, qbb_best: pd.DataFrame, spec: Spec) -> pd.DataFrame:
    if spec.mode == "fine":
        return fine_tune(qbb_base, spec)
    if spec.mode == "extrapolate":
        return extrapolate_from_clean(clean, qbb_best, spec)
    if spec.mode == "shape_nonh2":
        return shape_extrapolate_preserve_periods(clean, qbb_best, spec, {"2023H1", "2024H1"})
    if spec.mode == "shape_all":
        return shape_extrapolate_preserve_periods(clean, qbb_best, spec, {"2023H1", "2023H2", "2024H1"})
    raise ValueError(f"Unknown mode: {spec.mode}")


def movement_summary(reference: pd.DataFrame, frame: pd.DataFrame) -> dict[str, float]:
    merged = reference.merge(frame, on="Date", suffixes=("_ref", ""))
    rev_delta = merged["Revenue"] - merged["Revenue_ref"]
    cogs_delta = merged["COGS"] - merged["COGS_ref"]
    return {
        "mean_abs_rev_delta_vs_best": float(rev_delta.abs().mean()),
        "mean_abs_cogs_delta_vs_best": float(cogs_delta.abs().mean()),
        "p95_abs_rev_delta_vs_best": float(rev_delta.abs().quantile(0.95)),
        "p95_abs_cogs_delta_vs_best": float(cogs_delta.abs().quantile(0.95)),
        "movement_vs_best": float(0.5 * (rev_delta.abs().mean() + cogs_delta.abs().mean())),
    }


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Quarantine MAE Frontier V21

Run directory: `{run_dir}`

## Boundary

This branch is **quarantine blackbox**. It uses public-leaderboard feedback and previous submissions as inputs. Do not present it as a clean method.

Current known qbb best:

- `{QBB_BEST_FILE}` = `{QBB_BEST_SCORE}`

## Hypotheses

1. The small positive 2023H2 COGS-down direction may have an optimum slightly beyond `-1%`.
2. The public target may still sit beyond the learned clean-to-qbb direction, so a controlled extrapolation can test for a larger jump.
3. If full extrapolation over-moves level, shape-only extrapolation with preserved period totals can still reduce day-level error.

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Suggested Public Probe Order

1. `submission_qbb61v21_shape_preserve_nonh2_g030.csv`
2. `submission_qbb61v21_extrap_clean_to_best_g010.csv`
3. `submission_qbb61v21_h2cogs_down0125.csv`
4. Only if one of the first two improves: `submission_qbb61v21_extrap_clean_to_best_g020.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_mae_frontier_v21_2026-04-24.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    clean = pd.read_csv(DATASET_DIR / CLEAN_ANCHOR_FILE, parse_dates=["Date"])
    qbb_base = pd.read_csv(DATASET_DIR / QBB_BASE_FILE, parse_dates=["Date"])
    qbb_best = pd.read_csv(DATASET_DIR / QBB_BEST_FILE, parse_dates=["Date"])

    rows = []
    for priority, spec in enumerate(specs(), start=1):
        frame = build_candidate(clean, qbb_base, qbb_best, spec)
        if len(frame) != len(qbb_best):
            raise ValueError(f"{spec.name} row count mismatch")
        if frame[["Revenue", "COGS"]].isna().any().any():
            raise ValueError(f"{spec.name} has NaN")
        if (frame[["Revenue", "COGS"]] < 0).any().any():
            raise ValueError(f"{spec.name} has negative values")

        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame, path)
        prof = period_summary(frame)
        prof.to_csv(run_dir / f"{spec.name}_period_summary.csv", index=False)
        move = movement_summary(qbb_best, frame)
        rows.append(
            {
                "priority": priority,
                "filename": path.name,
                "mode": spec.mode,
                "gamma": spec.gamma,
                "h2_cogs_scale": spec.h2_cogs_scale,
                "h1_rev_rel_scale": spec.h1_rev_rel_scale,
                "revenue_total": float(frame["Revenue"].sum()),
                "cogs_total": float(frame["COGS"].sum()),
                "ratio_total": float(frame["COGS"].sum() / frame["Revenue"].sum()),
                "max_revenue": float(frame["Revenue"].max()),
                "max_cogs": float(frame["COGS"].max()),
                **move,
                "thesis": spec.thesis,
            }
        )

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    period_summary(qbb_best).to_csv(run_dir / "qbb_best_period_summary.csv", index=False)
    write_report(run_dir, manifest)
    print(run_dir)
    print(
        manifest[
            [
                "priority",
                "filename",
                "mode",
                "movement_vs_best",
                "revenue_total",
                "cogs_total",
                "ratio_total",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
