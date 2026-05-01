from __future__ import annotations

from pathlib import Path

import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json


RUN_PREFIX = "public_structural_revenue_challengers"
DATASET_DIR = Path("dataset")
CLAMP_EPSILON = 0.005

SOURCE_FILES = {
    "public_anchor": DATASET_DIR / "submission_blend_catboost_core_lightgbm_context_rev70_cogs100.csv",
    "revswitch": DATASET_DIR / "submission_blend_md2y_revswitch_60_40.csv",
    "bottomup_category": DATASET_DIR / "submission_bottomup_category.csv",
    "bottomup_category_segment": DATASET_DIR / "submission_bottomup_category_segment_blend50.csv",
    "bottomup_revratio_segment": DATASET_DIR / "submission_bottomup_revratio_segment.csv",
}

STRUCTURAL_CANDIDATES = [
    {
        "candidate_id": "public_structural_revswitch_z20_cogs100",
        "priority": 1,
        "donor_key": "revswitch",
        "revenue_weight": 0.20,
        "thesis": "nearest-anchor structural probe using the historical revenue-switch donor.",
    },
    {
        "candidate_id": "public_structural_bottomup_category_z10_cogs100",
        "priority": 2,
        "donor_key": "bottomup_category",
        "revenue_weight": 0.10,
        "thesis": "mild semi-bottom-up probe using category revenue shape with anchor-level scale.",
    },
    {
        "candidate_id": "public_structural_bottomup_catseg_z10_cogs100",
        "priority": 3,
        "donor_key": "bottomup_category_segment",
        "revenue_weight": 0.10,
        "thesis": "mild semi-bottom-up probe using blended category/segment revenue shape.",
    },
    {
        "candidate_id": "public_structural_revswitch_z30_cogs100",
        "priority": 4,
        "donor_key": "revswitch",
        "revenue_weight": 0.30,
        "thesis": "larger near-anchor structural move if the revenue-switch signal is truly helping public.",
    },
    {
        "candidate_id": "public_structural_bottomup_revratio_segment_z20_cogs100",
        "priority": 5,
        "donor_key": "bottomup_revratio_segment",
        "revenue_weight": 0.20,
        "thesis": "wildcard direct-revenue grouped donor with strong structural deviation and fixed pure COGS.",
    },
    {
        "candidate_id": "public_structural_bottomup_category_z20_cogs100",
        "priority": 6,
        "donor_key": "bottomup_category",
        "revenue_weight": 0.20,
        "thesis": "stronger category structural move if the mild version transfers.",
    },
    {
        "candidate_id": "public_structural_bottomup_catseg_z20_cogs100",
        "priority": 7,
        "donor_key": "bottomup_category_segment",
        "revenue_weight": 0.20,
        "thesis": "stronger category/segment structural move if semi-bottom-up signal survives public transfer.",
    },
]


def load_submission(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["Date"])
    return df.sort_values("Date").reset_index(drop=True)


def invalid_row_count(df: pd.DataFrame) -> int:
    invalid = (
        (df["Revenue"] < 0.0)
        | (df["COGS"] < 0.0)
        | (df["COGS"] > df["Revenue"] * (1.0 - CLAMP_EPSILON))
    )
    return int(invalid.sum())


def zscore_align_revenue(anchor_revenue: pd.Series, donor_revenue: pd.Series) -> pd.Series:
    donor_std = float(donor_revenue.std())
    if donor_std <= 1e-12:
        aligned = pd.Series(anchor_revenue.mean(), index=donor_revenue.index, dtype=float)
    else:
        aligned = (
            (donor_revenue - donor_revenue.mean())
            * (float(anchor_revenue.std()) / donor_std)
            + float(anchor_revenue.mean())
        )
    return aligned.clip(lower=0.0)


def build_candidate(anchor_df: pd.DataFrame, donor_df: pd.DataFrame, revenue_weight: float) -> tuple[pd.DataFrame, pd.Series]:
    aligned_revenue = zscore_align_revenue(anchor_df["Revenue"], donor_df["Revenue"])
    candidate_df = anchor_df.copy()
    candidate_df["Revenue"] = (
        (1.0 - revenue_weight) * anchor_df["Revenue"] + revenue_weight * aligned_revenue
    ).clip(lower=0.0)
    candidate_df["COGS"] = anchor_df["COGS"]
    return candidate_df, aligned_revenue


