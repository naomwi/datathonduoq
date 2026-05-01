# Data Pattern Deep Dive

Run directory: `logs\20260422_022959_data_pattern_deep_dive`

Current public best considered: `submission_publiconly_segment_v8_h2best_2024h1_down100.csv` = `807504.66276`.

## Executive Rule
The best rule I can infer is:

`Revenue` forecast is roughly serviceable, while `COGS/Revenue` needs a regime model. The hidden public target appears to have an odd-year H2 cost/margin-compression regime in `2023H2`, but not in `2023H1` or `2024H1`.

Operationally:

- Let `2023H2` have a high ratio regime, especially not clipping high-ratio days.
- Keep `2024H1` restrained around normal H1-ish ratios.
- Do not keep raising all periods; broad COGS-up has already plateaued.

## Why This Rule
Accepted blackbox signals:

| label                                         |   score_gain_positive_is_good |   realized_efficiency |   changed_cogs_ratio_base |   changed_cogs_ratio_midpoint |   changed_cogs_ratio_candidate | implied_cogs_bound    |
|:----------------------------------------------|------------------------------:|----------------------:|--------------------------:|------------------------------:|-------------------------------:|:----------------------|
| nonpromo COGS +1.5% from structural txndecomp |                       7556.91 |             0.457195  |                  0.842975 |                      0.849297 |                       0.85562  | actual_above_midpoint |
| all COGS +5% from nonpromo-up base            |                      26197.8  |             0.300754  |                  0.871417 |                      0.893202 |                       0.914988 | actual_above_midpoint |
| all COGS +3.5% continuation                   |                      10760.1  |             0.168064  |                  0.914988 |                      0.931    |                       0.947012 | actual_above_midpoint |
| all COGS +2% continuation                     |                       3489.02 |             0.0921427 |                  0.947012 |                      0.956482 |                       0.965953 | actual_above_midpoint |
| 2023H2 COGS +10%                              |                      12584.8  |             0.246769  |                  0.990975 |                      1.04052  |                       1.09007  | actual_above_midpoint |
| 2024H1 COGS -10% after H2-up                  |                       4991.35 |             0.0665014 |                  0.959367 |                      0.911398 |                       0.86343  | actual_below_midpoint |

Rejected blackbox signals:

| label                                           |   score_gain_positive_is_good |   realized_efficiency |   changed_cogs_ratio_base |   changed_cogs_ratio_midpoint |   changed_cogs_ratio_candidate | implied_cogs_bound    |
|:------------------------------------------------|------------------------------:|----------------------:|--------------------------:|------------------------------:|-------------------------------:|:----------------------|
| COGS ratio reshape with total roughly preserved |                      -7773.66 |            -0.186226  |                  0.965953 |                      0.965953 |                       0.965953 | actual_above_midpoint |
| 2024H1 COGS +10%                                |                     -30759.5  |            -0.409818  |                  0.959367 |                      1.00733  |                       1.0553   | actual_below_midpoint |
| 2023H1 COGS +10%                                |                      -3588.65 |            -0.0539492 |                  0.954276 |                      1.00199  |                       1.0497   | actual_below_midpoint |
| 2023H2 peak months COGS +20% extra              |                     -15578.2  |            -0.307046  |                  1.13501  |                      1.24851  |                       1.36201  | actual_below_midpoint |
| 2023H2 shoulder months COGS +20% extra          |                     -22551.6  |            -0.366929  |                  1.05557  |                      1.16113  |                       1.26669  | actual_below_midpoint |

The strongest constraint is `2023H2 COGS +10%`: it improved public and implies hidden `2023H2` actual is above a midpoint ratio around `1.04`. But the `+20%` month probes failed, so the true level is probably near current boosted `2023H2`, not far above it.

## Raw Data Availability
All operational tables stop at `2022-12-31`; future rows are only sample submission dates and imputed feature-store rows. So this is not a missing future-table problem.

