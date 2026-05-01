from __future__ import annotations

from pathlib import Path

import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json


RUN_PREFIX = "public_anchor_rev70_cogs100_repair"
DATASET_DIR = Path("dataset")
CLAMP_EPSILON = 0.005

SOURCE_FILES = {
    "public_anchor": DATASET_DIR / "submission_blend_catboost_core_lightgbm_context_rev70_cogs100.csv",
    "donor_95": DATASET_DIR / "submission_blend_catboost_core_lightgbm_context_rev70_cogs95.csv",
    "donor_90": DATASET_DIR / "submission_blend_catboost_core_lightgbm_context_rev70_cogs90.csv",
    "donor_85": DATASET_DIR / "submission_blend_catboost_core_lightgbm_context_rev70_cogs85.csv",
}

REPAIR_CANDIDATES = [
    {
        "candidate_id": "public_anchor_rev70_cogs100_clamp_only",
        "priority": 1,
        "mode": "clamp_only",
        "thesis": "keep the current public winner intact except for impossible negative-margin rows.",
    },
    {
        "candidate_id": "public_anchor_rev70_cogs100_repair95",
        "priority": 2,
        "mode": "repair_invalid_rows",
        "donor_key": "donor_95",
        "thesis": "repair only invalid rows using the closest lower-CatBoost COGS path, then clamp.",
    },
    {
        "candidate_id": "public_anchor_rev70_cogs100_repair90",
        "priority": 3,
        "mode": "repair_invalid_rows",
        "donor_key": "donor_90",
        "thesis": "repair only invalid rows using the next-closest public-tested COGS path, then clamp.",
    },
    {
        "candidate_id": "public_anchor_rev70_cogs100_repair85",
        "priority": 4,
        "mode": "repair_invalid_rows",
        "donor_key": "donor_85",
        "thesis": "repair only invalid rows using the strongest lower-weight public winner, then clamp.",
    },
]


def load_submission(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["Date"])
    return df.sort_values("Date").reset_index(drop=True)


def clamp_cogs(revenue: pd.Series, cogs: pd.Series) -> pd.Series:
    capped = cogs.clip(lower=0.0)
    upper = revenue * (1.0 - CLAMP_EPSILON)
    return capped.where(capped <= upper, upper)


def invalid_mask(df: pd.DataFrame) -> pd.Series:
    return df["COGS"] > df["Revenue"] * (1.0 - CLAMP_EPSILON)


def build_candidate(anchor_df: pd.DataFrame, mode: str, donor_df: pd.DataFrame | None = None) -> pd.DataFrame:
    candidate_df = anchor_df.copy()

    if mode == "clamp_only":
        candidate_df["COGS"] = clamp_cogs(candidate_df["Revenue"], candidate_df["COGS"])
        return candidate_df

    if mode != "repair_invalid_rows":
        raise ValueError(f"Unknown repair mode: {mode}")
    if donor_df is None:
        raise ValueError("repair_invalid_rows mode requires a donor submission")

    mask = invalid_mask(candidate_df)
    repaired_cogs = candidate_df["COGS"].where(~mask, donor_df["COGS"])
    candidate_df["COGS"] = clamp_cogs(candidate_df["Revenue"], repaired_cogs)
    return candidate_df


def compute_stats(candidate_df: pd.DataFrame, anchor_df: pd.DataFrame) -> dict[str, float | int]:
    revenue_abs_diff = (candidate_df["Revenue"] - anchor_df["Revenue"]).abs()
    cogs_abs_diff = (candidate_df["COGS"] - anchor_df["COGS"]).abs()
    combined_abs_diff = 0.5 * (revenue_abs_diff + cogs_abs_diff)
    return {
        "rows_changed_revenue": int((revenue_abs_diff > 1e-9).sum()),
        "rows_changed_cogs": int((cogs_abs_diff > 1e-9).sum()),
        "anchor_invalid_rows": int(invalid_mask(anchor_df).sum()),
        "candidate_invalid_rows": int(invalid_mask(candidate_df).sum()),
        "mean_abs_diff_revenue_vs_anchor": float(revenue_abs_diff.mean()),
        "mean_abs_diff_cogs_vs_anchor": float(cogs_abs_diff.mean()),
        "mean_abs_diff_combined_vs_anchor": float(combined_abs_diff.mean()),
        "max_abs_diff_cogs_vs_anchor": float(cogs_abs_diff.max()),
    }


