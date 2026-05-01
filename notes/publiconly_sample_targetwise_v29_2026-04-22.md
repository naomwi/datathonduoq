# Public-Only Sample Targetwise V29

Run directory: `logs\20260422_101853_publiconly_sample_targetwise_v29`

Current best: `submission_sample_v28_a0725_ratio_away_sample0125.csv` scored `699793.67454`.

Known results:

|                                                       |   public_score |
|:------------------------------------------------------|---------------:|
| submission_sample_v26_a0725_ratio_away_sample0100.csv |         699961 |
| submission_sample_v28_a0725_ratio_away_sample0125.csv |         699794 |

Interpretation:

- COGS-ratio away ladder is still improving but slowly.
- Target-wise sample-shape alpha is the next high-variance axis for the `67x` goal.
- These candidates keep the improved COGS-away alpha `0.125` and vary Revenue/COGS sample-shape strength separately.

Candidate manifest:

|   priority | filename                                           | path                                                       | thesis                                                       |   rev_rows_changed_vs_current |   cogs_rows_changed_vs_current |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   directional_best_case_gain_vs_current |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_all |   ratio_2023h1 |   ratio_2023h2 |   ratio_2024h1 |   best_case_score_if_direction_correct |
|-----------:|:---------------------------------------------------|:-----------------------------------------------------------|:-------------------------------------------------------------|------------------------------:|-------------------------------:|--------------------------------:|---------------------------------:|----------------------------------------:|---------------------------------:|------------------------------:|------------:|---------------:|---------------:|---------------:|---------------------------------------:|
|          1 | submission_sample_v29_rev070_cogs0725_away0125.csv | dataset\submission_sample_v29_rev070_cogs0725_away0125.csv | Revenue shape alpha 0.700, COGS alpha 0.725, COGS away 0.125 |                           547 |                              0 |                 14350.5         |                      3.95982e-10 |                                 7175.25 |                                1 |                             1 |    0.939044 |       0.969243 |         1.0001 |         0.8672 |                                 692618 |
|          2 | submission_sample_v29_rev075_cogs0725_away0125.csv | dataset\submission_sample_v29_rev075_cogs0725_away0125.csv | Revenue shape alpha 0.750, COGS alpha 0.725, COGS away 0.125 |                           547 |                              0 |                 14350.5         |                      1.16415e-10 |                                 7175.25 |                                1 |                             1 |    0.939044 |       0.969243 |         1.0001 |         0.8672 |                                 692618 |
|          3 | submission_sample_v29_rev080_cogs0725_away0125.csv | dataset\submission_sample_v29_rev080_cogs0725_away0125.csv | Revenue shape alpha 0.800, COGS alpha 0.725, COGS away 0.125 |                           547 |                              0 |                 43051.5         |                      1.16415e-10 |                                21525.7  |                                1 |                             1 |    0.939044 |       0.969243 |         1.0001 |         0.8672 |                                 678268 |
|          4 | submission_sample_v29_rev0725_cogs070_away0125.csv | dataset\submission_sample_v29_rev0725_cogs070_away0125.csv | Revenue alpha 0.725, COGS shape alpha 0.700, COGS away 0.125 |                             0 |                            547 |                     7.35031e-11 |                  12348.3         |                                 6174.13 |                                1 |                             1 |    0.939044 |       0.969243 |         1.0001 |         0.8672 |                                 693620 |
|          5 | submission_sample_v29_rev0725_cogs075_away0125.csv | dataset\submission_sample_v29_rev0725_cogs075_away0125.csv | Revenue alpha 0.725, COGS shape alpha 0.750, COGS away 0.125 |                             0 |                            547 |                     7.35031e-11 |                  12348.3         |                                 6174.13 |                                1 |                             1 |    0.939044 |       0.969243 |         1.0001 |         0.8672 |                                 693620 |
|          6 | submission_sample_v29_rev0725_cogs080_away0125.csv | dataset\submission_sample_v29_rev0725_cogs080_away0125.csv | Revenue alpha 0.725, COGS shape alpha 0.800, COGS away 0.125 |                             0 |                            547 |                     7.35031e-11 |                  37044.8         |                                18522.4  |                                1 |                             1 |    0.939044 |       0.969243 |         1.0001 |         0.8672 |                                 681271 |
|          7 | submission_sample_v29_rev070_cogs080_away0125.csv  | dataset\submission_sample_v29_rev070_cogs080_away0125.csv  | Revenue alpha 0.700, COGS alpha 0.800, COGS away 0.125       |                           547 |                            547 |                 14350.5         |                  37044.8         |                                25697.6  |                                1 |                             1 |    0.939044 |       0.969243 |         1.0001 |         0.8672 |                                 674096 |
|          8 | submission_sample_v29_rev080_cogs070_away0125.csv  | dataset\submission_sample_v29_rev080_cogs070_away0125.csv  | Revenue alpha 0.800, COGS alpha 0.700, COGS away 0.125       |                           547 |                            547 |                 43051.5         |                  12348.3         |                                27699.9  |                                1 |                             1 |    0.939044 |       0.969243 |         1.0001 |         0.8672 |                                 672094 |

Suggested order:

1. Finish COGS-ratio next with `submission_sample_v28_a0725_ratio_away_sample0150.csv`.
2. If that stalls, submit `submission_sample_v29_rev0725_cogs075_away0125.csv`.
3. If COGS shape alpha up improves, continue to `submission_sample_v29_rev0725_cogs080_away0125.csv`.
4. If it fails, test Revenue alpha with `submission_sample_v29_rev070_cogs0725_away0125.csv`.
