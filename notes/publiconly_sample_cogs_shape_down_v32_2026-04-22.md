# Public-Only Sample COGS Shape Down V32

Run directory: `logs\20260422_103539_publiconly_sample_cogs_shape_down_v32`

Current best: `submission_sample_v30_a0725_ratio_away_sample0250.csv` scored `699376.3267`.

Known results:

|                                                       |   public_score |
|:------------------------------------------------------|---------------:|
| submission_sample_v30_a0725_ratio_away_sample0250.csv |         699376 |
| submission_sample_v31_rev0725_cogs0750_away0250.csv   |         699662 |

Interpretation:

- `submission_sample_v31_rev0725_cogs0750_away0250.csv` worsened by `286.01845`.
- That candidate only changed the COGS day-level shape, not total Revenue or total COGS.
- The next useful probe is the opposite side: reduce COGS sample-shape alpha below `0.725`.

Candidate manifest:

|   priority | filename                                            | path                                                        | thesis                                                 |   rev_alpha |   cogs_alpha |   cogs_away_alpha |   rev_rows_changed_vs_current |   cogs_rows_changed_vs_current |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   directional_best_case_gain_vs_current |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_all |   ratio_2023h1 |   ratio_2023h2 |   ratio_2024h1 |   best_case_score_if_direction_correct |
|-----------:|:----------------------------------------------------|:------------------------------------------------------------|:-------------------------------------------------------|------------:|-------------:|------------------:|------------------------------:|-------------------------------:|--------------------------------:|---------------------------------:|----------------------------------------:|---------------------------------:|------------------------------:|------------:|---------------:|---------------:|---------------:|---------------------------------------:|
|          1 | submission_sample_v32_rev0725_cogs0712_away0250.csv | dataset\submission_sample_v32_rev0725_cogs0712_away0250.csv | small opposite step after cogs0750 failed              |       0.725 |       0.7125 |              0.25 |                             0 |                            547 |                     7.35031e-11 |                          6232.18 |                                 3116.09 |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 696260 |
|          2 | submission_sample_v32_rev0725_cogs0700_away0250.csv | dataset\submission_sample_v32_rev0725_cogs0700_away0250.csv | symmetric opposite step to cogs0750                    |       0.725 |       0.7    |              0.25 |                             0 |                            547 |                     7.35031e-11 |                         12464.4  |                                 6232.18 |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 693144 |
|          3 | submission_sample_v32_rev0725_cogs0688_away0250.csv | dataset\submission_sample_v32_rev0725_cogs0688_away0250.csv | moderate COGS shape reduction                          |       0.725 |       0.6875 |              0.25 |                             0 |                            547 |                     7.35031e-11 |                         18696.5  |                                 9348.27 |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 690028 |
|          4 | submission_sample_v32_rev0725_cogs0675_away0250.csv | dataset\submission_sample_v32_rev0725_cogs0675_away0250.csv | stronger COGS shape reduction                          |       0.725 |       0.675  |              0.25 |                             0 |                            547 |                     7.35031e-11 |                         24928.7  |                                12464.4  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 686912 |
|          5 | submission_sample_v32_rev0725_cogs0650_away0250.csv | dataset\submission_sample_v32_rev0725_cogs0650_away0250.csv | high-variance COGS shape reduction                     |       0.725 |       0.65   |              0.25 |                             0 |                            547 |                     7.35031e-11 |                         37393.1  |                                18696.5  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 680680 |
|          6 | submission_sample_v32_rev0725_cogs0600_away0250.csv | dataset\submission_sample_v32_rev0725_cogs0600_away0250.csv | extreme COGS shape reduction for public-only diagnosis |       0.725 |       0.6    |              0.25 |                             0 |                            547 |                     7.35031e-11 |                         62321.8  |                                31160.9  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 668215 |

Suggested order:

1. Submit `submission_sample_v32_rev0725_cogs0712_away0250.csv` if you want the safer half-step.
2. Submit `submission_sample_v32_rev0725_cogs0700_away0250.csv` if you want the symmetric opposite step.
3. If either improves clearly, continue `submission_sample_v32_rev0725_cogs0688_away0250.csv`, then `submission_sample_v32_rev0725_cogs0675_away0250.csv`.
4. If both fail, COGS-shape target-wise axis is dead and we move to Revenue-shape direction.
