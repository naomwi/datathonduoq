# Clean V18 Daily Ratio Tail Router

Run directory: `logs\20260429_190851_clean_v18_daily_ratio_tail_router`

## Boundary

This is **clean-input public-guided research**. It rebuilds current clean best from raw/train inputs, then uses train-derived recurring priors for daily COGS/Revenue ratio. It does not read `sample_submission.csv`, previous submissions, quarantine files, or test target values as inputs.

## Hypothesis

V17 showed H2 COGS ratio level helps, but stronger period-level COGS-down (`c550`) over-shoots public. V18 therefore stops changing period totals aggressively and tests:

1. Daily `COGS = Revenue * learned_ratio(month, day, dow, discount-prior, source-prior, regime)`.
2. Tail/RMSE routing that applies stronger ratio correction only on high-Revenue days.
3. Regime routing from train folds: recent-even is strongest for H2 ratio validation, recovery-low is strongest for H1.

Future discount/source features are not actual test features; they are recurring priors learned from train history.

## Daily Ratio Validation

| half   | regime          |    mae |   rmse |       r2 |
|:-------|:----------------|-------:|-------:|---------:|
| H1     | recent_weighted | 109177 | 160372 | 0.994149 |
| H1     | all_median      | 109177 | 160372 | 0.994149 |
| H1     | pre2019_high    | 110274 | 163767 | 0.993898 |
| H1     | recovery_low    | 113454 | 167912 | 0.993585 |
| H1     | recent_even     | 114610 | 174807 | 0.993048 |
| H2     | recent_even     | 177017 | 409838 | 0.912674 |
| H2     | pre2019_high    | 275548 | 599765 | 0.812983 |
| H2     | recent_weighted | 303541 | 661651 | 0.772397 |
| H2     | all_median      | 303541 | 661651 | 0.772397 |
| H2     | recovery_low    | 308548 | 670345 | 0.766377 |

## Candidate Manifest

|   priority | filename                                                              | scopes        | regime       |   alpha | mode   | preserve   |   tail_quantile |   tail_boost | note                                                                                                       |   revenue_total |   cogs_total |   delta_revenue_total |   delta_cogs_total |   mean_abs_cogs_delta |   max_abs_cogs_delta |   ratio_p95 |   ratio_max |   2023H1_cogs_delta |   2023H1_ratio |   2023H2_cogs_delta |   2023H2_ratio |   2024H1_cogs_delta |   2024H1_ratio |
|-----------:|:----------------------------------------------------------------------|:--------------|:-------------|--------:|:-------|:-----------|----------------:|-------------:|:-----------------------------------------------------------------------------------------------------------|----------------:|-------------:|----------------------:|-------------------:|----------------------:|---------------------:|------------:|------------:|--------------------:|---------------:|--------------------:|---------------:|--------------------:|---------------:|
|          1 | submission_cleanv18_v17_h2_dailyratio_recenteven_shape_a350.csv       | 2023H2        | recent_even  |    0.35 | all    | period     |             0.8 |         0    | Daily COGS ratio shape-only head for H2; preserves V17 2023H2 COGS total.                                  |     2.36279e+09 |  2.07568e+09 |                     0 |       -4.76837e-07 |               34334.2 |     550577           |     1.06496 |     1.1429  |                   0 |       0.841303 |         0           |       0.974788 |                   0 |       0.844885 |
|          2 | submission_cleanv18_v17_h2_dailyratio_recenteven_direct_a150.csv      | 2023H2        | recent_even  |    0.15 | all    | none       |             0.8 |         0    | Mild direct daily COGS = Revenue * learned_ratio for H2; tests total direction without big overshoot.      |     2.36279e+09 |  2.06728e+09 |                     0 |       -8.39396e+06 |               16714.1 |     335310           |     1.05892 |     1.13951 |                   0 |       0.841303 |        -8.39396e+06 |       0.961283 |                   0 |       0.844885 |
|          3 | submission_cleanv18_v17_h2_tailratio_recenteven_p80_a300.csv          | 2023H2        | recent_even  |    0.3  | tail   | period     |             0.8 |         1    | Tail/RMSE head: stronger learned ratio on top 20% H2 Revenue days, preserving period COGS total.           |     2.36279e+09 |  2.07568e+09 |                     0 |       -2.38419e-07 |               44425.8 |          1.0819e+06  |     1.0708  |     1.15798 |                   0 |       0.841303 |         0           |       0.974788 |                   0 |       0.844885 |
|          4 | submission_cleanv18_v17_h2_tailratio_recenteven_p90_a400.csv          | 2023H2        | recent_even  |    0.4  | tail   | period     |             0.9 |         1.25 | Sharper tail/RMSE head on top 10% H2 Revenue days; period COGS total preserved.                            |     2.36279e+09 |  2.07568e+09 |                     0 |        0           |               62651   |          1.69971e+06 |     1.07783 |     1.15925 |                   0 |       0.841303 |         1.19209e-07 |       0.974788 |                   0 |       0.844885 |
|          5 | submission_cleanv18_v17_router_h1recovery_h2recenteven_shape_a300.csv | 2023H1,2023H2 | router       |    0.3  | all    | period     |             0.8 |         0    | Regime-router candidate: H2 uses recent-even daily ratio; applied period-preserved to avoid level leakage. |     2.36279e+09 |  2.07568e+09 |                     0 |       -2.38419e-07 |               38755.7 |     469682           |     1.06576 |     1.14447 |                   0 |       0.841303 |         0           |       0.974788 |                   0 |       0.844885 |
|          6 | submission_cleanv18_v17_h1_dailyratio_recovery_shape_a350.csv         | 2023H1        | recovery_low |    0.35 | all    | period     |             0.8 |         0    | H1 recovery ratio daily shape head; preserves 2023H1 COGS total.                                           |     2.36279e+09 |  2.07568e+09 |                     0 |       -2.38419e-07 |               11050.6 |     259665           |     1.08838 |     1.19649 |                   0 |       0.841303 |         0           |       0.974788 |                   0 |       0.844885 |
|          7 | submission_cleanv18_v17_h2_dailyratio_recovery_direct_a200.csv        | 2023H2        | recovery_low |    0.2  | all    | none       |             0.8 |         0    | Mild direct H2 recovery daily ratio; alternate lower-volatility regime.                                    |     2.36279e+09 |  2.07371e+09 |                     0 |       -1.96151e+06 |               11752.2 |     258537           |     1.08456 |     1.19319 |                   0 |       0.841303 |        -1.96151e+06 |       0.971632 |                   0 |       0.844885 |