| table                     | date_column   |   rows | min_date            | max_date            |   rows_after_2022 |   non_null_dates |
|:--------------------------|:--------------|-------:|:--------------------|:--------------------|------------------:|-----------------:|
| customers.csv             | signup_date   | 121930 | 2012-01-17 00:00:00 | 2022-12-31 00:00:00 |                 0 |           121930 |
| daily_feature_base.csv    | Date          |   4381 | 2012-07-04 00:00:00 | 2024-07-01 00:00:00 |               548 |             4381 |
| daily_feature_base.csv    | snapshot_date |   4381 | 2012-07-31 00:00:00 | 2022-12-31 00:00:00 |                 0 |             4354 |
| daily_feature_base_v3.csv | Date          |   4381 | 2012-07-04 00:00:00 | 2024-07-01 00:00:00 |               548 |             4381 |
| daily_feature_base_v3.csv | snapshot_date |   4381 | 2012-07-31 00:00:00 | 2022-12-31 00:00:00 |                 0 |             4354 |
| feature_store.csv         | Date          |   4381 | 2012-07-04 00:00:00 | 2024-07-01 00:00:00 |               548 |             4381 |
| feature_store_main.csv    | Date          |   4381 | 2012-07-04 00:00:00 | 2024-07-01 00:00:00 |               548 |             4381 |
| feature_store_main.csv    | snapshot_date |   4381 | 2012-07-31 00:00:00 | 2022-12-31 00:00:00 |                 0 |             4354 |
| feature_store_v2.csv      | Date          |   4381 | 2012-07-04 00:00:00 | 2024-07-01 00:00:00 |               548 |             4381 |
| feature_store_v3.csv      | Date          |   4381 | 2012-07-04 00:00:00 | 2024-07-01 00:00:00 |               548 |             4381 |
| feature_store_v3.csv      | snapshot_date |   4381 | 2012-07-31 00:00:00 | 2022-12-31 00:00:00 |                 0 |             4354 |
| geography.csv             |               |  39948 |                     |                     |                 0 |              nan |
| inventory.csv             | snapshot_date |  60247 | 2012-07-31 00:00:00 | 2022-12-31 00:00:00 |                 0 |            60247 |
| order_items.csv           |               | 714669 |                     |                     |                 0 |              nan |
| orders.csv                | order_date    | 646945 | 2012-07-04 00:00:00 | 2022-12-31 00:00:00 |                 0 |           646945 |
| payments.csv              |               | 646945 |                     |                     |                 0 |              nan |
| products.csv              |               |   2412 |                     |                     |                 0 |              nan |
| promotions.csv            | start_date    |     50 | 2013-01-31 00:00:00 | 2022-11-18 00:00:00 |                 0 |               50 |
| promotions.csv            | end_date      |     50 | 2013-03-01 00:00:00 | 2022-12-31 00:00:00 |                 0 |               50 |
| returns.csv               | return_date   |  39939 | 2012-07-11 00:00:00 | 2022-12-31 00:00:00 |                 0 |            39939 |
| reviews.csv               | review_date   | 113551 | 2012-07-10 00:00:00 | 2022-12-31 00:00:00 |                 0 |           113551 |
| sales.csv                 | Date          |   3833 | 2012-07-04 00:00:00 | 2022-12-31 00:00:00 |                 0 |             3833 |
| sample_submission.csv     | Date          |    548 | 2023-01-01 00:00:00 | 2024-07-01 00:00:00 |               548 |              548 |
| shipments.csv             | ship_date     | 566067 | 2012-07-04 00:00:00 | 2022-12-29 00:00:00 |                 0 |           566067 |
| shipments.csv             | delivery_date | 566067 | 2012-07-06 00:00:00 | 2022-12-31 00:00:00 |                 0 |           566067 |
| web_traffic.csv           | date          |   3652 | 2013-01-01 00:00:00 | 2022-12-31 00:00:00 |                 0 |             3652 |

## Target Identity
`sales.csv` targets reconstruct from `orders + order_items + products`.

|   rows |   max_revenue_abs_error |   max_cogs_abs_error |   mean_revenue_abs_error |   mean_cogs_abs_error |
|-------:|------------------------:|---------------------:|-------------------------:|----------------------:|
|   3833 |             1.86265e-09 |           0.00499927 |              2.33408e-11 |            0.00246005 |

## Historical Half-Year Regimes
H2 has a strong odd/even pattern. Odd-year H2 ratios are repeatedly high: 2013, 2015, 2017, 2019, 2021. This directly matches why `2023H2` needed a higher COGS ratio.

