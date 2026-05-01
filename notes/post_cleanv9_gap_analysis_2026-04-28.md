# Post Clean V9 Gap Analysis

Run directory: `logs\20260428_211317_post_cleanv9_gap_analysis`

## What just happened

- Current clean best: `submission_cleanv7_source_h1_s020_r0870.csv = 673720.88479`.
- New big COGS-down test: `submission_cleanv9_big_h1_keeprev_cogs_r0820.csv = 678484.18208`.
- Delta: `+4763.30` MAE, so the hypothesis "2023H1 COGS ratio is far too high" is rejected.

## Main read

The clean branch is not primarily missing a broad period-level COGS ratio. It is missing a clean explanation for daily allocation/phase and selective high-ratio pockets. Blackbox improvements came from localized reshaping; clean COGS ratio changes that are too broad worsen.

## Score and total summary

| filename                                                |   public_score |   rows | start      | end        |   revenue_total |   cogs_total |   ratio_total |   max_revenue |    max_cogs |   rev_2023H1 |   cogs_2023H1 |   ratio_2023H1 |   rev_2023H2 |   cogs_2023H2 |   ratio_2023H2 |   rev_2024H1 |   cogs_2024H1 |   ratio_2024H1 |   rev_2024-07-01 |   cogs_2024-07-01 |   ratio_2024-07-01 |
|:--------------------------------------------------------|---------------:|-------:|:-----------|:-----------|----------------:|-------------:|--------------:|--------------:|------------:|-------------:|--------------:|---------------:|-------------:|--------------:|---------------:|-------------:|--------------:|---------------:|-----------------:|------------------:|-------------------:|
| submission_cleanv7_source_h1_s020_r0870.csv             |         673721 |    548 | 2023-01-01 | 2024-07-01 |     2.36279e+09 |  2.11916e+09 |      0.896887 |   1.21832e+07 | 1.17897e+07 |  8.50285e+08 |   7.39748e+08 |       0.87     |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.46735e+08 |       0.844885 |      7.10042e+06 |       7.68649e+06 |            1.08254 |
| submission_cleanv7_sourcefine_s0190_r0870.csv           |         674415 |    548 | 2023-01-01 | 2024-07-01 |     2.35389e+09 |  2.11142e+09 |      0.896989 |   1.20557e+07 | 1.16663e+07 |  8.41384e+08 |   7.32004e+08 |       0.87     |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.46735e+08 |       0.844885 |      7.10042e+06 |       7.68649e+06 |            1.08254 |
| submission_cleanv9_big_h1_keeprev_cogs_r0820.csv        |         678484 |    548 | 2023-01-01 | 2024-07-01 |     2.36279e+09 |  2.07665e+09 |      0.878894 |   1.21832e+07 | 1.11122e+07 |  8.50285e+08 |   6.97234e+08 |       0.82     |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.46735e+08 |       0.844885 |      7.10042e+06 |       7.68649e+06 |            1.08254 |
| submission_cleanv3_funnel_c110_h1r0876.csv              |         673760 |    548 | 2023-01-01 | 2024-07-01 |     2.36346e+09 |  2.12485e+09 |      0.89904  |   1.21928e+07 | 1.18804e+07 |  8.50952e+08 |   7.45434e+08 |       0.876    |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.46735e+08 |       0.844885 |      7.10042e+06 |       7.68649e+06 |            1.08254 |
| submission_cleanv6_merch_revshape_g010.csv              |         674337 |    548 | 2023-01-01 | 2024-07-01 |     2.36518e+09 |  2.12635e+09 |      0.899023 |   1.2275e+07  | 1.19043e+07 |  8.52667e+08 |   7.46937e+08 |       0.876    |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.46735e+08 |       0.844885 |      7.10042e+06 |       7.68649e+06 |            1.08254 |
| submission_qbb62_h1_backload_preserve_total_q2up040.csv |         661327 |    548 | 2023-01-01 | 2024-07-01 |     2.37257e+09 |  2.13276e+09 |      0.898925 |   1.26027e+07 | 1.19721e+07 |  8.633e+08   |   7.56492e+08 |       0.87628  |  6.20433e+08 |   6.2214e+08  |       1.00275  |  8.83183e+08 |   7.48114e+08 |       0.847066 |      5.65516e+06 |       6.01795e+06 |            1.06415 |
| submission_qbb65_h2_highratio_cogs_down060_keeprev.csv  |         659212 |    548 | 2023-01-01 | 2024-07-01 |     2.37257e+09 |  2.11525e+09 |      0.891542 |   1.26027e+07 | 1.19721e+07 |  8.633e+08   |   7.56492e+08 |       0.87628  |  6.20433e+08 |   6.04622e+08 |       0.974516 |  8.83183e+08 |   7.48114e+08 |       0.847066 |      5.65516e+06 |       6.01795e+06 |            1.06415 |
| submission_qbb68_h1_q1_cogs_down080_keeprev.csv         |         656302 |    548 | 2023-01-01 | 2024-07-01 |     2.37257e+09 |  2.09254e+09 |      0.881972 |   1.26027e+07 | 1.10144e+07 |  8.633e+08   |   7.33787e+08 |       0.849979 |  6.20433e+08 |   6.04622e+08 |       0.974516 |  8.83183e+08 |   7.48114e+08 |       0.847066 |      5.65516e+06 |       6.01795e+06 |            1.06415 |
| submission_qbb69_h1_q1_cogs_down120_keeprev.csv         |         655839 |    548 | 2023-01-01 | 2024-07-01 |     2.37257e+09 |  2.08119e+09 |      0.877187 |   1.26027e+07 | 1.09204e+07 |  8.633e+08   |   7.22434e+08 |       0.836829 |  6.20433e+08 |   6.04622e+08 |       0.974516 |  8.83183e+08 |   7.48114e+08 |       0.847066 |      5.65516e+06 |       6.01795e+06 |            1.06415 |

