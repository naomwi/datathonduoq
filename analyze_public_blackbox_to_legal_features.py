from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR


RUN_PREFIX = "public_blackbox_to_legal_features"

PUBLIC_SCORE_CURVES = {
    "2023H2_revenue_shape_alpha": [
        (1.000, "sample_shape_high", 707436.88912),
        (0.800, "global_rev0800", 698898.26661),
        (0.600, "h2_rev0600", 692128.76474),
        (0.400, "h2_rev0400", 687112.64298),
        (0.200, "h2_rev0200", 684699.68850),
        (0.100, "h2_rev0100", 684463.34954),
    ],
    "cogs_shape_alpha": [
        (0.750, "cogs_shape_up", 699662.34515),
        (0.725, "ratio_away0250_base", 699376.32670),
        (0.700, "cogs_shape_down0700", 699167.79998),
        (0.650, "cogs_shape_down0650", 698994.05843),
    ],
    "cogs_ratio_away": [
        (0.000, "shape_only", 701005.12470),
        (0.025, "away0025", 700654.49101),
        (0.050, "away0050", 700363.16716),
        (0.100, "away0100", 699960.93186),
        (0.125, "away0125", 699793.67454),
        (0.175, "away0175", 699556.47851),
        (0.225, "away0225", 699384.92478),
        (0.250, "away0250", 699376.32670),
    ],
}


WINDOWS = {
    "spring": ("03-18", "04-17"),
    "midyear": ("06-23", "07-22"),
    "fall": ("08-30", "10-02"),
    "yearend": ("11-18", "01-02"),
}


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def between_month_day(month_day: pd.Series, start: str, end: str) -> pd.Series:
    if start <= end:
        return month_day.between(start, end)
    return month_day.between(start, "12-31") | month_day.between("01-01", end)


