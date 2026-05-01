# Missing Big Signal Deep Dive

Run directory: `logs\20260421_235518_missing_big_signal_deep_dive`

## Main Finding
The target is exactly reconstructable from item-level transactions:

| target   | component   |   corr |         mae |     max_abs |        bias |   component_total_ratio |
|:---------|:------------|-------:|------------:|------------:|------------:|------------------------:|
| Revenue  | gross_rev   |      1 | 2.33408e-11 | 1.86265e-09 | 5.92251e-13 |                       1 |
| COGS     | gross_cogs  |      1 | 0.00246005  | 0.00499927  | 1.0993e-05  |                       1 |

This means `Revenue` is gross merchandise value, not net payment after discount, and `COGS` is the sum of `quantity * product.cogs`. The most credible gap to top teams is not TabPFN/CatBoost choice; it is whether the future is modeled as transaction components: order volume, units, unit price, product/category/segment mix, and promo/event calendars.

## Future Raw Coverage
No raw operational table has actual 2023-2024 observations:

| filename        | date_column   |   rows |   nonnull | min_date            | max_date            | has_future_after_2022   |
|:----------------|:--------------|-------:|----------:|:--------------------|:--------------------|:------------------------|
| sales.csv       | Date          |   3833 |      3833 | 2012-07-04 00:00:00 | 2022-12-31 00:00:00 | False                   |
| orders.csv      | order_date    | 646945 |    646945 | 2012-07-04 00:00:00 | 2022-12-31 00:00:00 | False                   |
| shipments.csv   | ship_date     | 566067 |    566067 | 2012-07-04 00:00:00 | 2022-12-29 00:00:00 | False                   |
| shipments.csv   | delivery_date | 566067 |    566067 | 2012-07-06 00:00:00 | 2022-12-31 00:00:00 | False                   |
| returns.csv     | return_date   |  39939 |     39939 | 2012-07-11 00:00:00 | 2022-12-31 00:00:00 | False                   |
| reviews.csv     | review_date   | 113551 |    113551 | 2012-07-10 00:00:00 | 2022-12-31 00:00:00 | False                   |
| web_traffic.csv | date          |   3652 |      3652 | 2013-01-01 00:00:00 | 2022-12-31 00:00:00 | False                   |
| inventory.csv   | snapshot_date |  60247 |     60247 | 2012-07-31 00:00:00 | 2022-12-31 00:00:00 | False                   |
| promotions.csv  | start_date    |     50 |        50 | 2013-01-31 00:00:00 | 2022-11-18 00:00:00 | False                   |
| promotions.csv  | end_date      |     50 |        50 | 2013-03-01 00:00:00 | 2022-12-31 00:00:00 | False                   |
| customers.csv   | signup_date   | 121930 |    121930 | 2012-01-17 00:00:00 | 2022-12-31 00:00:00 | False                   |

So any strong solution must forecast transaction structure, not read future orders/traffic/inventory.

## 2018-2022 Component Regime
|   year |   revenue_per_day |   orders_per_day |   units_per_day |     aov |   units_per_order |   price_per_unit |   cogs_per_unit |   cogs_ratio |   discount_share_gross |
|-------:|------------------:|-----------------:|----------------:|--------:|------------------:|-----------------:|----------------:|-------------:|-----------------------:|
|   2018 |       5.06883e+06 |         190.438  |         925.058 | 26616.6 |           4.85752 |          5479.47 |         4567.43 |     0.833553 |              0.0434562 |
|   2019 |       3.11452e+06 |         113.975  |         555.214 | 27326.3 |           4.87135 |          5609.6  |         4960.22 |     0.884238 |              0.0485677 |
|   2020 |       2.88118e+06 |          95.3033 |         455.956 | 30231.7 |           4.78427 |          6318.98 |         5309.71 |     0.84028  |              0.0459014 |
|   2021 |       2.85764e+06 |          94.589  |         451.351 | 30211.1 |           4.7717  |          6331.31 |         5712.72 |     0.902295 |              0.0496871 |
|   2022 |       3.20479e+06 |          98.6411 |         468.734 | 32489.4 |           4.75192 |          6837.12 |         5964.3  |     0.872341 |              0.0465414 |