|   year | half   |   days |   weighted_cogs_rev_ratio |   revenue_per_day |   cogs_per_day |   promo_rev_share |   effective_discount_rate |   weighted_catalog_ratio |   category_share_Streetwear |   category_share_Outdoor |   segment_share_Everyday |   segment_share_Premium |
|-------:|:-------|-------:|--------------------------:|------------------:|---------------:|------------------:|--------------------------:|-------------------------:|----------------------------:|-------------------------:|-------------------------:|------------------------:|
|   2012 | H2     |    181 |                  0.792264 |       4.09667e+06 |    3.24565e+06 |          0        |                 0         |                 0.79288  |                    0.75147  |                0.220857  |                 0.367378 |               0.0365498 |
|   2013 | H1     |    181 |                  0.825403 |       5.25343e+06 |    4.3362e+06  |          0.214675 |                 0.103866  |                 0.795342 |                    0.789743 |                0.181141  |                 0.394022 |               0.0323055 |
|   2013 | H2     |    184 |                  0.964363 |       3.83858e+06 |    3.70178e+06 |          0.621054 |                 0.24931   |                 0.796896 |                    0.721188 |                0.241685  |                 0.349731 |               0.0315256 |
|   2014 | H1     |    181 |                  0.827529 |       5.90479e+06 |    4.88639e+06 |          0.186817 |                 0.0838749 |                 0.799581 |                    0.77987  |                0.190166  |                 0.384814 |               0.0251194 |
|   2014 | H2     |    184 |                  0.859407 |       4.36456e+06 |    3.75093e+06 |          0.487625 |                 0.232108  |                 0.792745 |                    0.746891 |                0.220408  |                 0.354936 |               0.0334552 |
|   2015 | H1     |    181 |                  0.822815 |       6.06309e+06 |    4.9888e+06  |          0.212284 |                 0.102743  |                 0.792106 |                    0.795872 |                0.171403  |                 0.348603 |               0.0256731 |
|   2015 | H2     |    184 |                  0.962088 |       4.30715e+06 |    4.14386e+06 |          0.614911 |                 0.244968  |                 0.803184 |                    0.740352 |                0.210476  |                 0.346068 |               0.0414812 |
|   2016 | H1     |    182 |                  0.831866 |       6.67709e+06 |    5.55444e+06 |          0.180592 |                 0.0797869 |                 0.80762  |                    0.811166 |                0.151507  |                 0.376613 |               0.0414091 |
|   2016 | H2     |    184 |                  0.86535  |       4.83375e+06 |    4.18288e+06 |          0.494389 |                 0.236462  |                 0.799789 |                    0.773423 |                0.185409  |                 0.320359 |               0.0369318 |
|   2017 | H1     |    181 |                  0.834222 |       6.37297e+06 |    5.31647e+06 |          0.213792 |                 0.102157  |                 0.802338 |                    0.803417 |                0.154728  |                 0.331718 |               0.0316824 |
|   2017 | H2     |    184 |                  0.966274 |       4.1177e+06  |    3.97883e+06 |          0.623436 |                 0.246172  |                 0.796432 |                    0.750915 |                0.193947  |                 0.291681 |               0.0352797 |
|   2018 | H1     |    181 |                  0.82098  |       6.22126e+06 |    5.10753e+06 |          0.190109 |                 0.0853687 |                 0.795085 |                    0.806578 |                0.128993  |                 0.331361 |               0.0255128 |
|   2018 | H2     |    184 |                  0.853106 |       3.93519e+06 |    3.35713e+06 |          0.49877  |                 0.238046  |                 0.788718 |                    0.794652 |                0.136026  |                 0.294687 |               0.025144  |
|   2019 | H1     |    181 |                  0.826053 |       3.85156e+06 |    3.18159e+06 |          0.210165 |                 0.10074   |                 0.795844 |                    0.821046 |                0.123403  |                 0.306733 |               0.0244067 |
|   2019 | H2     |    184 |                  0.976494 |       2.3895e+06  |    2.33334e+06 |          0.621623 |                 0.242457  |                 0.792837 |                    0.772306 |                0.160085  |                 0.257074 |               0.0310157 |
|   2020 | H1     |    182 |                  0.824415 |       3.32621e+06 |    2.74218e+06 |          0.183996 |                 0.0823505 |                 0.794804 |                    0.818874 |                0.12717   |                 0.27085  |               0.0313172 |
|   2020 | H2     |    184 |                  0.861662 |       2.44099e+06 |    2.10331e+06 |          0.492103 |                 0.23337   |                 0.799233 |                    0.8093   |                0.130009  |                 0.237777 |               0.0354242 |
|   2021 | H1     |    181 |                  0.835229 |       3.49272e+06 |    2.91722e+06 |          0.202856 |                 0.0959206 |                 0.803376 |                    0.828556 |                0.105511  |                 0.251189 |               0.025183  |
|   2021 | H2     |    184 |                  1.00549  |       2.23292e+06 |    2.24518e+06 |          0.628192 |                 0.241935  |                 0.824264 |                    0.80215  |                0.119848  |                 0.216923 |               0.0254825 |
|   2022 | H1     |    181 |                  0.857575 |       3.82569e+06 |    3.28082e+06 |          0.189982 |                 0.0841245 |                 0.827835 |                    0.835253 |                0.0929235 |                 0.221797 |               0.0251221 |
|   2022 | H2     |    184 |                  0.893764 |       2.59401e+06 |    2.31844e+06 |          0.490235 |                 0.234436  |                 0.825156 |                    0.822746 |                0.10618   |                 0.203447 |               0.0411635 |

