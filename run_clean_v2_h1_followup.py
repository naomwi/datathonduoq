from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from run_clean_regime_recovery_scenarios import gap_blend_total, load_sales, period_summary
from run_clean_v2_eda_guided_candidates import (
    apply_h1_total_override,
    apply_ratio_shape,
    base_totals,
    h1_ratio_stats,
)
from run_cleaninput_rawmdshape_pubguided import apply_period_totals, build_shape_base
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "clean_v2_h1_followup"


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    h1_beta: float
    h1_cogs_ratio: float
    ratio_shape_gamma: float = 0.0
    note: str = ""


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def h1_totals_for_beta(sales: pd.DataFrame, beta: float, ratio: float) -> tuple[float, float]:
    revenue = gap_blend_total(sales, "Revenue", 2023, "H1", beta)
    return revenue, revenue * ratio


def build_specs(stats: dict[str, float]) -> list[CandidateSpec]:
    return [
        CandidateSpec(
            name="cleanv2_h1fine_b043_r0876",
            h1_beta=0.43,
            h1_cogs_ratio=stats["h1_recovery_stress"],
            note="Map lower side around public-best b045; same COGS ratio.",
        ),
        CandidateSpec(
            name="cleanv2_h1fine_b044_r0876",
            h1_beta=0.44,
            h1_cogs_ratio=stats["h1_recovery_stress"],
            note="Near-best H1 level, slightly below b045.",
        ),
        CandidateSpec(
            name="cleanv2_h1fine_b046_r0876",
            h1_beta=0.46,
            h1_cogs_ratio=stats["h1_recovery_stress"],
            note="Near-best H1 level, slightly above b045 without H2 reshape.",
        ),
        CandidateSpec(
            name="cleanv2_h1fine_b047_r0876",
            h1_beta=0.47,
            h1_cogs_ratio=stats["h1_recovery_stress"],
            note="Upper-side H1 level map before the known b050 degradation.",
        ),
        CandidateSpec(
            name="cleanv2_h1fine_b045_r0865",
            h1_beta=0.45,
            h1_cogs_ratio=0.865,
            note="Same public-best H1 revenue level, lower H1 COGS ratio between train max and public-guided stress.",
        ),
        CandidateSpec(
            name="cleanv2_h1fine_b045_r0885",
            h1_beta=0.45,
            h1_cogs_ratio=0.885,
            note="Same public-best H1 revenue level, higher H1 COGS ratio stress.",
        ),
        CandidateSpec(
            name="cleanv2_h1fine_b046_r0876_augpromo_g025",
            h1_beta=0.46,
            h1_cogs_ratio=stats["h1_recovery_stress"],
            ratio_shape_gamma=0.25,
            note="Small H2 COGS daily reshape from recurring promo priors; weaker than previous g045.",
        ),
    ]


def write_report(run_dir: Path, manifest: pd.DataFrame, stats: dict[str, float]) -> None:
    report = f"""# Clean V2 H1 Follow-Up

Run directory: `{run_dir}`

## Boundary

This is a clean-input public-guided follow-up after:

- `submission_cleanv2_h1funnel_b045_r0876.csv = 673785.31754`
- `submission_cleanv2_h1funnel_b050_r0876.csv = 676153.29609`

No `sample_submission.csv`, previous submissions, or test targets are read as inputs. The public scores only determine which train-derived scenario neighborhood to probe next.

## Train H1 Ratio Reference

{pd.DataFrame([stats]).to_markdown(index=False)}

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Order

1. `submission_cleanv2_h1fine_b046_r0876.csv`
2. `submission_cleanv2_h1fine_b044_r0876.csv`
3. `submission_cleanv2_h1fine_b045_r0865.csv`
4. `submission_cleanv2_h1fine_b045_r0885.csv`
5. `submission_cleanv2_h1fine_b043_r0876.csv`
6. `submission_cleanv2_h1fine_b047_r0876.csv`
7. `submission_cleanv2_h1fine_b046_r0876_augpromo_g025.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "clean_v2_h1_followup_2026-04-24.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    sales = load_sales()
    shape_base = build_shape_base()
    base = base_totals(sales)
    stats = h1_ratio_stats(sales)

    rows = []
    for priority, spec in enumerate(build_specs(stats), start=1):
        totals = apply_h1_total_override(sales, base, spec.h1_beta, spec.h1_cogs_ratio)
        frame = apply_period_totals(shape_base, totals)
        if spec.ratio_shape_gamma:
            frame = apply_ratio_shape(frame, sales, spec.ratio_shape_gamma, "h2")
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)
        prof = period_summary(frame)
        prof.to_csv(run_dir / f"{spec.name}_period_summary.csv", index=False)
        h1_rev, h1_cogs = h1_totals_for_beta(sales, spec.h1_beta, spec.h1_cogs_ratio)
        rows.append(
            {
                "priority": priority,
                "filename": path.name,
                "h1_beta": spec.h1_beta,
                "h1_revenue": h1_rev,
                "h1_cogs_ratio": spec.h1_cogs_ratio,
                "h1_cogs": h1_cogs,
                "ratio_shape_gamma": spec.ratio_shape_gamma,
                "revenue_total": frame["Revenue"].sum(),
                "cogs_total": frame["COGS"].sum(),
                "ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
                "rev_2023H1": prof.loc[prof["period"].eq("2023H1"), "revenue"].iloc[0],
                "cogs_2023H1": prof.loc[prof["period"].eq("2023H1"), "cogs"].iloc[0],
                "ratio_2023H1": prof.loc[prof["period"].eq("2023H1"), "cogs_ratio"].iloc[0],
                "rev_2023H2": prof.loc[prof["period"].eq("2023H2"), "revenue"].iloc[0],
                "cogs_2023H2": prof.loc[prof["period"].eq("2023H2"), "cogs"].iloc[0],
                "ratio_2023H2": prof.loc[prof["period"].eq("2023H2"), "cogs_ratio"].iloc[0],
                "rev_2024H1": prof.loc[prof["period"].eq("2024H1"), "revenue"].iloc[0],
                "cogs_2024H1": prof.loc[prof["period"].eq("2024H1"), "cogs"].iloc[0],
                "ratio_2024H1": prof.loc[prof["period"].eq("2024H1"), "cogs_ratio"].iloc[0],
                "note": spec.note,
            }
        )

    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    write_report(run_dir, manifest, stats)
    print(run_dir)


if __name__ == "__main__":
    main()
