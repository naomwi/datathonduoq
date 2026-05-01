# Clean V2 Deep EDA - 2026-04-24

Run directory: `logs\20260424_110621_clean_v2_train_evidence`

## Boundary

This EDA uses source/train data only. It does not use `sample_submission.csv` or previous submissions as inputs.

## Executive Read

1. `2019` remains the structural break: Revenue drops together with orders/conversion, not because traffic disappears.
2. H1 is the cleaner recovery candidate: H1 has better shape stability than H2 and should support a train-derived regime recovery head.
3. H2 Revenue is noisy: broad or localized H2 Revenue freedom is hard to justify cleanly; the EDA supports stronger H2 shrinkage.
4. COGS deserves its own ratio model: COGS/Revenue ratio has period-specific dispersion that Revenue-only modeling cannot capture.
5. Promotions are useful, but `promotions.csv` ends at `2022-12-31`; clean test-period promo features must be train-derived recurring priors, not direct future schedules.
6. Traffic, order source, returns, shipments, reviews, and future item mix are strong diagnostics but must be forecasted or summarized from train history before they can be clean features.

## Source Coverage

| file            |   rows |   columns | date_cols               | min_date            | max_date            |   null_cells |
|:----------------|-------:|----------:|:------------------------|:--------------------|:--------------------|-------------:|
| sales.csv       |   3833 |         3 | Date                    | 2012-07-04 00:00:00 | 2022-12-31 00:00:00 |            0 |
| orders.csv      | 646945 |         8 | order_date              | 2012-07-04 00:00:00 | 2022-12-31 00:00:00 |            0 |
| order_items.csv | 714669 |         7 |                         | NaT                 | NaT                 |      1152816 |
| payments.csv    | 646945 |         4 |                         | NaT                 | NaT                 |            0 |
| shipments.csv   | 566067 |         4 | ship_date,delivery_date | 2012-07-04 00:00:00 | 2022-12-31 00:00:00 |            0 |
| returns.csv     |  39939 |         7 | return_date             | 2012-07-11 00:00:00 | 2022-12-31 00:00:00 |            0 |
| reviews.csv     | 113551 |         7 | review_date             | 2012-07-10 00:00:00 | 2022-12-31 00:00:00 |            0 |
| web_traffic.csv |   3652 |         7 | date                    | 2013-01-01 00:00:00 | 2022-12-31 00:00:00 |            0 |
| promotions.csv  |     50 |        10 | start_date,end_date     | 2013-01-31 00:00:00 | 2022-12-31 00:00:00 |           40 |
| inventory.csv   |  60247 |        17 | snapshot_date           | 2012-07-31 00:00:00 | 2022-12-31 00:00:00 |            0 |
| products.csv    |   2412 |         8 |                         | NaT                 | NaT                 |            0 |
| customers.csv   | 121930 |         7 | signup_date             | 2012-01-17 00:00:00 | 2022-12-31 00:00:00 |            0 |
| geography.csv   |  39948 |         4 |                         | NaT                 | NaT                 |            0 |

## Forecast Safety Audit

| source          | policy                      | reason                                                                                                                               | min_date            | max_date            |   rows |
|:----------------|:----------------------------|:-------------------------------------------------------------------------------------------------------------------------------------|:--------------------|:--------------------|-------:|
| calendar        | future-known                | Generated from forecast dates; safe.                                                                                                 | NaT                 | NaT                 |    nan |
| promotions.csv  | train-only-recurring-policy | Provided promo history ends before test; safe only as train-derived recurring priors, not direct future schedule or realized uplift. | 2013-01-31 00:00:00 | 2022-12-31 00:00:00 |     50 |
| products.csv    | mostly-static               | Safe for product attributes if treated as catalog metadata; price/cogs history must not be inferred as future actuals.               | NaT                 | NaT                 |   2412 |
| orders.csv      | unknown-future              | Future orders are the outcome pathway; use only train-derived summaries or forecasted policies.                                      | 2012-07-04 00:00:00 | 2022-12-31 00:00:00 | 646945 |
| order_items.csv | unknown-future              | Future item mix and quantities are target-adjacent; use only train-derived priors.                                                   | NaT                 | NaT                 | 714669 |
| payments.csv    | unknown-future              | Payment amount follows orders; not future-known.                                                                                     | NaT                 | NaT                 | 646945 |
| web_traffic.csv | unknown-future              | Useful driver historically, but future traffic must be forecasted or policy-imputed.                                                 | 2013-01-01 00:00:00 | 2022-12-31 00:00:00 |   3652 |
| inventory.csv   | policy-imputed              | Inventory snapshots can be operational plans only if provided for future; otherwise train-only.                                      | 2012-07-31 00:00:00 | 2022-12-31 00:00:00 |  60247 |
| returns.csv     | post-outcome                | Return dates lag orders and are not valid future drivers for target submission.                                                      | 2012-07-11 00:00:00 | 2022-12-31 00:00:00 |  39939 |
| reviews.csv     | post-outcome                | Reviews lag orders and should be treated as diagnostic only.                                                                         | 2012-07-10 00:00:00 | 2022-12-31 00:00:00 | 113551 |
| shipments.csv   | post-outcome                | Shipment and delivery are downstream of orders; diagnostic only.                                                                     | 2012-07-04 00:00:00 | 2022-12-31 00:00:00 | 566067 |
| customers.csv   | partial-future-risk         | Signup history is useful; future customer acquisitions must be forecasted.                                                           | 2012-01-17 00:00:00 | 2022-12-31 00:00:00 | 121930 |

