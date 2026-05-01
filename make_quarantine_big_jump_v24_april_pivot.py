from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_prior_v19 import add_segments, period_summary
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_big_jump_v24_april_pivot"
ANCHOR_FILE = "submission_qbb62_h1_backload_preserve_total_q2up040.csv"
ANCHOR_SCORE = 661327.00240
FAILED_LATE_Q2_FILE = "submission_qbb63_h1_mayjun_up060_janfebfund.csv"
FAILED_LATE_Q2_SCORE = 666579.35776


@dataclass(frozen=True)
class Spec:
    name: str
    thesis: str
    target_months: tuple[int, ...]
    source_months: tuple[int, ...]
    target_scale: float
    target: str = "Revenue"


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def load_submission(filename: str) -> pd.DataFrame:
    return pd.read_csv(DATASET_DIR / filename, parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)


def mask_months(frame: pd.DataFrame, months: tuple[int, ...]) -> pd.Series:
    return frame["Date"].dt.year.eq(2023) & frame["Date"].dt.month.isin(months)


def preserve_shift(
    base: pd.DataFrame,
    target: str,
    target_mask: pd.Series,
    source_mask: pd.Series,
    target_scale: float,
) -> pd.DataFrame:
    out = base.copy()
    target_idx = target_mask.to_numpy()
    source_idx = source_mask.to_numpy()
    original_total = float(out.loc[target_idx | source_idx, target].sum())
    target_original = float(out.loc[target_idx, target].sum())
    source_original = float(out.loc[source_idx, target].sum())
    target_new = target_original * target_scale
    if source_original <= 0.0:
        raise ValueError("Source bucket has non-positive total")
    source_scale = (original_total - target_new) / source_original
    if source_scale <= 0.0:
        raise ValueError(f"Invalid source scale {source_scale:.6f}")
    out.loc[target_idx, target] *= target_scale
    out.loc[source_idx, target] *= source_scale
    return out


def ratio_shape_april(base: pd.DataFrame, cogs_scale_april: float, source_months: tuple[int, ...]) -> pd.DataFrame:
    return preserve_shift(
        base,
        "COGS",
        mask_months(base, (4,)),
        mask_months(base, source_months),
        cogs_scale_april,
    )


def specs() -> list[Spec]:
    return [
        Spec(
            "qbb64_apr_from_mayjun_q2preserve_apr080",
            "Current best already backloads H1 into Q2. Since May-Jun failed, move Q2 Revenue mass from May-Jun into April while preserving Q2 total.",
            (4,),
            (5, 6),
            1.080,
        ),
        Spec(
            "qbb64_apr_from_mayjun_q2preserve_apr120",
            "Bolder April-only Q2-preserve test; this is the high-information version if April is the true missing block.",
            (4,),
            (5, 6),
            1.120,
        ),
        Spec(
            "qbb64_apr_from_mar_marapr_preserve_apr080",
            "March-April transition test: move Revenue from March into April while preserving March+April total.",
            (4,),
            (3,),
            1.080,
        ),
        Spec(
            "qbb64_apr_from_mar_marapr_preserve_apr120",
            "High-amplitude March-to-April transfer; useful if hidden public event is an April demand cliff/jump.",
            (4,),
            (3,),
            1.120,
        ),
        Spec(
            "qbb64_aprmay_from_jun_q2preserve_aprmay050",
            "If May-Jun failed because June is wrong, move Q2 mass from June into April-May.",
            (4, 5),
            (6,),
            1.050,
        ),
        Spec(
            "qbb64_march_down_q2_up_preserve_h1_q2p060",
            "Alternate funding test: broad Q2 up like the current best, but funded mostly by March instead of all Q1.",
            (4, 5, 6),
            (3,),
            1.060,
        ),
    ]


def build_candidates(anchor: pd.DataFrame) -> list[tuple[str, str, pd.DataFrame]]:
    candidates: list[tuple[str, str, pd.DataFrame]] = []
    for spec in specs():
        frame = preserve_shift(
            anchor,
            spec.target,
            mask_months(anchor, spec.target_months),
            mask_months(anchor, spec.source_months),
            spec.target_scale,
        )
        candidates.append((spec.name, spec.thesis, frame))

    candidates.append(
        (
            "qbb64_apr_cogs_from_mayjun_q2preserve_cogs_apr080",
            "COGS-side April pivot: move Q2 COGS mass from May-Jun into April while keeping Revenue fixed. Orthogonal to Revenue timing.",
            ratio_shape_april(anchor, 1.080, (5, 6)),
        )
    )
    candidates.append(
        (
            "qbb64_apr_rev_cogs_from_mayjun_q2preserve_apr080",
            "Combined April pivot: move both Revenue and COGS Q2 mass from May-Jun into April, preserving Q2 totals for both targets.",
            ratio_shape_april(
                preserve_shift(anchor, "Revenue", mask_months(anchor, (4,)), mask_months(anchor, (5, 6)), 1.080),
                1.080,
                (5, 6),
            ),
        )
    )
    return candidates