def compute_stats(
    candidate_df: pd.DataFrame,
    anchor_df: pd.DataFrame,
    aligned_revenue: pd.Series,
    donor_df: pd.DataFrame,
) -> dict[str, float | int]:
    revenue_abs_diff = (candidate_df["Revenue"] - anchor_df["Revenue"]).abs()
    cogs_abs_diff = (candidate_df["COGS"] - anchor_df["COGS"]).abs()
    aligned_abs_diff = (aligned_revenue - anchor_df["Revenue"]).abs()
    return {
        "rows_changed_revenue": int((revenue_abs_diff > 1e-9).sum()),
        "rows_changed_cogs": int((cogs_abs_diff > 1e-9).sum()),
        "anchor_invalid_rows": invalid_row_count(anchor_df),
        "candidate_invalid_rows": invalid_row_count(candidate_df),
        "mean_abs_diff_revenue_vs_anchor": float(revenue_abs_diff.mean()),
        "mean_abs_diff_cogs_vs_anchor": float(cogs_abs_diff.mean()),
        "mean_pct_shift_revenue_vs_anchor": float(
            ((candidate_df["Revenue"] - anchor_df["Revenue"]) / anchor_df["Revenue"].replace(0.0, 1.0)).mean()
        ),
        "aligned_donor_mean_abs_diff_vs_anchor": float(aligned_abs_diff.mean()),
        "aligned_donor_corr_vs_anchor": float(anchor_df["Revenue"].corr(aligned_revenue)),
        "raw_donor_corr_vs_anchor": float(anchor_df["Revenue"].corr(donor_df["Revenue"])),
    }


def write_report(run_dir: Path, manifest_df: pd.DataFrame) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Public Structural Revenue Challengers\n\n")
        f.write("## Framing\n")
        f.write("- Public anchor is `submission_blend_catboost_core_lightgbm_context_rev70_cogs100.csv`.\n")
        f.write("- Every challenger freezes COGS from the current public winner.\n")
        f.write("- Only Revenue is changed.\n")
        f.write("- Revenue donors are z-score aligned to the anchor forecast distribution before blending.\n")
        f.write("- Goal: test semi-bottom-up / structural Revenue signal without contaminating public winner COGS.\n\n")
        f.write("## Candidate Manifest\n")
        f.write(manifest_df.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Creating public structural revenue challengers in %s", run_dir)

    anchor_df = load_submission(SOURCE_FILES["public_anchor"])
    donors = {
        donor_key: load_submission(path)
        for donor_key, path in SOURCE_FILES.items()
        if donor_key != "public_anchor"
    }

    for donor_key, donor_df in donors.items():
        if not anchor_df["Date"].equals(donor_df["Date"]):
            raise ValueError(f"Date mismatch between public anchor and donor {donor_key}")

    manifest_rows: list[dict[str, object]] = []
    for spec in STRUCTURAL_CANDIDATES:
        donor_key = str(spec["donor_key"])
        donor_df = donors[donor_key]
        candidate_df, aligned_revenue = build_candidate(
            anchor_df=anchor_df,
            donor_df=donor_df,
            revenue_weight=float(spec["revenue_weight"]),
        )
        stats = compute_stats(candidate_df, anchor_df, aligned_revenue, donor_df)

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
                "donor_key": donor_key,
                "revenue_weight": spec["revenue_weight"],
                "rows_changed_revenue": stats["rows_changed_revenue"],
                "rows_changed_cogs": stats["rows_changed_cogs"],
                "anchor_invalid_rows": stats["anchor_invalid_rows"],
                "candidate_invalid_rows": stats["candidate_invalid_rows"],
                "mean_abs_diff_revenue_vs_anchor": stats["mean_abs_diff_revenue_vs_anchor"],
                "mean_abs_diff_cogs_vs_anchor": stats["mean_abs_diff_cogs_vs_anchor"],
                "mean_pct_shift_revenue_vs_anchor": stats["mean_pct_shift_revenue_vs_anchor"],
                "aligned_donor_mean_abs_diff_vs_anchor": stats["aligned_donor_mean_abs_diff_vs_anchor"],
                "aligned_donor_corr_vs_anchor": stats["aligned_donor_corr_vs_anchor"],
                "raw_donor_corr_vs_anchor": stats["raw_donor_corr_vs_anchor"],
                "thesis": spec["thesis"],
                "dataset_file": str(dataset_path),
            }
        )

    manifest_df = pd.DataFrame(manifest_rows).sort_values(
        ["priority", "mean_abs_diff_revenue_vs_anchor"],
        ascending=[True, True],
    ).reset_index(drop=True)
    manifest_df.to_csv(run_dir / "manifest.csv", index=False)
    write_json(run_dir / "manifest.json", {"candidates": manifest_rows})
    write_report(run_dir, manifest_df)
    logger.info("Saved manifest to %s", run_dir / "manifest.csv")


if __name__ == "__main__":
    main()