## Annual Breaks

|   year |     revenue |   revenue_yoy |   orders |   orders_yoy |    sessions |   sessions_yoy |   conversion |   conversion_yoy |     aov |      aov_yoy |   cogs_ratio |
|-------:|------------:|--------------:|---------:|-------------:|------------:|---------------:|-------------:|-----------------:|--------:|-------------:|-------------:|
|   2017 | 1.91116e+09 |    -0.0919284 |    76010 |   -0.0758326 | 8.9926e+06  |     0.0701148  |   0.0084525  |       -0.136385  | 25143.6 | -0.0174166   |     0.886573 |
|   2018 | 1.85012e+09 |    -0.0319396 |    69510 |   -0.0855151 | 9.41508e+06 |     0.0469812  |   0.00738283 |       -0.126551  | 26616.6 |  0.0585854   |     0.833553 |
|   2019 | 1.1368e+09  |    -0.385553  |    41601 |   -0.401511  | 9.99015e+06 |     0.0610789  |   0.0041642  |       -0.435961  | 27326.3 |  0.0266624   |     0.884238 |
|   2020 | 1.05451e+09 |    -0.0723867 |    34881 |   -0.161535  | 1.05911e+07 |     0.0601527  |   0.00329343 |       -0.209109  | 30231.7 |  0.106323    |     0.84028  |
|   2021 | 1.04304e+09 |    -0.0108793 |    34525 |   -0.0102061 | 1.09917e+07 |     0.0378283  |   0.003141   |       -0.0462836 | 30211.1 | -0.000680098 |     0.902295 |
|   2022 | 1.16975e+09 |     0.121481  |    36004 |    0.0428385 | 1.10637e+07 |     0.00654429 |   0.00325426 |        0.0360583 | 32489.4 |  0.0754115   |     0.872341 |

## Recent Half-Year Periods

| period   |   days |     revenue |        cogs |   cogs_ratio |   orders |    sessions |   conversion |     aov |   discount_rate |   promo_line_share |
|:---------|-------:|------------:|------------:|-------------:|---------:|------------:|-------------:|--------:|----------------:|-------------------:|
| 2019H1   |    181 | 6.97133e+08 | 5.75869e+08 |     0.826053 |    23250 | 5.52578e+06 |   0.00420755 | 29984.2 |       0.0321534 |           0.290964 |
| 2019H2   |    184 | 4.39669e+08 | 4.29334e+08 |     0.976494 |    18351 | 4.46437e+06 |   0.00411055 | 23958.9 |       0.0745941 |           0.650557 |
| 2020H1   |    182 | 6.05371e+08 | 4.99077e+08 |     0.824415 |    19559 | 5.92407e+06 |   0.00330162 | 30951   |       0.0325842 |           0.274345 |
| 2020H2   |    184 | 4.49141e+08 | 3.87008e+08 |     0.861662 |    15322 | 4.66702e+06 |   0.00328304 | 29313.5 |       0.0638509 |           0.484078 |
| 2021H1   |    181 | 6.32182e+08 | 5.28017e+08 |     0.835229 |    19930 | 6.10512e+06 |   0.00326447 | 31720.1 |       0.0323382 |           0.29731  |
| 2021H2   |    184 | 4.10858e+08 | 4.13114e+08 |     1.00549  |    14595 | 4.8866e+06  |   0.00298674 | 28150.6 |       0.0763817 |           0.650483 |
| 2022H1   |    181 | 6.9245e+08  | 5.93828e+08 |     0.857575 |    20765 | 6.16574e+06 |   0.0033678  | 33347   |       0.0317498 |           0.275739 |
| 2022H2   |    184 | 4.77298e+08 | 4.26592e+08 |     0.893764 |    15239 | 4.89791e+06 |   0.00311132 | 31320.9 |       0.0680006 |           0.502723 |