## Delta vs current clean best

| filename                                                |   public_score |   public_delta_vs_anchor |   delta_revenue_total |   delta_cogs_total |   delta_abs_total |   max_abs_daily_rev_delta |   max_abs_daily_cogs_delta |
|:--------------------------------------------------------|---------------:|-------------------------:|----------------------:|-------------------:|------------------:|--------------------------:|---------------------------:|
| submission_cleanv7_sourcefine_s0190_r0870.csv           |         674415 |                 694.135  |          -8.90046e+06 |       -7.7434e+06  |       1.66439e+07 |          127529           |           123411           |
| submission_cleanv9_big_h1_keeprev_cogs_r0820.csv        |         678484 |                4763.3    |           0           |       -4.25142e+07 |       4.25142e+07 |               0           |           677571           |
| submission_cleanv3_funnel_c110_h1r0876.csv              |         673760 |                  39.0836 |      667187           |        5.68617e+06 |       6.35335e+06 |            9559.71        |            90623.4         |
| submission_cleanv6_merch_revshape_g010.csv              |         674337 |                 616.192  |           2.38264e+06 |        7.18891e+06 |       1.46217e+07 |           99931.8         |           114573           |
| submission_qbb62_h1_backload_preserve_total_q2up040.csv |         661327 |              -12393.9    |           9.7775e+06  |        1.36044e+07 |       1.81882e+08 |               1.44526e+06 |                1.66853e+06 |
| submission_qbb65_h2_highratio_cogs_down060_keeprev.csv  |         659212 |              -14509      |           9.7775e+06  |       -3.9138e+06  |       1.95481e+08 |               1.44526e+06 |                1.66853e+06 |
| submission_qbb68_h1_q1_cogs_down080_keeprev.csv         |         656302 |              -17419.2    |           9.7775e+06  |       -2.66191e+07 |       2.07019e+08 |               1.44526e+06 |                1.66853e+06 |
| submission_qbb69_h1_q1_cogs_down120_keeprev.csv         |         655839 |              -17882.4    |           9.7775e+06  |       -3.79718e+07 |       2.18372e+08 |               1.44526e+06 |                1.66853e+06 |

## Period matrix

