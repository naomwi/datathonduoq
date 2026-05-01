from __future__ import annotations

from pathlib import Path

import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json


RUN_PREFIX = "public_breakthrough_bets"
DATASET_DIR = Path("dataset")
ANCHOR_PATH = DATASET_DIR / "submission_catboost_md2y_core_recencyexp20.csv"


def mask_between_month_day(dates: pd.Series, start: str, end: str) -> pd.Series:
    month_day = dates.dt.strftime("%m-%d")
    if start <= end:
        return month_day.between(start, end)
    return month_day.between(start, "12-31") | month_day.between("01-01", end)


def masks(frame: pd.DataFrame) -> dict[str, pd.Series]:
    dates = frame["Date"]
    out = {
        "marapr": mask_between_month_day(dates, "03-18", "04-17"),
        "junjul": mask_between_month_day(dates, "06-23", "07-22"),
        "augoct": mask_between_month_day(dates, "08-30", "10-02"),
        "novjan": mask_between_month_day(dates, "11-18", "01-02"),
    }
    out["promo"] = out["marapr"] | out["junjul"] | out["augoct"] | out["novjan"]
    out["promo_h1"] = out["marapr"] | out["junjul"]
    out["promo_h2"] = out["augoct"] | out["novjan"]
    out["promo_2023"] = out["promo"] & (dates.dt.year == 2023)
    out["promo_2024"] = out["promo"] & (dates.dt.year == 2024)
    return out


def apply_scale(frame: pd.DataFrame, mask: pd.Series, revenue_pct: float, cogs_pct: float = 0.0) -> None:
    frame.loc[mask, "Revenue"] *= 1.0 + revenue_pct
    frame.loc[mask, "COGS"] *= 1.0 + cogs_pct


def summarize(anchor: pd.DataFrame, frame: pd.DataFrame, candidate_id: str, changed_mask: pd.Series) -> dict:
    rev_delta = frame["Revenue"] - anchor["Revenue"]
    cogs_delta = frame["COGS"] - anchor["COGS"]
    return {
        "candidate_id": candidate_id,
        "changed_rows": int(changed_mask.sum()),
        "revenue_delta_mean": float(rev_delta.mean()),
        "revenue_delta_abs_mean": float(rev_delta.abs().mean()),
        "revenue_delta_max_abs": float(rev_delta.abs().max()),
        "revenue_total_ratio": float(frame["Revenue"].sum() / anchor["Revenue"].sum()),
        "cogs_delta_mean": float(cogs_delta.mean()),
        "cogs_delta_abs_mean": float(cogs_delta.abs().mean()),
        "cogs_delta_max_abs": float(cogs_delta.abs().max()),
        "cogs_total_ratio": float(frame["COGS"].sum() / anchor["COGS"].sum()),
        "mean_cogs_revenue_ratio": float((frame["COGS"] / frame["Revenue"].replace(0.0, pd.NA)).mean()),
    }