## Era Shift: Recent Low vs Pre-2019 High

| half   | metric           |    pre2019_high |      recent_low |   recent_vs_pre2019_pct |
|:-------|:-----------------|----------------:|----------------:|------------------------:|
| H1     | revenue          |     1.10197e+09 |     6.56784e+08 |             -0.403993   |
| H1     | cogs             |     9.11652e+08 |     5.49198e+08 |             -0.39758    |
| H1     | orders           | 43160.8         | 20876           |             -0.516321   |
| H1     | sessions         |     4.50005e+06 |     5.93018e+06 |              0.317804   |
| H1     | conversion       |     0.00969724  |     0.00353536  |             -0.635426   |
| H1     | aov              | 25510.2         | 31500.6         |              0.234823   |
| H1     | cogs_ratio       |     0.827136    |     0.835818    |              0.0104968  |
| H1     | discount_rate    |     0.0309792   |     0.0322064   |              0.0396145  |
| H1     | promo_line_share |     0.273009    |     0.28459     |              0.0424205  |
| H2     | revenue          |     7.78839e+08 |     4.44242e+08 |             -0.42961    |
| H2     | cogs             |     7.08873e+08 |     4.14012e+08 |             -0.415957   |
| H2     | orders           | 34819.7         | 15876.8         |             -0.544029   |
| H2     | sessions         |     3.63594e+06 |     4.72898e+06 |              0.300619   |
| H2     | conversion       |     0.00978396  |     0.00337291  |             -0.655261   |
| H2     | aov              | 22586.5         | 28185.9         |              0.247914   |
| H2     | cogs_ratio       |     0.911765    |     0.934353    |              0.0247737  |
| H2     | discount_rate    |     0.0719711   |     0.0707068   |             -0.0175665  |
| H2     | promo_line_share |     0.566523    |     0.57196     |              0.00959648 |

## Seasonality Stability

Daily shape correlation:

| half   |   pairwise_corr_mean |   pairwise_corr_median |   pairwise_corr_min |   pairwise_corr_max |   pairs |
|:-------|---------------------:|-----------------------:|--------------------:|--------------------:|--------:|
| H1     |             0.798129 |               0.787989 |            0.667978 |            0.926871 |      45 |
| H2     |             0.707719 |               0.700258 |            0.550647 |            0.903723 |      45 |

Monthly share stability:

| half   |   month |   revenue_share_mean |   revenue_share_std |   revenue_share_cv |   cogs_share_mean |   cogs_share_std |   cogs_share_cv |
|:-------|--------:|---------------------:|--------------------:|-------------------:|------------------:|-----------------:|----------------:|
| H1     |       1 |             0.086682 |          0.00952177 |          0.109847  |         0.0846913 |       0.00948812 |       0.112032  |
| H1     |       2 |             0.107085 |          0.00834659 |          0.0779434 |         0.104609  |       0.00871991 |       0.083357  |
| H1     |       3 |             0.16853  |          0.0161189  |          0.0956443 |         0.174198  |       0.0165557  |       0.0950398 |
| H1     |       4 |             0.212106 |          0.0144492  |          0.0681227 |         0.216325  |       0.0149779  |       0.0692379 |
| H1     |       5 |             0.219412 |          0.0103827  |          0.0473207 |         0.211693  |       0.0106519  |       0.0503177 |
| H1     |       6 |             0.206186 |          0.017827   |          0.0864608 |         0.208484  |       0.0181809  |       0.0872053 |
| H2     |       7 |             0.224189 |          0.0199764  |          0.089105  |         0.222481  |       0.017887   |       0.0803975 |
| H2     |       8 |             0.209857 |          0.0496913  |          0.236787  |         0.231807  |       0.0161757  |       0.0697809 |
| H2     |       9 |             0.175741 |          0.0135088  |          0.076868  |         0.172204  |       0.00946739 |       0.0549778 |
| H2     |      10 |             0.157826 |          0.0120374  |          0.0762699 |         0.138154  |       0.00595035 |       0.0430703 |
| H2     |      11 |             0.1178   |          0.0127289  |          0.108054  |         0.111611  |       0.00815698 |       0.0730843 |
| H2     |      12 |             0.114587 |          0.015379   |          0.134213  |         0.123743  |       0.01543    |       0.124694  |

