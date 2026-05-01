# Exploratory Data Analysis (EDA) Insights

## 1. Descriptive (What happened?)
- **Revenue Trend**: Over the 10-year span (2012-2022), revenue has shown consistent year-over-year geometric growth, layered with high-variance spikes indicating sudden sales events.
- **Seasonality**: There are distinct weekly cycles, with revenue dropping on weekends. Yearly, certain months show strong cyclical peaks.

## 2. Diagnostic (Why did it happen?)
- **Traffic Funnel**: The web traffic strongly correlates with revenue. Spikes in sessions perfectly match revenue peaks. The causal driver of revenue peaks is directly observable through user volume.
- **Promotions**: The `promo_pct` (percentage of order items bought with a promo code) drives those traffic and revenue spikes. We can visually confirm that intense promotional periods cause immediate massive uplift.
- **Target Reconciliation Insight**: The definition of `Revenue` was proven to be `quantity * unit_price` evaluated precisely on the `order_date`. Cancellations and refunds are completely ignored in the daily `Revenue` metric. We must forecast gross ordered sales, not net realized sales!

## 3. Predictive (What is likely to happen?)
- Extrapolating the historical data using geometric growth (like the baseline) is structurally sound, but adding features for traffic lags, promotion presence, and correct categorical daily indicators (like day-of-week) will dramatically improve accuracy.

## 4. Prescriptive (What should we do?)
- **Modeling**: We must construct a rigorous feature store. The primary exogenous drivers are lag features, seasonal indicators, and trailing traffic.
- **Business Action**: To maximize valid revenue without worrying about cancellations, the business structurally pushes promos to drive traffic. However, long-term health isn't captured by the gross revenue figure, so we might want to optionally monitor returns to provide deeper business value in the report.