| filename                                                |   public_score | period     |   revenue_total |   cogs_total |   cogs_ratio |   mean_daily_revenue |   mean_daily_cogs |   peak_daily_revenue |   peak_daily_cogs |
|:--------------------------------------------------------|---------------:|:-----------|----------------:|-------------:|-------------:|---------------------:|------------------:|---------------------:|------------------:|
| submission_cleanv7_source_h1_s020_r0870.csv             |         673721 | 2023H1     |     8.50285e+08 |  7.39748e+08 |     0.87     |          4.69771e+06 |       4.087e+06   |          1.21832e+07 |       1.17897e+07 |
| submission_cleanv7_source_h1_s020_r0870.csv             |         673721 | 2023H2     |     6.21578e+08 |  6.24991e+08 |     1.00549  |          3.37814e+06 |       3.39669e+06 |          6.88027e+06 |       8.24856e+06 |
| submission_cleanv7_source_h1_s020_r0870.csv             |         673721 | 2024H1     |     8.83831e+08 |  7.46735e+08 |     0.844885 |          4.85621e+06 |       4.10294e+06 |          1.20408e+07 |       1.10684e+07 |
| submission_cleanv7_source_h1_s020_r0870.csv             |         673721 | 2024-07-01 |     7.10042e+06 |  7.68649e+06 |     1.08254  |          7.10042e+06 |       7.68649e+06 |          7.10042e+06 |       7.68649e+06 |
| submission_cleanv7_sourcefine_s0190_r0870.csv           |         674415 | 2023H1     |     8.41384e+08 |  7.32004e+08 |     0.87     |          4.64853e+06 |       4.04422e+06 |          1.20557e+07 |       1.16663e+07 |
| submission_cleanv7_sourcefine_s0190_r0870.csv           |         674415 | 2023H2     |     6.21578e+08 |  6.24991e+08 |     1.00549  |          3.37814e+06 |       3.39669e+06 |          6.88027e+06 |       8.24856e+06 |
| submission_cleanv7_sourcefine_s0190_r0870.csv           |         674415 | 2024H1     |     8.83831e+08 |  7.46735e+08 |     0.844885 |          4.85621e+06 |       4.10294e+06 |          1.20408e+07 |       1.10684e+07 |
| submission_cleanv7_sourcefine_s0190_r0870.csv           |         674415 | 2024-07-01 |     7.10042e+06 |  7.68649e+06 |     1.08254  |          7.10042e+06 |       7.68649e+06 |          7.10042e+06 |       7.68649e+06 |
| submission_cleanv9_big_h1_keeprev_cogs_r0820.csv        |         678484 | 2023H1     |     8.50285e+08 |  6.97234e+08 |     0.82     |          4.69771e+06 |       3.85212e+06 |          1.21832e+07 |       1.11122e+07 |
| submission_cleanv9_big_h1_keeprev_cogs_r0820.csv        |         678484 | 2023H2     |     6.21578e+08 |  6.24991e+08 |     1.00549  |          3.37814e+06 |       3.39669e+06 |          6.88027e+06 |       8.24856e+06 |
| submission_cleanv9_big_h1_keeprev_cogs_r0820.csv        |         678484 | 2024H1     |     8.83831e+08 |  7.46735e+08 |     0.844885 |          4.85621e+06 |       4.10294e+06 |          1.20408e+07 |       1.10684e+07 |
| submission_cleanv9_big_h1_keeprev_cogs_r0820.csv        |         678484 | 2024-07-01 |     7.10042e+06 |  7.68649e+06 |     1.08254  |          7.10042e+06 |       7.68649e+06 |          7.10042e+06 |       7.68649e+06 |
| submission_cleanv3_funnel_c110_h1r0876.csv              |         673760 | 2023H1     |     8.50952e+08 |  7.45434e+08 |     0.876    |          4.70139e+06 |       4.11842e+06 |          1.21928e+07 |       1.18804e+07 |
| submission_cleanv3_funnel_c110_h1r0876.csv              |         673760 | 2023H2     |     6.21578e+08 |  6.24991e+08 |     1.00549  |          3.37814e+06 |       3.39669e+06 |          6.88027e+06 |       8.24856e+06 |
| submission_cleanv3_funnel_c110_h1r0876.csv              |         673760 | 2024H1     |     8.83831e+08 |  7.46735e+08 |     0.844885 |          4.85621e+06 |       4.10294e+06 |          1.20408e+07 |       1.10684e+07 |
| submission_cleanv3_funnel_c110_h1r0876.csv              |         673760 | 2024-07-01 |     7.10042e+06 |  7.68649e+06 |     1.08254  |          7.10042e+06 |       7.68649e+06 |          7.10042e+06 |       7.68649e+06 |
| submission_cleanv6_merch_revshape_g010.csv              |         674337 | 2023H1     |     8.52667e+08 |  7.46937e+08 |     0.876    |          4.71087e+06 |       4.12672e+06 |          1.2275e+07  |       1.19043e+07 |
| submission_cleanv6_merch_revshape_g010.csv              |         674337 | 2023H2     |     6.21578e+08 |  6.24991e+08 |     1.00549  |          3.37814e+06 |       3.39669e+06 |          6.91846e+06 |       8.24856e+06 |
| submission_cleanv6_merch_revshape_g010.csv              |         674337 | 2024H1     |     8.83831e+08 |  7.46735e+08 |     0.844885 |          4.85621e+06 |       4.10294e+06 |          1.20973e+07 |       1.10684e+07 |
| submission_cleanv6_merch_revshape_g010.csv              |         674337 | 2024-07-01 |     7.10042e+06 |  7.68649e+06 |     1.08254  |          7.10042e+06 |       7.68649e+06 |          7.10042e+06 |       7.68649e+06 |
| submission_qbb62_h1_backload_preserve_total_q2up040.csv |         661327 | 2023H1     |     8.633e+08   |  7.56492e+08 |     0.87628  |          4.76961e+06 |       4.17952e+06 |          1.232e+07   |       1.19721e+07 |
| submission_qbb62_h1_backload_preserve_total_q2up040.csv |         661327 | 2023H2     |     6.20433e+08 |  6.2214e+08  |     1.00275  |          3.37192e+06 |       3.3812e+06  |          6.6151e+06  |       8.02636e+06 |
| submission_qbb62_h1_backload_preserve_total_q2up040.csv |         661327 | 2024H1     |     8.83183e+08 |  7.48114e+08 |     0.847066 |          4.85265e+06 |       4.11052e+06 |          1.26027e+07 |       1.09204e+07 |
| submission_qbb62_h1_backload_preserve_total_q2up040.csv |         661327 | 2024-07-01 |     5.65516e+06 |  6.01795e+06 |     1.06415  |          5.65516e+06 |       6.01795e+06 |          5.65516e+06 |       6.01795e+06 |
| submission_qbb65_h2_highratio_cogs_down060_keeprev.csv  |         659212 | 2023H1     |     8.633e+08   |  7.56492e+08 |     0.87628  |          4.76961e+06 |       4.17952e+06 |          1.232e+07   |       1.19721e+07 |
| submission_qbb65_h2_highratio_cogs_down060_keeprev.csv  |         659212 | 2023H2     |     6.20433e+08 |  6.04622e+08 |     0.974516 |          3.37192e+06 |       3.28599e+06 |          6.6151e+06  |       7.54478e+06 |
| submission_qbb65_h2_highratio_cogs_down060_keeprev.csv  |         659212 | 2024H1     |     8.83183e+08 |  7.48114e+08 |     0.847066 |          4.85265e+06 |       4.11052e+06 |          1.26027e+07 |       1.09204e+07 |
| submission_qbb65_h2_highratio_cogs_down060_keeprev.csv  |         659212 | 2024-07-01 |     5.65516e+06 |  6.01795e+06 |     1.06415  |          5.65516e+06 |       6.01795e+06 |          5.65516e+06 |       6.01795e+06 |
| submission_qbb68_h1_q1_cogs_down080_keeprev.csv         |         656302 | 2023H1     |     8.633e+08   |  7.33787e+08 |     0.849979 |          4.76961e+06 |       4.05407e+06 |          1.232e+07   |       1.10144e+07 |
| submission_qbb68_h1_q1_cogs_down080_keeprev.csv         |         656302 | 2023H2     |     6.20433e+08 |  6.04622e+08 |     0.974516 |          3.37192e+06 |       3.28599e+06 |          6.6151e+06  |       7.54478e+06 |
| submission_qbb68_h1_q1_cogs_down080_keeprev.csv         |         656302 | 2024H1     |     8.83183e+08 |  7.48114e+08 |     0.847066 |          4.85265e+06 |       4.11052e+06 |          1.26027e+07 |       1.09204e+07 |
| submission_qbb68_h1_q1_cogs_down080_keeprev.csv         |         656302 | 2024-07-01 |     5.65516e+06 |  6.01795e+06 |     1.06415  |          5.65516e+06 |       6.01795e+06 |          5.65516e+06 |       6.01795e+06 |
| submission_qbb69_h1_q1_cogs_down120_keeprev.csv         |         655839 | 2023H1     |     8.633e+08   |  7.22434e+08 |     0.836829 |          4.76961e+06 |       3.99135e+06 |          1.232e+07   |       1.05355e+07 |
| submission_qbb69_h1_q1_cogs_down120_keeprev.csv         |         655839 | 2023H2     |     6.20433e+08 |  6.04622e+08 |     0.974516 |          3.37192e+06 |       3.28599e+06 |          6.6151e+06  |       7.54478e+06 |
| submission_qbb69_h1_q1_cogs_down120_keeprev.csv         |         655839 | 2024H1     |     8.83183e+08 |  7.48114e+08 |     0.847066 |          4.85265e+06 |       4.11052e+06 |          1.26027e+07 |       1.09204e+07 |
| submission_qbb69_h1_q1_cogs_down120_keeprev.csv         |         655839 | 2024-07-01 |     5.65516e+06 |  6.01795e+06 |     1.06415  |          5.65516e+06 |       6.01795e+06 |          5.65516e+06 |       6.01795e+06 |

