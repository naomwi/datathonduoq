from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from logging_utils import create_run_dir, setup_logger, write_json


RUN_PREFIX = "public_router_eom_challengers"
DATASET_DIR = Path("dataset")
LOGS_DIR = Path("logs")
ROUTER_RUN_DIR = LOGS_DIR / "20260420_185314_public_revenue_router_v1"
ROUTER_SUBMISSION_PATH = DATASET_DIR / "submission_public_revenue_router_v1_clip.csv"
ROUTER_OOF_PATH = ROUTER_RUN_DIR / "oof_daily_predictions.csv"
TAIL_FOLDS = [2, 3]

VARIANTS = [
    {
        "candidate_id": "public_router_v1_eom_day1_12pct",
        "mode": "day_ratio",
        "day_ratio_override": {1: 1.12},
        "blend_strength": 1.0,
        "min_ratio": 1.0,
        "max_ratio": 1.20,
        "thesis": "Minimal specialist: only uplift the second-to-last day of each month.",
    },
    {
        "candidate_id": "public_router_v1_eom_tail_soft",
        "mode": "day_ratio",
        "blend_strength": 0.60,
        "min_ratio": 1.0,
        "max_ratio": 1.25,
        "thesis": "Use tail-fold day-level EOM uplifts with conservative 60% strength.",
    },
    {
        "candidate_id": "public_router_v1_eom_tail_full",
        "mode": "day_ratio",
        "blend_strength": 1.0,
        "min_ratio": 1.0,
        "max_ratio": 1.25,
        "thesis": "Use full day-level EOM uplift learned from the 2021-2022 tail folds.",
    },
    {
        "candidate_id": "public_router_v1_eom_monthday_shrunk",
        "mode": "monthday_ratio",
        "blend_strength": 0.70,
        "min_ratio": 0.95,
        "max_ratio": 1.28,
        "prior_strength": 4.0,
        "thesis": "Month-aware EOM uplift with strong shrinkage back to the day-level prior.",
    },
]


