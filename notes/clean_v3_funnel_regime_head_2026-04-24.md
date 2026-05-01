# Clean V3 Funnel Regime Head

Run directory: `logs\20260424_115258_clean_v3_funnel_regime_head`

## Boundary

This script uses provided train/source data only for modeling signals and rebuilds daily shape from raw inputs. It does not read `sample_submission.csv`, previous submissions, or test target values as feature inputs.

The candidate family is still **clean-input public-guided** where conversion-recovery values are chosen around public feedback. The script also emits a stricter train-fold selected candidate so the difference is explicit.

## Components Implemented

1. Period-total head: predicts half-year Revenue totals before daily allocation.
2. Funnel model: `Revenue = sessions_prior * conversion_regime * AOV_prior`.
3. Regime-mixture model: blends recent-low and high-regime same-half donors.
4. COGS ratio head: predicts `COGS / Revenue` separately from Revenue.

## Revenue Donor Validation

| target   | half   | donor           |   mean_abs_error |   mean_ape |   worst_ape |   mean_bias |   folds |
|:---------|:-------|:----------------|-----------------:|-----------:|------------:|------------:|--------:|
| revenue  | H1     | trend_log       |      1.91703e+08 |   0.2711   |    0.676225 | 7.6054e+07  |       5 |
| revenue  | H1     | recent4         |      1.92431e+08 |   0.292063 |    0.643374 | 1.89771e+08 |       5 |
| revenue  | H1     | regime_b20      |      2.31634e+08 |   0.352361 |    0.648905 | 2.31634e+08 |       5 |
| revenue  | H1     | regime_b30      |      2.52565e+08 |   0.384431 |    0.661097 | 2.52565e+08 |       5 |
| revenue  | H1     | regime_b40      |      2.73497e+08 |   0.4165   |    0.694718 | 2.73497e+08 |       5 |
| revenue  | H1     | regime_b44      |      2.81869e+08 |   0.429328 |    0.708166 | 2.81869e+08 |       5 |
| revenue  | H1     | regime_b50      |      2.94428e+08 |   0.44857  |    0.728338 | 2.94428e+08 |       5 |
| revenue  | H1     | funnel_last_c05 |      3.26593e+08 |   0.484878 |    0.859515 | 3.26593e+08 |       5 |
| revenue  | H2     | trend_log       |      1.12368e+08 |   0.239024 |    0.645508 | 2.96428e+07 |       5 |
| revenue  | H2     | recent4         |      1.41777e+08 |   0.309404 |    0.746703 | 1.34078e+08 |       5 |
| revenue  | H2     | regime_b20      |      1.70075e+08 |   0.373345 |    0.774161 | 1.70075e+08 |       5 |
| revenue  | H2     | regime_b30      |      1.88073e+08 |   0.413381 |    0.787891 | 1.88073e+08 |       5 |
| revenue  | H2     | regime_b40      |      2.06071e+08 |   0.453417 |    0.80162  | 2.06071e+08 |       5 |
| revenue  | H2     | regime_b44      |      2.13271e+08 |   0.469432 |    0.807112 | 2.13271e+08 |       5 |
| revenue  | H2     | regime_b50      |      2.2407e+08  |   0.493454 |    0.815349 | 2.2407e+08  |       5 |
| revenue  | H2     | funnel_last_c05 |      2.33226e+08 |   0.507549 |    1.08145  | 2.33226e+08 |       5 |

## COGS Ratio Donor Validation

| target     | half   | donor   |   mean_abs_error |   mean_ape |   worst_ape |    mean_bias |   folds |
|:-----------|:-------|:--------|-----------------:|-----------:|------------:|-------------:|--------:|
| cogs_ratio | H1     | median  |       0.00992428 |  0.0117189 |   0.0367566 | -0.00648456  |       5 |
| cogs_ratio | H1     | recent4 |       0.0102084  |  0.0120957 |   0.0330156 | -0.00509323  |       5 |
| cogs_ratio | H1     | q75     |       0.0106441  |  0.0126579 |   0.029979  | -0.00228596  |       5 |
| cogs_ratio | H1     | q90     |       0.0106981  |  0.0127602 |   0.0269963 |  0.000375009 |       5 |
| cogs_ratio | H1     | q95     |       0.0108061  |  0.0128977 |   0.0265267 |  0.000973995 |       5 |
| cogs_ratio | H1     | q98     |       0.0108708  |  0.0129802 |   0.026245  |  0.00133339  |       5 |
| cogs_ratio | H1     | max     |       0.010914   |  0.0130353 |   0.0260572 |  0.00157298  |       5 |
| cogs_ratio | H2     | q75     |       0.0681545  |  0.0770548 |   0.130414  |  0.0468148   |       5 |
| cogs_ratio | H2     | q90     |       0.0713918  |  0.0808719 |   0.131758  |  0.0524615   |       5 |
| cogs_ratio | H2     | recent4 |       0.0750452  |  0.0812589 |   0.102382  |  0.00225232  |       5 |
| cogs_ratio | H2     | q95     |       0.0735901  |  0.0834591 |   0.132206  |  0.0562818   |       5 |
| cogs_ratio | H2     | q98     |       0.0749091  |  0.0850115 |   0.132475  |  0.0585739   |       5 |
| cogs_ratio | H2     | max     |       0.0757884  |  0.0860464 |   0.133268  |  0.0601021   |       5 |
| cogs_ratio | H2     | median  |       0.0864559  |  0.0952598 |   0.127748  |  0.0246374   |       5 |

## Candidate Manifest

