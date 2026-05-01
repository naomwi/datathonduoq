# Clean V6 Merchandise Margin Priors

Run directory: `logs\20260428_131658_clean_v6_merch_margin_priors`

## Boundary

This is clean-input public-guided. It does not read `sample_submission.csv`, previous submissions, blackbox files, or test targets.

The new signal comes from train-only `orders.csv`, `order_items.csv`, and `products.csv` through `2022-12-31`:

- `discount_per_unit`
- weighted item margin rate
- category/segment margin rates
- size/color revenue shares

Future values are not used directly. They are projected by recurring train `month-day` priors, then applied as gentle period-total-preserving daily shape adjustments.

## Why This Exists

The LLM-council audit found that broad operational COGS ratio failed, but product economics by category/segment had stronger clean evidence for COGS-ratio residuals. This tests that more specific mechanism without using forbidden inputs.

## Factor Profile

|       |   merch_cogs_factor |   merch_revenue_factor |
|:------|--------------------:|-----------------------:|
| count |         366         |            366         |
| mean  |           1.05651   |              1.00252   |
| std   |           0.0843723 |              0.0359574 |
| min   |           0.980199  |              0.898212  |
| 5%    |           0.982842  |              0.945854  |
| 25%   |           0.985866  |              0.979621  |
| 50%   |           1         |              1         |
| 75%   |           1.11689   |              1.02749   |
| 95%   |           1.20991   |              1.06481   |
| max   |           1.21852   |              1.11107   |

## Candidate Manifest

|   priority | filename                                             | scope   |   cogs_gamma |   revenue_gamma |   revenue_total |   cogs_total |   ratio_total | note                                                                                                          |   rev_2023H1 |   cogs_2023H1 |   ratio_2023H1 |   rev_2023H2 |   cogs_2023H2 |   ratio_2023H2 |   rev_2024-07-01 |   cogs_2024-07-01 |   ratio_2024-07-01 |   rev_2024H1 |   cogs_2024H1 |   ratio_2024H1 |   rev_abs_delta_mean |   cogs_abs_delta_mean |   rev_abs_delta_max |   cogs_abs_delta_max |   revenue_total_ratio_vs_base |   cogs_total_ratio_vs_base |   max_revenue |    max_cogs |
|-----------:|:-----------------------------------------------------|:--------|-------------:|----------------:|----------------:|-------------:|--------------:|:--------------------------------------------------------------------------------------------------------------|-------------:|--------------:|---------------:|-------------:|--------------:|---------------:|-----------------:|------------------:|-------------------:|-------------:|--------------:|---------------:|---------------------:|----------------------:|--------------------:|---------------------:|------------------------------:|---------------------------:|--------------:|------------:|
|          1 | submission_cleanv6_merch_base_h1b044_r0876.csv       | all     |         0    |             0   |     2.36518e+09 |  2.12635e+09 |      0.899023 | Sanity rebuild of current clean base; do not submit.                                                          |  8.52667e+08 |   7.46937e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |                 0    |                   0   |                 0   |                    0 |                             1 |                          1 |   1.22173e+07 | 1.19043e+07 |
|          2 | submission_cleanv6_merch_cogs_g010.csv               | all     |         0.1  |             0   |     2.36518e+09 |  2.12635e+09 |      0.899023 | Gentle COGS-only merchandise economics prior from discount/unit and category/segment margin month-day priors. |  8.52667e+08 |   7.46937e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |                 0    |               23078.5 |                 0   |               152547 |                             1 |                          1 |   1.22173e+07 | 1.2028e+07  |
|          3 | submission_cleanv6_merch_cogs_g020.csv               | all     |         0.2  |             0   |     2.36518e+09 |  2.12635e+09 |      0.899023 | Moderate COGS-only merchandise economics prior; Revenue unchanged.                                            |  8.52667e+08 |   7.46937e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |                 0    |               45933.7 |                 0   |               304275 |                             1 |                          1 |   1.22173e+07 | 1.21511e+07 |
|          4 | submission_cleanv6_merch_cogs_g035.csv               | all     |         0.35 |             0   |     2.36518e+09 |  2.12635e+09 |      0.899023 | Stronger COGS-only merchandise economics prior; still period-total preserving.                                |  8.52667e+08 |   7.46937e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |                 0    |               79807.5 |                 0   |               530347 |                             1 |                          1 |   1.22173e+07 | 1.23344e+07 |
|          5 | submission_cleanv6_merch_h1_cogs_g025.csv            | h1      |         0.25 |             0   |     2.36518e+09 |  2.12635e+09 |      0.899023 | H1-only COGS merchandise economics prior.                                                                     |  8.52667e+08 |   7.46937e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |                 0    |               37947.4 |                 0   |               379834 |                             1 |                          1 |   1.22173e+07 | 1.22124e+07 |
|          6 | submission_cleanv6_merch_revshape_g010.csv           | all     |         0    |             0.1 |     2.36518e+09 |  2.12635e+09 |      0.899023 | Revenue shape prior from train recurring color/size mix; COGS unchanged.                                      |  8.52667e+08 |   7.46937e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |             12307.9  |                   0   |             72099.2 |                    0 |                             1 |                          1 |   1.2275e+07  | 1.19043e+07 |
|          7 | submission_cleanv6_merch_revshape_g020.csv           | all     |         0    |             0.2 |     2.36518e+09 |  2.12635e+09 |      0.899023 | Stronger Revenue color/size daily-shape prior; COGS unchanged.                                                |  8.52667e+08 |   7.46937e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |             24600.4  |                   0   |            144106   |                    0 |                             1 |                          1 |   1.23326e+07 | 1.19043e+07 |
|          8 | submission_cleanv6_merch_combo_rev010_cogs020.csv    | all     |         0.2  |             0.1 |     2.36518e+09 |  2.12635e+09 |      0.899023 | Combined color/size Revenue shape and merchandise COGS-ratio prior.                                           |  8.52667e+08 |   7.46937e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |             12307.9  |               45933.7 |             72099.2 |               304275 |                             1 |                          1 |   1.2275e+07  | 1.21511e+07 |
|          9 | submission_cleanv6_merch_h1_combo_rev010_cogs025.csv | h1      |         0.25 |             0.1 |     2.36518e+09 |  2.12635e+09 |      0.899023 | H1-only combined merchandise prior.                                                                           |  8.52667e+08 |   7.46937e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |              9058.38 |               37947.4 |             72099.2 |               379834 |                             1 |                          1 |   1.2275e+07  | 1.22124e+07 |

## Suggested Submit Order

1. `submission_cleanv6_merch_cogs_g010.csv`
2. `submission_cleanv6_merch_cogs_g020.csv`
3. `submission_cleanv6_merch_revshape_g010.csv`
4. `submission_cleanv6_merch_combo_rev010_cogs020.csv`
5. `submission_cleanv6_merch_h1_cogs_g025.csv`

If `cogs_g010` fails, do not escalate `cogs_g020/g035`; pivot to the strict period-total funnel head.
