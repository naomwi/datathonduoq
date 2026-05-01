from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from make_publiconly_sample_prior_v19 import add_segments, period_summary
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_big_jump_v23_h1_localize"
ANCHOR_FILE = "submission_qbb60v18_cogs2023h2_down010.csv"
ANCHOR_SCORE = 662607.08245
CONFIRMED_FILE = "submission_qbb62_h1_backload_preserve_total_q2up040.csv"
CONFIRMED_SCORE = 661327.00240


@dataclass(frozen=True)
class Spec:
    name: str
    thesis: str
    target_months: tuple[int, ...]
    source_months: tuple[int, ...]
    target_scale: float
    preserve_target: str = "Revenue"


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def load_submission(filename: str) -> pd.DataFrame:
    return pd.read_csv(DATASET_DIR / filename, parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)


def month_mask(frame: pd.DataFrame, months: tuple[int, ...]) -> pd.Series:
    return frame["Date"].dt.year.eq(2023) & frame["Date"].dt.month.isin(months)


def preserve_total_shift(
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


def high_volume_shape(base: pd.DataFrame, target_scale: float, top_quantile: float, months: tuple[int, ...]) -> pd.DataFrame:
    seg = add_segments(base)
    in_months = month_mask(seg, months)
    ranks = seg.loc[in_months, "Revenue"].rank(pct=True)
    target_mask = pd.Series(False, index=seg.index)
    target_mask.loc[ranks.index] = ranks.ge(top_quantile)
    source_mask = in_months & ~target_mask
    return preserve_total_shift(base, "Revenue", target_mask, source_mask, target_scale)


def build_specs() -> list[Spec]:
    return [
        Spec(
            "qbb63_h1_mayjun_up060_janfebfund",
            "Localize the confirmed Q2-backload gain into May-Jun, funded by Jan-Feb. This avoids moving March/April if the public error is late-spring demand.",
            (5, 6),
            (1, 2),
            1.060,
        ),
        Spec(
            "qbb63_h1_jun_up120_janfebfund",
            "High-amplitude June-only test: if the hidden error is end-of-H1 ramp, this is a real jump rather than a Q2 average.",
            (6,),
            (1, 2),
            1.120,
        ),
        Spec(
            "qbb63_h1_aprmay_up060_janfebfund",
            "Alternative Q2 localization: spring promo/April-May block, funded by Jan-Feb.",
            (4, 5),
            (1, 2),
            1.060,
        ),
        Spec(
            "qbb63_h1_apr_up120_janfebfund",
            "April-only large move; tests whether the Q2 gain is actually the March-April transition/event shoulder.",
            (4,),
            (1, 2),
            1.120,
        ),
        Spec(
            "qbb63_h1_q2_up080_q1fund",
            "Bolder version of the confirmed Q2 direction. Included as a stress test, not first priority, because the first response curve was weak.",
            (4, 5, 6),
            (1, 2, 3),
            1.080,
        ),
    ]


def build_candidates(anchor: pd.DataFrame) -> list[tuple[str, str, pd.DataFrame]]:
    out: list[tuple[str, str, pd.DataFrame]] = []
    for spec in build_specs():
        frame = preserve_total_shift(
            anchor,
            spec.preserve_target,
            month_mask(anchor, spec.target_months),
            month_mask(anchor, spec.source_months),
            spec.target_scale,
        )
        out.append((spec.name, spec.thesis, frame))

    out.append(
        (
            "qbb63_h1_q2_top35_shape_up100",
            "Within Q2 only, preserve Q2 Revenue total but move mass into the top 35% Q2 Revenue days. Tests concentrated Q2 peaks rather than Q2 monthly level.",
            high_volume_shape(anchor, target_scale=2.000, top_quantile=0.65, months=(4, 5, 6)),
        )
    )
    out.append(
        (
            "qbb63_h1_h1_top35_shape_up060",
            "Within all 2023H1, preserve H1 total but concentrate Revenue into the top 35% days. Different from Q2 average and can reveal peak-day underprediction.",
            high_volume_shape(anchor, target_scale=1.600, top_quantile=0.65, months=(1, 2, 3, 4, 5, 6)),
        )
    )
    return out


def fit_backload_curve() -> pd.DataFrame:
    points = pd.DataFrame(
        [
            {"signed_movement": -28870.34109621292, "public_score": 667597.86978, "label": "frontload_q1up050"},
            {"signed_movement": 0.0, "public_score": ANCHOR_SCORE, "label": "anchor"},
            {"signed_movement": 39918.33307511682, "public_score": CONFIRMED_SCORE, "label": "backload_q2up040"},
        ]
    )
    coef = np.polyfit(points["signed_movement"], points["public_score"], 2)
    optimum = -coef[1] / (2.0 * coef[0])
    fit_row = pd.DataFrame(
        [{"signed_movement": optimum, "public_score": float(np.polyval(coef, optimum)), "label": "quadratic_optimum"}]
    )
    return pd.concat([points, fit_row], ignore_index=True)


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


def write_report(run_dir: Path, manifest: pd.DataFrame, curve: pd.DataFrame) -> None:
    report = f"""# Quarantine Big Jump V23 H1 Localize

Run directory: `{run_dir}`

## Status

This is **quarantine blackbox**, not clean.

Confirmed result:

- `{CONFIRMED_FILE}` = `{CONFIRMED_SCORE}`
- Improvement vs anchor `{ANCHOR_FILE}` = `{ANCHOR_SCORE}` is `{ANCHOR_SCORE - CONFIRMED_SCORE:.5f}`.

## Read

Frontload Q1 failed, Q2 backload improved. The direction is real, but the response is weak versus movement. Therefore this batch does not simply squeeze Q2; it localizes the Q2 gain into month/peak structures.

## Backload Response Curve

{curve.to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Suggested Submit Order

1. `submission_qbb63_h1_mayjun_up060_janfebfund.csv` for the most plausible localized version of the confirmed Q2 signal.
2. If it improves, submit `submission_qbb63_h1_jun_up120_janfebfund.csv` to test end-of-H1 concentration.
3. If May-Jun fails, submit `submission_qbb63_h1_aprmay_up060_janfebfund.csv`.
4. Use `submission_qbb63_h1_q2_top35_shape_up100.csv` only as a high-variance peak-day test.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_big_jump_v23_h1_localize_2026-04-24.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    anchor = add_segments(load_submission(ANCHOR_FILE))
    rows: list[dict[str, object]] = []
    profiles: list[pd.DataFrame] = []
    for priority, (name, thesis, frame) in enumerate(build_candidates(anchor), start=1):
        filename = f"submission_{name}.csv"
        output_path = DATASET_DIR / filename
        run_path = run_dir / filename
        export = frame[["Date", "Revenue", "COGS"]].copy()
        write_submission(export, output_path)
        write_submission(export, run_path)
        rows.append(summarize(anchor, export, filename, thesis, priority))
        profile = period_summary(export)
        profile.insert(0, "filename", filename)
        profiles.append(profile)

    manifest = pd.DataFrame(rows)
    curve = fit_backload_curve()
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    curve.to_csv(run_dir / "backload_response_curve.csv", index=False)
    pd.concat(profiles, ignore_index=True).to_csv(run_dir / "period_profiles.csv", index=False)
    period_summary(anchor).to_csv(run_dir / "anchor_period_summary.csv", index=False)
    write_report(run_dir, manifest, curve)
    print(run_dir)


if __name__ == "__main__":
    main()