## Raw date audit

| file            | date_column   |   non_null | min_date   | max_date   | has_forecast_period_rows   |   rows_in_forecast_period |
|:----------------|:--------------|-----------:|:-----------|:-----------|:---------------------------|--------------------------:|
| sales.csv       | Date          |       3833 | 2012-07-04 | 2022-12-31 | False                      |                         0 |
| orders.csv      | order_date    |     646945 | 2012-07-04 | 2022-12-31 | False                      |                         0 |
| order_items.csv |               |          0 |            |            | False                      |                         0 |
| payments.csv    |               |          0 |            |            | False                      |                         0 |
| returns.csv     | return_date   |      39939 | 2012-07-11 | 2022-12-31 | False                      |                         0 |
| shipments.csv   | ship_date     |     566067 | 2012-07-04 | 2022-12-29 | False                      |                         0 |
| shipments.csv   | delivery_date |     566067 | 2012-07-06 | 2022-12-31 | False                      |                         0 |
| web_traffic.csv | date          |       3652 | 2013-01-01 | 2022-12-31 | False                      |                         0 |
| promotions.csv  | start_date    |         50 | 2013-01-31 | 2022-11-18 | False                      |                         0 |
| promotions.csv  | end_date      |         50 | 2013-03-01 | 2022-12-31 | False                      |                         0 |
| inventory.csv   | snapshot_date |      60247 | 2012-07-31 | 2022-12-31 | False                      |                         0 |
| reviews.csv     | review_date   |     113551 | 2012-07-10 | 2022-12-31 | False                      |                         0 |
| customers.csv   | signup_date   |     121930 | 2012-01-17 | 2022-12-31 | False                      |                         0 |
| products.csv    |               |          0 |            |            | False                      |                         0 |

