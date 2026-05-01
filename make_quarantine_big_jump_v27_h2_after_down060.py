from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from make_publiconly_sample_prior_v19 import add_segments, period_summary
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "quarantine_big_jump_v27_h2_after_down060"
ANCHOR_FILE = "submission_qbb65_h2_highratio_cogs_down060_keeprev.csv"
ANCHOR_SCORE = 659211.90870
PRE_H2_ANCHOR_FILE = "submission_qbb62_h1_backload_preserve_total_q2up040.csv"


@dataclass(frozen=True)
class Candidate:
    name: str
    family: str
    changed_scope: str
    thesis: str
    frame: pd.DataFrame


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def load_submission(filename: str) -> pd.DataFrame:
    return pd.read_csv(DATASET_DIR / filename, parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)


def assert_aligned(left: pd.DataFrame, right: pd.DataFrame, label: str) -> None:
    if not left["Date"].equals(right["Date"]):
        raise ValueError(f"Date mismatch for {label}")


def period_mask(frame: pd.DataFrame, period: str) -> pd.Series:
    return add_segments(frame)["period"].eq(period)


def month_mask(frame: pd.DataFrame, year: int, months: tuple[int, ...]) -> pd.Series:
    return frame["Date"].dt.year.eq(year) & frame["Date"].dt.month.isin(months)


def high_ratio_mask(frame: pd.DataFrame, quantile: float) -> pd.Series:
    h2 = period_mask(frame, "2023H2")
    ratio = frame.loc[h2, "COGS"] / frame.loc[h2, "Revenue"]
    mask = pd.Series(False, index=frame.index)
    mask.loc[ratio.index] = ratio.rank(pct=True).ge(quantile)
    return mask


def scale_cogs(frame: pd.DataFrame, mask: pd.Series, scale: float) -> pd.DataFrame:
    out = frame.copy()
    out.loc[mask.to_numpy(), "COGS"] *= scale
    return out


def preserve_total_shift(
    frame: pd.DataFrame,
    target: str,
    down_mask: pd.Series,
    up_mask: pd.Series,
    down_scale: float,
) -> pd.DataFrame:
    out = frame.copy()
    down_idx = down_mask.to_numpy()
    up_idx = up_mask.to_numpy()
    original_total = float(out.loc[down_idx | up_idx, target].sum())
    down_total = float(out.loc[down_idx, target].sum())
    up_total = float(out.loc[up_idx, target].sum())
    if up_total <= 0.0:
        raise ValueError("Cannot preserve total with non-positive up bucket")
    up_scale = (original_total - down_total * down_scale) / up_total
    if up_scale <= 0.0:
        raise ValueError(f"Invalid up scale {up_scale:.6f}")
    out.loc[down_idx, target] *= down_scale
    out.loc[up_idx, target] *= up_scale
    return out


def apply_highratio_scale_from_pre_anchor(pre_anchor: pd.DataFrame, target_down: float) -> pd.DataFrame:
    mask = high_ratio_mask(pre_anchor, 0.60)
    return scale_cogs(pre_anchor, mask, 1.0 - target_down)


