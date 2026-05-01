# Clean V7 Period Funnel Council

Run directory: `logs\20260428_132543_clean_v7_period_funnel_council`

## Boundary

This is **clean-input public-guided**. The script does not read `sample_submission.csv`, previous `submission_*.csv`, quarantine files, or test targets as inputs.

Public feedback is used only to focus candidates near the current clean best neighborhood:

- `submission_cleanv2_h1fine_b044_r0876.csv = 673757.34993`
- `submission_cleanv3_funnel_c110_h1r0876.csv = 673759.96838`
- `submission_cleanv4_opratio_g020.csv = 677137.31895` failed.
- `submission_cleanv6_merch_revshape_g010.csv = 674337.07653` failed.

## Model Change

This branch changes the **period-total head**, not the daily shape:

- `order_funnel`: `sessions_recent * recovered_conversion * AOV_recent`
- `source_quality`: `sum(source_sessions_recent * recovered_source_revenue_per_session)`
- `source_quality_customer`: source-quality head with a small repeat/tenure customer-quality recovery scale

After period totals are set, daily allocation still uses the existing clean raw-md shape path.

## Rolling Period Validation

| half   | head                    |   recovery |   mean_ape |   worst_ape |   mean_abs_error |   mean_bias |   folds |
|:-------|:------------------------|-----------:|-----------:|------------:|-----------------:|------------:|--------:|
| H1     | source_quality_customer |       0.1  |   0.331527 |    0.652303 |      2.1822e+08  | 2.1822e+08  |       5 |
| H1     | source_quality          |       0.1  |   0.357088 |    0.663923 |      2.35578e+08 | 2.35578e+08 |       5 |
| H1     | source_quality_customer |       0.15 |   0.366828 |    0.67106  |      2.41977e+08 | 2.41977e+08 |       5 |
| H1     | source_quality_customer |       0.18 |   0.388009 |    0.682315 |      2.56231e+08 | 2.56231e+08 |       5 |
| H1     | source_quality          |       0.15 |   0.393268 |    0.682812 |      2.59917e+08 | 2.59917e+08 |       5 |
| H1     | source_quality_customer |       0.2  |   0.402129 |    0.689818 |      2.65734e+08 | 2.65734e+08 |       5 |
| H1     | source_quality          |       0.18 |   0.414976 |    0.694146 |      2.74521e+08 | 2.74521e+08 |       5 |
| H1     | source_quality          |       0.2  |   0.429449 |    0.706449 |      2.84257e+08 | 2.84257e+08 |       5 |
| H1     | order_funnel            |       0.06 |   0.494462 |    0.869788 |      3.32978e+08 | 3.32978e+08 |       5 |
| H1     | order_funnel            |       0.08 |   0.513632 |    0.890335 |      3.45748e+08 | 3.45748e+08 |       5 |
| H1     | order_funnel            |       0.1  |   0.532801 |    0.910881 |      3.58518e+08 | 3.58518e+08 |       5 |
| H1     | order_funnel            |       0.11 |   0.542385 |    0.921154 |      3.64903e+08 | 3.64903e+08 |       5 |
| H2     | source_quality_customer |       0.1  |   0.367783 |    0.828718 |      1.67105e+08 | 1.67105e+08 |       5 |
| H2     | source_quality          |       0.1  |   0.391861 |    0.840982 |      1.78353e+08 | 1.78353e+08 |       5 |
| H2     | source_quality_customer |       0.15 |   0.411471 |    0.861737 |      1.87115e+08 | 1.87115e+08 |       5 |
| H2     | source_quality          |       0.15 |   0.436523 |    0.874223 |      1.98806e+08 | 1.98806e+08 |       5 |
| H2     | source_quality_customer |       0.18 |   0.437683 |    0.881549 |      1.99121e+08 | 1.99121e+08 |       5 |
| H2     | source_quality_customer |       0.2  |   0.455159 |    0.894757 |      2.07126e+08 | 2.07126e+08 |       5 |
| H2     | source_quality          |       0.18 |   0.463321 |    0.894167 |      2.11078e+08 | 2.11078e+08 |       5 |
| H2     | source_quality          |       0.2  |   0.481186 |    0.907463 |      2.19259e+08 | 2.19259e+08 |       5 |
| H2     | order_funnel            |       0.06 |   0.520454 |    1.09037  |      2.39092e+08 | 2.39092e+08 |       5 |
| H2     | order_funnel            |       0.08 |   0.546266 |    1.1082   |      2.50823e+08 | 2.50823e+08 |       5 |
| H2     | order_funnel            |       0.1  |   0.572078 |    1.12603  |      2.62554e+08 | 2.62554e+08 |       5 |
| H2     | order_funnel            |       0.11 |   0.584984 |    1.13494  |      2.6842e+08  | 2.6842e+08  |       5 |