## Train half-year profile

|   year | half   |     revenue |        cogs |    ratio |   daily_revenue_mean |   daily_revenue_max |
|-------:|:-------|------------:|------------:|---------:|---------------------:|--------------------:|
|   2012 | H2     | 7.41498e+08 | 5.87462e+08 | 0.792264 |          4.09667e+06 |         1.00865e+07 |
|   2013 | H1     | 9.50871e+08 | 7.84852e+08 | 0.825403 |          5.25343e+06 |         1.38093e+07 |
|   2013 | H2     | 7.06298e+08 | 6.81128e+08 | 0.964363 |          3.83858e+06 |         1.09982e+07 |
|   2014 | H1     | 1.06877e+09 | 8.84436e+08 | 0.827529 |          5.90479e+06 |         1.73474e+07 |
|   2014 | H2     | 8.03078e+08 | 6.90171e+08 | 0.859407 |          4.36456e+06 |         1.39008e+07 |
|   2015 | H1     | 1.09742e+09 | 9.02972e+08 | 0.822815 |          6.06309e+06 |         1.52948e+07 |
|   2015 | H2     | 7.92515e+08 | 7.62469e+08 | 0.962088 |          4.30715e+06 |         1.02968e+07 |
|   2016 | H1     | 1.21523e+09 | 1.01091e+09 | 0.831866 |          6.67709e+06 |         1.73882e+07 |
|   2016 | H2     | 8.8941e+08  | 7.69651e+08 | 0.86535  |          4.83375e+06 |         1.51587e+07 |
|   2017 | H1     | 1.15351e+09 | 9.62281e+08 | 0.834222 |          6.37297e+06 |         1.76393e+07 |
|   2017 | H2     | 7.57657e+08 | 7.32105e+08 | 0.966274 |          4.1177e+06  |         1.01622e+07 |
|   2018 | H1     | 1.12605e+09 | 9.24463e+08 | 0.82098  |          6.22126e+06 |         2.09053e+07 |
|   2018 | H2     | 7.24075e+08 | 6.17713e+08 | 0.853106 |          3.93519e+06 |         1.37864e+07 |
|   2019 | H1     | 6.97133e+08 | 5.75869e+08 | 0.826053 |          3.85156e+06 |         1.05605e+07 |
|   2019 | H2     | 4.39669e+08 | 4.29334e+08 | 0.976494 |          2.3895e+06  |         5.52563e+06 |
|   2020 | H1     | 6.05371e+08 | 4.99077e+08 | 0.824415 |          3.32621e+06 |         1.00209e+07 |
|   2020 | H2     | 4.49141e+08 | 3.87008e+08 | 0.861662 |          2.44099e+06 |         8.48039e+06 |
|   2021 | H1     | 6.32182e+08 | 5.28017e+08 | 0.835229 |          3.49272e+06 |         1.07959e+07 |
|   2021 | H2     | 4.10858e+08 | 4.13114e+08 | 1.00549  |          2.23292e+06 |         6.54804e+06 |
|   2022 | H1     | 6.9245e+08  | 5.93828e+08 | 0.857575 |          3.82569e+06 |         1.16432e+07 |
|   2022 | H2     | 4.77298e+08 | 4.26592e+08 | 0.893764 |          2.59401e+06 |         7.9288e+06  |

## Current gap hypothesis

1. We are not losing because CatBoost/TabPFN is weak; blackbox gains are mostly post-target geometry.
2. We are not losing because 2023H1 total COGS ratio should be aggressively lower; V9 r0820 worsened.
3. We are likely missing a clean driver for **when** demand/COGS happen inside a period: source-quality, cohort/repeat customers, payment risk, return alignment, promo mix, or stockout/product availability.
4. The next clean attempt should model daily weights, not only period totals: `daily_weight = calendar x promo x source_quality_prior x return/stockout pressure`.

## Next clean directions

- Build a daily allocation model for 2023H1/Q1/Q2 using only train-derived priors: source-quality, COD cancellation risk, return-rate by original order date, and stockout pressure.
- Keep period totals close to `cleanv7`; only change daily shape first. V9 proves broad COGS-ratio movement is fragile.
- Use blackbox as diagnosis only: it says Q1/H2 high-ratio pockets matter, but clean must explain those pockets using raw operational mechanisms.
