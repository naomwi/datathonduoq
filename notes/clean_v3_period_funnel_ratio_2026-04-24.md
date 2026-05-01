# Clean V3 Period Funnel Ratio

Run directory: `logs\20260424_114308_clean_v3_period_funnel_ratio`

## Boundary

This is a clean-input, public-guided calibration branch. It rebuilds the anchor/daily shape from raw provided inputs and train `sales.csv`; it does not read `sample_submission.csv`, previous submissions, or test targets as inputs.

Public feedback is used only to focus the neighborhood around the current clean-input best:

- `submission_cleanv2_h1fine_b044_r0876.csv = 673757.34993`
- `submission_cleanv2_h1fine_b045_r0876.csv = 673785.31754`
- `submission_cleanv2_h1fine_b046_r0876.csv = 673951.68734`
- `submission_cleanv2_h1funnel_b050_r0876.csv = 676153.29609`

## Method

Revenue period head:

- `2023H1 Revenue = recent_low_H1 + beta * (pre2019_high_H1 - recent_low_H1)`
- Current best beta neighborhood is around `0.44`.

COGS ratio head:

- `2023H1 COGS = 2023H1 Revenue * h1_ratio`
- `2023H2 COGS = 2023H2 Revenue * h2_ratio` for H2 ratio candidates.
- H2 ratio candidates use train quantiles instead of the old max-ratio stress.

## Train Ratio Reference

|   h1_q05 |   h1_q09 |   h1_q095 |   h1_q0975 |   h1_q098 |   h1_q099 |   h1_q10 |   h2_q05 |   h2_q09 |   h2_q095 |   h2_q0975 |   h2_q098 |   h2_q099 |   h2_q10 |
|---------:|---------:|----------:|-----------:|----------:|----------:|---------:|---------:|---------:|----------:|-----------:|----------:|----------:|---------:|
| 0.826791 | 0.837463 |  0.847519 |   0.852547 |  0.853553 |  0.855564 | 0.857575 | 0.927926 | 0.979394 |  0.992442 |   0.998966 |   1.00027 |   1.00288 |  1.00549 |

## Candidate Manifest

|   priority | filename                                             |   h1_beta |   h1_cogs_ratio_input |   h2_cogs_ratio_input |   ratio_shape_gamma |   revenue_total |   cogs_total |   ratio_total |   rev_2023H1 |   cogs_2023H1 |   ratio_2023H1 |   rev_2023H2 |   cogs_2023H2 |   ratio_2023H2 |   rev_2024H1 |   cogs_2024H1 |   ratio_2024H1 | note                                                                             |
|-----------:|:-----------------------------------------------------|----------:|----------------------:|----------------------:|--------------------:|----------------:|-------------:|--------------:|-------------:|--------------:|---------------:|-------------:|--------------:|---------------:|-------------:|--------------:|---------------:|:---------------------------------------------------------------------------------|
|          1 | submission_cleanv3_b0440_h1r0870.csv                 |     0.44  |                 0.87  |            nan        |                0    |     2.36518e+09 |  2.12123e+09 |      0.89686  |  8.52667e+08 |   7.41821e+08 |          0.87  |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.46735e+08 |       0.844885 | Best H1 level held fixed; lower H1 ratio toward train-plausible recovery stress. |
|          2 | submission_cleanv3_b0440_h1r0882.csv                 |     0.44  |                 0.882 |            nan        |                0    |     2.36518e+09 |  2.13147e+09 |      0.901186 |  8.52667e+08 |   7.52053e+08 |          0.882 |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.46735e+08 |       0.844885 | Best H1 level held fixed; higher H1 ratio to test whether COGS is undercalled.   |
|          3 | submission_cleanv3_b0440_h1r0876_h2q98.csv           |     0.44  |                 0.876 |              1.00027  |                0    |     2.36518e+09 |  2.12311e+09 |      0.897652 |  8.52667e+08 |   7.46937e+08 |          0.876 |  6.21578e+08 |   6.21747e+08 |       1.00027  |  8.83831e+08 |   7.46735e+08 |       0.844885 | Keep best H1; replace 2023H2 max-ratio stress with train H2 q98 ratio.           |
|          4 | submission_cleanv3_b0440_h1r0876_h2q975.csv          |     0.44  |                 0.876 |              0.998966 |                0    |     2.36518e+09 |  2.12229e+09 |      0.897309 |  8.52667e+08 |   7.46937e+08 |          0.876 |  6.21578e+08 |   6.20936e+08 |       0.998966 |  8.83831e+08 |   7.46735e+08 |       0.844885 | Keep best H1; soften 2023H2 ratio from max to train q97.5.                       |
|          5 | submission_cleanv3_b0440_h1r0876_h2q95.csv           |     0.44  |                 0.876 |              0.992442 |                0    |     2.36518e+09 |  2.11824e+09 |      0.895594 |  8.52667e+08 |   7.46937e+08 |          0.876 |  6.21578e+08 |   6.1688e+08  |       0.992442 |  8.83831e+08 |   7.46735e+08 |       0.844885 | Keep best H1; stronger clean H2 ratio normalization to train q95.                |
|          6 | submission_cleanv3_b0440_h1r0870_h2q98.csv           |     0.44  |                 0.87  |              1.00027  |                0    |     2.36518e+09 |  2.11799e+09 |      0.895489 |  8.52667e+08 |   7.41821e+08 |          0.87  |  6.21578e+08 |   6.21747e+08 |       1.00027  |  8.83831e+08 |   7.46735e+08 |       0.844885 | Lower H1 ratio plus mild 2023H2 ratio normalization.                             |
|          7 | submission_cleanv3_b0435_h1r0876.csv                 |     0.435 |                 0.876 |            nan        |                0    |     2.36295e+09 |  2.1244e+09  |      0.899045 |  8.50442e+08 |   7.44987e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.46735e+08 |       0.844885 | Fine-map H1 period head just below current best b044.                            |
|          8 | submission_cleanv3_b0445_h1r0876.csv                 |     0.445 |                 0.876 |            nan        |                0    |     2.3674e+09  |  2.1283e+09  |      0.899002 |  8.54893e+08 |   7.48887e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.46735e+08 |       0.844885 | Fine-map H1 period head just above current best b044.                            |
|          9 | submission_cleanv3_b0440_h1r0876_h2q98_dailyg025.csv |     0.44  |                 0.876 |              1.00027  |                0.25 |     2.36518e+09 |  2.12311e+09 |      0.897652 |  8.52667e+08 |   7.46937e+08 |          0.876 |  6.21578e+08 |   6.21747e+08 |       1.00027  |  8.83831e+08 |   7.46735e+08 |       0.844885 | H2 q98 total plus train-derived promo/month daily COGS-ratio reshaping.          |

## Submit Order

1. `submission_cleanv3_b0440_h1r0870.csv`
2. `submission_cleanv3_b0440_h1r0882.csv`
3. `submission_cleanv3_b0440_h1r0876_h2q98.csv`
4. `submission_cleanv3_b0435_h1r0876.csv`
5. `submission_cleanv3_b0445_h1r0876.csv`
6. `submission_cleanv3_b0440_h1r0876_h2q975.csv`
7. `submission_cleanv3_b0440_h1r0870_h2q98.csv`
8. `submission_cleanv3_b0440_h1r0876_h2q98_dailyg025.csv`
9. `submission_cleanv3_b0440_h1r0876_h2q95.csv`