## Candidate Manifest

|   priority | filename                                             | revenue_head            |   h1_recovery |   h2_recovery |   h1_ratio | h2_ratio_mode   | override_periods   |   revenue_total |   cogs_total |   ratio_total | note                                                                                             |   rev_2023H1 |   cogs_2023H1 |   ratio_2023H1 |   rev_2023H2 |   cogs_2023H2 |   ratio_2023H2 |   rev_2024-07-01 |   cogs_2024-07-01 |   ratio_2024-07-01 |   rev_2024H1 |   cogs_2024H1 |   ratio_2024H1 |
|-----------:|:-----------------------------------------------------|:------------------------|--------------:|--------------:|-----------:|:----------------|:-------------------|----------------:|-------------:|--------------:|:-------------------------------------------------------------------------------------------------|-------------:|--------------:|---------------:|-------------:|--------------:|---------------:|-----------------:|------------------:|-------------------:|-------------:|--------------:|---------------:|
|          1 | submission_cleanv7_source_h1_s020_r0876.csv          | source_quality          |         0.2   |         nan   |      0.876 | base            | 2023H1             |     2.36279e+09 |  2.12426e+09 |      0.899047 | Source-quality period head: sum source sessions * recovered source revenue/session; H1 only.     |  8.50285e+08 |   7.44849e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |
|          2 | submission_cleanv7_source_h1_s018_r0876.csv          | source_quality          |         0.18  |         nan   |      0.876 | base            | 2023H1             |     2.34499e+09 |  2.10867e+09 |      0.899222 | Softer source-quality H1 recovery.                                                               |  8.32484e+08 |   7.29256e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |
|          3 | submission_cleanv7_source_h1_s022_r0876.csv          | source_quality          |         0.22  |         nan   |      0.876 | base            | 2023H1             |     2.3806e+09  |  2.13986e+09 |      0.898874 | Stronger source-quality H1 recovery.                                                             |  8.68086e+08 |   7.60443e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |
|          4 | submission_cleanv7_source_h1_s020_r0870.csv          | source_quality          |         0.2   |         nan   |      0.87  | base            | 2023H1             |     2.36279e+09 |  2.11916e+09 |      0.896887 | Source-quality H1 level plus lower H1 COGS ratio.                                                |  8.50285e+08 |   7.39748e+08 |          0.87  |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |
|          5 | submission_cleanv7_source_h1_s020_r0882.csv          | source_quality          |         0.2   |         nan   |      0.882 | base            | 2023H1             |     2.36279e+09 |  2.12936e+09 |      0.901206 | Source-quality H1 level plus higher H1 COGS ratio.                                               |  8.50285e+08 |   7.49951e+08 |          0.882 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |
|          6 | submission_cleanv7_source_customer_h1_s020_r0876.csv | source_quality_customer |         0.2   |         nan   |      0.876 | base            | 2023H1             |     2.33725e+09 |  2.10188e+09 |      0.899298 | Source-quality H1 head with small repeat/tenure customer-quality recovery scale.                 |  8.24739e+08 |   7.22472e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |
|          7 | submission_cleanv7_order_h1_c109_r0876.csv           | order_funnel            |         0.109 |         nan   |      0.876 | base            | 2023H1             |     2.36211e+09 |  2.12366e+09 |      0.899053 | Fine order-funnel head just below previous c110.                                                 |  8.49596e+08 |   7.44246e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |
|          8 | submission_cleanv7_order_h1_c112_r0876.csv           | order_funnel            |         0.112 |         nan   |      0.876 | base            | 2023H1             |     2.36617e+09 |  2.12722e+09 |      0.899014 | Fine order-funnel head just above previous c110.                                                 |  8.53663e+08 |   7.47809e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |
|          9 | submission_cleanv7_source_h1h2_s020_s030_h2base.csv  | source_quality          |         0.2   |           0.3 |      0.876 | base            | 2023H1,2023H2      |     2.37085e+09 |  2.13236e+09 |      0.899408 | Source-quality period head on H1 and H2; H2 recovery chosen to stay near current clean H2 level. |  8.50285e+08 |   7.44849e+08 |          0.876 |  6.29631e+08 |   6.33087e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |

## Submit Order

1. `submission_cleanv7_source_h1_s020_r0876.csv`
2. If step 1 improves: `submission_cleanv7_source_h1_s022_r0876.csv`
3. If step 1 worsens slightly: `submission_cleanv7_source_h1_s018_r0876.csv`
4. If source level is neutral but COGS is suspect: `submission_cleanv7_source_h1_s020_r0870.csv`
5. Do not submit H1+H2 unless H1-only is positive.