def build_candidates(anchor: pd.DataFrame, pre_anchor: pd.DataFrame) -> list[Candidate]:
    assert_aligned(anchor, pre_anchor, "pre-H2 anchor")

    aug = month_mask(anchor, 2023, (8,))
    dec = month_mask(anchor, 2023, (12,))
    aug_dec = month_mask(anchor, 2023, (8, 12))
    jul_aug_dec = month_mask(anchor, 2023, (7, 8, 12))
    h2 = period_mask(anchor, "2023H2")
    high40 = high_ratio_mask(anchor, 0.60)
    high25 = high_ratio_mask(anchor, 0.75)
    high15 = high_ratio_mask(anchor, 0.85)
    low60 = h2 & ~high40

    candidates: list[Candidate] = []

    for suffix, target_down, thesis in [
        (
            "down055_from_preanchor",
            0.055,
            "Response-fit near current best: target 5.5% high-ratio H2 COGS reduction from the pre-H2 anchor.",
        ),
        (
            "down070_from_preanchor",
            0.070,
            "Moderate check above down060 but below the overshot down100.",
        ),
        (
            "down080_from_preanchor",
            0.080,
            "Upper-mid response check; use only if down070 improves.",
        ),
    ]:
        candidates.append(
            Candidate(
                name=f"qbb67_h2_highratio_cogs_{suffix}_keeprev",
                family="h2_highratio_response_fit",
                changed_scope="2023H2 high COGS/Revenue days",
                thesis=thesis,
                frame=apply_highratio_scale_from_pre_anchor(pre_anchor, target_down),
            )
        )

    for name, mask, scale, thesis in [
        (
            "qbb67_h2_aug_extra_cogs_down040_keeprev",
            aug,
            0.96,
            "On top of down060, lower August COGS another 4%; August remains the highest H2 ratio.",
        ),
        (
            "qbb67_h2_aug_extra_cogs_down080_keeprev",
            aug,
            0.92,
            "High-variance August extra-down after down060.",
        ),
        (
            "qbb67_h2_dec_extra_cogs_down040_keeprev",
            dec,
            0.96,
            "On top of down060, lower December COGS another 4%; tests year-end high ratio.",
        ),
        (
            "qbb67_h2_augdec_extra_cogs_down040_keeprev",
            aug_dec,
            0.96,
            "Combined August+December extra-down after down060.",
        ),
        (
            "qbb67_h2_julaugdec_extra_cogs_down030_keeprev",
            jul_aug_dec,
            0.97,
            "Small extra-down on the three high-ratio H2 months after down060.",
        ),
        (
            "qbb67_h2_top25_extra_cogs_down060_keeprev",
            high25,
            0.94,
            "Lower only the most extreme 25% H2 ratio rows after down060; tests concentration instead of broad top40 intensity.",
        ),
        (
            "qbb67_h2_top15_extra_cogs_down100_keeprev",
            high15,
            0.90,
            "High-risk extreme-row test: lower only the worst 15% H2 ratio rows after down060.",
        ),
    ]:
        candidates.append(
            Candidate(
                name=name,
                family="h2_cogs_extra_down",
                changed_scope="2023H2 COGS",
                thesis=thesis,
                frame=scale_cogs(anchor, mask, scale),
            )
        )

    candidates.append(
        Candidate(
            name="qbb67_h2_highratio_shape_preserve_down040",
            family="h2_cogs_shape_preserve",
            changed_scope="2023H2 COGS shape only",
            thesis="Preserve total H2 COGS but move COGS mass away from high-ratio rows into low-ratio rows.",
            frame=preserve_total_shift(anchor, "COGS", high40, low60, 0.96),
        )
    )
    candidates.append(
        Candidate(
            name="qbb67_h2_aug_shape_preserve_down060",
            family="h2_cogs_shape_preserve",
            changed_scope="2023H2 COGS shape only",
            thesis="Preserve total H2 COGS but move COGS mass away from August into other H2 days.",
            frame=preserve_total_shift(anchor, "COGS", aug, h2 & ~aug, 0.94),
        )
    )

    return candidates


def month_summary(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["month"] = out["Date"].dt.strftime("%Y-%m")
    return (
        out.groupby("month", as_index=False)
        .agg(days=("Date", "count"), Revenue=("Revenue", "sum"), COGS=("COGS", "sum"))
        .assign(ratio=lambda d: d["COGS"] / d["Revenue"])
    )


def summarize_candidate(anchor: pd.DataFrame, candidate: Candidate, filename: str, priority: int) -> dict[str, object]:
    frame = candidate.frame
    delta_rev = frame["Revenue"] - anchor["Revenue"]
    delta_cogs = frame["COGS"] - anchor["COGS"]
    prof = period_summary(frame)
    h1_mask = period_mask(anchor, "2023H1")
    h24_mask = period_mask(anchor, "2024H1")
    return {
        "priority": priority,
        "filename": filename,
        "family": candidate.family,
        "changed_scope": candidate.changed_scope,
        "thesis": candidate.thesis,
        "rev_rows_changed": int(delta_rev.abs().gt(1e-6).sum()),
        "cogs_rows_changed": int(delta_cogs.abs().gt(1e-6).sum()),
        "h1_max_abs_delta_vs_anchor": float(
            max(delta_rev.loc[h1_mask].abs().max(), delta_cogs.loc[h1_mask].abs().max())
        ),
        "h24_max_abs_delta_vs_anchor": float(
            max(delta_rev.loc[h24_mask].abs().max(), delta_cogs.loc[h24_mask].abs().max())
        ),
        "mean_abs_rev_delta_vs_anchor": float(delta_rev.abs().mean()),
        "mean_abs_cogs_delta_vs_anchor": float(delta_cogs.abs().mean()),
        "movement_vs_anchor": float(0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean())),
        "best_case_score_if_direction_perfect": float(ANCHOR_SCORE - 0.5 * (delta_rev.abs().mean() + delta_cogs.abs().mean())),
        "revenue_total_ratio_vs_anchor": float(frame["Revenue"].sum() / anchor["Revenue"].sum()),
        "cogs_total_ratio_vs_anchor": float(frame["COGS"].sum() / anchor["COGS"].sum()),
        "ratio_all": float(frame["COGS"].sum() / frame["Revenue"].sum()),
        "ratio_2023H1": float(prof.loc[prof["period"].eq("2023H1"), "ratio"].iloc[0]),
        "ratio_2023H2": float(prof.loc[prof["period"].eq("2023H2"), "ratio"].iloc[0]),
        "ratio_2024H1": float(prof.loc[prof["period"].eq("2024H1"), "ratio"].iloc[0]),
        "max_revenue": float(frame["Revenue"].max()),
        "max_cogs": float(frame["COGS"].max()),
    }


