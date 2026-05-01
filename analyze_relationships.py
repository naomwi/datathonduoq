from __future__ import annotations

from pathlib import Path

import pandas as pd

from feature_pipeline import TRAIN_END, build_daily_base


OUT_DIR = Path("outputs/analysis")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    base = build_daily_base()
    train = base[base["Date"] <= pd.Timestamp(TRAIN_END)].copy()

    summary = train[["Revenue", "COGS"]].describe().T
    summary.to_csv(OUT_DIR / "target_summary.csv")

    corr_candidates = [
        "Revenue",
        "COGS",
        "order_count",
        "unique_customers",
        "total_units",
        "gross_margin",
        "total_discount",
        "promo_line_share",
        "promo_2_share",
        "avg_discount_rate",
        "aov_proxy",
        "margin_rate",
        "return_qty",
        "refund_amt",
        "review_count",
        "avg_rating",
        "sessions",
        "unique_visitors",
        "page_views",
        "bounce_rate",
        "avg_session_duration_sec",
        "active_promo_count",
        "active_stackable_promo_count",
        "stock_on_hand",
        "units_received",
        "units_sold",
        "stockout_days_avg",
        "days_of_supply_avg",
        "fill_rate_avg",
        "stockout_rate",
        "overstock_rate",
        "sell_through_rate_avg",
    ]
    corr_candidates += [col for col in train.columns if col.startswith(("traffic_share_", "category_rev_share_", "segment_rev_share_"))]
    corr_candidates = [col for col in corr_candidates if col in train.columns]

    revenue_corr = (
        train[corr_candidates]
        .corr(numeric_only=True)["Revenue"]
        .drop("Revenue")
        .sort_values(ascending=False)
        .rename("corr_with_revenue")
        .to_frame()
    )
    revenue_corr.to_csv(OUT_DIR / "revenue_correlations.csv")

    lag_signals = [
        "sessions",
        "unique_visitors",
        "page_views",
        "order_count",
        "unique_customers",
        "total_units",
        "total_discount",
        "promo_line_share",
        "return_qty",
        "refund_amt",
        "review_count",
        "stockout_rate",
        "fill_rate_avg",
        "days_of_supply_avg",
        "sell_through_rate_avg",
    ]

    lag_rows: list[dict[str, float | int | str]] = []
    for signal in lag_signals:
        if signal not in train.columns:
            continue
        for lag in range(0, 29):
            lag_rows.append(
                {
                    "signal": signal,
                    "lag": lag,
                    "corr_with_revenue": train["Revenue"].corr(train[signal].shift(lag)),
                }
            )
    lag_df = pd.DataFrame(lag_rows)
    lag_df.to_csv(OUT_DIR / "lag_correlation_grid.csv", index=False)

    best_lag = lag_df.loc[
        lag_df.groupby("signal")["corr_with_revenue"].apply(lambda s: s.abs().idxmax())
    ].sort_values("corr_with_revenue", key=lambda s: s.abs(), ascending=False)
    best_lag.to_csv(OUT_DIR / "best_signal_lags.csv", index=False)

    autocorr_rows = []
    for lag in [1, 2, 3, 4, 5, 6, 7, 14, 21, 28, 35, 42, 56, 84, 91, 182, 364, 365, 728, 730]:
        autocorr_rows.append(
            {
                "lag": lag,
                "revenue_autocorr": train["Revenue"].corr(train["Revenue"].shift(lag)),
                "cogs_autocorr": train["COGS"].corr(train["COGS"].shift(lag)),
            }
        )
    autocorr = pd.DataFrame(autocorr_rows)
    autocorr.to_csv(OUT_DIR / "target_autocorrelation.csv", index=False)

    month_profile = train.groupby(train["Date"].dt.month)["Revenue"].mean().rename("avg_revenue")
    dow_profile = train.groupby(train["Date"].dt.dayofweek)["Revenue"].mean().rename("avg_revenue")
    month_profile.to_csv(OUT_DIR / "revenue_by_month.csv")
    dow_profile.to_csv(OUT_DIR / "revenue_by_dayofweek.csv")

    report_path = OUT_DIR / "relationship_report.md"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Data Relationship Analysis\n\n")
        f.write("## Target Summary\n")
        f.write(summary.to_markdown())
        f.write("\n\n")

        f.write("## Strongest Same-day Relationships with Revenue\n")
        f.write(revenue_corr.head(15).to_markdown())
        f.write("\n\n")
        f.write("## Weakest / Negative Same-day Relationships with Revenue\n")
        f.write(revenue_corr.tail(12).to_markdown())
        f.write("\n\n")

        f.write("## Best Lag per Signal\n")
        f.write(best_lag.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Revenue / COGS Autocorrelation\n")
        f.write(autocorr.to_markdown(index=False))
        f.write("\n\n")

        f.write("## Seasonality\n")
        f.write("### Average Revenue by Month\n")
        f.write(month_profile.to_frame().to_markdown())
        f.write("\n\n")
        f.write("### Average Revenue by Day of Week\n")
        f.write(dow_profile.to_frame().to_markdown())
        f.write("\n\n")

        f.write("## Feature Engineering Decisions\n")
        f.write("- Keep dense target-history features: short lags, 4-week lags, and yearly lags.\n")
        f.write("- Add lagged order / customer / unit signals because they are the strongest business-side drivers.\n")
        f.write("- Add short-horizon traffic lag and rolling features because traffic has weak but consistent leading signal.\n")
        f.write("- Add delayed return / refund features because the relationship peaks after about 10 days.\n")
        f.write("- Add category and segment revenue-share history to capture product-mix shifts.\n")
        f.write("- Add inventory regime features with as-of alignment because inventory is monthly and should not leak future snapshots.\n")
        f.write("- Keep promotions as intensity / share features, but use them as lagged history rather than same-day realized promo usage.\n")

    print(f"Saved analysis report to {report_path}")


if __name__ == "__main__":
    main()