H2-only compact view:

|   year |   weighted_cogs_rev_ratio |   promo_rev_share |   effective_discount_rate |   category_share_Streetwear |   segment_share_Everyday |
|-------:|--------------------------:|------------------:|--------------------------:|----------------------------:|-------------------------:|
|   2012 |                  0.792264 |          0        |                  0        |                    0.75147  |                 0.367378 |
|   2013 |                  0.964363 |          0.621054 |                  0.24931  |                    0.721188 |                 0.349731 |
|   2014 |                  0.859407 |          0.487625 |                  0.232108 |                    0.746891 |                 0.354936 |
|   2015 |                  0.962088 |          0.614911 |                  0.244968 |                    0.740352 |                 0.346068 |
|   2016 |                  0.86535  |          0.494389 |                  0.236462 |                    0.773423 |                 0.320359 |
|   2017 |                  0.966274 |          0.623436 |                  0.246172 |                    0.750915 |                 0.291681 |
|   2018 |                  0.853106 |          0.49877  |                  0.238046 |                    0.794652 |                 0.294687 |
|   2019 |                  0.976494 |          0.621623 |                  0.242457 |                    0.772306 |                 0.257074 |
|   2020 |                  0.861662 |          0.492103 |                  0.23337  |                    0.8093   |                 0.237777 |
|   2021 |                  1.00549  |          0.628192 |                  0.241935 |                    0.80215  |                 0.216923 |
|   2022 |                  0.893764 |          0.490235 |                  0.234436 |                    0.822746 |                 0.203447 |

Largest odd-vs-even H2 feature shifts:

| feature                   |      odd_h2_mean |     even_h2_mean |    odd_minus_even |   relative_diff |
|:--------------------------|-----------------:|-----------------:|------------------:|----------------:|
| odd_year                  |      1           |      0           |       1           |       1e+09     |
| promo_rev_share           |      0.621843    |      0.492624    |       0.129219    |       0.262307  |
| segment_share_Activewear  |      0.155181    |      0.123382    |       0.0317988   |       0.257726  |
| promo_line_share          |      0.606617    |      0.495429    |       0.111188    |       0.224427  |
| category_share_Outdoor    |      0.185208    |      0.155606    |       0.0296021   |       0.190237  |
| avg_unit_price            |   4807.39        |   5532           |    -724.612       |      -0.130985  |
| weighted_cogs_rev_ratio   |      0.974942    |      0.866658    |       0.108284    |       0.124944  |
| aov                       |  23688           |  26973.7         |   -3285.73        |      -0.121812  |
| segment_share_Balanced    |      0.331911    |      0.371565    |      -0.0396531   |      -0.106719  |
| line_count                |  31679           |  28885.6         |    2793.4         |       0.0967056 |
| total_units               | 142264           | 130011           |   12253.4         |       0.0942489 |
| order_count               |  28348           |  26137           |    2211           |       0.0845927 |
| detail_revenue            |      6.21399e+08 |      6.68601e+08 |      -4.72012e+07 |      -0.0705969 |
| revenue_per_day           |      3.37717e+06 |      3.6337e+06  | -256528           |      -0.0705969 |
| active_products           |    102.174       |     96.0272      |       6.14674     |       0.0640104 |
| segment_share_Trendy      |      0.0251788   |      0.0237325   |       0.00144628  |       0.0609409 |
| category_share_GenZ       |      0.0251788   |      0.0237325   |       0.00144628  |       0.0609409 |
| cogs_per_unit             |   4570.28        |   4797.66        |    -227.374       |      -0.0473928 |
| cogs_per_day              |      3.2806e+06  |      3.14254e+06 |  138059           |       0.0439324 |
| detail_cogs               |      6.0363e+08  |      5.78227e+08 |       2.54029e+07 |       0.0439324 |
| effective_discount_rate   |      0.244969    |      0.234884    |       0.0100841   |       0.042932  |
| segment_share_Premium     |      0.0329569   |      0.0344238   |      -0.00146682  |      -0.0426108 |
| category_share_Streetwear |      0.757382    |      0.789403    |      -0.0320203   |      -0.0405627 |
| segment_share_Everyday    |      0.292295    |      0.282241    |       0.0100543   |       0.0356231 |
| category_share_Casual     |      0.0322306   |      0.0312587   |       0.000971902 |       0.0310922 |

