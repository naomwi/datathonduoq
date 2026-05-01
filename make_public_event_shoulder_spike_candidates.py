from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json


RUN_PREFIX = "public_event_shoulder_spike_candidates"
SOURCE_RUN_DIR = Path("logs/20260421_181237_tabpfn_api_optimized_sprint")
DATASET_DIR = Path("dataset")
BASE_PATH = DATASET_DIR / "submission_tabpfn_promo_windowmix_v1.csv"


def mask_between_month_day(dates: pd.Series, start: str, end: str) -> pd.Series:
    md = dates.dt.strftime("%m-%d")
    if start <= end:
        return md.between(start, end)
    return md.between(start, "12-31") | md.between("01-01", end)


def union_masks(masks: list[pd.Series]) -> pd.Series:
    out = masks[0].copy()
    for mask in masks[1:]:
        out |= mask
    return out


def main_promo_mask(dates: pd.Series) -> pd.Series:
    return union_masks(
        [
            mask_between_month_day(dates, "03-18", "04-17"),
            mask_between_month_day(dates, "06-23", "07-22"),
            mask_between_month_day(dates, "08-30", "10-02"),
            mask_between_month_day(dates, "11-18", "01-02"),
        ]
    )


def shoulder_masks(dates: pd.Series) -> dict[str, pd.Series]:
    return {
        "spring_pre7": mask_between_month_day(dates, "03-11", "03-17"),
        "spring_post7": mask_between_month_day(dates, "04-18", "04-24"),
        "midyear_pre7": mask_between_month_day(dates, "06-16", "06-22"),
        "midyear_post7": mask_between_month_day(dates, "07-23", "07-29"),
        "fall_pre7": mask_between_month_day(dates, "08-23", "08-29"),
        "fall_post7": mask_between_month_day(dates, "10-03", "10-09"),
    }


def odd_extra_masks(dates: pd.Series) -> dict[str, pd.Series]:
    return {
        "rural": mask_between_month_day(dates, "01-30", "03-01"),
        "urban": mask_between_month_day(dates, "07-30", "09-02"),
    }


