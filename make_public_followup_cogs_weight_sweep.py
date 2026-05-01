from __future__ import annotations

from pathlib import Path

import pandas as pd
import numpy as np

from logging_utils import create_run_dir, setup_logger, write_json


RUN_PREFIX = "public_followup_cogs_weight_sweep"
DATASET_DIR = Path("dataset")

SOURCE_FILES = {
    "public_winner_70_30": DATASET_DIR / "submission_blend_catboost_core_lightgbm_context_70_30.csv",
    "public_anchor_rev70_cogs80": DATASET_DIR / "submission_blend_catboost_core_lightgbm_context_rev70_cogs80.csv",
}

COGS_WEIGHT_CANDIDATES = [
    {
        "candidate_id": "blend_catboost_core_lightgbm_context_rev70_cogs78",
        "cogs_catboost_weight": 0.78,
        "priority": 1,
        "thesis": "small step below the new public winner to test whether the optimum is slightly under 0.80 on COGS.",
    },
    {
        "candidate_id": "blend_catboost_core_lightgbm_context_rev70_cogs82",
        "cogs_catboost_weight": 0.82,
        "priority": 2,
        "thesis": "small step above the new public winner to test whether more CatBoost helps on COGS.",
    },
    {
        "candidate_id": "blend_catboost_core_lightgbm_context_rev70_cogs85",
        "cogs_catboost_weight": 0.85,
        "priority": 3,
        "thesis": "moderate CatBoost-heavy COGS variant with revenue frozen at the public-best 0.70 blend.",
    },
    {
        "candidate_id": "blend_catboost_core_lightgbm_context_rev70_cogs90",
        "cogs_catboost_weight": 0.90,
        "priority": 4,
        "thesis": "aggressive COGS-heavy probe to test whether hidden COGS favors near-pure CatBoost.",
    },
    {
        "candidate_id": "blend_catboost_core_lightgbm_context_rev70_cogs95",
        "cogs_catboost_weight": 0.95,
        "priority": 5,
        "thesis": "near-pure CatBoost COGS with revenue still locked to the public-best 0.70 blend.",
    },
    {
        "candidate_id": "blend_catboost_core_lightgbm_context_rev70_cogs100",
        "cogs_catboost_weight": 1.00,
        "priority": 6,
        "thesis": "pure CatBoost COGS donor while preserving the proven 0.70 revenue blend.",
    },
]


def load_submission(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["Date"])
    return df.sort_values("Date").reset_index(drop=True)


def make_cogs_followup(
    winner_df: pd.DataFrame,
    anchor_df: pd.DataFrame,
    cogs_catboost_weight: float,
) -> pd.DataFrame:
    progress = (cogs_catboost_weight - 0.70) / 0.10
    cogs_delta = anchor_df["COGS"] - winner_df["COGS"]
    return pd.DataFrame(
        {
            "Date": anchor_df["Date"],
            # Revenue must stay frozen to the already-public-confirmed winner.
            "Revenue": anchor_df["Revenue"],
            "COGS": winner_df["COGS"] + progress * cogs_delta,
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
        f.write("# Public Follow-Up COGS Weight Sweep\n\n")
        f.write("## Framing\n")
        f.write("- Current public anchor is `rev70_cogs80`.\n")
        f.write("- Revenue stays frozen to the already confirmed public winner path.\n")
        f.write("- This batch uses only the observed public pair (`70_30` and `rev70_cogs80`) and interpolates/extrapolates COGS around that path.\n")
        f.write("- No candidate in this batch changes Revenue.\n\n")
        f.write("## Candidate Manifest\n")
        f.write(manifest_df.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Creating public follow-up COGS weight sweep in %s", run_dir)

    winner_df = load_submission(SOURCE_FILES["public_winner_70_30"])
    anchor_df = load_submission(SOURCE_FILES["public_anchor_rev70_cogs80"])

    if not winner_df["Date"].equals(anchor_df["Date"]):
        raise ValueError("Public winner and current public anchor dates do not align")
    if not np.allclose(winner_df["Revenue"].to_numpy(), anchor_df["Revenue"].to_numpy(), rtol=0.0, atol=1e-6):
        raise ValueError("Expected public winner and rev70_cogs80 to share identical Revenue")

    manifest_rows: list[dict[str, object]] = []
    for spec in COGS_WEIGHT_CANDIDATES:
        candidate_df = make_cogs_followup(
            winner_df=winner_df,
            anchor_df=anchor_df,
            cogs_catboost_weight=float(spec["cogs_catboost_weight"]),
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
                "revenue_catboost_weight": 0.70,
                "cogs_catboost_weight": spec["cogs_catboost_weight"],
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