Important pattern: volume collapsed after 2018-2019, while `AOV`, `price_per_unit`, and `cogs_per_unit` rose sharply. Direct daily models can fit this locally while still missing the future split between level and mix.

## Product Mix Drift
- 2022 Streetwear revenue share: `0.8383`.
- 2022 Balanced segment revenue share: `0.4885`.
- Streetwear and Balanced have trended up for years; Outdoor/Activewear trended down. This is a plausible COGS-ratio and promo-window lever.

## Lunar Tet Check
Current calendar only knows Jan/Feb, not the moving lunar date. Historical Tet effect is noisy but real enough to keep as a diagnostic family:

| window    |   years |   rev_rel_median |   rev_rel_mean |   cogs_rel_median |   cogs_ratio_median |
|:----------|--------:|-----------------:|---------------:|------------------:|--------------------:|
| post15_35 |      10 |         0.985467 |        0.99025 |          0.963812 |            0.811295 |
| post4_14  |      10 |         0.971925 |        1.03594 |          0.977039 |            0.809718 |
| pre14_1   |      10 |         1.05361  |        1.06392 |          1.05632  |            0.807602 |
| pre7_1    |      10 |         0.99973  |        1.05543 |          0.980052 |            0.807682 |
| tet0_3    |      10 |         1.07767  |        1.15439 |          1.07314  |            0.812749 |
| tet0_6    |      10 |         1.05073  |        1.0929  |          1.05076  |            0.813455 |

This is probably not a single 180k-MAE key by itself, but top solutions likely include exact Vietnamese holiday/event calendars.

## Submission Shape Check
| filename                                            |   rows |   revenue_mean |   cogs_mean |   revenue_total_ratio_vs_best |   cogs_total_ratio_vs_best |   revenue_corr_vs_best |   cogs_corr_vs_best |   mean_abs_revenue_diff_vs_best |   mean_abs_cogs_diff_vs_best |
|:----------------------------------------------------|-------:|---------------:|------------:|------------------------------:|---------------------------:|-----------------------:|--------------------:|--------------------------------:|-----------------------------:|
| submission_promo_cogsratio_bestrev_a010_clip005.csv |    548 |    3.99841e+06 | 3.36726e+06 |                      1        |                   1        |               1        |            1        |                     0           |                         0    |
| submission_tabpfn_promo_windowmix_v1.csv            |    548 |    3.99841e+06 | 3.36148e+06 |                      1        |                   0.998284 |               1        |            0.999981 |                     1.69949e-12 |                      5777.37 |
| submission_public_probe_promo_windows_rev_up8.csv   |    548 |    3.99841e+06 | 3.36148e+06 |                      1        |                   0.998284 |               0.998727 |            0.999981 |                 37463.4         |                      5777.37 |
| submission_catboost_md2y_core_recencyexp20.csv      |    548 |    3.89589e+06 | 3.36148e+06 |                      0.974359 |                   0.998284 |               0.994241 |            0.999981 |                102522           |                      5777.37 |
| submission_public_revenue_gate_v3_soft.csv          |    548 |    3.93285e+06 | 3.36148e+06 |                      0.983604 |                   0.998284 |               0.983143 |            0.999981 |                245432           |                      5777.37 |
| submission_catboost_md2y_core_price_history.csv     |    548 |    3.79498e+06 | 3.29695e+06 |                      0.949123 |                   0.97912  |               0.977072 |            0.98593  |                362129           |                    232629    |
| sample_submission.csv                               |    548 |    3.2498e+06  | 2.78381e+06 |                      0.812772 |                   0.826729 |               0.894188 |            0.90543  |                846290           |                    664796    |

`sample_submission.csv` is far below the current best level, so it is unlikely to be a magic 700k baseline. Its value is only as a weak shape donor after level alignment.

## Decision
The next serious direction should be `transaction-decomposition v2`, not another model swap:

- Build forecasts for `order_count`, `total_units`, `gross_price_per_unit`, and `gross_cogs_per_unit`.
- Use category/segment mix as a constrained COGS-ratio layer, not as a raw daily Revenue replacement.
- Add exact moving holiday/event features: Tet dates, 11.11, 12.12, Black Friday, month-end/payday.
- Blend component forecasts only where they explain public shift: promo windows, Tet/event windows, and COGS ratio.
- Keep the current best Revenue shape as anchor until a component forecast beats it on public-like folds.