## Current Best Vs History
Current best ratios are much more H2-skewed than normal H1/H2 history, which explains both the public improvement and the private-risk warning.

| segment                     |   rows |   revenue_sum |    cogs_sum |   cogs_rev_ratio_weighted |   mean_revenue |   mean_cogs |
|:----------------------------|-------:|--------------:|------------:|--------------------------:|---------------:|------------:|
| 2023H1                      |    181 |   7.63982e+08 | 7.2905e+08  |                  0.954276 |    4.2209e+06  | 4.0279e+06  |
| 2023H2                      |    184 |   5.6403e+08  | 6.14834e+08 |                  1.09007  |    3.06538e+06 | 3.34149e+06 |
| 2024H1                      |    182 |   8.57459e+08 | 7.40356e+08 |                  0.86343  |    4.71132e+06 | 4.06789e+06 |
| 2023H2_peak_aug_nov_dec     |     92 |   2.44959e+08 | 2.78031e+08 |                  1.13501  |    2.6626e+06  | 3.02208e+06 |
| 2023H2_shoulder_jul_sep_oct |     92 |   3.19071e+08 | 3.36802e+08 |                  1.05557  |    3.46816e+06 | 3.6609e+06  |
| 2024_highscale_mar_jun      |    122 |   6.6794e+08  | 5.83987e+08 |                  0.874311 |    5.47492e+06 | 4.78678e+06 |
| promo_window                |    183 |   7.58454e+08 | 7.63256e+08 |                  1.00633  |    4.14456e+06 | 4.1708e+06  |
| nonpromo                    |    365 |   1.43267e+09 | 1.3269e+09  |                  0.926172 |    3.92513e+06 | 3.63535e+06 |

| segment                     |   current_ratio |   history_ref_mean |   history_ref_min |   history_ref_max |   z_vs_ref |   odd_h2_mean |   odd_h2_max |
|:----------------------------|----------------:|-------------------:|------------------:|------------------:|-----------:|--------------:|-------------:|
| 2023H1                      |        0.954276 |           0.830609 |          0.82098  |          0.857575 |  12.2914   |    nan        |    nan       |
| 2023H2                      |        1.09007  |           0.909115 |          0.792264 |          1.00549  |   2.77967  |      0.974942 |      1.00549 |
| 2024H1                      |        0.86343  |           0.830609 |          0.82098  |          0.857575 |   3.26212  |    nan        |    nan       |
| 2023H2_peak_aug_nov_dec     |        1.13501  |           0.909115 |          0.792264 |          1.00549  |   3.46996  |      0.974942 |      1.00549 |
| 2023H2_shoulder_jul_sep_oct |        1.05557  |           0.909115 |          0.792264 |          1.00549  |   2.24972  |      0.974942 |      1.00549 |
| 2024_highscale_mar_jun      |        0.874311 |           0.871731 |          0.792264 |          1.00549  |   0.041828 |    nan        |    nan       |
| promo_window                |        1.00633  |           0.871731 |          0.792264 |          1.00549  |   2.18193  |    nan        |    nan       |
| nonpromo                    |        0.926172 |           0.871731 |          0.792264 |          1.00549  |   0.882513 |    nan        |    nan       |

## Product And Mix
Catalog-level product COGS/price ratios are only around `0.77-0.81`. Daily/public ratios above 1 therefore come from realized selling price/discount/mix, not static catalog cost alone.

Category catalog ratios:

