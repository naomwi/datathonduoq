# Clean V3 Ratio Axis

Run directory: `logs\20260424_134519_clean_v3_ratio_axis`

## Boundary

This is a clean-input public-guided follow-up. It freezes the H1 level at the submitted `c110` funnel head:

`2023H1 Revenue = 2022 sessions * recovered_conversion(0.110) * 2022 AOV`

Then it changes only COGS ratio assumptions. It does not read `sample_submission.csv`, previous submissions, or test targets as inputs.

Known score:

- `submission_cleanv3_funnel_c110_h1r0876.csv = 673759.96838`

## Train Ratio Reference

|   h1_q05 |   h1_q075 |   h1_q09 |   h1_q095 |   h1_q0975 |   h1_q098 |   h1_q099 |   h1_q10 |   h2_q05 |   h2_q075 |   h2_q09 |   h2_q095 |   h2_q0975 |   h2_q098 |   h2_q099 |   h2_q10 |
|---------:|----------:|---------:|----------:|-----------:|----------:|----------:|---------:|---------:|----------:|---------:|----------:|-----------:|----------:|----------:|---------:|
| 0.826791 |  0.833633 | 0.837463 |  0.847519 |   0.852547 |  0.853553 |  0.855564 | 0.857575 | 0.927926 |  0.965796 | 0.979394 |  0.992442 |   0.998966 |   1.00027 |   1.00288 |  1.00549 |

## Candidate Manifest

|   priority | filename                                            |   h1_cogs_ratio |   h2_cogs_ratio |   h1_2024_cogs_ratio |   revenue_total |   cogs_total |   ratio_total |   rev_2023H1 |   cogs_2023H1 |   ratio_2023H1 |   rev_2023H2 |   cogs_2023H2 |   ratio_2023H2 |   rev_2024H1 |   cogs_2024H1 |   ratio_2024H1 | note                                                          |
|-----------:|:----------------------------------------------------|----------------:|----------------:|---------------------:|----------------:|-------------:|--------------:|-------------:|--------------:|---------------:|-------------:|--------------:|---------------:|-------------:|--------------:|---------------:|:--------------------------------------------------------------|
|          1 | submission_cleanv3_ratio_c110_h1r0870.csv           |           0.87  |      nan        |           nan        |     2.36346e+09 |  2.11974e+09 |      0.89688  |  8.50952e+08 |   7.40328e+08 |          0.87  |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.46735e+08 |       0.844885 | Same c110 funnel H1 level; lower H1 COGS ratio.               |
|          2 | submission_cleanv3_ratio_c110_h1r0882.csv           |           0.882 |      nan        |           nan        |     2.36346e+09 |  2.12995e+09 |      0.9012   |  8.50952e+08 |   7.5054e+08  |          0.882 |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.46735e+08 |       0.844885 | Same c110 funnel H1 level; higher H1 COGS ratio.              |
|          3 | submission_cleanv3_ratio_c110_h1r0866.csv           |           0.866 |      nan        |           nan        |     2.36346e+09 |  2.11634e+09 |      0.89544  |  8.50952e+08 |   7.36924e+08 |          0.866 |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.46735e+08 |       0.844885 | Lower H1 COGS ratio stress, still above train H1 max.         |
|          4 | submission_cleanv3_ratio_c110_h2q98.csv             |           0.876 |        1.00027  |           nan        |     2.36346e+09 |  2.1216e+09  |      0.897667 |  8.50952e+08 |   7.45434e+08 |          0.876 |  6.21578e+08 |   6.21747e+08 |       1.00027  |  8.83831e+08 |   7.46735e+08 |       0.844885 | Normalize 2023H2 COGS ratio from train max to train H2 q98.   |
|          5 | submission_cleanv3_ratio_c110_h2q975.csv            |           0.876 |        0.998966 |           nan        |     2.36346e+09 |  2.12079e+09 |      0.897324 |  8.50952e+08 |   7.45434e+08 |          0.876 |  6.21578e+08 |   6.20936e+08 |       0.998966 |  8.83831e+08 |   7.46735e+08 |       0.844885 | Normalize 2023H2 COGS ratio from train max to train H2 q97.5. |
|          6 | submission_cleanv3_ratio_c110_h1r0870_h2q98.csv     |           0.87  |        1.00027  |           nan        |     2.36346e+09 |  2.1165e+09  |      0.895507 |  8.50952e+08 |   7.40328e+08 |          0.87  |  6.21578e+08 |   6.21747e+08 |       1.00027  |  8.83831e+08 |   7.46735e+08 |       0.844885 | Combine lower H1 ratio with mild H2 ratio normalization.      |
|          7 | submission_cleanv3_ratio_c110_2024h1q95.csv         |           0.876 |      nan        |             0.847519 |     2.36346e+09 |  2.12717e+09 |      0.900025 |  8.50952e+08 |   7.45434e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.49064e+08 |       0.847519 | Small 2024H1 COGS ratio lift to train H1 q95.                 |
|          8 | submission_cleanv3_ratio_c110_2024h1q98.csv         |           0.876 |      nan        |             0.853553 |     2.36346e+09 |  2.13251e+09 |      0.902281 |  8.50952e+08 |   7.45434e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.54396e+08 |       0.853553 | Stronger 2024H1 COGS ratio lift to train H1 q98.              |
|          9 | submission_cleanv3_ratio_c110_h1r0870_2024h1q95.csv |           0.87  |      nan        |             0.847519 |     2.36346e+09 |  2.12207e+09 |      0.897865 |  8.50952e+08 |   7.40328e+08 |          0.87  |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.49064e+08 |       0.847519 | Lower 2023H1 ratio plus small 2024H1 ratio lift.              |

## Submit Order

1. `submission_cleanv3_ratio_c110_h1r0870.csv`
2. `submission_cleanv3_ratio_c110_h1r0882.csv`
3. `submission_cleanv3_ratio_c110_h2q98.csv`
4. `submission_cleanv3_ratio_c110_h1r0866.csv`
5. `submission_cleanv3_ratio_c110_h1r0870_h2q98.csv`
6. `submission_cleanv3_ratio_c110_2024h1q95.csv`
7. `submission_cleanv3_ratio_c110_h2q975.csv`
8. `submission_cleanv3_ratio_c110_2024h1q98.csv`
9. `submission_cleanv3_ratio_c110_h1r0870_2024h1q95.csv`
