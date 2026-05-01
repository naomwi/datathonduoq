# Clean V12 Monthly Funnel Router

Run directory: `logs\20260428_220951_clean_v12_monthly_funnel_router`

## Boundary

This is **clean-input research**. It does not read `sample_submission.csv`, prior submission files, quarantine files, or test target values as inputs. Operational inputs are summarized only from train rows through `2022-12-31`.

## Why This Exists

V10 showed that public likes a paired 2023H1 signal: Q1->Q2 Revenue timing plus lower monthly COGS-ratio regime. Ratio-only V10 failed, so V12 tries to explain the paired signal with monthly funnel and operational COGS-ratio drivers instead of hard-coded year donors.

## Validation Summary

| name                                        |   alpha | revenue_profile   | preserve_h1_cogs_total   | apply_revenue   | apply_ratio   |         mae |        rmse |       r2 |
|:--------------------------------------------|--------:|:------------------|:-------------------------|:----------------|:--------------|------------:|------------:|---------:|
| cleanv12_v10ops_h1_ratio_discount_a050      |    0.5  | v10_ops           | False                    | True            | True          | 4.7715e+06  | 6.0706e+06  | 0.985397 |
| cleanv12_monthfunnel_h1_revenue_only_a050   |    0.5  | ops               | True                     | True            | False         | 4.94575e+06 | 6.13042e+06 | 0.985108 |
| cleanv12_monthfunnel_h1_ratio_discount_a050 |    0.5  | ops               | False                    | True            | True          | 4.94696e+06 | 6.18591e+06 | 0.984837 |
| cleanv12_monthfunnel_h1_preservecogs_a050   |    0.5  | ops               | True                     | True            | True          | 4.98579e+06 | 6.17824e+06 | 0.984874 |
| cleanv12_v10control_h1_a075                 |    0.75 | v10               | False                    | True            | True          | 6.9997e+06  | 9.06111e+06 | 0.967465 |
| cleanv12_v10ops_h1_ratio_discount_a075      |    0.75 | v10_ops           | False                    | True            | True          | 7.15473e+06 | 9.10339e+06 | 0.967161 |
| cleanv12_monthfunnel_h1_ratio_discount_a075 |    0.75 | ops               | False                    | True            | True          | 7.41802e+06 | 9.27622e+06 | 0.965902 |
| cleanv12_monthfunnel_h1_preservecogs_a075   |    0.75 | ops               | True                     | True            | True          | 7.47965e+06 | 9.26798e+06 | 0.965963 |

## Final Forecast Priors

| mode    |   month |   revenue_share |   cogs_ratio |
|:--------|--------:|----------------:|-------------:|
| ops     |       1 |       0.0882015 |     0.817475 |
| ops     |       2 |       0.108547  |     0.808596 |
| ops     |       3 |       0.165828  |     0.858449 |
| ops     |       4 |       0.217779  |     0.85211  |
| ops     |       5 |       0.217587  |     0.804268 |
| ops     |       6 |       0.202058  |     0.839972 |
| v10_ops |       1 |       0.0868287 |     0.817475 |
| v10_ops |       2 |       0.104745  |     0.808596 |
| v10_ops |       3 |       0.164151  |     0.858449 |
| v10_ops |       4 |       0.217132  |     0.85211  |
| v10_ops |       5 |       0.222169  |     0.804268 |
| v10_ops |       6 |       0.204974  |     0.839972 |
| v10     |       1 |       0.0854558 |     0.810186 |
| v10     |       2 |       0.100943  |     0.81171  |
| v10     |       3 |       0.162474  |     0.860608 |
| v10     |       4 |       0.216485  |     0.850409 |
| v10     |       5 |       0.226751  |     0.802774 |
| v10     |       6 |       0.207891  |     0.839907 |

## Candidate Manifest

