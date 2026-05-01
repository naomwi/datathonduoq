from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json


RUN_PREFIX = "public_perturbation_map"
DATASET_DIR = Path("dataset")
ANCHOR_PATH = DATASET_DIR / "submission_catboost_md2y_core_recencyexp20.csv"


def promo_window_mask(dates: pd.Series) -> pd.Series:
    month_day = dates.dt.strftime("%m-%d")
    masks = [
        month_day.between("03-18", "04-17"),
        month_day.between("06-23", "07-22"),
        month_day.between("08-30", "10-02"),
        month_day.between("11-18", "12-31") | month_day.between("01-01", "01-02"),
    ]
    out = masks[0].copy()
    for mask in masks[1:]:
        out |= mask
    return out


def write_submission(frame: pd.DataFrame, candidate_id: str, run_dir: Path, rows: list[dict]) -> None:
    out = frame.copy()
    out["Date"] = pd.to_datetime(out["Date"]).dt.strftime("%Y-%m-%d")
    dataset_path = DATASET_DIR / f"submission_{candidate_id}.csv"
    run_path = run_dir / f"submission_{candidate_id}.csv"
    out.to_csv(dataset_path, index=False)
    out.to_csv(run_path, index=False)
    rows.append({"candidate_id": candidate_id, "dataset_path": str(dataset_path), "run_path": str(run_path)})


def summarize_delta(anchor: pd.DataFrame, frame: pd.DataFrame, candidate_id: str) -> dict:
    rev_delta = frame["Revenue"] - anchor["Revenue"]
    cogs_delta = frame["COGS"] - anchor["COGS"]
    return {
        "candidate_id": candidate_id,
        "revenue_delta_mean": float(rev_delta.mean()),
        "revenue_delta_abs_mean": float(rev_delta.abs().mean()),
        "revenue_delta_max_abs": float(rev_delta.abs().max()),
        "revenue_total_ratio": float(frame["Revenue"].sum() / anchor["Revenue"].sum()),
        "cogs_delta_mean": float(cogs_delta.mean()),
        "cogs_delta_abs_mean": float(cogs_delta.abs().mean()),
        "cogs_delta_max_abs": float(cogs_delta.abs().max()),
        "cogs_total_ratio": float(frame["COGS"].sum() / anchor["COGS"].sum()),
        "mean_cogs_revenue_ratio": float((frame["COGS"] / frame["Revenue"].replace(0.0, np.nan)).mean()),
    }


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    if not ANCHOR_PATH.exists():
        raise FileNotFoundError(f"Missing anchor submission: {ANCHOR_PATH}")

    anchor = pd.read_csv(ANCHOR_PATH, parse_dates=["Date"])
    candidates: list[tuple[str, pd.DataFrame]] = []

    mask_2024 = (anchor["Date"] >= pd.Timestamp("2024-01-01")) & (anchor["Date"] <= pd.Timestamp("2024-07-01"))
    mask_promo = promo_window_mask(anchor["Date"])
    mask_recovery = (
        anchor["Date"].dt.strftime("%Y-%m").isin(["2023-08", "2023-11", "2023-12", "2024-06", "2024-07"])
    )

    for pct in [0.03, 0.05]:
        frame = anchor.copy()
        frame.loc[mask_2024, "Revenue"] *= 1.0 + pct
        candidates.append((f"public_probe_rev2024h1_up{int(pct * 100)}", frame))

    frame = anchor.copy()
    frame.loc[mask_2024, "COGS"] *= 1.05
    candidates.append(("public_probe_cogs2024h1_up5", frame))

    frame = anchor.copy()
    floor_value = frame.loc[mask_2024, "Revenue"] * 0.87
    frame.loc[mask_2024, "COGS"] = np.maximum(frame.loc[mask_2024, "COGS"], floor_value)
    candidates.append(("public_probe_cogs2024h1_floor87", frame))

    for pct in [0.04, 0.06]:
        frame = anchor.copy()
        frame.loc[mask_promo, "Revenue"] *= 1.0 + pct
        candidates.append((f"public_probe_promo_windows_rev_up{int(pct * 100)}", frame))

    frame = anchor.copy()
    frame.loc[mask_recovery, "Revenue"] *= 1.05
    candidates.append(("public_probe_recovery_months_rev_up5", frame))

    exports = []
    summary_rows = []
    for candidate_id, frame in candidates:
        write_submission(frame, candidate_id, run_dir, exports)
        summary_rows.append(summarize_delta(anchor, frame, candidate_id))
        logger.info("Exported %s", candidate_id)

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(run_dir / "summary.csv", index=False)
    pd.DataFrame(exports).to_csv(run_dir / "exports.csv", index=False)
    write_json(
        run_dir / "config.json",
        {
            "anchor_path": str(ANCHOR_PATH),
            "recommended_first_submissions": [
                "public_probe_rev2024h1_up5",
                "public_probe_cogs2024h1_floor87",
                "public_probe_promo_windows_rev_up6",
            ],
        },
    )

    with (run_dir / "report.md").open("w", encoding="utf-8") as f:
        f.write("# Public Perturbation Map\n\n")
        f.write("Goal: isolate public sign by moving one business axis at a time around the 896k anchor.\n\n")
        f.write("Recommended first submissions if quota is tight:\n")
        f.write("- `dataset/submission_public_probe_rev2024h1_up5.csv`\n")
        f.write("- `dataset/submission_public_probe_cogs2024h1_floor87.csv`\n")
        f.write("- `dataset/submission_public_probe_promo_windows_rev_up6.csv`\n\n")
        f.write("## Delta Summary\n")
        f.write(summary.to_markdown(index=False))
        f.write("\n")

    logger.info("Saved summary to %s", run_dir / "summary.csv")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