def summarize_residuals(oof: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    oof = oof.copy()
    dates = pd.to_datetime(oof["Date"])
    oof["year"] = dates.dt.year
    oof["month_day"] = dates.dt.strftime("%m-%d")
    oof["rev_ratio_error"] = oof["Revenue"] / oof["Revenue_pred"].replace(0.0, np.nan) - 1.0
    oof["rev_log_error"] = np.log1p(oof["Revenue"].clip(lower=0.0)) - np.log1p(oof["Revenue_pred"].clip(lower=0.0))

    masks = {"main_promo": main_promo_mask(dates)}
    masks.update(shoulder_masks(dates))
    masks.update({f"extra_{name}": mask for name, mask in odd_extra_masks(dates).items()})
    rows = []
    for name, mask in masks.items():
        sub = oof.loc[mask]
        rows.append(
            {
                "segment": name,
                "rows": int(mask.sum()),
                "ratio_error_mean": float(sub["rev_ratio_error"].mean()),
                "ratio_error_median": float(sub["rev_ratio_error"].median()),
                "log_error_mean": float(sub["rev_log_error"].mean()),
                "log_error_median": float(sub["rev_log_error"].median()),
                "abs_error_mean": float((sub["Revenue"] - sub["Revenue_pred"]).abs().mean()),
            }
        )

    excluded = main_promo_mask(dates) | odd_extra_masks(dates)["rural"] | odd_extra_masks(dates)["urban"]
    candidates = oof.loc[~excluded].copy()
    md_year = (
        candidates.groupby(["month_day", "year"])["rev_ratio_error"]
        .median()
        .reset_index()
        .pivot(index="month_day", columns="year", values="rev_ratio_error")
    )
    year_cols = [col for col in [2020, 2021, 2022] if col in md_year.columns]
    md_year["min_recent"] = md_year[[col for col in [2021, 2022] if col in md_year.columns]].min(axis=1)
    md_year["median_all"] = md_year[year_cols].median(axis=1)
    md_year["score"] = md_year["min_recent"].fillna(-999) + 0.5 * md_year["median_all"].fillna(-999)
    positive = md_year.loc[md_year["min_recent"] > 0.03].sort_values("score", ascending=False)
    top10 = positive.head(10).index.tolist()
    top20 = positive.head(20).index.tolist()
    return pd.DataFrame(rows), top10, top20


def export_candidate(
    run_dir: Path,
    base: pd.DataFrame,
    candidate_id: str,
    changes: list[tuple[str, pd.Series, float]],
) -> dict[str, object]:
    frame = base.copy()
    dates = pd.to_datetime(frame["Date"])
    applied = pd.Series(False, index=frame.index)
    for _, mask, pct in changes:
        frame.loc[mask, "Revenue"] *= 1.0 + pct
        applied |= mask

    out = frame.copy()
    out["Date"] = dates.dt.strftime("%Y-%m-%d")
    dataset_path = DATASET_DIR / f"submission_{candidate_id}.csv"
    run_path = run_dir / f"submission_{candidate_id}.csv"
    out.to_csv(dataset_path, index=False)
    out.to_csv(run_path, index=False)
    delta = frame["Revenue"] - base["Revenue"]
    row: dict[str, object] = {
        "candidate_id": candidate_id,
        "dataset_path": str(dataset_path),
        "run_path": str(run_path),
        "changed_rows": int(applied.sum()),
        "revenue_total_ratio_vs_base": float(frame["Revenue"].sum() / base["Revenue"].sum()),
        "revenue_delta_mean": float(delta.mean()),
        "revenue_delta_abs_mean": float(delta.abs().mean()),
        "revenue_delta_max_abs": float(delta.abs().max()),
    }
    for label, mask, pct in changes:
        row[f"{label}_rows"] = int(mask.sum())
        row[f"{label}_pct"] = pct
    return row


def write_report(run_dir: Path, residual_summary: pd.DataFrame, top10: list[str], top20: list[str], summary: pd.DataFrame) -> None:
    with (run_dir / "report.md").open("w", encoding="utf-8") as f:
        f.write("# Public Event Shoulder / Spike Candidates\n\n")
        f.write("Generated from OOF residuals around the current best public base. Main promo windows and odd extra promo windows are excluded from spike discovery.\n\n")
        f.write("## Residual Segment Summary\n")
        f.write(residual_summary.to_markdown(index=False))
        f.write("\n\n")
        f.write(f"Top10 spike month-days: `{', '.join(top10)}`\n\n")
        f.write(f"Top20 spike month-days: `{', '.join(top20)}`\n\n")
        f.write("## Candidate Summary\n")
        f.write(summary.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    base = pd.read_csv(BASE_PATH, parse_dates=["Date"])
    dates = pd.to_datetime(base["Date"])
    oof = pd.read_csv(SOURCE_RUN_DIR / "anchor_oof_table.csv", parse_dates=["Date"])

    residual_summary, top10, top20 = summarize_residuals(oof)
    residual_summary.to_csv(run_dir / "residual_segment_summary.csv", index=False)

    shoulders = shoulder_masks(dates)
    spring_mid_fall_all = union_masks(list(shoulders.values()))
    spring_mid_fall_pre = union_masks([shoulders["spring_pre7"], shoulders["midyear_pre7"], shoulders["fall_pre7"]])
    spring_mid_fall_post = union_masks([shoulders["spring_post7"], shoulders["midyear_post7"], shoulders["fall_post7"]])
    mid_fall_all = union_masks([shoulders["midyear_pre7"], shoulders["midyear_post7"], shoulders["fall_pre7"], shoulders["fall_post7"]])
    positive_shoulder_core = union_masks(
        [
            shoulders["spring_pre7"],
            shoulders["spring_post7"],
            shoulders["midyear_post7"],
            shoulders["fall_pre7"],
        ]
    )
    spring_and_fall_pre = union_masks([shoulders["spring_pre7"], shoulders["spring_post7"], shoulders["fall_pre7"]])

    md = dates.dt.strftime("%m-%d")
    spike10 = md.isin(top10) & ~main_promo_mask(dates)
    spike20 = md.isin(top20) & ~main_promo_mask(dates)

    specs: list[tuple[str, list[tuple[str, pd.Series, float]]]] = [
        ("public_event_shoulder_smf_prepost7_up4", [("shoulder_smf", spring_mid_fall_all, 0.04)]),
        (
            "public_event_shoulder_smf_pre5_post3",
            [("shoulder_pre", spring_mid_fall_pre, 0.05), ("shoulder_post", spring_mid_fall_post, 0.03)],
        ),
        ("public_event_shoulder_midfall_prepost7_up5", [("shoulder_midfall", mid_fall_all, 0.05)]),
        ("public_event_posshoulder_core_up5", [("pos_shoulder_core", positive_shoulder_core, 0.05)]),
        ("public_event_spring_fallpre_up6", [("spring_fallpre", spring_and_fall_pre, 0.06)]),
        ("public_event_fallpre_only_up8", [("fall_pre", shoulders["fall_pre7"], 0.08)]),
        ("public_event_spike_md_top10_up6", [("spike_top10", spike10, 0.06)]),
        ("public_event_spike_md_top10_up8", [("spike_top10", spike10, 0.08)]),
        ("public_event_spike_md_top20_up4", [("spike_top20", spike20, 0.04)]),
    ]

    rows = [export_candidate(run_dir, base, candidate_id, changes) for candidate_id, changes in specs]
    summary = pd.DataFrame(rows)
    summary.to_csv(run_dir / "summary.csv", index=False)
    write_json(
        run_dir / "config.json",
        {
            "base_path": str(BASE_PATH),
            "source_run_dir": str(SOURCE_RUN_DIR),
            "current_best_public": {"submission_tabpfn_promo_windowmix_v1.csv": 883183.19507},
            "top10_spike_month_days": top10,
            "top20_spike_month_days": top20,
        },
    )
    write_report(run_dir, residual_summary, top10, top20, summary)
    logger.info("Saved %s event shoulder/spike candidates to %s", len(summary), run_dir)
    print(residual_summary.to_string(index=False))
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