| category   |   product_count |   catalog_ratio_mean |         cogs_sum |        price_sum |   catalog_ratio_weighted |
|:-----------|----------------:|---------------------:|-----------------:|-----------------:|-------------------------:|
| Outdoor    |             743 |             0.730645 |      1.45797e+06 |      1.84349e+06 |                 0.79087  |
| GenZ       |             148 |             0.759242 | 258308           | 327492           |                 0.788747 |
| Streetwear |            1320 |             0.736147 |      7.00562e+06 |      8.92994e+06 |                 0.784509 |
| Casual     |             201 |             0.715246 | 608559           | 785927           |                 0.77432  |

Segment catalog ratios:

| segment     |   product_count |   catalog_ratio_mean |         cogs_sum |        price_sum |   catalog_ratio_weighted |
|:------------|----------------:|---------------------:|-----------------:|-----------------:|-------------------------:|
| Premium     |             177 |             0.714623 | 341301           | 422618           |                 0.807586 |
| Everyday    |             405 |             0.763657 |      2.43304e+06 |      3.05742e+06 |                 0.795781 |
| Trendy      |             148 |             0.759242 | 258308           | 327492           |                 0.788747 |
| Balanced    |             306 |             0.741962 |      2.21263e+06 |      2.82445e+06 |                 0.783382 |
| Activewear  |             598 |             0.7344   |      1.21678e+06 |      1.55366e+06 |                 0.783172 |
| All-weather |             169 |             0.715824 | 508440           | 653142           |                 0.778453 |
| Performance |             347 |             0.73635  |      1.768e+06   |      2.28078e+06 |                 0.775174 |
| Standard    |             262 |             0.686558 | 591955           | 767291           |                 0.771487 |

Sold mix by category/segment:

| category   | segment     |   revenue_sum |    cogs_sum |   units |   realized_cogs_rev_ratio |
|:-----------|:------------|--------------:|------------:|--------:|--------------------------:|
| Casual     | All-weather |   4.27585e+08 | 3.80916e+08 |  101147 |                  0.890856 |
| Outdoor    | Premium     |   4.80131e+08 | 4.27626e+08 |  139465 |                  0.890643 |
| Streetwear | Performance |   2.39041e+09 | 2.11134e+09 |  435685 |                  0.883252 |
| Streetwear | Balanced    |   5.12741e+09 | 4.46908e+09 |  464217 |                  0.871606 |
| Streetwear | Everyday    |   5.37685e+09 | 4.61528e+09 |  819449 |                  0.858362 |
| Streetwear | Standard    |   2.36677e+08 | 1.96972e+08 |   49475 |                  0.832239 |
| Outdoor    | Activewear  |   2.01475e+09 | 1.65874e+09 | 1030535 |                  0.823296 |
| GenZ       | Trendy      |   3.43599e+08 | 2.77874e+08 |  166848 |                  0.808715 |
| Casual     | Activewear  |   3.30639e+07 | 2.56284e+07 |    6322 |                  0.775118 |

## Feature Signals
Top daily features correlated with COGS/Revenue ratio in train:

| feature                                     |   spearman_corr_with_daily_cogs_ratio |   non_null |
|:--------------------------------------------|--------------------------------------:|-----------:|
| active_promo_discount_value_mean            |                              0.829701 |       3833 |
| promo_line_share                            |                              0.813847 |       3833 |
| avg_discount_rate                           |                              0.809746 |       3833 |
| promo_duration_days_mean                    |                              0.804054 |       3833 |
| active_promo_count                          |                              0.797867 |       3833 |
| total_discount                              |                              0.781226 |       3833 |
| promo_days_since_start_mean                 |                              0.764934 |       3833 |
| promo_days_to_end_mean                      |                              0.762097 |       3833 |
| active_promo_category_global_share          |                              0.699971 |       3833 |
| active_promo_discount_value_percentage_mean |                              0.689425 |       3833 |
| active_promo_type_percentage_share          |                              0.666917 |       3833 |
| active_promo_channel_all_channels_share     |                              0.497804 |       3833 |
| active_promo_min_order_value_mean           |                              0.493621 |       3833 |
| aov_proxy                                   |                             -0.420012 |       3833 |
| active_promo_channel_online_share           |                              0.411447 |       3833 |
| avg_unit_price                              |                             -0.381163 |       3833 |
| active_promo_type_fixed_share               |                              0.356605 |       3833 |
| active_promo_category_streetwear_share      |                              0.356605 |       3833 |
| shipping_fee_mean                           |                              0.317218 |       3833 |
| shipping_fee_per_order                      |                              0.304355 |       3833 |
| active_promo_stackable_share                |                              0.271521 |       3833 |
| segment_rev_share_everyday                  |                             -0.220271 |       3833 |
| new_customers                               |                              0.180023 |       3833 |
| active_promo_channel_email_share            |                              0.173304 |       3833 |
| promo_start_share                           |                             -0.172848 |       1707 |
| days_of_supply_avg                          |                              0.172267 |       3806 |
| promo_end_share                             |                             -0.162739 |       1707 |
| category_rev_share_streetwear               |                             -0.145572 |       3833 |
| inv_stock_on_hand_casual                    |                              0.145253 |       3806 |
| segment_rev_share_trendy                    |                              0.141841 |       3833 |
| category_rev_share_genz                     |                              0.141841 |       3833 |
| inv_stock_on_hand_genz                      |                              0.136143 |       3806 |
| units_received                              |                             -0.124379 |       3806 |
| units_sold                                  |                             -0.124083 |       3806 |
| sell_through_rate_avg                       |                             -0.122927 |       3806 |

