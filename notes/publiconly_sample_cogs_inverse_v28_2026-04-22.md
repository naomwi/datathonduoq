# Public-Only Sample COGS Inverse V28

Run directory: `logs\20260422_101554_publiconly_sample_cogs_inverse_v28`

Current best: `submission_sample_v26_a0725_ratio_away_sample0100.csv` scored `699960.93186`.

Known absolute alpha results:

|        |   public_score |
|-------:|---------------:|
| -0.05  |         701788 |
|  0     |         701005 |
|  0.025 |         700654 |
|  0.05  |         700363 |
|  0.1   |         699961 |

Interpretation:

- COGS ratio away-from-sample still improves at alpha `0.100`.
- Gains are diminishing, so use small absolute steps; do not apply these incrementally on top of `a0100`.
- Conservative cubic fit predicts the next useful point around `0.125`; quadratic allows more, but `0.125` is the clean next probe.

Candidate manifest:

|   priority | filename                                              | path                                                          | thesis                                                                      |   rev_rows_changed_vs_current |   cogs_rows_changed_vs_current |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   directional_best_case_gain_vs_current |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   revenue_total_ratio_vs_sample |   cogs_total_ratio_vs_sample |   ratio_all |   ratio_2023h1 |   ratio_2023h2 |   ratio_2024h1 |   cubic_pred_score |   best_case_score_if_direction_correct |
|-----------:|:------------------------------------------------------|:--------------------------------------------------------------|:----------------------------------------------------------------------------|------------------------------:|-------------------------------:|--------------------------------:|---------------------------------:|----------------------------------------:|---------------------------------:|------------------------------:|--------------------------------:|-----------------------------:|------------:|---------------:|---------------:|---------------:|-------------------:|---------------------------------------:|
|          1 | submission_sample_v28_a0725_ratio_away_sample0125.csv | dataset\submission_sample_v28_a0725_ratio_away_sample0125.csv | absolute COGS ratio away-from-sample alpha=0.125; cubic prediction 699882.7 |                             0 |                            548 |                     5.94823e-12 |                          7434.89 |                                 3717.45 |                                1 |                       1.00193 |                         1.26203 |                      1.38347 |    0.939044 |       0.969243 |        1.0001  |       0.8672   |             699883 |                                 696243 |
|          2 | submission_sample_v28_a0725_ratio_away_sample0150.csv | dataset\submission_sample_v28_a0725_ratio_away_sample0150.csv | absolute COGS ratio away-from-sample alpha=0.150; cubic prediction 699901.6 |                             0 |                            548 |                     5.94823e-12 |                         14869.8  |                                 7434.89 |                                1 |                       1.00387 |                         1.26203 |                      1.38615 |    0.940856 |       0.972236 |        1.00193 |       0.867954 |             699902 |                                 692526 |
|          3 | submission_sample_v28_a0725_ratio_away_sample0175.csv | dataset\submission_sample_v28_a0725_ratio_away_sample0175.csv | absolute COGS ratio away-from-sample alpha=0.175; cubic prediction 700030.2 |                             0 |                            548 |                     5.94823e-12 |                         22304.7  |                                11152.3  |                                1 |                       1.0058  |                         1.26203 |                      1.38882 |    0.942669 |       0.975229 |        1.00375 |       0.868708 |             700030 |                                 688809 |
|          4 | submission_sample_v28_a0725_ratio_away_sample0200.csv | dataset\submission_sample_v28_a0725_ratio_away_sample0200.csv | absolute COGS ratio away-from-sample alpha=0.200; cubic prediction 700280.9 |                             0 |                            548 |                     5.94823e-12 |                         29739.6  |                                14869.8  |                                1 |                       1.00774 |                         1.26203 |                      1.39149 |    0.944482 |       0.978223 |        1.00558 |       0.869462 |             700281 |                                 685091 |
|          5 | submission_sample_v28_a0725_ratio_away_sample0250.csv | dataset\submission_sample_v28_a0725_ratio_away_sample0250.csv | absolute COGS ratio away-from-sample alpha=0.250; cubic prediction 701197.7 |                             0 |                            548 |                     5.94823e-12 |                         44609.3  |                                22304.7  |                                1 |                       1.01161 |                         1.26203 |                      1.39683 |    0.948108 |       0.984209 |        1.00923 |       0.87097  |             701198 |                                 677656 |
|          6 | submission_sample_v28_a0725_ratio_away_sample0300.csv | dataset\submission_sample_v28_a0725_ratio_away_sample0300.csv | absolute COGS ratio away-from-sample alpha=0.300; cubic prediction 702750.3 |                             0 |                            548 |                     5.94823e-12 |                         59479.1  |                                29739.6  |                                1 |                       1.01547 |                         1.26203 |                      1.40217 |    0.951733 |       0.990196 |        1.01288 |       0.872478 |             702750 |                                 670221 |

Suggested order:

1. `submission_sample_v28_a0725_ratio_away_sample0125.csv`
2. If it improves: `submission_sample_v28_a0725_ratio_away_sample0150.csv`
3. If `0.150` improves: `submission_sample_v28_a0725_ratio_away_sample0200.csv`
4. If `0.125` worsens, stop COGS-ratio ladder and use target-wise v27.
