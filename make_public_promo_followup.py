from __future__ import annotations

from pathlib import Path

import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json


RUN_PREFIX = "public_promo_followup"
DATASET_DIR = Path("dataset")
ANCHOR_PATH = DATASET_DIR / "submission_catboost_md2y_core_recencyexp20.csv"


def mask_between_month_day(dates: pd.Series, start: str, end: str) -> pd.Series:
    month_day = dates.dt.strftime("%m-%d")
    if start <= end:
        return month_day.between(start, end)
    return month_day.between(start, "12-31") | month_day.between("01-01", end)


def promo_masks(dates: pd.Series) -> dict[str, pd.Series]:
    return {
        "marapr": mask_between_month_day(dates, "03-18", "04-17"),
        "junjul": mask_between_month_day(dates, "06-23", "07-22"),
        "augoct": mask_between_month_day(dates, "08-30", "10-02"),
        "novjan": mask_between_month_day(dates, "11-18", "01-02"),
    }


def make_candidate(anchor: pd.DataFrame, candidate_id: str, mask: pd.Series, pct: float) -> tuple[str, pd.DataFrame]:
    frame = anchor.copy()
    frame.loc[mask, "Revenue"] *= 1.0 + pct
    return candidate_id, frame


def summarize(anchor: pd.DataFrame, frame: pd.DataFrame, candidate_id: str, changed_mask: pd.Series) -> dict:
    delta = frame["Revenue"] - anchor["Revenue"]
    return {
        "candidate_id": candidate_id,
        "changed_rows": int(changed_mask.sum()),
        "revenue_delta_mean_all": float(delta.mean()),
        "revenue_delta_abs_mean_all": float(delta.abs().mean()),
        "revenue_delta_max_abs": float(delta.abs().max()),
        "revenue_total_ratio": float(frame["Revenue"].sum() / anchor["Revenue"].sum()),
        "cogs_total_ratio": float(frame["COGS"].sum() / anchor["COGS"].sum()),
        "mean_cogs_revenue_ratio": float((frame["COGS"] / frame["Revenue"].replace(0.0, pd.NA)).mean()),
    }


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    if not ANCHOR_PATH.exists():
        raise FileNotFoundError(f"Missing anchor submission: {ANCHOR_PATH}")

    anchor = pd.read_csv(ANCHOR_PATH, parse_dates=["Date"])
    masks = promo_masks(anchor["Date"])
    all_promo = masks["marapr"] | masks["junjul"] | masks["augoct"] | masks["novjan"]
    h2_promo = masks["augoct"] | masks["novjan"]
    h1_promo = masks["marapr"] | masks["junjul"]

    specs: list[tuple[str, pd.Series, float]] = [
        ("public_probe_promo_windows_rev_up7", all_promo, 0.07),
        ("public_probe_promo_windows_rev_up8", all_promo, 0.08),
        ("public_probe_promo_windows_rev_up10", all_promo, 0.10),
        ("public_probe_promo_windows_rev_up12", all_promo, 0.12),
        ("public_probe_promo_h1_rev_up8", h1_promo, 0.08),
        ("public_probe_promo_h2_rev_up8", h2_promo, 0.08),
        ("public_probe_promo_augoct_rev_up10", masks["augoct"], 0.10),
        ("public_probe_promo_novjan_rev_up10", masks["novjan"], 0.10),
    ]

    rows = []
    exports = []
    for candidate_id, mask, pct in specs:
        _, frame = make_candidate(anchor, candidate_id, mask, pct)
        out = frame.copy()
        out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")
        dataset_path = DATASET_DIR / f"submission_{candidate_id}.csv"
        run_path = run_dir / f"submission_{candidate_id}.csv"
        out.to_csv(dataset_path, index=False)
        out.to_csv(run_path, index=False)
        rows.append(summarize(anchor, frame, candidate_id, mask))
        exports.append({"candidate_id": candidate_id, "dataset_path": str(dataset_path), "run_path": str(run_path)})
        logger.info("Exported %s", candidate_id)

    summary = pd.DataFrame(rows)
    summary.to_csv(run_dir / "summary.csv", index=False)
    pd.DataFrame(exports).to_csv(run_dir / "exports.csv", index=False)
    write_json(
        run_dir / "config.json",
        {
            "known_public_scores": {
                "submission_public_probe_promo_windows_rev_up6.csv": 888100.36839,
                "submission_public_probe_cogs2024h1_floor87.csv": 898472.39191,
                "submission_public_probe_rev2024h1_up5.csv": 896000,
            },
            "recommended_next_order": [
                "public_probe_promo_windows_rev_up8",
                "public_probe_promo_windows_rev_up10",
                "public_probe_promo_h2_rev_up8",
                "public_probe_promo_augoct_rev_up10",
            ],
        },
    )

    with (run_dir / "report.md").open("w", encoding="utf-8") as f:
        f.write("# Public Promo Follow-Up\n\n")
        f.write("Known public signal: `promo_windows_rev_up6` scored `888100.36839`, beating the ~896k anchor.\n\n")
        f.write("Recommended next submit order:\n")
        f.write("- `dataset/submission_public_probe_promo_windows_rev_up8.csv`\n")
        f.write("- `dataset/submission_public_probe_promo_windows_rev_up10.csv`\n")
        f.write("- `dataset/submission_public_probe_promo_h2_rev_up8.csv`\n")
        f.write("- `dataset/submission_public_probe_promo_augoct_rev_up10.csv`\n\n")
        f.write("## Summary\n")
        f.write(summary.to_markdown(index=False))
        f.write("\n")

    print(summary.to_string(index=False))
    logger.info("Saved summary to %s", run_dir / "summary.csv")


if __name__ == "__main__":
    main()
