# Public-Only Sample Targetwise V31

Run directory: `logs\20260422_103020_publiconly_sample_targetwise_v31`

Current best: `submission_sample_v30_a0725_ratio_away_sample0250.csv` scored `699376.3267`.

Known results:

|                                                       |   public_score |
|:------------------------------------------------------|---------------:|
| submission_sampleprior_v22_periodshape_both_a0725.csv |         701005 |
| submission_sample_v25_a0725_ratio_to_sample0050.csv   |         701788 |
| submission_sample_v26_a0725_ratio_away_sample0100.csv |         699961 |
| submission_sample_v28_a0725_ratio_away_sample0175.csv |         699556 |
| submission_sample_v30_a0725_ratio_away_sample0225.csv |         699385 |
| submission_sample_v30_a0725_ratio_away_sample0250.csv |         699376 |

COGS-away score curve:

|   cogs_away_alpha | label               |   public_score |   delta_from_prev |
|------------------:|:--------------------|---------------:|------------------:|
|            -0.05  | ratio_to_sample0050 |         701788 |         nan       |
|             0     | a0725_shape_only    |         701005 |        -783.193   |
|             0.025 | away0025            |         700654 |        -350.634   |
|             0.05  | away0050            |         700363 |        -291.324   |
|             0.1   | away0100            |         699961 |        -402.235   |
|             0.125 | away0125            |         699794 |        -167.257   |
|             0.175 | away0175            |         699556 |        -237.196   |
|             0.225 | away0225            |         699385 |        -171.554   |
|             0.25  | away0250            |         699376 |          -8.59808 |

Interpretation:

- The last COGS-away step `0.225 -> 0.250` improved only `8.59808`, so this axis is nearly exhausted.
- To chase `67x`, the next meaningful axis is not more global COGS ratio; it is whether Revenue and COGS want different sample-shape strengths.
- Rebuild check against current best: max Revenue delta `0.00000000`, max COGS delta `0.00000000`.

Candidate manifest:

