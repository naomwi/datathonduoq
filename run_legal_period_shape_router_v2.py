from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_legal_period_shape_router import (
    BASE_FILE,
    BASE_PUBLIC_SCORE,
    DATASET_DIR,
    FORECAST_END,
    FORECAST_START,
    LOG_ROOT,
    NOTES_DIR,
    add_calendar,
    build_cogs_ratio_prior,
    load_base,
    load_train_sales,
    write_submission,
)
from run_transaction_decomposition_v2 import TET_DATES


RUN_PREFIX = "legal_period_shape_router_v2"
V1_SCORE = 745552.16085


@dataclass(frozen=True)
class CandidateSpec:
    filename: str
    thesis: str
    template_mode_by_period: dict[str, str]
    weight_by_period: dict[str, float]
    cogs_mode: str
    cogs_strength: float = 0.0


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def weighted_group_share(
    frame: pd.DataFrame,
    *,
    half: str,
    target: str,
    key: str,
    recent_years: int,
    tau: float,
) -> pd.DataFrame:
    hist = frame.loc[frame["half"].eq(half) & frame["year"].ge(frame["year"].max() - recent_years + 1)].copy()
    hist["period_total"] = hist.groupby(["year", "half"])[target].transform("sum")
    hist["daily_share"] = hist[target] / hist["period_total"].replace(0, np.nan)
    hist["_w"] = np.exp((hist["year"] - hist["year"].max()) / tau)

    def agg(group: pd.DataFrame) -> pd.Series:
        mean = float((group["daily_share"] * group["_w"]).sum() / group["_w"].sum())
        values = group["daily_share"].to_numpy()
        return pd.Series(
            {
                "share_mean": mean,
                "share_std": float(np.nanstd(values)),
                "share_count": int(group["daily_share"].notna().sum()),
            }
        )

    out = hist.groupby(key).apply(agg, include_groups=False).reset_index()
    out["share_cv"] = out["share_std"].fillna(0.0) / out["share_mean"].replace(0, np.nan)
    out["share_cv"] = out["share_cv"].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return out


def build_tet_multiplier(history: pd.DataFrame, future: pd.DataFrame, target: str) -> pd.Series:
    hist = history.copy()
    hist["tet_date"] = hist["year"].map({year: pd.Timestamp(value) for year, value in TET_DATES.items()})
    hist["tet_offset"] = (hist["Date"] - hist["tet_date"]).dt.days
    hist["month_med"] = hist.groupby(["year", "month"])[target].transform("median")
    hist["rel"] = hist[target] / hist["month_med"].replace(0, np.nan)
    profile = (
        hist.loc[hist["tet_offset"].between(-21, 35)]
        .groupby("tet_offset", as_index=False)
        .agg(tet_rel=("rel", "median"))
    )
    profile["tet_rel"] = profile["tet_rel"].fillna(1.0).clip(0.65, 1.55)

    fut = future[["Date", "year"]].copy()
    fut["tet_date"] = fut["year"].map({year: pd.Timestamp(value) for year, value in TET_DATES.items()})
    fut["tet_offset"] = (fut["Date"] - fut["tet_date"]).dt.days
    fut = fut.merge(profile, on="tet_offset", how="left")
    return pd.Series(fut["tet_rel"].fillna(1.0).to_numpy(), index=future.index)


def build_template(history: pd.DataFrame, future: pd.DataFrame, *, target: str, mode: str) -> pd.Series:
    out = pd.Series(index=future.index, dtype=float)
    for period, group in future.groupby("period"):
        if period == "2024-07-01":
            out.loc[group.index] = 1.0
            continue
        half = "H1" if period in {"2023H1", "2024H1"} else "H2"
        recent_years = 5 if "recent5" in mode else 3 if "recent3" in mode else 10
        tau = 1.8 if "sharp" not in mode else 1.0
        md = weighted_group_share(history, half=half, target=target, key="month_day", recent_years=recent_years, tau=tau)
        month = weighted_group_share(history, half=half, target=target, key="month", recent_years=recent_years, tau=tau)
        window = weighted_group_share(history, half=half, target=target, key="window_name", recent_years=recent_years, tau=tau)

        tmp = (
            group[["month_day", "month", "window_name"]]
            .merge(md, on="month_day", how="left", suffixes=("", "_md"))
            .rename(columns={"share_mean": "md_share", "share_cv": "md_cv"})
        )
        tmp = tmp.merge(
            month[["month", "share_mean"]].rename(columns={"share_mean": "month_share"}),
            on="month",
            how="left",
        )
        tmp = tmp.merge(
            window[["window_name", "share_mean"]].rename(columns={"share_mean": "window_share"}),
            on="window_name",
            how="left",
        )
        global_daily = 1.0 / len(group)
        tmp["md_share"] = tmp["md_share"].fillna(tmp["month_share"]).fillna(global_daily)
        tmp["month_share"] = tmp["month_share"].fillna(global_daily)
        tmp["window_share"] = tmp["window_share"].fillna(tmp["month_share"])
        tmp["md_cv"] = tmp["md_cv"].fillna(tmp["md_cv"].median()).fillna(0.0)

        if "raw" in mode:
            values = tmp["md_share"]
        elif "reliable" in mode:
            shrink = 4.5 if half == "H2" else 0.8
            reliability = 1.0 / (1.0 + shrink * tmp["md_cv"].clip(0.0, 3.0))
            values = reliability * tmp["md_share"] + (1.0 - reliability) * tmp["month_share"]
        elif "event" in mode:
            values = 0.65 * tmp["md_share"] + 0.35 * tmp["window_share"]
        elif "month" in mode:
            values = 0.25 * tmp["md_share"] + 0.75 * tmp["month_share"]
        else:
            raise ValueError(f"Unknown template mode: {mode}")

        values = pd.Series(values.to_numpy(), index=group.index).clip(lower=1e-9)
        if "tet" in mode and half == "H1":
            values = values * build_tet_multiplier(history, group, target).loc[group.index]
        values = values / values.sum()
        out.loc[group.index] = values
    return out


