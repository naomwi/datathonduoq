from __future__ import annotations

from pathlib import Path

import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json


RUN_PREFIX = "public_blend_sweep"
DATASET_DIR = Path("dataset")

SOURCE_FILES = {
    "catboost_core": DATASET_DIR / "submission_catboost_md2y_core.csv",
    "lightgbm_context": DATASET_DIR / "submission_lightgbm_md2y_context.csv",
    "public_winner_70_30": DATASET_DIR / "submission_blend_catboost_core_lightgbm_context_70_30.csv",
}

BLEND_CANDIDATES = [
    {
        "candidate_id": "blend_catboost_core_lightgbm_context_75_25",
        "revenue_catboost_weight": 0.75,
        "cogs_catboost_weight": 0.75,
        "priority": 1,
        "thesis": "near-anchor uniform blend with slightly more CatBoost than the proven 70/30 winner",
    },
    {
        "candidate_id": "blend_catboost_core_lightgbm_context_rev70_cogs80",
        "revenue_catboost_weight": 0.70,
        "cogs_catboost_weight": 0.80,
        "priority": 2,
        "thesis": "keep proven revenue diversity but make COGS more CatBoost-heavy now that public metric is confirmed COGS-aware",
    },
    {
        "candidate_id": "blend_catboost_core_lightgbm_context_80_20",
        "revenue_catboost_weight": 0.80,
        "cogs_catboost_weight": 0.80,
        "priority": 3,
        "thesis": "uniform tighter blend that leans further into the stronger single-model anchor",
    },
    {
        "candidate_id": "blend_catboost_core_lightgbm_context_rev75_cogs85",
        "revenue_catboost_weight": 0.75,
        "cogs_catboost_weight": 0.85,
        "priority": 4,
        "thesis": "CatBoost-heavier COGS repair while keeping some LightGBM diversity on revenue",
    },
    {
        "candidate_id": "blend_catboost_core_lightgbm_context_85_15",
        "revenue_catboost_weight": 0.85,
        "cogs_catboost_weight": 0.85,
        "priority": 5,
        "thesis": "very conservative challenger that stays close to CatBoost but preserves a minority diversity vote",
    },
    {
        "candidate_id": "blend_catboost_core_lightgbm_context_rev80_cogs90",
        "revenue_catboost_weight": 0.80,
        "cogs_catboost_weight": 0.90,
        "priority": 6,
        "thesis": "highest CatBoost bias in this batch, mainly a COGS-aware stress test rather than a default first submit",
    },
]


def load_submission(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["Date"])
    return df.sort_values("Date").reset_index(drop=True)


def make_blend(
    catboost_df: pd.DataFrame,
    lightgbm_df: pd.DataFrame,
    revenue_catboost_weight: float,
    cogs_catboost_weight: float,
) -> pd.DataFrame:
    merged = catboost_df.merge(lightgbm_df, on="Date", suffixes=("_cb", "_lgb"))
    blended = pd.DataFrame(
        {
            "Date": merged["Date"],
            "Revenue": revenue_catboost_weight * merged["Revenue_cb"]
            + (1.0 - revenue_catboost_weight) * merged["Revenue_lgb"],
            "COGS": cogs_catboost_weight * merged["COGS_cb"] + (1.0 - cogs_catboost_weight) * merged["COGS_lgb"],
        }
    )
    return blended


def compute_drift_stats(candidate_df: pd.DataFrame, winner_df: pd.DataFrame) -> dict[str, float]:
    merged = candidate_df.merge(winner_df, on="Date", suffixes=("_candidate", "_winner"))
    revenue_abs_diff = (merged["Revenue_candidate"] - merged["Revenue_winner"]).abs()
    cogs_abs_diff = (merged["COGS_candidate"] - merged["COGS_winner"]).abs()
    return {
        "mean_abs_diff_revenue_vs_70_30": float(revenue_abs_diff.mean()),
        "mean_abs_diff_cogs_vs_70_30": float(cogs_abs_diff.mean()),
        "mean_abs_diff_combined_vs_70_30": float(0.5 * (revenue_abs_diff.mean() + cogs_abs_diff.mean())),
    }


def write_report(run_dir: Path, manifest_df: pd.DataFrame) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Public Blend Challengers\n\n")
        f.write("## Framing\n")
        f.write("- Source files are the two already-public-tested components: CatBoost core and LightGBM context.\n")
        f.write("- The proven public winner so far is the existing 70/30 uniform blend.\n")
        f.write("- This batch only explores near-anchor, CatBoost-heavier challengers now that the public metric is confirmed COGS-aware.\n\n")
        f.write("## Candidate Manifest\n")
        f.write(manifest_df.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Creating public blend challengers in %s", run_dir)

    catboost_df = load_submission(SOURCE_FILES["catboost_core"])
    lightgbm_df = load_submission(SOURCE_FILES["lightgbm_context"])
    winner_df = load_submission(SOURCE_FILES["public_winner_70_30"])

    if not catboost_df["Date"].equals(lightgbm_df["Date"]):
        raise ValueError("CatBoost and LightGBM submission dates do not align")
    if not catboost_df["Date"].equals(winner_df["Date"]):
        raise ValueError("Source submissions and current public winner dates do not align")

    manifest_rows: list[dict[str, object]] = []
    for spec in BLEND_CANDIDATES:
        blended = make_blend(
            catboost_df,
            lightgbm_df,
            revenue_catboost_weight=float(spec["revenue_catboost_weight"]),
            cogs_catboost_weight=float(spec["cogs_catboost_weight"]),
        )
        drift_stats = compute_drift_stats(blended, winner_df)
        output_name = f"submission_{spec['candidate_id']}.csv"
        dataset_path = DATASET_DIR / output_name
        run_path = run_dir / output_name

        export_df = blended.copy()
        export_df["Date"] = export_df["Date"].dt.strftime("%Y-%m-%d")
        export_df.to_csv(dataset_path, index=False)
        export_df.to_csv(run_path, index=False)
        logger.info("Exported %s", output_name)

        manifest_rows.append(
            {
                "priority": spec["priority"],
                "candidate_id": spec["candidate_id"],
                "revenue_catboost_weight": spec["revenue_catboost_weight"],
                "cogs_catboost_weight": spec["cogs_catboost_weight"],
                "mean_abs_diff_revenue_vs_70_30": drift_stats["mean_abs_diff_revenue_vs_70_30"],
                "mean_abs_diff_cogs_vs_70_30": drift_stats["mean_abs_diff_cogs_vs_70_30"],
                "mean_abs_diff_combined_vs_70_30": drift_stats["mean_abs_diff_combined_vs_70_30"],
                "thesis": spec["thesis"],
                "dataset_file": str(dataset_path),
            }
        )

    manifest_df = pd.DataFrame(manifest_rows).sort_values(
        ["priority", "mean_abs_diff_combined_vs_70_30"],
        ascending=[True, True],
    ).reset_index(drop=True)
    manifest_df.to_csv(run_dir / "manifest.csv", index=False)
    write_json(run_dir / "manifest.json", {"candidates": manifest_rows})
    write_report(run_dir, manifest_df)
    logger.info("Saved manifest to %s", run_dir / "manifest.csv")


if __name__ == "__main__":
    main()
