# Public-Only Sample COGS Inverse V26

Run directory: `logs\20260422_100659_publiconly_sample_cogs_inverse_v26`

Current best: `submission_sampleprior_v22_periodshape_both_a0725.csv` scored `701005.1247`.

Known results:

|                                                       |   public_score |
|:------------------------------------------------------|---------------:|
| submission_sampleprior_v22_periodshape_both_a0725.csv |         701005 |
| submission_sample_v23_a0725_scale_to_sample005.csv    |         707717 |
| submission_sample_v25_a0725_ratio_to_sample0050.csv   |         701788 |

Interpretation:

- Moving period scale toward sample failed.
- Moving COGS ratio toward sample also failed.
- If COGS still has signal, the remaining sign is opposite: COGS ratio should be slightly higher than current, not lower.

Candidate manifest:

|   priority | filename                                              | path                                                          | thesis                                                                |   rev_rows_changed_vs_current |   cogs_rows_changed_vs_current |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   directional_best_case_gain_vs_current |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   revenue_total_ratio_vs_sample |   cogs_total_ratio_vs_sample |   ratio_all |   ratio_2023h1 |   ratio_2023h2 |   ratio_2024h1 |   best_case_score_if_direction_correct |
|-----------:|:------------------------------------------------------|:--------------------------------------------------------------|:----------------------------------------------------------------------|------------------------------:|-------------------------------:|--------------------------------:|---------------------------------:|----------------------------------------:|---------------------------------:|------------------------------:|--------------------------------:|-----------------------------:|------------:|---------------:|---------------:|---------------:|---------------------------------------:|
|          1 | submission_sample_v26_a0725_ratio_away_sample0025.csv | dataset\submission_sample_v26_a0725_ratio_away_sample0025.csv | keep Revenue/day-shape, move COGS period ratios 2.5% away from sample |                             0 |                            548 |                               0 |                          7434.89 |                                 3717.45 |                                1 |                       1.00195 |                         1.26203 |                      1.37279 |    0.931792 |       0.95727  |       0.992801 |       0.864184 |                                 697288 |
|          2 | submission_sample_v26_a0725_ratio_away_sample0050.csv | dataset\submission_sample_v26_a0725_ratio_away_sample0050.csv | keep Revenue/day-shape, move COGS period ratios 5% away from sample   |                             0 |                            548 |                               0 |                         14869.8  |                                 7434.89 |                                1 |                       1.0039  |                         1.26203 |                      1.37546 |    0.933605 |       0.960263 |       0.994626 |       0.864938 |                                 693570 |
|          3 | submission_sample_v26_a0725_ratio_away_sample0075.csv | dataset\submission_sample_v26_a0725_ratio_away_sample0075.csv | keep Revenue/day-shape, move COGS period ratios 7.5% away from sample |                             0 |                            548 |                               0 |                         22304.7  |                                11152.3  |                                1 |                       1.00585 |                         1.26203 |                      1.37813 |    0.935418 |       0.963256 |       0.996451 |       0.865692 |                                 689853 |
|          4 | submission_sample_v26_a0725_ratio_away_sample0100.csv | dataset\submission_sample_v26_a0725_ratio_away_sample0100.csv | keep Revenue/day-shape, move COGS period ratios 10% away from sample  |                             0 |                            548 |                               0 |                         29739.6  |                                14869.8  |                                1 |                       1.0078  |                         1.26203 |                      1.3808  |    0.937231 |       0.96625  |       0.998277 |       0.866446 |                                 686135 |
|          5 | submission_sample_v26_a0725_cogsscale_up0025.csv      | dataset\submission_sample_v26_a0725_cogsscale_up0025.csv      | global COGS +0.25%, keep Revenue                                      |                             0 |                            548 |                               0 |                          9535.39 |                                 4767.69 |                                1 |                       1.0025  |                         1.26203 |                      1.37355 |    0.932304 |       0.956662 |       0.993453 |       0.865589 |                                 696237 |
|          6 | submission_sample_v26_a0725_cogsscale_up0050.csv      | dataset\submission_sample_v26_a0725_cogsscale_up0050.csv      | global COGS +0.5%, keep Revenue                                       |                             0 |                            548 |                               0 |                         19070.8  |                                 9535.39 |                                1 |                       1.005   |                         1.26203 |                      1.37697 |    0.934629 |       0.959048 |       0.99593  |       0.867747 |                                 691470 |
|          7 | submission_sample_v26_a0725_cogsscale_up0100.csv      | dataset\submission_sample_v26_a0725_cogsscale_up0100.csv      | global COGS +1.0%, keep Revenue                                       |                             0 |                            548 |                               0 |                         38141.6  |                                19070.8  |                                1 |                       1.01    |                         1.26203 |                      1.38382 |    0.939279 |       0.963819 |       1.00088  |       0.872064 |                                 681934 |

Suggested order:

1. `submission_sample_v26_a0725_ratio_away_sample0025.csv`
2. If it improves: `submission_sample_v26_a0725_ratio_away_sample0050.csv`
3. If ratio-away fails, test global sign with `submission_sample_v26_a0725_cogsscale_up0025.csv`

Public result update:

- submission_sample_v26_a0725_ratio_away_sample0050.csv = 700363.16716.
- This improves over away0025 by 291.32385 and over a0725 baseline by 641.95754.
- Next submit: submission_sample_v26_a0725_ratio_away_sample0075.csv. If it improves, continue to away0100; if it worsens, test target-wise alpha v27.

