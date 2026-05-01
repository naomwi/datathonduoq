"""
Create late-only Revenue blends from the recencyexp20 anchor and direct-v2 probes.

Default behavior is intentionally conservative:
  - write all generated submissions into a fresh logs/ run directory;
  - keep anchor COGS unchanged;
  - publish nothing into dataset/ unless --publish-probes is passed.

This is a disjoint probe script, not a training pipeline.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ANCHOR_PATH = Path("dataset/submission_catboost_md2y_core_recencyexp20.csv")
DIRECT_GLOB = "submission_direct_v2_cut*.csv"
DIRECT_DIR = Path("dataset")
DATASET_DIR = Path("dataset")
LOGS_DIR = Path("logs")
RUN_PREFIX = "direct_v2_late_hybrid_probe"

LATE_CUTS = (45, 60, 90)
BLEND_WEIGHTS = (0.10, 0.20, 0.30)

# Clamp the donor first, then clamp final output. The blend can still move
# the late Revenue curve, but cannot become a full direct-v2 replacement.
DONOR_REL_CLAMP = 0.35
DONOR_ABS_CLAMP = 1_500_000.0
FINAL_REL_CLAMP = 0.12
FINAL_ABS_CLAMP = 700_000.0

DIRECT_SUMMARY_PATH = Path("logs/20260421_122415_public_revenue_direct_horizon_v2_fixed/summary.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build direct-v2 late-only Revenue hybrid probes under logs/."
    )
    parser.add_argument(
        "--publish-probes",
        action="store_true",
        help="Also copy generated probe submissions to dataset/ with a probe-prefixed name.",
    )
    parser.add_argument(
        "--anchor-path",
        type=Path,
        default=ANCHOR_PATH,
        help=f"Anchor submission path. Default: {ANCHOR_PATH}",
    )
    parser.add_argument(
        "--direct-dir",
        type=Path,
        default=DIRECT_DIR,
        help=f"Directory containing {DIRECT_GLOB}. Default: {DIRECT_DIR}",
    )
    return parser.parse_args()


def create_run_dir() -> Path:
    run_dir = LOGS_DIR / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    (run_dir / "submissions").mkdir(parents=True, exist_ok=False)
    return run_dir


def read_submission(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    required = {"Date", "Revenue", "COGS"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {sorted(missing)}")
    df = df[["Date", "Revenue", "COGS"]].copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    return df


def direct_id_from_path(path: Path) -> str:
    return path.stem.replace("submission_", "")


def direct_cut_from_id(direct_id: str) -> int | None:
    match = re.search(r"cut(\d+)", direct_id)
    return int(match.group(1)) if match else None


def clamp_around_anchor(
    values: pd.Series,
    anchor: pd.Series,
    rel_cap: float,
    abs_cap: float,
) -> np.ndarray:
    cap = np.minimum(np.abs(anchor.to_numpy(dtype=float)) * rel_cap, abs_cap)
    lower = np.maximum(anchor.to_numpy(dtype=float) - cap, 0.0)
    upper = anchor.to_numpy(dtype=float) + cap
    return np.clip(values.to_numpy(dtype=float), lower, upper)


def make_hybrid(
    anchor: pd.DataFrame,
    direct: pd.DataFrame,
    source_id: str,
    late_cut: int,
    weight: float,
) -> tuple[pd.DataFrame, dict]:
    merged = anchor.merge(
        direct,
        on="Date",
        how="inner",
        suffixes=("_anchor", "_direct"),
        validate="one_to_one",
    )
    if len(merged) != len(anchor):
        raise ValueError(
            f"{source_id}: date mismatch, matched {len(merged)} rows but anchor has {len(anchor)} rows"
        )

    merged["forecast_step"] = np.arange(1, len(merged) + 1)
    late_mask = merged["forecast_step"] > late_cut

    donor_rev = clamp_around_anchor(
        merged["Revenue_direct"],
        merged["Revenue_anchor"],
        DONOR_REL_CLAMP,
        DONOR_ABS_CLAMP,
    )
    blended_rev = (
        merged["Revenue_anchor"].to_numpy(dtype=float) * (1.0 - weight)
        + donor_rev * weight
    )
    final_rev = clamp_around_anchor(
        pd.Series(blended_rev),
        merged["Revenue_anchor"],
        FINAL_REL_CLAMP,
        FINAL_ABS_CLAMP,
    )

    out_rev = merged["Revenue_anchor"].to_numpy(dtype=float).copy()
    out_rev[late_mask.to_numpy()] = final_rev[late_mask.to_numpy()]

    output = pd.DataFrame(
        {
            "Date": merged["Date"].dt.strftime("%Y-%m-%d"),
            "Revenue": out_rev,
            "COGS": merged["COGS_anchor"].to_numpy(dtype=float),
        }
    )

    delta = output["Revenue"].to_numpy(dtype=float) - merged["Revenue_anchor"].to_numpy(dtype=float)
    late_delta = delta[late_mask.to_numpy()]
    late_anchor = merged.loc[late_mask, "Revenue_anchor"].to_numpy(dtype=float)

    summary = {
        "candidate_id": f"{source_id}_lateafter{late_cut}_w{int(round(weight * 100)):02d}",
        "source_direct_id": source_id,
        "source_direct_cut": direct_cut_from_id(source_id),
        "late_after_step": late_cut,
        "blend_weight": weight,
        "rows_total": int(len(output)),
        "rows_blended": int(late_mask.sum()),
        "revenue_delta_mean_all": float(delta.mean()),
        "revenue_delta_abs_mean_all": float(np.abs(delta).mean()),
        "revenue_delta_max_abs_all": float(np.abs(delta).max()),
        "late_revenue_delta_mean": float(late_delta.mean()) if len(late_delta) else 0.0,
        "late_revenue_delta_abs_mean": float(np.abs(late_delta).mean()) if len(late_delta) else 0.0,
        "late_revenue_delta_max_abs": float(np.abs(late_delta).max()) if len(late_delta) else 0.0,
        "late_revenue_delta_pct_mean": (
            float(np.mean(late_delta / np.maximum(late_anchor, 1.0))) if len(late_delta) else 0.0
        ),
        "cogs_delta_max_abs": 0.0,
        "donor_rel_clamp": DONOR_REL_CLAMP,
        "donor_abs_clamp": DONOR_ABS_CLAMP,
        "final_rel_clamp": FINAL_REL_CLAMP,
        "final_abs_clamp": FINAL_ABS_CLAMP,
    }
    return output, summary


def load_direct_summary() -> pd.DataFrame | None:
    if not DIRECT_SUMMARY_PATH.exists():
        return None
    df = pd.read_csv(DIRECT_SUMMARY_PATH)
    if "gate_pass" in df.columns:
        df["gate_pass"] = df["gate_pass"].astype(str).str.lower().eq("true")
    return df


def write_report(
    run_dir: Path,
    summary_df: pd.DataFrame,
    direct_summary: pd.DataFrame | None,
    published_paths: list[Path],
) -> None:
    gate_lines = []
    if direct_summary is not None:
        gate_cols = [
            c
            for c in [
                "candidate_id",
                "gate_pass",
                "c_combined_oof",
                "anchor_combined_oof",
                "c_recent_weighted",
                "anc_recent_weighted",
                "c_late_rev",
                "anc_late_rev",
            ]
            if c in direct_summary.columns
        ]
        gate_lines = direct_summary[gate_cols].to_markdown(index=False).splitlines()

    best_shape = summary_df.sort_values(
        ["late_revenue_delta_abs_mean", "blend_weight"],
        ascending=[True, True],
    ).head(9)
    shape_cols = [
        "candidate_id",
        "rows_blended",
        "late_revenue_delta_mean",
        "late_revenue_delta_abs_mean",
        "late_revenue_delta_max_abs",
        "late_revenue_delta_pct_mean",
    ]

    report = [
        "# Direct-v2 Late Hybrid Probe",
        "",
        "Default output is logs-only. COGS is frozen from the recencyexp20 anchor.",
        "",
        "## Clamp",
        "",
        f"- Donor Revenue clamp: +/-{DONOR_REL_CLAMP:.0%}, capped at {DONOR_ABS_CLAMP:,.0f}.",
        f"- Final Revenue clamp: +/-{FINAL_REL_CLAMP:.0%}, capped at {FINAL_ABS_CLAMP:,.0f}.",
        "",
        "## Existing Direct-v2 Gate",
        "",
    ]
    if gate_lines:
        report.extend(gate_lines)
    else:
        report.append("No direct-v2 summary was found; no offline gate is available.")

    report.extend(
        [
            "",
            "## Most Conservative Generated Shapes",
            "",
            best_shape[shape_cols].to_markdown(index=False),
            "",
            "## Publish Status",
            "",
        ]
    )
    if published_paths:
        report.extend(f"- Published explicit probe: `{path.as_posix()}`" for path in published_paths)
    else:
        report.append("- Nothing was published into `dataset/`.")

    report.extend(
        [
            "",
            "## Files",
            "",
            "- `summary.csv`: all generated probe shape metrics.",
            "- `submissions/`: log-scoped candidate CSVs.",
        ]
    )
    (run_dir / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    run_dir = create_run_dir()
    submissions_dir = run_dir / "submissions"

    anchor = read_submission(args.anchor_path)
    direct_paths = sorted(args.direct_dir.glob(DIRECT_GLOB))
    if not direct_paths:
        raise FileNotFoundError(f"No direct submissions found in {args.direct_dir} matching {DIRECT_GLOB}")

    direct_summary = load_direct_summary()
    if direct_summary is not None:
        direct_summary.to_csv(run_dir / "direct_v2_source_summary.csv", index=False)

    all_summaries: list[dict] = []
    published_paths: list[Path] = []

    for direct_path in direct_paths:
        direct = read_submission(direct_path)
        source_id = direct_id_from_path(direct_path)

        for late_cut in LATE_CUTS:
            for weight in BLEND_WEIGHTS:
                submission, summary = make_hybrid(anchor, direct, source_id, late_cut, weight)
                candidate_id = summary["candidate_id"]
                out_path = submissions_dir / f"submission_probe_{candidate_id}.csv"
                submission.to_csv(out_path, index=False)
                summary["log_output_path"] = out_path.as_posix()
                all_summaries.append(summary)

                if args.publish_probes:
                    dataset_path = DATASET_DIR / out_path.name
                    shutil.copyfile(out_path, dataset_path)
                    summary["dataset_output_path"] = dataset_path.as_posix()
                    published_paths.append(dataset_path)
                else:
                    summary["dataset_output_path"] = ""

    summary_df = pd.DataFrame(all_summaries)
    summary_df.to_csv(run_dir / "summary.csv", index=False)

    config = {
        "anchor_path": args.anchor_path.as_posix(),
        "direct_dir": args.direct_dir.as_posix(),
        "direct_glob": DIRECT_GLOB,
        "late_cuts": list(LATE_CUTS),
        "blend_weights": list(BLEND_WEIGHTS),
        "donor_rel_clamp": DONOR_REL_CLAMP,
        "donor_abs_clamp": DONOR_ABS_CLAMP,
        "final_rel_clamp": FINAL_REL_CLAMP,
        "final_abs_clamp": FINAL_ABS_CLAMP,
        "publish_probes": bool(args.publish_probes),
        "direct_summary_path": DIRECT_SUMMARY_PATH.as_posix(),
    }
    (run_dir / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    write_report(run_dir, summary_df, direct_summary, published_paths)

    print(f"Run dir: {run_dir}")
    print(f"Generated candidates: {len(summary_df)}")
    print(f"Published to dataset: {len(published_paths)}")
    print(f"Summary: {run_dir / 'summary.csv'}")
    print(f"Report: {run_dir / 'report.md'}")


if __name__ == "__main__":
    main()
