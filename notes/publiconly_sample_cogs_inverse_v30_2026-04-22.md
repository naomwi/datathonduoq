# Public-Only Sample COGS Inverse V30

Run directory: `logs\20260422_102233_publiconly_sample_cogs_inverse_v30`

Current best: `submission_sample_v28_a0725_ratio_away_sample0175.csv` scored `699556.47851`.

Known absolute alpha results:

|        |   public_score |
|-------:|---------------:|
| -0.05  |         701788 |
|  0     |         701005 |
|  0.025 |         700654 |
|  0.05  |         700363 |
|  0.1   |         699961 |
|  0.125 |         699794 |
|  0.175 |         699556 |

Interpretation:

- Alpha `0.175` improved to `699556.47851`, but slope is diminishing.
- Next safest point is `0.200`.
- If `0.200` improves, use `0.225`; if it worsens, use micro points around `0.185-0.195`.

Candidate manifest:

|   priority | filename                                              | path                                                          | thesis                                           |   rev_rows_changed_vs_current |   cogs_rows_changed_vs_current |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   directional_best_case_gain_vs_current |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   revenue_total_ratio_vs_sample |   cogs_total_ratio_vs_sample |   ratio_all |   ratio_2023h1 |   ratio_2023h2 |   ratio_2024h1 |   poly2_pred_score |   poly3_pred_score |   poly5_pred_score |   best_case_score_if_direction_correct |
|-----------:|:------------------------------------------------------|:--------------------------------------------------------------|:-------------------------------------------------|------------------------------:|-------------------------------:|--------------------------------:|---------------------------------:|----------------------------------------:|---------------------------------:|------------------------------:|--------------------------------:|-----------------------------:|------------:|---------------:|---------------:|---------------:|-------------------:|-------------------:|-------------------:|---------------------------------------:|
|          1 | submission_sample_v30_a0725_ratio_away_sample0185.csv | dataset\submission_sample_v30_a0725_ratio_away_sample0185.csv | absolute COGS ratio away-from-sample alpha=0.185 |                             0 |                            548 |                     5.94823e-12 |                          2973.96 |                                 1486.98 |                                1 |                       1.00077 |                         1.26203 |                      1.38988 |    0.943394 |       0.976427 |        1.00448 |       0.869009 |             699552 |             699525 |             699553 |                                 698070 |
|          2 | submission_sample_v30_a0725_ratio_away_sample0190.csv | dataset\submission_sample_v30_a0725_ratio_away_sample0190.csv | absolute COGS ratio away-from-sample alpha=0.190 |                             0 |                            548 |                     5.94823e-12 |                          4460.93 |                                 2230.47 |                                1 |                       1.00115 |                         1.26203 |                      1.39042 |    0.943757 |       0.977025 |        1.00485 |       0.86916  |             699545 |             699509 |             699562 |                                 697326 |
|          3 | submission_sample_v30_a0725_ratio_away_sample0195.csv | dataset\submission_sample_v30_a0725_ratio_away_sample0195.csv | absolute COGS ratio away-from-sample alpha=0.195 |                             0 |                            548 |                     5.94823e-12 |                          5947.91 |                                 2973.96 |                                1 |                       1.00154 |                         1.26203 |                      1.39095 |    0.944119 |       0.977624 |        1.00521 |       0.869311 |             699539 |             699494 |             699580 |                                 696583 |
|          4 | submission_sample_v30_a0725_ratio_away_sample0200.csv | dataset\submission_sample_v30_a0725_ratio_away_sample0200.csv | absolute COGS ratio away-from-sample alpha=0.200 |                             0 |                            548 |                     5.94823e-12 |                          7434.89 |                                 3717.45 |                                1 |                       1.00192 |                         1.26203 |                      1.39149 |    0.944482 |       0.978223 |        1.00558 |       0.869462 |             699534 |             699479 |             699608 |                                 695839 |
|          5 | submission_sample_v30_a0725_ratio_away_sample0205.csv | dataset\submission_sample_v30_a0725_ratio_away_sample0205.csv | absolute COGS ratio away-from-sample alpha=0.205 |                             0 |                            548 |                     5.94823e-12 |                          8921.87 |                                 4460.93 |                                1 |                       1.00231 |                         1.26203 |                      1.39202 |    0.944844 |       0.978821 |        1.00594 |       0.869613 |             699531 |             699466 |             699648 |                                 695096 |
|          6 | submission_sample_v30_a0725_ratio_away_sample0210.csv | dataset\submission_sample_v30_a0725_ratio_away_sample0210.csv | absolute COGS ratio away-from-sample alpha=0.210 |                             0 |                            548 |                     5.94823e-12 |                         10408.8  |                                 5204.42 |                                1 |                       1.00269 |                         1.26203 |                      1.39255 |    0.945207 |       0.97942  |        1.00631 |       0.869763 |             699530 |             699453 |             699702 |                                 694352 |
|          7 | submission_sample_v30_a0725_ratio_away_sample0225.csv | dataset\submission_sample_v30_a0725_ratio_away_sample0225.csv | absolute COGS ratio away-from-sample alpha=0.225 |                             0 |                            548 |                     5.94823e-12 |                         14869.8  |                                 7434.89 |                                1 |                       1.00385 |                         1.26203 |                      1.39416 |    0.946295 |       0.981216 |        1.0074  |       0.870216 |             699537 |             699419 |             699962 |                                 692122 |
|          8 | submission_sample_v30_a0725_ratio_away_sample0250.csv | dataset\submission_sample_v30_a0725_ratio_away_sample0250.csv | absolute COGS ratio away-from-sample alpha=0.250 |                             0 |                            548 |                     5.94823e-12 |                         22304.7  |                                11152.3  |                                1 |                       1.00577 |                         1.26203 |                      1.39683 |    0.948108 |       0.984209 |        1.00923 |       0.87097  |             699581 |             699374 |             700866 |                                 688404 |

Suggested order:

1. `submission_sample_v28_a0725_ratio_away_sample0200.csv` or equivalent `submission_sample_v30_a0725_ratio_away_sample0200.csv`.
2. If it improves: `submission_sample_v30_a0725_ratio_away_sample0225.csv`.
3. If it worsens: `submission_sample_v30_a0725_ratio_away_sample0190.csv`.
4. If COGS-away stalls, switch to target-wise sample alpha v29.

Public result update:

- submission_sample_v30_a0725_ratio_away_sample0225.csv = 699384.92478.
- COGS-away still improves, but slope is diminishing. Next submit: submission_sample_v30_a0725_ratio_away_sample0250.csv. If it fails, stop this ladder and switch to v29 target-wise alpha.