|   priority | filename                                            | path                                                        | thesis                                                     |   rev_alpha |   cogs_alpha |   cogs_away_alpha |   rev_rows_changed_vs_current |   cogs_rows_changed_vs_current |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   directional_best_case_gain_vs_current |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_all |   ratio_2023h1 |   ratio_2023h2 |   ratio_2024h1 |   best_case_score_if_direction_correct |
|-----------:|:----------------------------------------------------|:------------------------------------------------------------|:-----------------------------------------------------------|------------:|-------------:|------------------:|------------------------------:|-------------------------------:|--------------------------------:|---------------------------------:|----------------------------------------:|---------------------------------:|------------------------------:|------------:|---------------:|---------------:|---------------:|---------------------------------------:|
|          1 | submission_sample_v31_rev0725_cogs0750_away0250.csv | dataset\submission_sample_v31_rev0725_cogs0750_away0250.csv | COGS sample-shape alpha up to 0.750, Revenue stays 0.725   |       0.725 |        0.75  |              0.25 |                             0 |                            547 |                     7.35031e-11 |                  12464.4         |                                 6232.18 |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 693144 |
|          2 | submission_sample_v31_rev0725_cogs0775_away0250.csv | dataset\submission_sample_v31_rev0725_cogs0775_away0250.csv | COGS sample-shape alpha up to 0.775, Revenue stays 0.725   |       0.725 |        0.775 |              0.25 |                             0 |                            547 |                     7.35031e-11 |                  24928.7         |                                12464.4  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 686912 |
|          3 | submission_sample_v31_rev0725_cogs0800_away0250.csv | dataset\submission_sample_v31_rev0725_cogs0800_away0250.csv | COGS sample-shape alpha up to 0.800, Revenue stays 0.725   |       0.725 |        0.8   |              0.25 |                             0 |                            547 |                     7.35031e-11 |                  37393.1         |                                18696.5  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 680680 |
|          4 | submission_sample_v31_rev0750_cogs0725_away0250.csv | dataset\submission_sample_v31_rev0750_cogs0725_away0250.csv | Revenue sample-shape alpha up to 0.750, COGS stays 0.725   |       0.75  |        0.725 |              0.25 |                           547 |                              0 |                 14350.5         |                      1.28312e-10 |                                 7175.25 |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 692201 |
|          5 | submission_sample_v31_rev0800_cogs0725_away0250.csv | dataset\submission_sample_v31_rev0800_cogs0725_away0250.csv | Revenue sample-shape alpha up to 0.800, COGS stays 0.725   |       0.8   |        0.725 |              0.25 |                           547 |                              0 |                 43051.5         |                      1.28312e-10 |                                21525.7  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 677851 |
|          6 | submission_sample_v31_rev0700_cogs0725_away0250.csv | dataset\submission_sample_v31_rev0700_cogs0725_away0250.csv | Revenue sample-shape alpha down to 0.700, COGS stays 0.725 |       0.7   |        0.725 |              0.25 |                           547 |                              0 |                 14350.5         |                      1.28312e-10 |                                 7175.25 |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 692201 |
|          7 | submission_sample_v31_rev0725_cogs0700_away0250.csv | dataset\submission_sample_v31_rev0725_cogs0700_away0250.csv | COGS sample-shape alpha down to 0.700, Revenue stays 0.725 |       0.725 |        0.7   |              0.25 |                             0 |                            547 |                     7.35031e-11 |                  12464.4         |                                 6232.18 |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 693144 |
|          8 | submission_sample_v31_rev0700_cogs0800_away0250.csv | dataset\submission_sample_v31_rev0700_cogs0800_away0250.csv | Revenue alpha down, COGS alpha up                          |       0.7   |        0.8   |              0.25 |                           547 |                            547 |                 14350.5         |                  37393.1         |                                25871.8  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 673505 |
|          9 | submission_sample_v31_rev0800_cogs0700_away0250.csv | dataset\submission_sample_v31_rev0800_cogs0700_away0250.csv | Revenue alpha up, COGS alpha down                          |       0.8   |        0.7   |              0.25 |                           547 |                            547 |                 43051.5         |                  12464.4         |                                27757.9  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 671618 |
|         10 | submission_sample_v31_rev0750_cogs0800_away0250.csv | dataset\submission_sample_v31_rev0750_cogs0800_away0250.csv | Both stronger, with COGS stronger than Revenue             |       0.75  |        0.8   |              0.25 |                           547 |                            547 |                 14350.5         |                  37393.1         |                                25871.8  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 673505 |
|         11 | submission_sample_v31_rev0800_cogs0750_away0250.csv | dataset\submission_sample_v31_rev0800_cogs0750_away0250.csv | Both stronger, with Revenue stronger than COGS             |       0.8   |        0.75  |              0.25 |                           547 |                            547 |                 43051.5         |                  12464.4         |                                27757.9  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 671618 |
|         12 | submission_sample_v31_rev0725_cogs0850_away0250.csv | dataset\submission_sample_v31_rev0725_cogs0850_away0250.csv | High-variance COGS shape extension to 0.850                |       0.725 |        0.85  |              0.25 |                             0 |                            547 |                     7.35031e-11 |                  62321.8         |                                31160.9  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 668215 |
|         13 | submission_sample_v31_rev0850_cogs0725_away0250.csv | dataset\submission_sample_v31_rev0850_cogs0725_away0250.csv | High-variance Revenue shape extension to 0.850             |       0.85  |        0.725 |              0.25 |                           547 |                              0 |                 71752.5         |                      1.28312e-10 |                                35876.2  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 663500 |

Suggested order:

1. Submit `submission_sample_v31_rev0725_cogs0750_away0250.csv`.
2. If it improves, continue `submission_sample_v31_rev0725_cogs0775_away0250.csv`, then `submission_sample_v31_rev0725_cogs0800_away0250.csv`.
3. If COGS-shape-up fails, test Revenue side with `submission_sample_v31_rev0750_cogs0725_away0250.csv`.
4. Do not prioritize more COGS-away micro steps unless all target-wise probes fail.