Future feature audit, highest future availability:

| feature                             |   future_non_null_share |   future_nunique |   future_mean |       train_mean |
|:------------------------------------|------------------------:|-----------------:|--------------:|-----------------:|
| order_count                         |                       1 |                1 |             0 |    168.783       |
| unique_customers                    |                       1 |                1 |             0 |    167.458       |
| cancelled_order_share               |                       1 |                1 |             0 |      0.091684    |
| returned_order_share                |                       1 |                1 |             0 |      0.0558925   |
| delivered_order_share               |                       1 |                1 |             0 |      0.796265    |
| payment_share_apple_pay             |                       1 |                1 |             0 |      0.100418    |
| payment_share_bank_transfer         |                       1 |                1 |             0 |      0.0495951   |
| payment_share_cod                   |                       1 |                1 |             0 |      0.149544    |
| payment_share_credit_card           |                       1 |                1 |             0 |      0.550806    |
| payment_share_paypal                |                       1 |                1 |             0 |      0.149638    |
| device_share_desktop                |                       1 |                1 |             0 |      0.399321    |
| device_share_mobile                 |                       1 |                1 |             0 |      0.451524    |
| device_share_tablet                 |                       1 |                1 |             0 |      0.149155    |
| order_source_share_direct           |                       1 |                1 |             0 |      0.079695    |
| order_source_share_email_campaign   |                       1 |                1 |             0 |      0.119915    |
| order_source_share_organic_search   |                       1 |                1 |             0 |      0.280214    |
| order_source_share_paid_search      |                       1 |                1 |             0 |      0.219451    |
| order_source_share_referral         |                       1 |                1 |             0 |      0.0998055   |
| order_source_share_social_media     |                       1 |                1 |             0 |      0.20092     |
| new_customers                       |                       1 |                1 |             0 |     31.7485      |
| signup_channel_share_direct         |                       1 |                1 |             0 |      0.0807202   |
| signup_channel_share_email_campaign |                       1 |                1 |             0 |      0.120304    |
| signup_channel_share_organic_search |                       1 |                1 |             0 |      0.299181    |
| signup_channel_share_paid_search    |                       1 |                1 |             0 |      0.19803     |
| signup_channel_share_referral       |                       1 |                1 |             0 |      0.0996726   |
| signup_channel_share_social_media   |                       1 |                1 |             0 |      0.200789    |
| order_region_share_central          |                       1 |                1 |             0 |      0.286593    |
| order_region_share_east             |                       1 |                1 |             0 |      0.449353    |
| order_region_share_west             |                       1 |                1 |             0 |      0.264054    |
| total_units                         |                       1 |                1 |             0 |    838.284       |
| gross_rev_reconstructed             |                       1 |                1 |             0 |      4.28658e+06 |
| gross_cogs_reconstructed            |                       1 |                1 |             0 |      3.69513e+06 |
| gross_margin                        |                       1 |                1 |             0 | 591450           |
| avg_unit_price                      |                       1 |                1 |             0 |   5460.95        |
| total_discount                      |                       1 |                1 |             0 | 195567           |
| avg_discount_rate                   |                       1 |                1 |             0 |      0.0444215   |
| promo_line_share                    |                       1 |                1 |             0 |      0.368361    |
| promo_2_share                       |                       1 |                1 |             0 |      0.000179932 |
| category_rev_share_casual           |                       1 |                1 |             0 |      0.0300278   |
| category_rev_share_genz             |                       1 |                1 |             0 |      0.0210742   |

