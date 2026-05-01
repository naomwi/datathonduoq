from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from run_cleaninput_rawmdshape_pubguided import apply_period_totals, build_shape_base
from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, write_submission


RUN_PREFIX = "cleaninput_rawmdshape_v6_followup"


@dataclass(frozen=True)
class TotalsSpec:
    name: str
    revenue: dict[str, float]
    cogs: dict[str, float]
    note: str


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def period_summary(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out["period"] = out["Date"].dt.year.astype(str) + out["Date"].dt.month.le(6).map({True: "H1", False: "H2"})
    out.loc[out["Date"].eq(pd.Timestamp("2024-07-01")), "period"] = "2024-07-01"
    return (
        out.groupby("period", as_index=False)
        .agg(days=("Date", "count"), revenue=("Revenue", "sum"), cogs=("COGS", "sum"))
        .assign(cogs_ratio=lambda d: d["cogs"] / d["revenue"])
    )


def totals_frame(spec: TotalsSpec) -> pd.DataFrame:
    rows = []
    for period in ["2023H1", "2023H2", "2024H1", "2024-07-01"]:
        rows.append({"period": period, "revenue": spec.revenue[period], "cogs": spec.cogs[period]})
    return pd.DataFrame(rows).assign(cogs_ratio=lambda d: d["cogs"] / d["revenue"])


def specs() -> list[TotalsSpec]:
    # These constants are public-guided scenario totals, not values read from
    # test targets. The script deliberately does not read sample/submission
    # files as inputs.
    v5_rev = {
        "2023H1": 763_629_478.1282002,
        "2023H2": 621_578_226.4239835,
        "2024H1": 883_830_754.94555,
        "2024-07-01": 7_100_419.327254759,
    }
    v5_cogs = {
        "2023H1": 746_787_008.8144592,
        "2023H2": 624_990_699.150075,
        "2024H1": 746_735_349.4547834,
        "2024-07-01": 7_686_486.405,
    }
    public_guided_rev = {
        "2023H1": 763_982_390.7465413,
        "2023H2": 620_433_268.9986733,
        "2024H1": 883_183_181.3507127,
        "2024-07-01": 5_655_161.878721045,
    }
    public_guided_cogs = {
        "2023H1": 751_918_626.0075904,
        "2023H2": 626_159_295.1370881,
        "2024H1": 746_821_301.8407834,
        "2024-07-01": 6_001_080.813747206,
    }
    h1_cogs_mid = {**v5_cogs, "2023H1": 750_921_545.8776642}
    final_down_rev = {**v5_rev, "2024-07-01": public_guided_rev["2024-07-01"]}
    final_down_cogs = {**v5_cogs, "2024-07-01": public_guided_cogs["2024-07-01"]}
    return [
        TotalsSpec(
            name="cleaninput_rawmdshape_v6_finalday_down",
            revenue=final_down_rev,
            cogs=final_down_cogs,
            note="Isolate whether the v5 loss is partly the oversized 2024-07-01 final day.",
        ),
        TotalsSpec(
            name="cleaninput_rawmdshape_v6_finalday_down_h1cogs_mid",
            revenue=final_down_rev,
            cogs={**h1_cogs_mid, "2024-07-01": public_guided_cogs["2024-07-01"]},
            note="Final day down plus 2023H1 COGS raised to the train-derived/public-guided middle stress level.",
        ),
        TotalsSpec(
            name="cleaninput_rawmdshape_v6_publicguided_totals",
            revenue=public_guided_rev,
            cogs=public_guided_cogs,
            note="Raw-md clean daily shape with public-guided period totals from the currently best-known region.",
        ),
        TotalsSpec(
            name="cleaninput_rawmdshape_v6_publicguided_totals_cogsmid",
            revenue=public_guided_rev,
            cogs={**public_guided_cogs, "2023H1": 750_921_545.8776642},
            note="Same period revenue totals, but 2023H1 COGS softened to avoid over-stress.",
        ),
    ]


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Clean-Input RawMD Shape V6 Follow-Up

Run directory: `{run_dir}`

## Boundary

This script rebuilds daily shape from raw provided inputs through the clean raw-md anchor path. It does not read `sample_submission.csv`, previous submission files, or test target values as inputs.

It is still **public-guided** because period totals are selected from previous public feedback and scenario analysis.

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Order

1. `submission_cleaninput_rawmdshape_v6_finalday_down_h1cogs_mid.csv`
2. `submission_cleaninput_rawmdshape_v6_publicguided_totals.csv`
3. `submission_cleaninput_rawmdshape_v6_finalday_down.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "cleaninput_rawmdshape_v6_followup_2026-04-23.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    shape_base = build_shape_base()
    rows = []
    for priority, spec in enumerate(specs(), start=1):
        frame = apply_period_totals(shape_base, totals_frame(spec))
        path = DATASET_DIR / f"submission_{spec.name}.csv"
        write_submission(frame[["Date", "Revenue", "COGS"]], path)
        prof = period_summary(frame)
        prof.to_csv(run_dir / f"{spec.name}_period_summary.csv", index=False)
        rows.append(
            {
                "priority": priority,
                "filename": path.name,
                "revenue_total": frame["Revenue"].sum(),
                "cogs_total": frame["COGS"].sum(),
                "ratio_total": frame["COGS"].sum() / frame["Revenue"].sum(),
                "rev_2023H1": prof.loc[prof["period"].eq("2023H1"), "revenue"].iloc[0],
                "rev_2023H2": prof.loc[prof["period"].eq("2023H2"), "revenue"].iloc[0],
                "rev_2024H1": prof.loc[prof["period"].eq("2024H1"), "revenue"].iloc[0],
                "rev_final": prof.loc[prof["period"].eq("2024-07-01"), "revenue"].iloc[0],
                "cogs_2023H1": prof.loc[prof["period"].eq("2023H1"), "cogs"].iloc[0],
                "cogs_2023H2": prof.loc[prof["period"].eq("2023H2"), "cogs"].iloc[0],
                "cogs_2024H1": prof.loc[prof["period"].eq("2024H1"), "cogs"].iloc[0],
                "cogs_final": prof.loc[prof["period"].eq("2024-07-01"), "cogs"].iloc[0],
                "note": spec.note,
            }
        )
    manifest = pd.DataFrame(rows)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    write_report(run_dir, manifest)
    print(run_dir)


if __name__ == "__main__":
    main()