|   priority | filename                                                   |   alpha | revenue_profile   | ratio_profile   | preserve_h1_cogs_total   | apply_revenue   | apply_ratio   | note                                                                                            |   revenue_total |   cogs_total |   delta_revenue_total |   delta_cogs_total |   h1_revenue |     h1_cogs |   h1_ratio |   h1_q1_rev_share |   h1_q2_rev_share |   h1_q1_ratio |   h1_q2_ratio |   base_h1_q1_rev_share |   base_h1_q1_ratio |
|-----------:|:-----------------------------------------------------------|--------:|:------------------|:----------------|:-------------------------|:----------------|:--------------|:------------------------------------------------------------------------------------------------|----------------:|-------------:|----------------------:|-------------------:|-------------:|------------:|-----------:|------------------:|------------------:|--------------:|--------------:|-----------------------:|-------------------:|
|          1 | submission_cleanv12_monthfunnel_h1_ratio_discount_a050.csv |    0.5  | ops               | ops             | False                    | True            | True          | Monthly funnel Revenue profile plus operational COGS-ratio head; allows H1 COGS level movement. |     2.36279e+09 |  2.1032e+09  |                     0 |       -1.59641e+07 |  8.50285e+08 | 7.23784e+08 |   0.851225 |          0.365885 |          0.634115 |      0.860605 |      0.845812 |               0.369194 |           0.887641 |
|          2 | submission_cleanv12_monthfunnel_h1_ratio_discount_a075.csv |    0.75 | ops               | ops             | False                    | True            | True          | Stronger monthly funnel and COGS-ratio router.                                                  |     2.36279e+09 |  2.09524e+09 |                     0 |       -2.39236e+07 |  8.50285e+08 | 7.15824e+08 |   0.841864 |          0.364231 |          0.635769 |      0.847083 |      0.838874 |               0.369194 |           0.887641 |
|          3 | submission_cleanv12_monthfunnel_h1_preservecogs_a050.csv   |    0.5  | ops               | ops             | True                     | True            | True          | RMSE/R2 hedge: monthly router but preserve total H1 COGS.                                       |     2.36279e+09 |  2.11916e+09 |                     0 |        0           |  8.50285e+08 | 7.39748e+08 |   0.87     |          0.365885 |          0.634115 |      0.879587 |      0.864468 |               0.369194 |           0.887641 |
|          4 | submission_cleanv12_monthfunnel_h1_preservecogs_a075.csv   |    0.75 | ops               | ops             | True                     | True            | True          | Stronger preserve-total COGS monthly router.                                                    |     2.36279e+09 |  2.11916e+09 |                     0 |        0           |  8.50285e+08 | 7.39748e+08 |   0.87     |          0.364231 |          0.635769 |      0.875393 |      0.86691  |               0.369194 |           0.887641 |
|          5 | submission_cleanv12_monthfunnel_h1_revenue_only_a050.csv   |    0.5  | ops               | ops             | True                     | True            | False         | Isolate monthly Revenue timing from COGS-ratio changes.                                         |     2.36279e+09 |  2.11916e+09 |                     0 |        0           |  8.50285e+08 | 7.39748e+08 |   0.87     |          0.365885 |          0.634115 |      0.887478 |      0.859915 |               0.369194 |           0.887641 |
|          6 | submission_cleanv12_v10ops_h1_ratio_discount_a050.csv      |    0.5  | v10_ops           | ops             | False                    | True            | True          | Blend V10 train-regime Revenue shape with operational funnel profile and ratio model.           |     2.36279e+09 |  2.10313e+09 |                     0 |       -1.60262e+07 |  8.50285e+08 | 7.23722e+08 |   0.851152 |          0.362459 |          0.637541 |      0.860708 |      0.845719 |               0.369194 |           0.887641 |
|          7 | submission_cleanv12_v10ops_h1_ratio_discount_a075.csv      |    0.75 | v10_ops           | ops             | False                    | True            | True          | Stronger V10/ops hybrid router.                                                                 |     2.36279e+09 |  2.09517e+09 |                     0 |       -2.39868e+07 |  8.50285e+08 | 7.15761e+08 |   0.84179  |          0.359092 |          0.640908 |      0.847239 |      0.838736 |               0.369194 |           0.887641 |
|          8 | submission_cleanv12_v10control_h1_a075.csv                 |    0.75 | v10               | ops             | False                    | True            | True          | Control: reproduce V10-style train profile inside V12 framework.                                |     2.36279e+09 |  2.09469e+09 |                     0 |       -2.44731e+07 |  8.50285e+08 | 7.15275e+08 |   0.841218 |          0.353953 |          0.646047 |      0.847509 |      0.837771 |               0.369194 |           0.887641 |

## Submit Read

1. If prioritizing public MAE: test `submission_cleanv12_v10ops_h1_ratio_discount_a050.csv`.
2. If prioritizing RMSE/R2/report: test `submission_cleanv12_monthfunnel_h1_preservecogs_a050.csv`.
3. Do not submit ratio-only variants; `cleanv10_h1_ratio1719_keeprev_a100` already rejected that isolated hypothesis.