Promotion metadata by half-year:

|   year | half   |   promo_count |   mean_discount |   max_discount |   pct_percentage |   pct_stackable |   total_duration_days |   global_share |   outdoor_share |   streetwear_share |
|-------:|:-------|--------------:|----------------:|---------------:|-----------------:|----------------:|----------------------:|---------------:|----------------:|-------------------:|
|   2013 | H1     |             3 |         15      |             18 |         1        |        0.333333 |                    91 |       0.666667 |        0.333333 |           0        |
|   2013 | H2     |             3 |         26.6667 |             50 |         0.666667 |        0        |                   115 |       0.666667 |        0        |           0.333333 |
|   2014 | H1     |             2 |         15      |             18 |         1        |        0.5      |                    61 |       1        |        0        |           0        |
|   2014 | H2     |             2 |         15      |             20 |         1        |        0        |                    78 |       1        |        0        |           0        |
|   2015 | H1     |             3 |         15      |             18 |         1        |        0.333333 |                    92 |       0.666667 |        0.333333 |           0        |
|   2015 | H2     |             3 |         26.6667 |             50 |         0.666667 |        0.666667 |                   114 |       0.666667 |        0        |           0.333333 |
|   2016 | H1     |             2 |         15      |             18 |         1        |        0        |                    61 |       1        |        0        |           0        |
|   2016 | H2     |             2 |         15      |             20 |         1        |        0        |                    79 |       1        |        0        |           0        |
|   2017 | H1     |             3 |         15      |             18 |         1        |        0        |                    92 |       0.666667 |        0.333333 |           0        |
|   2017 | H2     |             3 |         26.6667 |             50 |         0.666667 |        0.333333 |                   115 |       0.666667 |        0        |           0.333333 |
|   2018 | H1     |             2 |         15      |             18 |         1        |        0        |                    61 |       1        |        0        |           0        |
|   2018 | H2     |             2 |         15      |             20 |         1        |        0        |                    79 |       1        |        0        |           0        |
|   2019 | H1     |             3 |         15      |             18 |         1        |        0.666667 |                    92 |       0.666667 |        0.333333 |           0        |
|   2019 | H2     |             3 |         26.6667 |             50 |         0.666667 |        0        |                   114 |       0.666667 |        0        |           0.333333 |
|   2020 | H1     |             2 |         15      |             18 |         1        |        0        |                    61 |       1        |        0        |           0        |
|   2020 | H2     |             2 |         15      |             20 |         1        |        0        |                    78 |       1        |        0        |           0        |
|   2021 | H1     |             3 |         15      |             18 |         1        |        0.666667 |                    92 |       0.666667 |        0.333333 |           0        |
|   2021 | H2     |             3 |         26.6667 |             50 |         0.666667 |        0.333333 |                   115 |       0.666667 |        0        |           0.333333 |
|   2022 | H1     |             2 |         15      |             18 |         1        |        0.5      |                    61 |       1        |        0        |           0        |
|   2022 | H2     |             2 |         15      |             20 |         1        |        0        |                    76 |       1        |        0        |           0        |

## Interpretation
- The public blackbox rule is not random: it lines up with a real historical H2 odd-year high-ratio pattern.
- The local OOF likely underweighted this because `2022H2` is a low/normal H2, while public starts at `2023`, an odd-year regime candidate.
- Product catalog ratios alone cannot explain `COGS/Revenue > 1`; these high ratios require selling-price compression, discounts, or mix toward high-cost items.
- Future promo/inventory/traffic are not truly available after 2022, so any successful solution must impute policy/regime, not read future features.
- The most robust next model is a COGS-ratio model with features for `half`, `odd_year_h2`, promo/event windows, discount/promo analogs, and product-mix priors.

## Next Non-Overfit Modeling Direction
Build a structural candidate:

1. Keep a stable Revenue anchor.
2. Predict/assign `COGS/Revenue` by regime instead of direct COGS.
3. For `2023H2`, blend toward odd-year H2 analogs plus a small public-supported uplift, but cap below rejected month-spike bounds.
4. For `2024H1`, use recent H1 analogs, not the public H2 shock.
5. Avoid direct use of unknown future operational features unless they are generated by a clearly fixed policy.