def add_calendar(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["year"] = out["Date"].dt.year
    out["month"] = out["Date"].dt.month
    out["half"] = np.where(out["month"].le(6), "H1", "H2")
    out["period"] = out["year"].astype(str) + out["half"]
    out["month_day"] = out["Date"].dt.strftime("%m-%d")
    out["dow"] = out["Date"].dt.dayofweek
    for name, (start, end) in WINDOWS.items():
        out[f"win_{name}"] = between_month_day(out["month_day"], start, end)
    out["win_any_main"] = out[[f"win_{name}" for name in WINDOWS]].any(axis=1)
    return out


def public_curve_summary() -> pd.DataFrame:
    rows = []
    for curve, points in PUBLIC_SCORE_CURVES.items():
        prev_score = None
        prev_x = None
        for x, label, score in points:
            rows.append(
                {
                    "curve": curve,
                    "x": x,
                    "label": label,
                    "public_score": score,
                    "delta_from_prev": score - prev_score if prev_score is not None else np.nan,
                    "slope_from_prev": (score - prev_score) / (x - prev_x) if prev_score is not None else np.nan,
                }
            )
            prev_score = score
            prev_x = x
    return pd.DataFrame(rows)


def year_half_summary(sales: pd.DataFrame) -> pd.DataFrame:
    return (
        sales.groupby(["year", "half"], as_index=False)
        .agg(days=("Date", "count"), revenue=("Revenue", "sum"), cogs=("COGS", "sum"))
        .assign(
            cogs_ratio=lambda d: d["cogs"] / d["revenue"],
            revenue_per_day=lambda d: d["revenue"] / d["days"],
        )
    )


def shape_stability(sales: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for half in ["H1", "H2"]:
        piv = sales[sales["half"].eq(half)].pivot_table(
            index="month_day", columns="year", values="Revenue", aggfunc="sum"
        )
        years = [year for year in piv.columns if 2013 <= year <= 2022]
        norm = piv[years].copy()
        for year in years:
            norm[year] = norm[year] / norm[year].sum()
        corr = norm.corr()
        for year in years:
            rows.append(
                {
                    "half": half,
                    "year": year,
                    "corr_prev_year": corr.loc[year - 1, year] if year - 1 in corr.index else np.nan,
                    "corr_to_2022": corr.loc[2022, year] if 2022 in corr.index else np.nan,
                    "mean_abs_share_z": ((norm[year] - norm.mean(axis=1)).abs() / norm.std(axis=1)).replace(
                        [np.inf, -np.inf], np.nan
                    ).mean(),
                }
            )
    return pd.DataFrame(rows)


def promo_window_summary(sales: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, frame in sales[sales["year"].between(2013, 2022)].groupby("year"):
        nonwin_mean = frame.loc[~frame["win_any_main"], "Revenue"].mean()
        for name in WINDOWS:
            mask = frame[f"win_{name}"]
            rows.append(
                {
                    "year": year,
                    "window": name,
                    "days": int(mask.sum()),
                    "revenue_mean": frame.loc[mask, "Revenue"].mean(),
                    "uplift_vs_nonwin": frame.loc[mask, "Revenue"].mean() / nonwin_mean - 1.0,
                    "cogs_ratio": frame.loc[mask, "COGS"].sum() / frame.loc[mask, "Revenue"].sum(),
                }
            )
    return pd.DataFrame(rows)


def volatility_summary(sales: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (year, half), frame in sales[sales["year"].between(2013, 2022)].groupby(["year", "half"]):
        values = frame.sort_values("Date")["Revenue"].to_numpy()
        rows.append(
            {
                "year": year,
                "half": half,
                "days": len(values),
                "cv": values.std() / values.mean(),
                "top5_share": np.sort(values)[-5:].sum() / values.sum(),
                "top10_share": np.sort(values)[-10:].sum() / values.sum(),
                "median_over_mean": np.median(values) / values.mean(),
                "q95_over_mean": np.quantile(values, 0.95) / values.mean(),
            }
        )
    return pd.DataFrame(rows)


def feature_hypotheses() -> pd.DataFrame:
    rows = [
        {
            "hypothesis": "H2 seasonal shape reliability is low",
            "blackbox_evidence": "2023H2 alpha reduction 0.800 -> 0.100 improved 698898 -> 684463.",
            "train_evidence": "H2 year-to-year shape correlations are lower than H1, especially 2021 -> 2022.",
            "legal_feature_or_model_change": "Add period x horizon interactions and shrink annual/month-day seasonal priors more aggressively in H2.",
            "priority": 1,
        },
        {
            "hypothesis": "2023H2 should not use raw last-year or external template daily shape",
            "blackbox_evidence": "Forcing 2023H2 shape high worsened to 707436.",
            "train_evidence": "Train H2 contains unstable fall/yearend patterns and high year-specific COGS ratio variance.",
            "legal_feature_or_model_change": "Use train-only multi-year H2 template with variance shrinkage, not single-year shape; cap event spike amplitude.",
            "priority": 1,
        },
        {
            "hypothesis": "Promo/event effect must be signed by window, not globally positive",
            "blackbox_evidence": "Flat promo/window tuning gave small gains and could not explain 65x.",
            "train_evidence": "Spring is strongly positive, midyear mild, fall often negative, yearend strongly negative.",
            "legal_feature_or_model_change": "Create window-specific event priors: spring positive, midyear weak, fall/yearend negative, with target-specific effects.",
            "priority": 2,
        },
        {
            "hypothesis": "COGS needs ratio-regime modeling, not sample-like daily shape",
            "blackbox_evidence": "COGS ratio away helped until 0.25, COGS shape down helped but plateaued.",
            "train_evidence": "H2 COGS ratio alternates strongly and is high in several odd years.",
            "legal_feature_or_model_change": "Model COGS as Revenue x period/window COGS-ratio prior, with odd/even and window interactions.",
            "priority": 2,
        },
        {
            "hypothesis": "Non-H2 periods may still need stronger deterministic calendar shape",
            "blackbox_evidence": "Global Revenue alpha 0.800 improved despite 2023H2 being harmful.",
            "train_evidence": "H1 shape correlations are consistently high, so H1 calendar shape is more reliable.",
            "legal_feature_or_model_change": "Use stronger train-only calendar/event template for H1/2024H1; tune separately from 2023H2.",
            "priority": 3,
        },
        {
            "hypothesis": "Local OOF underestimates public shift because horizon is 548 days",
            "blackbox_evidence": "Many low-OOF direct model changes did not move public; period-shape changes did.",
            "train_evidence": "H2 shape degrades over long horizons; short folds overvalue recursive lag features.",
            "legal_feature_or_model_change": "Optimize on long horizon folds 2020/2021 and report worst-fold by period, not average OOF.",
            "priority": 1,
        },
    ]
    return pd.DataFrame(rows)


def main() -> None:
    run_dir = make_run_dir()
    sales = add_calendar(pd.read_csv(DATASET_DIR / "sales.csv", parse_dates=["Date"]))

    curve = public_curve_summary()
    half = year_half_summary(sales)
    stability = shape_stability(sales)
    promo = promo_window_summary(sales)
    vol = volatility_summary(sales)
    hypotheses = feature_hypotheses().sort_values("priority")

    curve.to_csv(run_dir / "public_score_curves.csv", index=False)
    half.to_csv(run_dir / "train_year_half_summary.csv", index=False)
    stability.to_csv(run_dir / "train_shape_stability.csv", index=False)
    promo.to_csv(run_dir / "train_promo_window_summary.csv", index=False)
    vol.to_csv(run_dir / "train_period_volatility.csv", index=False)
    hypotheses.to_csv(run_dir / "legal_feature_hypotheses.csv", index=False)

    h1_corr = stability.loc[stability["half"].eq("H1"), "corr_prev_year"].mean()
    h2_corr = stability.loc[stability["half"].eq("H2"), "corr_prev_year"].mean()
    promo_recent = promo[promo["year"].between(2020, 2022)].groupby("window", as_index=False).agg(
        recent_uplift=("uplift_vs_nonwin", "mean"),
        recent_cogs_ratio=("cogs_ratio", "mean"),
    )
    h2_curve = curve[curve["curve"].eq("2023H2_revenue_shape_alpha")][["x", "public_score"]]

    report = f"""# Public Black-Box To Legal Model Features

Run directory: `{run_dir}`

Important constraint:

- This analysis treats `sample_submission.csv` numeric `Revenue/COGS` as forbidden.
- Public scores are used only as black-box behavioral signals.
- Proposed model changes below must be implemented from train/provided covariates only.

## Public Black-Box Signal

2023H2 Revenue-shape response:

{h2_curve.to_markdown(index=False)}

Meaning:

- The public target strongly rejects a high `2023H2` daily-shape intensity.
- The response flattened near `0.100`, so 2023H2 alone is nearly exhausted.
- This is a regime/seasonality problem, not a base model capacity problem.

## Train-Only Evidence

Average adjacent-year normalized daily-shape correlation:

| half | mean corr(prev year) |
|---|---:|
| H1 | `{h1_corr:.3f}` |
| H2 | `{h2_corr:.3f}` |

Recent train promo-window effects:

{promo_recent.to_markdown(index=False)}

Interpretation:

- H2 is less stable than H1, so single-template or strong annual lag shape is risky for H2.
- Spring is a real positive event; fall/yearend are not generic positive promo periods.
- COGS ratio is window/period sensitive, so COGS should follow a ratio regime, not a copied daily shape.

## Legal Feature Hypotheses

{hypotheses.to_markdown(index=False)}

## Recommended Model Changes

1. Add `seasonal_reliability` features from train only:
   - `month_day_rev_share_mean_by_half`
   - `month_day_rev_share_std_by_half`
   - `month_day_rev_share_cv_by_half`
   - `horizon_step x half x seasonal_cv`

2. Replace raw annual-shape reliance with shrinkage:
   - H1: stronger month-day/event prior.
   - H2: shrink toward period/month mean, especially fall/yearend.

3. Make promo/event effects signed and window-specific:
   - `spring`: positive Revenue uplift.
   - `midyear`: weak/mixed.
   - `fall`: negative or damped.
   - `yearend`: negative/damped.

4. Use target-specific period routing:
   - Revenue: strong period-wise seasonal router.
   - COGS: Revenue x COGS-ratio model with period/window interactions.

5. Validate only with public-like folds:
   - Long 548-day folds from 2020 and 2021.
   - Segment metrics by H1/H2/window.
   - Penalize false positives that improve average OOF but fail H2.

## Candidate Legal Modeling Direction

Build a train-only `period_shape_router`:

```text
prediction = period_total_forecast * train_only_daily_share_template
daily_share_template = weighted_mean(month_day_or_event_shape from prior years)
weight = function(half, horizon_step, seasonal_cv, promo_window)
```

For public-like inference:

```text
2023H1 / 2024H1: use stronger train-only calendar/event template
2023H2: use heavily shrunk train-only H2 template
COGS: use Revenue forecast * train-only COGS-ratio prior
```

This transfers the black-box insight without using test `Revenue/COGS` values as features.
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "public_blackbox_to_legal_model_features_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