## COGS Ratio Dispersion

| half   |   cogs_ratio_mean |   cogs_ratio_std |   cogs_ratio_p10 |   cogs_ratio_p50 |   cogs_ratio_p90 |   revenue_daily_cv |
|:-------|------------------:|-----------------:|-----------------:|-----------------:|-----------------:|-------------------:|
| H1     |          0.826102 |        0.0501367 |         0.782132 |         0.809712 |         0.908974 |           0.587074 |
| H2     |          0.930412 |        0.158761  |         0.788467 |         0.894566 |         1.05016  |           0.569904 |

## Revenue Driver Correlations

| target   | feature            |      corr |   abs_corr |
|:---------|:-------------------|----------:|-----------:|
| Revenue  | COGS               |  0.976022 |   0.976022 |
| Revenue  | orders             |  0.937662 |   0.937662 |
| Revenue  | units              |  0.92159  |   0.92159  |
| Revenue  | conversion         |  0.626526 |   0.626526 |
| Revenue  | fill_rate          | -0.432997 |   0.432997 |
| Revenue  | refund_rate        | -0.322824 |   0.322824 |
| Revenue  | sessions           |  0.32105  |   0.32105  |
| Revenue  | cogs_ratio         | -0.166735 |   0.166735 |
| Revenue  | promo_discount_max | -0.143281 |   0.143281 |
| Revenue  | discount_rate      | -0.13983  |   0.13983  |
| Revenue  | stockout_flag      |  0.13709  |   0.13709  |
| Revenue  | promo_line_share   | -0.117435 |   0.117435 |

## COGS Ratio Driver Correlations

| target     | feature            |       corr |   abs_corr |
|:-----------|:-------------------|-----------:|-----------:|
| cogs_ratio | promo_discount_max |  0.920865  |  0.920865  |
| cogs_ratio | active_promo_count |  0.645899  |  0.645899  |
| cogs_ratio | promo_line_share   |  0.593691  |  0.593691  |
| cogs_ratio | aov                | -0.556592  |  0.556592  |
| cogs_ratio | revenue_per_unit   | -0.519235  |  0.519235  |
| cogs_ratio | discount_rate      |  0.442612  |  0.442612  |
| cogs_ratio | Revenue            | -0.166735  |  0.166735  |
| cogs_ratio | refund_rate        |  0.098439  |  0.098439  |
| cogs_ratio | sessions           |  0.0522558 |  0.0522558 |
| cogs_ratio | units              |  0.0411217 |  0.0411217 |
| cogs_ratio | orders             |  0.0349482 |  0.0349482 |
| cogs_ratio | conversion         |  0.0297273 |  0.0297273 |

## Category / Segment Mix Shifts

| half   | category   |   share_pre2019_high |   share_recent_low |   item_cogs_ratio_pre2019_high |   item_cogs_ratio_recent_low | dimension   |   share_delta_recent_minus_pre | segment     |
|:-------|:-----------|---------------------:|-------------------:|-------------------------------:|-----------------------------:|:------------|-------------------------------:|:------------|
| H2     | nan        |             0.282039 |          0.451981  |                       0.923027 |                     0.95431  | segment     |                      0.169942  | Balanced    |
| H1     | nan        |             0.255711 |          0.424404  |                       0.830617 |                     0.831767 | segment     |                      0.168692  | Balanced    |
| H2     | nan        |             0.33628  |          0.23282   |                       0.927332 |                     0.932537 | segment     |                     -0.10346   | Everyday    |
| H1     | nan        |             0.367079 |          0.265755  |                       0.820775 |                     0.827351 | segment     |                     -0.101324  | Everyday    |
| H2     | Outdoor    |             0.183983 |          0.117474  |                       0.859234 |                     0.87115  | category    |                     -0.0665085 | nan         |
| H2     | nan        |             0.153612 |          0.0904551 |                       0.84775  |                     0.849441 | segment     |                     -0.0631564 | Activewear  |
| H1     | Outdoor    |             0.151119 |          0.103843  |                       0.818609 |                     0.830255 | category    |                     -0.0472766 | nan         |
| H2     | Streetwear |             0.768087 |          0.812853  |                       0.928322 |                     0.951085 | category    |                      0.0447657 | nan         |
| H1     | nan        |             0.171313 |          0.128871  |                       0.845684 |                     0.859494 | segment     |                     -0.0424414 | Performance |
| H1     | nan        |             0.124391 |          0.0838972 |                       0.805174 |                     0.805909 | segment     |                     -0.0404939 | Activewear  |
| H1     | Streetwear |             0.80736  |          0.83545   |                       0.827845 |                     0.836267 | category    |                      0.0280895 | nan         |
| H2     | nan        |             0.135868 |          0.110984  |                       0.951637 |                     0.96226  | segment     |                     -0.0248833 | Performance |