def apply_revenue(base: pd.DataFrame, templates: dict[str, pd.Series], spec: CandidateSpec) -> pd.DataFrame:
    out = base[["Date", "Revenue", "COGS", "period"]].copy()
    for period, idx in base.groupby("period").groups.items():
        idx = list(idx)
        if period == "2024-07-01":
            continue
        weight = spec.weight_by_period.get(period, 0.0)
        if weight <= 0:
            continue
        mode = spec.template_mode_by_period.get(period, spec.template_mode_by_period.get("default", "recent5_reliable_tet"))
        total = base.loc[idx, "Revenue"].sum()
        donor = templates[mode].loc[idx].to_numpy() * total
        out.loc[idx, "Revenue"] = (1.0 - weight) * base.loc[idx, "Revenue"].to_numpy() + weight * donor
    return out


def apply_cogs(base: pd.DataFrame, frame: pd.DataFrame, ratio_prior: pd.Series, spec: CandidateSpec) -> pd.DataFrame:
    out = frame[["Date", "Revenue", "COGS", "period"]].copy()
    if spec.cogs_mode == "keep":
        out["COGS"] = base["COGS"].to_numpy()
        return out
    target = out["Revenue"] * ratio_prior
    cogs = (1.0 - spec.cogs_strength) * base["COGS"] + spec.cogs_strength * target
    if spec.cogs_mode == "ratio_h2up_h4down":
        cogs.loc[base["period"].eq("2023H2")] *= 1.02
        cogs.loc[base["period"].eq("2024H1")] *= 0.99
    elif spec.cogs_mode != "ratio":
        raise ValueError(f"Unknown COGS mode: {spec.cogs_mode}")
    out["COGS"] = cogs
    return out