def add_days_to_eom(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out["month"] = out["Date"].dt.month
    out["days_to_eom"] = (out["Date"] + pd.offsets.MonthEnd(0) - out["Date"]).dt.days
    return out


def load_router_oof() -> pd.DataFrame:
    df = pd.read_csv(ROUTER_OOF_PATH, parse_dates=["Date"])
    df = df[df["candidate_id"] == "public_revenue_router_v1_clip"].copy()
    df["ratio_true_pred"] = df["Revenue_true"] / df["Revenue_pred"].replace(0.0, np.nan)
    return add_days_to_eom(df)


def build_tail_ratio_tables(oof_df: pd.DataFrame) -> tuple[dict[int, float], pd.DataFrame]:
    tail = oof_df[oof_df["fold"].isin(TAIL_FOLDS)].copy()
    eom_tail = tail[tail["days_to_eom"] <= 2].copy()
    day_ratio = (
        eom_tail.groupby("days_to_eom")["ratio_true_pred"]
        .median()
        .clip(lower=1.0, upper=1.30)
        .to_dict()
    )
    monthday = (
        eom_tail.groupby(["month", "days_to_eom"])["ratio_true_pred"]
        .agg(["median", "count"])
        .reset_index()
        .rename(columns={"median": "monthday_ratio"})
    )
    monthday["day_ratio"] = monthday["days_to_eom"].map(day_ratio)
    monthday["monthday_ratio"] = monthday["monthday_ratio"].clip(lower=0.85, upper=1.45)
    return {int(k): float(v) for k, v in day_ratio.items()}, monthday


def resolve_ratio_series(
    df: pd.DataFrame,
    *,
    mode: str,
    day_ratio: dict[int, float],
    monthday_table: pd.DataFrame,
    blend_strength: float,
    min_ratio: float,
    max_ratio: float,
    prior_strength: float = 0.0,
    day_ratio_override: dict[int, float] | None = None,
) -> pd.Series:
    base_day_ratio = day_ratio.copy()
    if day_ratio_override:
        for key, value in day_ratio_override.items():
            base_day_ratio[int(key)] = float(value)

    resolved = pd.Series(1.0, index=df.index, dtype=float)
    eom_mask = df["days_to_eom"] <= 2
    resolved.loc[eom_mask] = df.loc[eom_mask, "days_to_eom"].map(base_day_ratio).fillna(1.0).astype(float)

    if mode == "monthday_ratio":
        lookup = monthday_table.copy()
        lookup["shrunk_ratio"] = (
            lookup["monthday_ratio"] * lookup["count"] + lookup["day_ratio"] * prior_strength
        ) / (lookup["count"] + prior_strength)
        monthday_lookup = lookup.set_index(["month", "days_to_eom"])["shrunk_ratio"].to_dict()
        monthday_values = [
            float(monthday_lookup.get((int(month), int(days_to_eom)), base_day_ratio.get(int(days_to_eom), 1.0)))
            for month, days_to_eom in zip(df["month"], df["days_to_eom"], strict=False)
        ]
        resolved = pd.Series(monthday_values, index=df.index, dtype=float)
        resolved.loc[~eom_mask] = 1.0

    blended = 1.0 + blend_strength * (resolved - 1.0)
    return blended.clip(lower=min_ratio, upper=max_ratio)


def apply_variant_to_frame(
    df: pd.DataFrame,
    *,
    ratio_series: pd.Series,
) -> pd.DataFrame:
    out = df.copy()
    out["Revenue_pred"] = (out["Revenue_pred"] * ratio_series).clip(lower=0.0)
    return out


def evaluate_variant(pred_df: pd.DataFrame) -> dict[str, float]:
    eval_df = pred_df.copy()
    eval_df["rev_abs_err"] = (eval_df["Revenue_pred"] - eval_df["Revenue_true"]).abs()
    eval_df["cogs_abs_err"] = (eval_df["COGS_pred"] - eval_df["COGS_true"]).abs()
    tail_mask = eval_df["fold"].isin(TAIL_FOLDS)
    eom_mask = eval_df["days_to_eom"] <= 2
    return {
        "revenue_mae_mean": float(eval_df["rev_abs_err"].mean()),
        "combined_mae_mean": float(0.5 * (eval_df["rev_abs_err"].mean() + eval_df["cogs_abs_err"].mean())),
        "tail_revenue_mae_mean": float(eval_df.loc[tail_mask, "rev_abs_err"].mean()),
        "tail_combined_mae_mean": float(
            0.5 * (eval_df.loc[tail_mask, "rev_abs_err"].mean() + eval_df.loc[tail_mask, "cogs_abs_err"].mean())
        ),
        "eom_revenue_mae_mean": float(eval_df.loc[eom_mask, "rev_abs_err"].mean()),
        "non_eom_revenue_mae_mean": float(eval_df.loc[~eom_mask, "rev_abs_err"].mean()),
        "tail_eom_revenue_mae_mean": float(eval_df.loc[tail_mask & eom_mask, "rev_abs_err"].mean()),
        "tail_non_eom_revenue_mae_mean": float(eval_df.loc[tail_mask & ~eom_mask, "rev_abs_err"].mean()),
    }


def write_report(
    run_dir: Path,
    day_ratio: dict[int, float],
    summary_df: pd.DataFrame,
    variant_eval_df: pd.DataFrame,
) -> None:
    report_path = run_dir / "report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Public Router EOM Challengers\n\n")
        f.write("## Framing\n")
        f.write("- Base public anchor: `submission_public_revenue_router_v1_clip.csv`\n")
        f.write("- Adjustment scope: Revenue only, days_to_eom <= 2\n")
        f.write("- Learning signal: OOF for `public_revenue_router_v1_clip`, tail folds 2021-2022 only\n")
        f.write(f"- Tail day-level ratios learned from OOF: `{day_ratio}`\n\n")
        f.write("## Variant Summary\n")
        f.write(summary_df.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Variant Evaluation Rows\n")
        f.write(variant_eval_df.to_markdown(index=False))
        f.write("\n")


def main() -> None:
    run_dir = create_run_dir(RUN_PREFIX)
    logger = setup_logger(RUN_PREFIX, run_dir)
    logger.info("Starting public router EOM challengers in %s", run_dir)

    oof_df = load_router_oof()
    day_ratio, monthday_table = build_tail_ratio_tables(oof_df)
    write_json(
        run_dir / "config.json",
        {
            "tail_folds": TAIL_FOLDS,
            "base_submission": str(ROUTER_SUBMISSION_PATH),
            "base_day_ratio": day_ratio,
            "variants": VARIANTS,
        },
    )

    variant_rows: list[dict[str, object]] = []
    for variant in VARIANTS:
        ratio_series = resolve_ratio_series(
            oof_df,
            mode=str(variant["mode"]),
            day_ratio=day_ratio,
            monthday_table=monthday_table,
            blend_strength=float(variant["blend_strength"]),
            min_ratio=float(variant["min_ratio"]),
            max_ratio=float(variant["max_ratio"]),
            prior_strength=float(variant.get("prior_strength", 0.0)),
            day_ratio_override=variant.get("day_ratio_override"),
        )
        eval_df = apply_variant_to_frame(oof_df, ratio_series=ratio_series)
        metrics = evaluate_variant(eval_df)
        variant_rows.append({"candidate_id": variant["candidate_id"], **metrics, "thesis": variant["thesis"]})
        eval_df.to_csv(run_dir / f"oof_{variant['candidate_id']}.csv", index=False)

    summary_df = pd.DataFrame(variant_rows).sort_values(
        ["tail_combined_mae_mean", "tail_revenue_mae_mean", "revenue_mae_mean"]
    ).reset_index(drop=True)
    summary_df.to_csv(run_dir / "summary.csv", index=False)

    public_df = add_days_to_eom(pd.read_csv(ROUTER_SUBMISSION_PATH, parse_dates=["Date"]))
    for variant in VARIANTS:
        ratio_series = resolve_ratio_series(
            public_df,
            mode=str(variant["mode"]),
            day_ratio=day_ratio,
            monthday_table=monthday_table,
            blend_strength=float(variant["blend_strength"]),
            min_ratio=float(variant["min_ratio"]),
            max_ratio=float(variant["max_ratio"]),
            prior_strength=float(variant.get("prior_strength", 0.0)),
            day_ratio_override=variant.get("day_ratio_override"),
        )
        adjusted = public_df.copy()
        adjusted["Revenue"] = (adjusted["Revenue"] * ratio_series).clip(lower=0.0)
        output = adjusted[["Date", "Revenue", "COGS"]].copy()
        output["Date"] = output["Date"].dt.strftime("%Y-%m-%d")
        dataset_path = DATASET_DIR / f"submission_{variant['candidate_id']}.csv"
        run_path = run_dir / f"submission_{variant['candidate_id']}.csv"
        output.to_csv(dataset_path, index=False)
        output.to_csv(run_path, index=False)
        logger.info("Exported %s", variant["candidate_id"])

    write_report(run_dir, day_ratio, summary_df, pd.DataFrame(variant_rows))
    logger.info("Saved summary to %s", run_dir / "summary.csv")
    if not summary_df.empty:
        logger.info("Top variant: %s", summary_df.iloc[0]["candidate_id"])


if __name__ == "__main__":
    main()