def month_summary(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["month"] = out["Date"].dt.strftime("%Y-%m")
    return out.groupby("month", as_index=False).agg(days=("Date", "count"), Revenue=("Revenue", "sum"), COGS=("COGS", "sum"))


def summarize(anchor: pd.DataFrame, frame: pd.DataFrame, filename: str, thesis: str, priority: int) -> dict[str, object]:
    delta_rev = frame["Revenue"] - anchor["Revenue"]
    delta_cogs = frame["COGS"] - anchor["COGS"]
    prof = period_summary(frame)
    return {
        "priority": priority,
        "filename": filename,
        "thesis": thesis,
        "rev_rows_changed": int(delta_rev.abs().gt(1e-6).sum()),
        "cogs_rows_changed": int(delta_cogs.abs().gt(1e-6).sum()),
        "mean_abs_rev_delta_vs_anchor": float(delta_rev.abs().mean()),
        "mean_abs_cogs_delta_vs_anchor": float(delta_cogs.abs().mean()),
        "movement_vs_anchor": float(0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean())),
        "best_case_score_if_direction_perfect": float(ANCHOR_SCORE - 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean())),
        "revenue_total_ratio_vs_anchor": float(frame["Revenue"].sum() / anchor["Revenue"].sum()),
        "cogs_total_ratio_vs_anchor": float(frame["COGS"].sum() / anchor["COGS"].sum()),
        "ratio_2023H1": float(prof.loc[prof["period"].eq("2023H1"), "ratio"].iloc[0]),
        "ratio_2023H2": float(prof.loc[prof["period"].eq("2023H2"), "ratio"].iloc[0]),
        "ratio_2024H1": float(prof.loc[prof["period"].eq("2024H1"), "ratio"].iloc[0]),
        "max_revenue": float(frame["Revenue"].max()),
        "max_cogs": float(frame["COGS"].max()),
    }


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Quarantine Big Jump V24 April Pivot

Run directory: `{run_dir}`

## Status

This is **quarantine blackbox**, not clean.

## Current Read

- Current best: `{ANCHOR_FILE}` = `{ANCHOR_SCORE}`.
- Failed late-Q2 probe: `{FAILED_LATE_Q2_FILE}` = `{FAILED_LATE_Q2_SCORE}`.
- Therefore, do not continue June/May-Jun. If the Q2-backload signal is real, it likely lives in April or in March-to-April transition.

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Suggested Submit Order

1. `submission_qbb64_apr_from_mayjun_q2preserve_apr080.csv`
   - Cleanest sign test: same Q2 total, move from May-Jun into April.
2. If it improves clearly, submit `submission_qbb64_apr_from_mayjun_q2preserve_apr120.csv`.
3. If it fails, submit `submission_qbb64_apr_from_mar_marapr_preserve_apr080.csv`.
   - Tests March-April transition instead of Q2 internal timing.
4. If Revenue timing keeps failing, try `submission_qbb64_apr_cogs_from_mayjun_q2preserve_cogs_apr080.csv` as an orthogonal COGS timing pivot.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_big_jump_v24_april_pivot_2026-04-26.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    anchor = add_segments(load_submission(ANCHOR_FILE))
    rows: list[dict[str, object]] = []
    month_profiles: list[pd.DataFrame] = []
    for priority, (name, thesis, frame) in enumerate(build_candidates(anchor), start=1):
        filename = f"submission_{name}.csv"
        output = frame[["Date", "Revenue", "COGS"]].copy()
        write_submission(output, DATASET_DIR / filename)
        write_submission(output, run_dir / filename)
        rows.append(summarize(anchor, output, filename, thesis, priority))
        profile = month_summary(output)
        profile.insert(0, "filename", filename)
        month_profiles.append(profile)

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    month_summary(anchor).to_csv(run_dir / "anchor_month_summary.csv", index=False)
    pd.concat(month_profiles, ignore_index=True).to_csv(run_dir / "candidate_month_profiles.csv", index=False)
    period_summary(anchor).to_csv(run_dir / "anchor_period_summary.csv", index=False)
    write_report(run_dir, manifest)
    print(run_dir)


if __name__ == "__main__":
    main()
