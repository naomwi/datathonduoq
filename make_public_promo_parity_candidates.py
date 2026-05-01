from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json


RUN_PREFIX = "public_promo_parity_candidates"
DATASET_DIR = Path("dataset")
BASE_PATH = DATASET_DIR / "submission_tabpfn_promo_windowmix_v1.csv"


def between(dates: pd.Series, start: str, end: str) -> pd.Series:
    return (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))


def mask_between_month_day(dates: pd.Series, start: str, end: str) -> pd.Series:
    month_day = dates.dt.strftime("%m-%d")
    if start <= end:
        return month_day.between(start, end)
    return month_day.between(start, "12-31") | month_day.between("01-01", end)


def main_promo_mask(dates: pd.Series) -> pd.Series:
    masks = [
        mask_between_month_day(dates, "03-18", "04-17"),
        mask_between_month_day(dates, "06-23", "07-22"),
        mask_between_month_day(dates, "08-30", "10-02"),
        mask_between_month_day(dates, "11-18", "01-02"),
    ]
    out = masks[0].copy()
    for mask in masks[1:]:
        out |= mask
    return out


def export_candidate(
    run_dir: Path,
    base: pd.DataFrame,
    candidate_id: str,
    multipliers: list[tuple[str, pd.Series, float]],
) -> dict[str, object]:
    frame = base.copy()
    dates = pd.to_datetime(frame["Date"])
    applied_mask = pd.Series(False, index=frame.index)
    for _, mask, pct in multipliers:
        frame.loc[mask, "Revenue"] *= 1.0 + pct
        applied_mask |= mask

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
        "changed_rows": int(applied_mask.sum()),
        "revenue_total_ratio_vs_base": float(frame["Revenue"].sum() / base["Revenue"].sum()),
        "revenue_delta_mean": float(delta.mean()),
        "revenue_delta_abs_mean": float(delta.abs().mean()),
        "revenue_delta_max_abs": float(delta.abs().max()),
    }
    for label, mask, pct in multipliers:
        row[f"{label}_rows"] = int(mask.sum())
        row[f"{label}_pct"] = pct
        row[f"{label}_delta_mean_on_mask"] = float(delta.loc[mask].mean()) if mask.any() else 0.0
    return row


def write_report(run_dir: Path, summary: pd.DataFrame) -> None:
    with (run_dir / "report.md").open("w", encoding="utf-8") as f:
        f.write("# Public Promo Parity Candidates\n\n")
        f.write("Hypothesis: the promotional calendar alternates extra `Rural Special` and `Urban Blowout` campaigns in odd years. Public 2023 should have these extra promos, while 2024 H1 should not have Rural Special. The current future policy smears recent 2021/2022 promos into both years.\n\n")
        f.write(summary.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    if not BASE_PATH.exists():
        raise FileNotFoundError(f"Missing base submission: {BASE_PATH}")
    base = pd.read_csv(BASE_PATH, parse_dates=["Date"])
    dates = pd.to_datetime(base["Date"])

    main_promo = main_promo_mask(dates)
    rural23 = between(dates, "2023-01-30", "2023-03-01")
    urban23 = between(dates, "2023-07-30", "2023-09-02")
    rural24 = between(dates, "2024-01-30", "2024-03-01")
    extra23 = rural23 | urban23
    extra23_nonmain = extra23 & ~main_promo
    urban23_nonmain = urban23 & ~main_promo

    specs: list[tuple[str, list[tuple[str, pd.Series, float]]]] = [
        ("public_parity_oddpromo23_nonmain_up8", [("extra23_nonmain", extra23_nonmain, 0.08)]),
        ("public_parity_oddpromo23_nonmain_up12", [("extra23_nonmain", extra23_nonmain, 0.12)]),
        ("public_parity_oddpromo23_all_up8", [("extra23_all", extra23, 0.08)]),
        ("public_parity_rural23_up8_only", [("rural23", rural23, 0.08)]),
        ("public_parity_urban23_nonmain_up10_only", [("urban23_nonmain", urban23_nonmain, 0.10)]),
        ("public_parity_rural24_down5_only", [("rural24", rural24, -0.05)]),
        (
            "public_parity_odd23_up8_even24_rural_down5",
            [("extra23_nonmain", extra23_nonmain, 0.08), ("rural24", rural24, -0.05)],
        ),
        (
            "public_parity_odd23_up12_even24_rural_down5",
            [("extra23_nonmain", extra23_nonmain, 0.12), ("rural24", rural24, -0.05)],
        ),
    ]

    rows = [export_candidate(run_dir, base, candidate_id, multipliers) for candidate_id, multipliers in specs]
    summary = pd.DataFrame(rows)
    summary.to_csv(run_dir / "summary.csv", index=False)
    write_json(
        run_dir / "config.json",
        {
            "base_path": str(BASE_PATH),
            "current_best_public": {"submission_tabpfn_promo_windowmix_v1.csv": 883183.19507},
            "hypothesis": "Odd years include extra Rural Special and Urban Blowout promotions; even years do not.",
        },
    )
    write_report(run_dir, summary)
    logger.info("Saved %s promo parity candidates to %s", len(summary), run_dir)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