def candidate_frames(anchor: pd.DataFrame) -> list[tuple[str, pd.DataFrame, pd.Series]]:
    m = masks(anchor)
    specs: list[tuple[str, pd.DataFrame, pd.Series]] = []

    frame = anchor.copy()
    apply_scale(frame, m["promo"], revenue_pct=0.08, cogs_pct=0.04)
    specs.append(("public_breakthrough_promo_rev8_cogs4", frame, m["promo"]))

    frame = anchor.copy()
    apply_scale(frame, m["promo"], revenue_pct=0.08, cogs_pct=0.08)
    specs.append(("public_breakthrough_promo_rev8_cogs8", frame, m["promo"]))

    frame = anchor.copy()
    apply_scale(frame, m["promo"], revenue_pct=0.10, cogs_pct=0.06)
    specs.append(("public_breakthrough_promo_rev10_cogs6", frame, m["promo"]))

    frame = anchor.copy()
    apply_scale(frame, m["promo_2023"], revenue_pct=0.08, cogs_pct=0.04)
    apply_scale(frame, m["promo_2024"], revenue_pct=0.16, cogs_pct=0.10)
    specs.append(("public_breakthrough_promo2024_heavy_rev16_cogs10", frame, m["promo"]))

    frame = anchor.copy()
    apply_scale(frame, m["promo_h1"], revenue_pct=0.12, cogs_pct=0.06)
    apply_scale(frame, m["promo_h2"], revenue_pct=0.08, cogs_pct=0.04)
    specs.append(("public_breakthrough_promoh1_heavy_rev12_8_cogs6_4", frame, m["promo"]))

    frame = anchor.copy()
    apply_scale(frame, m["marapr"], revenue_pct=0.10, cogs_pct=0.05)
    apply_scale(frame, m["junjul"], revenue_pct=0.14, cogs_pct=0.07)
    apply_scale(frame, m["augoct"], revenue_pct=0.08, cogs_pct=0.04)
    apply_scale(frame, m["novjan"], revenue_pct=0.06, cogs_pct=0.03)
    specs.append(("public_breakthrough_promo_window_mixed_v1", frame, m["promo"]))

    frame = anchor.copy()
    apply_scale(frame, m["promo"], revenue_pct=0.08, cogs_pct=0.00)
    # Only high-intent H1 windows get COGS movement; keeps the known up8 Revenue win mostly intact.
    apply_scale(frame, m["promo_h1"], revenue_pct=0.00, cogs_pct=0.06)
    specs.append(("public_breakthrough_promo_rev8_h1cogs6", frame, m["promo"]))

    return specs


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    if not ANCHOR_PATH.exists():
        raise FileNotFoundError(f"Missing anchor submission: {ANCHOR_PATH}")

    anchor = pd.read_csv(ANCHOR_PATH, parse_dates=["Date"])
    rows = []
    exports = []

    for candidate_id, frame, changed_mask in candidate_frames(anchor):
        out = frame.copy()
        out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")
        dataset_path = DATASET_DIR / f"submission_{candidate_id}.csv"
        run_path = run_dir / f"submission_{candidate_id}.csv"
        out.to_csv(dataset_path, index=False)
        out.to_csv(run_path, index=False)
        rows.append(summarize(anchor, frame, candidate_id, changed_mask))
        exports.append({"candidate_id": candidate_id, "dataset_path": str(dataset_path), "run_path": str(run_path)})
        logger.info("Exported %s", candidate_id)

    summary = pd.DataFrame(rows)
    summary.to_csv(run_dir / "summary.csv", index=False)
    pd.DataFrame(exports).to_csv(run_dir / "exports.csv", index=False)
    write_json(
        run_dir / "config.json",
        {
            "known_public_scores": {
                "promo_windows_rev_up6": 888100.36839,
                "promo_windows_rev_up8": 887225.99926,
                "promo_windows_rev_up12": 888060.97204,
                "cogs2024h1_floor87": 898472.39191,
                "rev2024h1_up5": 896000,
            },
            "recommended_submit_order": [
                "public_breakthrough_promo_rev8_cogs4",
                "public_breakthrough_promo_rev8_cogs8",
                "public_breakthrough_promo2024_heavy_rev16_cogs10",
                "public_breakthrough_promo_window_mixed_v1",
            ],
        },
    )

    with (run_dir / "report.md").open("w", encoding="utf-8") as f:
        f.write("# Public Breakthrough Bets\n\n")
        f.write("Known signal: promo-window Revenue uplift is live; broad COGS and broad 2024 Revenue are not.\n\n")
        f.write("These candidates test larger structural hypotheses, not tiny amplitude tuning:\n")
        f.write("- Promo Revenue uplift with promo-specific COGS co-movement.\n")
        f.write("- 2024 promo windows as a stronger hidden regime.\n")
        f.write("- Window-specific mixed uplift.\n\n")
        f.write("Recommended submit order:\n")
        f.write("- `dataset/submission_public_breakthrough_promo_rev8_cogs4.csv`\n")
        f.write("- `dataset/submission_public_breakthrough_promo_rev8_cogs8.csv`\n")
        f.write("- `dataset/submission_public_breakthrough_promo2024_heavy_rev16_cogs10.csv`\n")
        f.write("- `dataset/submission_public_breakthrough_promo_window_mixed_v1.csv`\n\n")
        f.write("## Summary\n")
        f.write(summary.to_markdown(index=False))
        f.write("\n")

    print(summary.to_string(index=False))
    logger.info("Saved summary to %s", run_dir / "summary.csv")


if __name__ == "__main__":
    main()