## Promotion Calendar

|   year | half   |   active_days |   avg_promo_count |   max_promo_count |   avg_discount_max |   max_discount |   stackable_days |
|-------:|:-------|--------------:|------------------:|------------------:|-------------------:|---------------:|-----------------:|
|   2017 | H1     |            72 |           1       |                 1 |            14.1806 |             20 |                0 |
|   2017 | H2     |           131 |           1.03053 |                 2 |            25.3893 |             50 |               34 |
|   2018 | H1     |            41 |           1       |                 1 |            13.561  |             20 |                0 |
|   2018 | H2     |            99 |           1       |                 1 |            16.2222 |             20 |                0 |
|   2019 | H1     |            72 |           1       |                 1 |            14.1806 |             20 |               62 |
|   2019 | H2     |           130 |           1.03077 |                 2 |            25.5077 |             50 |                0 |
|   2020 | H1     |            41 |           1       |                 1 |            13.561  |             20 |                0 |
|   2020 | H2     |            99 |           1       |                 1 |            16.2222 |             20 |                0 |
|   2021 | H1     |            71 |           1       |                 1 |            14.0986 |             20 |               39 |
|   2021 | H2     |           131 |           1.03053 |                 2 |            25.3893 |             50 |               66 |
|   2022 | H1     |            41 |           1       |                 1 |            13.561  |             20 |               33 |
|   2022 | H2     |            98 |           1       |                 1 |            16.2857 |             20 |                0 |

## Missing Insights For Clean V2

### 1. The model needs a funnel decomposition, not only a target decomposition

The structural break is better explained by:

- sessions
- conversion
- orders
- AOV
- units per order

than by calendar alone. A clean model should not necessarily forecast these future actuals directly, but it can use train-derived regime priors for conversion and AOV.

### 2. H1 recovery should be justified through conversion/AOV recovery

Blackbox said `2023H1 Revenue` was undercalled. EDA gives a cleaner explanation path:

- H1 shape is more stable.
- recent-low years understate high-regime H1 level.
- recovery can be described as a conversion/order-count recovery, not an arbitrary Revenue multiplier.

### 3. H2 should be regularized because its shape is less stable

H2 has weaker daily shape stability and stronger ratio noise. This supports H2 shrinkage and smaller H2 Revenue residual caps.

### 4. COGS ratio head should be trained separately

The COGS ratio dispersion table supports a dedicated ratio target. This is cleaner than moving COGS by hand after Revenue prediction.

### 5. Promo history is underused, but not future-known

`promotions.csv` contains historical promo windows only. This still helps: recurring month-day promo intensity, discount seasonality, and stackable-promo priors can be learned from train. The clean branch should not claim direct knowledge of 2023-2024 promo schedules unless a separate future promo plan is provided.

### 6. Inventory is risky

Inventory is operationally meaningful but its future availability must be audited. It should not be used as a future feature unless the future snapshots are explicitly part of the provided input scenario.

## Clean V2 Actions

1. Add train-derived H1 recovery features based on pre-2019 vs recent-low gaps.
2. Add H2 residual caps and compare against unrestricted H2 residuals.
3. Build a separate `COGS / Revenue` ratio model.
4. Use train-derived recurring promo priors from `promotions.csv`, not realized promo usage or assumed future schedules.
5. Keep traffic/order/returns/reviews as diagnostic or forecasted-policy features, not direct future inputs.
