# Clean V8 Bottom-Up Funnel Council

Run directory: `logs\20260428_205736_clean_v8_bottomup_funnel_council`

## Boundary

This is clean-input public-guided. It does not read `sample_submission.csv`, previous submissions, quarantine files, or test targets.

Known public signals used only for candidate focus:

- `submission_cleanv7_source_h1_s020_r0870.csv = 673720.88479`
- `submission_cleanv7_sourcefine_s0190_r0870.csv = 674415.02000`, so do not lower H1 source recovery aggressively.

## Model Change

V7 changed only period totals and kept raw-md daily shape.

V8 tests a more bottom-up daily model:

1. Source/channel sessions shape from `web_traffic.csv`.
2. Source revenue/session recovery from `orders.csv` + `order_items.csv`.
3. Optional product economics COGS shape from `order_items.csv` + `products.csv`.
4. Period totals remain controlled at the current clean-best source-quality head.

## Source Daily Shape Validation

| half   |   recovery |   mean_daily_mae |   mean_total_ape |
|:-------|-----------:|-----------------:|-----------------:|
| H1     |       0.1  |      6.27899e+06 |         0.401621 |
| H1     |       0.15 |      6.37399e+06 |         0.439    |
| H1     |       0.2  |      6.46917e+06 |         0.476378 |
| H1     |       0.25 |      6.56462e+06 |         0.513757 |
| H1     |       0.3  |      6.66085e+06 |         0.551136 |
| H2     |       0.1  |      4.341e+06   |         0.496994 |
| H2     |       0.15 |      4.42698e+06 |         0.545046 |
| H2     |       0.2  |      4.51377e+06 |         0.593098 |
| H2     |       0.25 |      4.60243e+06 |         0.64115  |
| H2     |       0.3  |      4.69256e+06 |         0.689202 |

## Candidate Manifest

