from __future__ import annotations

from pathlib import Path

import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json


RUN_PREFIX = "public_followup_revenue_with_pure_cogs"
DATASET_DIR = Path("dataset")

SOURCE_FILES = {
    "catboost_core": DATASET_DIR / "submission_catboost_md2y_core.csv",
    "lightgbm_context": DATASET_DIR / "submission_lightgbm_md2y_context.csv",
    "public_anchor_rev70_cogs100": DATASET_DIR / "submission_blend_catboost_core_lightgbm_context_rev70_cogs100.csv",
}

REVENUE_WEIGHT_CANDIDATES = [
    {
        "candidate_id": "blend_catboost_core_lightgbm_context_rev68_cogs100",
        "revenue_catboost_weight": 0.68,
        "priority": 1,
        "thesis": "small step below 0.70 in case revenue diversity should lean slightly more LightGBM while keeping pure CatBoost COGS.",
    },
    {
        "candidate_id": "blend_catboost_core_lightgbm_context_rev72_cogs100",
        "revenue_catboost_weight": 0.72,
        "priority": 2,
        "thesis": "small step above 0.70 in case the better COGS path also favors a slightly stronger CatBoost revenue vote.",
    },
    {
        "candidate_id": "blend_catboost_core_lightgbm_context_rev65_cogs100",
        "revenue_catboost_weight": 0.65,
        "priority": 3,
        "thesis": "broader revenue diversity probe with pure CatBoost COGS fixed.",
    },
    {
        "candidate_id": "blend_catboost_core_lightgbm_context_rev75_cogs100",
        "revenue_catboost_weight": 0.75,
        "priority": 4,
        "thesis": "CatBoost-heavier revenue blend with pure CatBoost COGS fixed.",
    },
    {
        "candidate_id": "blend_catboost_core_lightgbm_context_rev60_cogs100",
        "revenue_catboost_weight": 0.60,
        "priority": 5,
        "thesis": "aggressive revenue diversity stress test while keeping the now-proven pure CatBoost COGS path.",
    },
]


def load_submission(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["Date"])
    return df.sort_values("Date").reset_index(drop=True)


def make_blend(
    catboost_df: pd.DataFrame,
    lightgbm_df: pd.DataFrame,
    revenue_catboost_weight: float,
) -> pd.DataFrame:
    merged = catboost_df.merge(lightgbm_df, on="Date", suffixes=("_cb", "_lgb"))
    return pd.DataFrame(
        {
            "Date": merged["Date"],
            "Revenue": revenue_catboost_weight * merged["Revenue_cb"]
            + (1.0 - revenue_catboost_weight) * merged["Revenue_lgb"],
            "COGS": merged["COGS_cb"],
        }
    )


def compute_drift_stats(candidate_df: pd.DataFrame, anchor_df: pd.DataFrame) -> dict[str, float]:
    merged = candidate_df.merge(anchor_df, on="Date", suffixes=("_candidate", "_anchor"))
    revenue_abs_diff = (merged["Revenue_candidate"] - merged["Revenue_anchor"]).abs()
    cogs_abs_diff = (merged["COGS_candidate"] - merged["COGS_anchor"]).abs()
    return {
        "mean_abs_diff_revenue_vs_anchor": float(revenue_abs_diff.mean()),
        "mean_abs_diff_cogs_vs_anchor": float(cogs_abs_diff.mean()),
        "mean_abs_diff_combined_vs_anchor": float(0.5 * (revenue_abs_diff.mean() + cogs_abs_diff.mean())),
    }


def write_report(run_dir: Path, manifest_df: pd.DataFrame) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Public Follow-Up Revenue Sweep With Pure CatBoost COGS\n\n")
        f.write("## Framing\n")
        f.write("- Current public best is `rev70_cogs100`.\n")
        f.write("- This batch keeps `COGS = CatBoost pure` for every row.\n")
        f.write("- Only the Revenue CatBoost weight is swept around the current `0.70` anchor.\n\n")
        f.write("## Candidate Manifest\n")
        f.write(manifest_df.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Creating public follow-up revenue sweep with pure CatBoost COGS in %s", run_dir)

    catboost_df = load_submission(SOURCE_FILES["catboost_core"])
    lightgbm_df = load_submission(SOURCE_FILES["lightgbm_context"])
    anchor_df = load_submission(SOURCE_FILES["public_anchor_rev70_cogs100"])

    if not catboost_df["Date"].equals(lightgbm_df["Date"]):
        raise ValueError("CatBoost and LightGBM submission dates do not align")
    if not catboost_df["Date"].equals(anchor_df["Date"]):
        raise ValueError("Source submissions and current public anchor dates do not align")

    manifest_rows: list[dict[str, object]] = []
    for spec in REVENUE_WEIGHT_CANDIDATES:
        candidate_df = make_blend(
            catboost_df,
            lightgbm_df,
            revenue_catboost_weight=float(spec["revenue_catboost_weight"]),
        )
        drift_stats = compute_drift_stats(candidate_df, anchor_df)
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
                "revenue_catboost_weight": spec["revenue_catboost_weight"],
                "cogs_catboost_weight": 1.00,
                "mean_abs_diff_revenue_vs_anchor": drift_stats["mean_abs_diff_revenue_vs_anchor"],
                "mean_abs_diff_cogs_vs_anchor": drift_stats["mean_abs_diff_cogs_vs_anchor"],
                "mean_abs_diff_combined_vs_anchor": drift_stats["mean_abs_diff_combined_vs_anchor"],
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