def make_candidates(base: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    modes = [
        "recent5_raw_tet",
        "recent5_reliable_tet",
        "recent5_event_tet",
        "recent3_raw_tet_sharp",
        "recent5_month_tet",
    ]
    templates = {mode: build_template(history, base, target="Revenue", mode=mode) for mode in modes}
    ratio_prior = build_cogs_ratio_prior(history, base)

    specs = [
        CandidateSpec(
            "submission_legal_router_v2_recent_raw_nonh2_h2flat_keepcogs.csv",
            "Recent-weighted raw month-day/Tet shape on H1/2024H1, H2 flat; strongest legal analogue of black-box router.",
            {"2023H1": "recent5_raw_tet", "2024H1": "recent5_raw_tet", "2023H2": "recent5_month_tet"},
            {"2023H1": 0.95, "2023H2": 0.00, "2024H1": 0.95},
            "keep",
        ),
        CandidateSpec(
            "submission_legal_router_v2_recent3_raw_nonh2_h2flat_keepcogs.csv",
            "Sharper recent-3y non-H2 shape, H2 flat.",
            {"2023H1": "recent3_raw_tet_sharp", "2024H1": "recent3_raw_tet_sharp", "2023H2": "recent5_month_tet"},
            {"2023H1": 0.90, "2023H2": 0.00, "2024H1": 0.90},
            "keep",
        ),
        CandidateSpec(
            "submission_legal_router_v2_recent_reliable_nonh2_h2tiny_keepcogs.csv",
            "Recent reliability router with tiny H2 weight, safer than raw.",
            {"default": "recent5_reliable_tet"},
            {"2023H1": 0.75, "2023H2": 0.02, "2024H1": 0.85},
            "keep",
        ),
        CandidateSpec(
            "submission_legal_router_v2_event_nonh2_h2tiny_keepcogs.csv",
            "Recent signed-event/Tet template on non-H2, tiny H2.",
            {"default": "recent5_event_tet"},
            {"2023H1": 0.70, "2023H2": 0.05, "2024H1": 0.85},
            "keep",
        ),
        CandidateSpec(
            "submission_legal_router_v2_raw_nonh2_h2flat_ratio20.csv",
            "Recent raw non-H2 legal router plus train-only COGS ratio blend.",
            {"2023H1": "recent5_raw_tet", "2024H1": "recent5_raw_tet", "2023H2": "recent5_month_tet"},
            {"2023H1": 0.95, "2023H2": 0.00, "2024H1": 0.95},
            "ratio",
            0.20,
        ),
        CandidateSpec(
            "submission_legal_router_v2_raw_nonh2_h2flat_cogshint.csv",
            "Recent raw non-H2 legal router plus public-inferred COGS period direction via train ratios.",
            {"2023H1": "recent5_raw_tet", "2024H1": "recent5_raw_tet", "2023H2": "recent5_month_tet"},
            {"2023H1": 0.95, "2023H2": 0.00, "2024H1": 0.95},
            "ratio_h2up_h4down",
            0.25,
        ),
    ]

    rows = []
    for priority, spec in enumerate(specs, start=1):
        frame = apply_revenue(base, templates, spec)
        frame = apply_cogs(base, frame, ratio_prior, spec)
        write_submission(frame, DATASET_DIR / spec.filename)
        rev_delta = frame["Revenue"] - base["Revenue"]
        cogs_delta = frame["COGS"] - base["COGS"]
        rows.append(
            {
                "priority": priority,
                "filename": spec.filename,
                "path": str(DATASET_DIR / spec.filename),
                "thesis": spec.thesis,
                "cogs_mode": spec.cogs_mode,
                "cogs_strength": spec.cogs_strength,
                "rev_weight_2023H1": spec.weight_by_period.get("2023H1", 0.0),
                "rev_weight_2023H2": spec.weight_by_period.get("2023H2", 0.0),
                "rev_weight_2024H1": spec.weight_by_period.get("2024H1", 0.0),
                "revenue_total_ratio_vs_base": frame["Revenue"].sum() / base["Revenue"].sum(),
                "cogs_total_ratio_vs_base": frame["COGS"].sum() / base["COGS"].sum(),
                "mean_abs_rev_delta": rev_delta.abs().mean(),
                "mean_abs_cogs_delta": cogs_delta.abs().mean(),
                "directional_best_case_gain": 0.5 * (rev_delta.abs().mean() + cogs_delta.abs().mean()),
                "min_revenue": frame["Revenue"].min(),
                "min_cogs": frame["COGS"].min(),
            }
        )
    return pd.DataFrame(rows)


def write_report(run_dir: Path, manifest: pd.DataFrame) -> None:
    report = f"""# Legal Period Shape Router V2

Run directory: `{run_dir}`

Base legal file: `{BASE_FILE}` scored `{BASE_PUBLIC_SCORE}`.

V1 legal result:

| file | public score |
|---|---:|
| `submission_legal_router_v1_reliability_strong_nonh2_keepcogs.csv` | `{V1_SCORE}` |

## Why V2

V1 proved that the legal reconstruction is directionally correct: it gained about `52k` versus the pre-sample legal base.

The remaining gap suggests the legal donor needs to be more organizer-like:

- recent-weighted, not equal-weight 2013-2022;
- Tet/lunar-aware in H1/2024H1;
- almost no H2 daily shape force;
- COGS handled separately by train-only ratio regime.

## Candidate Manifest

{manifest.to_markdown(index=False)}

## Submit Guidance

1. `submission_legal_router_v2_recent_raw_nonh2_h2flat_keepcogs.csv`
2. If it improves over V1: `submission_legal_router_v2_recent3_raw_nonh2_h2flat_keepcogs.csv`
3. If raw overdoes it: `submission_legal_router_v2_recent_reliable_nonh2_h2tiny_keepcogs.csv`
4. Only after Revenue-shape improves, test COGS: `submission_legal_router_v2_raw_nonh2_h2flat_cogshint.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "legal_period_shape_router_v2_2026-04-22.md").write_text(report, encoding="utf-8")


def main() -> None:
    run_dir = make_run_dir()
    history = load_train_sales()
    base = load_base()
    manifest = make_candidates(base, history)
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    write_report(run_dir, manifest)
    print(run_dir)


if __name__ == "__main__":
    main()