|   priority | filename                                                      | scope   |   source_alpha | cogs_mode   |   merch_gamma |   source_recovery_h1 |   source_recovery_h2 |   h1_ratio |   revenue_total |   cogs_total |   ratio_total | note                                                                                          |   rev_2023H1 |   cogs_2023H1 |   ratio_2023H1 |   rev_2023H2 |   cogs_2023H2 |   ratio_2023H2 |   rev_2024-07-01 |   cogs_2024-07-01 |   ratio_2024-07-01 |   rev_2024H1 |   cogs_2024H1 |   ratio_2024H1 |   rev_abs_delta_mean |   cogs_abs_delta_mean |   rev_abs_delta_max |   cogs_abs_delta_max |   revenue_total_ratio_vs_base |   cogs_total_ratio_vs_base |   max_revenue |    max_cogs |
|-----------:|:--------------------------------------------------------------|:--------|---------------:|:------------|--------------:|---------------------:|---------------------:|-----------:|----------------:|-------------:|--------------:|:----------------------------------------------------------------------------------------------|-------------:|--------------:|---------------:|-------------:|--------------:|---------------:|-----------------:|------------------:|-------------------:|-------------:|--------------:|---------------:|---------------------:|----------------------:|--------------------:|---------------------:|------------------------------:|---------------------------:|--------------:|------------:|
|          1 | submission_cleanv8_bottomup_h1_sourceblend_a002_keepcogs.csv  | 2023H1  |           0.02 | keep        |           0   |                  0.2 |                  0.3 |       0.87 |     2.36279e+09 |  2.11916e+09 |      0.896887 | Micro source-channel daily Revenue shape; safest test after a010 showed large local movement. |  8.50285e+08 |   7.39748e+08 |           0.87 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |              35349.6 |                   0   |    965021           |          0           |                             1 |                          1 |   1.20408e+07 | 1.17897e+07 |
|          2 | submission_cleanv8_bottomup_h1_sourceblend_a005_keepcogs.csv  | 2023H1  |           0.05 | keep        |           0   |                  0.2 |                  0.3 |       0.87 |     2.36279e+09 |  2.11916e+09 |      0.896887 | Small source-channel daily Revenue shape; COGS daily shape unchanged.                         |  8.50285e+08 |   7.39748e+08 |           0.87 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |              88374.1 |                   0   |         2.41255e+06 |          0           |                             1 |                          1 |   1.20408e+07 | 1.17897e+07 |
|          3 | submission_cleanv8_bottomup_h1_sourceblend_a005_comove.csv    | 2023H1  |           0.05 | comove      |           0   |                  0.2 |                  0.3 |       0.87 |     2.36279e+09 |  2.11916e+09 |      0.896887 | Small source-channel daily Revenue shape with COGS co-moving at period ratio.                 |  8.50285e+08 |   7.39748e+08 |           0.87 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |              88374.1 |               88983.1 |         2.41255e+06 |          2.09839e+06 |                             1 |                          1 |   1.20408e+07 | 1.10684e+07 |
|          4 | submission_cleanv8_bottomup_h1_sourceblend_a010_keepcogs.csv  | 2023H1  |           0.1  | keep        |           0   |                  0.2 |                  0.3 |       0.87 |     2.36279e+09 |  2.11916e+09 |      0.896887 | Low-risk source-channel daily Revenue shape; COGS daily shape unchanged.                      |  8.50285e+08 |   7.39748e+08 |           0.87 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |             176748   |                   0   |         4.82511e+06 |          0           |                             1 |                          1 |   1.20408e+07 | 1.17897e+07 |
|          5 | submission_cleanv8_bottomup_h1_sourceblend_a025_keepcogs.csv  | 2023H1  |           0.25 | keep        |           0   |                  0.2 |                  0.3 |       0.87 |     2.36279e+09 |  2.11916e+09 |      0.896887 | Moderate source-channel daily Revenue shape; COGS daily shape unchanged.                      |  8.50285e+08 |   7.39748e+08 |           0.87 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |             441870   |                   0   |         1.20628e+07 |          0           |                             1 |                          1 |   1.80236e+07 | 1.17897e+07 |
|          6 | submission_cleanv8_bottomup_h1_sourceblend_a050_keepcogs.csv  | 2023H1  |           0.5  | keep        |           0   |                  0.2 |                  0.3 |       0.87 |     2.36279e+09 |  2.11916e+09 |      0.896887 | Strong source-channel daily Revenue shape; COGS daily shape unchanged.                        |  8.50285e+08 |   7.39748e+08 |           0.87 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |             883741   |                   0   |         2.41255e+07 |          0           |                             1 |                          1 |   2.97258e+07 | 1.17897e+07 |
|          7 | submission_cleanv8_bottomup_h1_sourceblend_a025_comove.csv    | 2023H1  |           0.25 | comove      |           0   |                  0.2 |                  0.3 |       0.87 |     2.36279e+09 |  2.11916e+09 |      0.896887 | Source-channel daily Revenue shape with COGS co-moving at period ratio.                       |  8.50285e+08 |   7.39748e+08 |           0.87 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |             441870   |              386151   |         1.20628e+07 |          1.04613e+07 |                             1 |                          1 |   1.80236e+07 | 1.56806e+07 |
|          8 | submission_cleanv8_bottomup_h1_sourceblend_a050_comove.csv    | 2023H1  |           0.5  | comove      |           0   |                  0.2 |                  0.3 |       0.87 |     2.36279e+09 |  2.11916e+09 |      0.896887 | Stronger source-channel daily Revenue shape with COGS co-moving.                              |  8.50285e+08 |   7.39748e+08 |           0.87 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |             883741   |              770513   |         2.41255e+07 |          2.09559e+07 |                             1 |                          1 |   2.97258e+07 | 2.58615e+07 |
|          9 | submission_cleanv8_bottomup_h1_sourceblend_a025_merch010.csv  | 2023H1  |           0.25 | merch       |           0.1 |                  0.2 |                  0.3 |       0.87 |     2.36279e+09 |  2.11916e+09 |      0.896887 | Source-channel daily Revenue shape plus merchandise economics COGS shape.                     |  8.50285e+08 |   7.39748e+08 |           0.87 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |             441870   |              386175   |         1.20628e+07 |          1.05273e+07 |                             1 |                          1 |   1.80236e+07 | 1.5953e+07  |
|         10 | submission_cleanv8_bottomup_h1_sourceblend_a050_merch010.csv  | 2023H1  |           0.5  | merch       |           0.1 |                  0.2 |                  0.3 |       0.87 |     2.36279e+09 |  2.11916e+09 |      0.896887 | Stronger source-channel daily Revenue shape plus merchandise COGS shape.                      |  8.50285e+08 |   7.39748e+08 |           0.87 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |             883741   |              770842   |         2.41255e+07 |          2.10624e+07 |                             1 |                          1 |   2.97258e+07 | 2.62456e+07 |
|         11 | submission_cleanv8_bottomup_all_sourceblend_a010_keepcogs.csv | major   |           0.1  | keep        |           0   |                  0.2 |                  0.3 |       0.87 |     2.36279e+09 |  2.11916e+09 |      0.896887 | Apply small bottom-up source daily shape to all major periods; high-risk broad test.          |  8.50285e+08 |   7.39748e+08 |           0.87 |  6.21578e+08 |   6.24991e+08 |        1.00549 |      7.10042e+06 |       7.68649e+06 |            1.08254 |  8.83831e+08 |   7.46735e+08 |       0.844885 |             516615   |                   0   |         1.43053e+07 |          0           |                             1 |                          1 |   1.68522e+07 | 1.17897e+07 |

## Submit Order

1. `submission_cleanv8_bottomup_h1_sourceblend_a002_keepcogs.csv`
2. If improves: `submission_cleanv8_bottomup_h1_sourceblend_a005_keepcogs.csv`
3. If Revenue shape improves but COGS looks suspect: `submission_cleanv8_bottomup_h1_sourceblend_a005_comove.csv`
4. Do not submit all-period sourceblend unless H1-only is positive.