|   priority | filename                                                  | total_mode   |   conv_recovery |   h1_ratio | h2_ratio_mode   | override_periods     |   revenue_total |   cogs_total |   ratio_total |   rev_2023H1 |   cogs_2023H1 |   ratio_2023H1 |   rev_2023H2 |   cogs_2023H2 |   ratio_2023H2 |   rev_2024H1 |   cogs_2024H1 |   ratio_2024H1 | note                                                                                           | selected_revenue_h1   | selected_revenue_h2   | selected_ratio_h1   | selected_ratio_h2   |
|-----------:|:----------------------------------------------------------|:-------------|----------------:|-----------:|:----------------|:---------------------|----------------:|-------------:|--------------:|-------------:|--------------:|---------------:|-------------:|--------------:|---------------:|-------------:|--------------:|---------------:|:-----------------------------------------------------------------------------------------------|:----------------------|:----------------------|:--------------------|:--------------------|
|          1 | submission_cleanv3_head_strict_cvselected.csv             | cv_selected  |          nan    |    nan     | cv_selected     | 2023H1,2023H2,2024H1 |     1.57342e+09 |  1.36012e+09 |      0.864441 |  5.96214e+08 |   4.92944e+08 |       0.826791 |  4.13099e+08 |   3.98969e+08 |       0.965796 |  5.57002e+08 |   4.60524e+08 |       0.826791 | Strict train-fold selected period and ratio donors for all major periods; no public beta.      | trend_log             | trend_log             | median              | q75                 |
|          2 | submission_cleanv3_head_funnel_last_c10_h1only_r0876.csv  | funnel_last  |            0.1  |      0.876 | base            | 2023H1               |     2.34991e+09 |  2.11297e+09 |      0.899173 |  8.37396e+08 |   7.33559e+08 |       0.876    |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.46735e+08 |       0.844885 | Business funnel head: 2022 sessions/AOV with 10% conversion-gap recovery; H1 only.             | trend_log             | trend_log             | median              | q75                 |
|          3 | submission_cleanv3_head_funnel_last_c12_h1only_r0876.csv  | funnel_last  |            0.12 |      0.876 | base            | 2023H1               |     2.37702e+09 |  2.13672e+09 |      0.898909 |  8.64508e+08 |   7.57309e+08 |       0.876    |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.46735e+08 |       0.844885 | Business funnel head with 12% conversion-gap recovery; H1 only.                                | trend_log             | trend_log             | median              | q75                 |
|          4 | submission_cleanv3_head_funnel_last_c08_h1only_r0876.csv  | funnel_last  |            0.08 |      0.876 | base            | 2023H1               |     2.32279e+09 |  2.08922e+09 |      0.899443 |  8.10285e+08 |   7.0981e+08  |       0.876    |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.46735e+08 |       0.844885 | Business funnel head with 8% conversion-gap recovery; H1 only.                                 | trend_log             | trend_log             | median              | q75                 |
|          5 | submission_cleanv3_head_funnel_last_c10_h1only_r0870.csv  | funnel_last  |            0.1  |      0.87  | base            | 2023H1               |     2.34991e+09 |  2.10795e+09 |      0.897035 |  8.37396e+08 |   7.28535e+08 |       0.87     |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.46735e+08 |       0.844885 | Funnel H1 head plus lower H1 COGS-ratio stress.                                                | trend_log             | trend_log             | median              | q75                 |
|          6 | submission_cleanv3_head_regime_b44_h1only_r0876.csv       | regime_b44   |          nan    |      0.876 | base            | 2023H1               |     2.38123e+09 |  2.14042e+09 |      0.898868 |  8.68725e+08 |   7.61003e+08 |       0.876    |  6.21578e+08 |   6.24991e+08 |       1.00549  |  8.83831e+08 |   7.46735e+08 |       0.844885 | Regime-mixture period head equivalent to current best neighborhood, expressed as a model head. | trend_log             | trend_log             | median              | q75                 |
|          7 | submission_cleanv3_head_regime_b44_h1_h2q98.csv           | regime_b44   |          nan    |      0.876 | q98             | 2023H1,2023H2        |     2.36097e+09 |  2.1169e+09  |      0.896624 |  8.68725e+08 |   7.61003e+08 |       0.876    |  6.01311e+08 |   6.01474e+08 |       1.00027  |  8.83831e+08 |   7.46735e+08 |       0.844885 | Regime H1 head plus COGS ratio head normalizing H2 to train q98.                               | trend_log             | trend_log             | median              | q75                 |
|          8 | submission_cleanv3_head_funnel_last_c10_all_r0876_q98.csv | funnel_last  |            0.1  |      0.876 | q98             | 2023H1,2023H2,2024H1 |     2.28506e+09 |  2.07814e+09 |      0.909444 |  8.37396e+08 |   7.33559e+08 |       0.876    |  6.03168e+08 |   6.03331e+08 |       1.00027  |  8.37396e+08 |   7.33559e+08 |       0.876    | Full funnel period-total head for 2023H1/2023H2/2024H1; higher-risk all-period test.           | trend_log             | trend_log             | median              | q75                 |

## Submit Order

1. `submission_cleanv3_head_funnel_last_c10_h1only_r0876.csv`
2. `submission_cleanv3_head_funnel_last_c08_h1only_r0876.csv`
3. `submission_cleanv3_head_funnel_last_c12_h1only_r0876.csv`
4. `submission_cleanv3_head_funnel_last_c10_h1only_r0870.csv`
5. `submission_cleanv3_head_regime_b44_h1_h2q98.csv`
6. `submission_cleanv3_head_strict_cvselected.csv`
7. `submission_cleanv3_head_funnel_last_c10_all_r0876_q98.csv`