def write_report(run_dir: Path, manifest_df: pd.DataFrame) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Public Anchor Rev70 COGS100 Repair\n\n")
        f.write("## Framing\n")
        f.write("- Source anchor is the current best public submission: `rev70_cogs100`.\n")
        f.write("- Revenue stays frozen from the public winner for every challenger in this batch.\n")
        f.write("- Only COGS is changed, and only on invalid or clamped rows.\n")
        f.write(f"- All challengers enforce `COGS <= Revenue * {1.0 - CLAMP_EPSILON:.3f}`.\n\n")
        f.write("## Candidate Manifest\n")
        f.write(manifest_df.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Creating public anchor rev70_cogs100 repair challengers in %s", run_dir)

    anchor_df = load_submission(SOURCE_FILES["public_anchor"])
    donors = {
        "donor_95": load_submission(SOURCE_FILES["donor_95"]),
        "donor_90": load_submission(SOURCE_FILES["donor_90"]),
        "donor_85": load_submission(SOURCE_FILES["donor_85"]),
    }

    for donor_name, donor_df in donors.items():
        if not anchor_df["Date"].equals(donor_df["Date"]):
            raise ValueError(f"Date mismatch between public anchor and {donor_name}")
        if not anchor_df["Revenue"].equals(donor_df["Revenue"]):
            raise ValueError(f"Revenue mismatch between public anchor and {donor_name}")

    manifest_rows: list[dict[str, object]] = []
    for spec in REPAIR_CANDIDATES:
        donor_key = spec.get("donor_key")
        donor_df = donors.get(str(donor_key)) if donor_key else None
        candidate_df = build_candidate(anchor_df, mode=str(spec["mode"]), donor_df=donor_df)
        stats = compute_stats(candidate_df, anchor_df)

        output_name = f"submission_{spec['candidate_id']}.csv"
        dataset_path = DATASET_DIR / output_name
        run_path = run_dir / output_name

        export_df = candidate_df.copy()
        export_df["Date"] = export_df["Date"].dt.strftime("%Y-%m-%d")
        export_df.to_csv(dataset_path, index=False)
        export_df.to_csv(run_path, index=False)
        logger.info("Exported %s", output_name)

        manifest_rows.append(
            {
                "priority": spec["priority"],
                "candidate_id": spec["candidate_id"],
                "mode": spec["mode"],
                "donor": donor_key or "",
                "rows_changed_revenue": stats["rows_changed_revenue"],
                "rows_changed_cogs": stats["rows_changed_cogs"],
                "anchor_invalid_rows": stats["anchor_invalid_rows"],
                "candidate_invalid_rows": stats["candidate_invalid_rows"],
                "mean_abs_diff_revenue_vs_anchor": stats["mean_abs_diff_revenue_vs_anchor"],
                "mean_abs_diff_cogs_vs_anchor": stats["mean_abs_diff_cogs_vs_anchor"],
                "mean_abs_diff_combined_vs_anchor": stats["mean_abs_diff_combined_vs_anchor"],
                "max_abs_diff_cogs_vs_anchor": stats["max_abs_diff_cogs_vs_anchor"],
                "thesis": spec["thesis"],
                "dataset_file": str(dataset_path),
            }
        )

    manifest_df = pd.DataFrame(manifest_rows).sort_values(
        ["priority", "mean_abs_diff_combined_vs_anchor"],
        ascending=[True, True],
    ).reset_index(drop=True)
    manifest_df.to_csv(run_dir / "manifest.csv", index=False)
    write_json(run_dir / "manifest.json", {"candidates": manifest_rows})
    write_report(run_dir, manifest_df)
    logger.info("Saved manifest to %s", run_dir / "manifest.csv")


if __name__ == "__main__":
    main()
