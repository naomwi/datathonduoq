# Clean V10 H1 Regime Shape

Run directory: `logs\20260428_211838_clean_v10_h1_regime_shape`

## Boundary

This is **clean-input public-guided**. It does not read `sample_submission.csv`, prior submission files, quarantine files, or test target values as inputs. It rebuilds the current clean frame from raw pipeline components, then applies train-derived H1 month priors.

Public feedback is used only to choose the family: V9 rejected broad H1 COGS-down, while blackbox diagnostics suggested a month/quarter phase issue. The numeric priors below are taken only from train `sales.csv`.

## Train Priors

Revenue month shares use median of train years `2014, 2016, 2017`.

|   month |   revenue_share |
|--------:|----------------:|
|       1 |       0.0854558 |
|       2 |       0.100943  |
|       3 |       0.162474  |
|       4 |       0.216485  |
|       5 |       0.226751  |
|       6 |       0.207891  |

COGS ratios use median of train years `2016, 2017, 2019`.

|   month |   cogs_ratio |
|--------:|-------------:|
|       1 |     0.810186 |
|       2 |     0.81171  |
|       3 |     0.860608 |
|       4 |     0.850409 |
|       5 |     0.802774 |
|       6 |     0.839907 |

## Candidate Manifest

|   priority | filename                                              |   alpha | use_revenue_shape   | note                                                                              |   revenue_total |   cogs_total |   delta_revenue_total |   delta_cogs_total |   h1_revenue |     h1_cogs |   h1_ratio |   h1_q1_rev_share |   h1_q2_rev_share |   h1_q1_ratio |   h1_q2_ratio |   base_h1_q1_rev_share |   base_h1_q1_ratio |
|-----------:|:------------------------------------------------------|--------:|:--------------------|:----------------------------------------------------------------------------------|----------------:|-------------:|----------------------:|-------------------:|-------------:|------------:|-----------:|------------------:|------------------:|--------------:|--------------:|-----------------------:|-------------------:|
|          1 | submission_cleanv10_h1_ratio1719_keeprev_a050.csv     |    0.5  | False               | Keep clean Revenue; move H1 COGS toward train median 2016/2017/2019 month ratios. |     2.36279e+09 |  2.10302e+09 |                     0 |       -1.61443e+07 |  8.50285e+08 | 7.23603e+08 |   0.851013 |          0.369194 |          0.630806 |      0.861013 |      0.84516  |               0.369194 |           0.887641 |
|          2 | submission_cleanv10_h1_ratio1719_keeprev_a075.csv     |    0.75 | False               | Stronger H1 month-ratio regime without changing Revenue timing.                   |     2.36279e+09 |  2.09494e+09 |                     0 |       -2.42165e+07 |  8.50285e+08 | 7.15531e+08 |   0.84152  |          0.369194 |          0.630806 |      0.847699 |      0.837903 |               0.369194 |           0.887641 |
|          3 | submission_cleanv10_h1_ratio1719_keeprev_a100.csv     |    1    | False               | Full H1 month-ratio regime from train years 2016/2017/2019.                       |     2.36279e+09 |  2.08687e+09 |                     0 |       -3.22886e+07 |  8.50285e+08 | 7.07459e+08 |   0.832026 |          0.369194 |          0.630806 |      0.834385 |      0.830645 |               0.369194 |           0.887641 |
|          4 | submission_cleanv10_h1_shape141617_ratio1719_a050.csv |    0.5  | True                | Blend H1 Revenue timing to 2014/2016/2017 shape and COGS ratio to 2016/2017/2019. |     2.36279e+09 |  2.10289e+09 |                     0 |       -1.62669e+07 |  8.50285e+08 | 7.23481e+08 |   0.850869 |          0.359033 |          0.640967 |      0.861632 |      0.84484  |               0.369194 |           0.887641 |
|          5 | submission_cleanv10_h1_shape141617_ratio1719_a075.csv |    0.75 | True                | Stronger train-regime H1 timing and monthly COGS ratio.                           |     2.36279e+09 |  2.09476e+09 |                     0 |       -2.44004e+07 |  8.50285e+08 | 7.15347e+08 |   0.841303 |          0.353953 |          0.646047 |      0.848068 |      0.837597 |               0.369194 |           0.887641 |
|          6 | submission_cleanv10_h1_shape141617_ratio1719_a100.csv |    1    | True                | Full train-regime H1 timing and monthly COGS ratio.                               |     2.36279e+09 |  2.08663e+09 |                     0 |       -3.25338e+07 |  8.50285e+08 | 7.07214e+08 |   0.831738 |          0.348873 |          0.651127 |      0.834109 |      0.830467 |               0.369194 |           0.887641 |

## Submit Read

1. Submit `submission_cleanv10_h1_shape141617_ratio1719_a075.csv` first if we want one large clean sign test.
2. If it improves: escalate to `submission_cleanv10_h1_shape141617_ratio1719_a100.csv`.
3. If it fails but not badly: try `submission_cleanv10_h1_ratio1719_keeprev_a075.csv` to isolate COGS month-ratio from Revenue timing.
4. If it fails badly: this route is not enough; move to return/order-date or stockout-pressure daily allocation.