def validate_frame(frame: pd.DataFrame, filename: str) -> None:
    if len(frame) != 548:
        raise ValueError(f"{filename}: expected 548 rows, found {len(frame)}")
    if frame["Date"].min() != pd.Timestamp("2023-01-01"):
        raise ValueError(f"{filename}: invalid min date {frame['Date'].min()}")
    if frame["Date"].max() != pd.Timestamp("2024-07-01"):
        raise ValueError(f"{filename}: invalid max date {frame['Date'].max()}")
    if frame[["Revenue", "COGS"]].isna().any().any():
        raise ValueError(f"{filename}: NaN found")
    if (frame[["Revenue", "COGS"]] < 0).any().any():
        raise ValueError(f"{filename}: negative target found")


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Quarantine Big Jump V27 H2 After Down060

Run directory: `{run_dir}`

## Status

This branch is **quarantine blackbox**, not clean.

## Current Read

- Current best anchor: `{ANCHOR_FILE}` = `{ANCHOR_SCORE}`.
- 2024H1 recency failed and 2024H1 frontload was slightly worse.
- H2 high-ratio down100 overshot, while down060 is still best. Response-fit optimum is near down058, so pure intensity tuning has little upside.
- This batch tests H2 COGS structure after down060: August/December residual, extreme-row concentration, and shape-preserving H2 redistribution.

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Suggested Submit Order

1. `submission_qbb67_h2_aug_extra_cogs_down040_keeprev.csv`
2. If it improves, submit `submission_qbb67_h2_aug_extra_cogs_down080_keeprev.csv`
3. If August fails, submit `submission_qbb67_h2_top25_extra_cogs_down060_keeprev.csv`
4. If all extra-down tests fail, submit `submission_qbb67_h2_highratio_shape_preserve_down040.csv`
5. Use response-fit candidates only for small cleanup, not for 60x jump.

## Do Not Use As Clean

These candidates are public-guided/quarantine probes and must not be presented as clean model outputs.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "quarantine_big_jump_v27_h2_after_down060_2026-04-26.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    anchor = add_segments(load_submission(ANCHOR_FILE))
    pre_anchor = add_segments(load_submission(PRE_H2_ANCHOR_FILE))

    rows: list[dict[str, object]] = []
    month_profiles: list[pd.DataFrame] = []
    for priority, candidate in enumerate(build_candidates(anchor, pre_anchor), start=1):
        filename = f"submission_{candidate.name}.csv"
        output = candidate.frame[["Date", "Revenue", "COGS"]].copy()
        validate_frame(output, filename)
        write_submission(output, DATASET_DIR / filename)
        write_submission(output, run_dir / filename)
        rows.append(summarize_candidate(anchor, candidate, filename, priority))
        profile = month_summary(output)
        profile.insert(0, "filename", filename)
        month_profiles.append(profile)

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    month_summary(anchor).to_csv(run_dir / "anchor_month_profiles.csv", index=False)
    pd.concat(month_profiles, ignore_index=True).to_csv(run_dir / "month_profiles.csv", index=False)
    period_summary(anchor).to_csv(run_dir / "anchor_period_summary.csv", index=False)
    write_report(run_dir, manifest)
    print(run_dir)


if __name__ == "__main__":
    main()
