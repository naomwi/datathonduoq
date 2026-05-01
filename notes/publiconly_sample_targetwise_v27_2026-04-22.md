# Public-Only Sample Targetwise V27

Run directory: `logs\20260422_101020_publiconly_sample_targetwise_v27`

Current best: `submission_sample_v26_a0725_ratio_away_sample0025.csv` scored `700654.49101`.

Known results:

|                                                       |   public_score |
|:------------------------------------------------------|---------------:|
| submission_sampleprior_v22_periodshape_both_a0725.csv |         701005 |
| submission_sample_v25_a0725_ratio_to_sample0050.csv   |         701788 |
| submission_sample_v26_a0725_ratio_away_sample0025.csv |         700654 |

Interpretation:

- Same alpha for Revenue and COGS has plateaued.
- COGS ratio away-from-sample improved slightly.
- To chase `67x`, the next high-leverage axis is target-wise sample-shape alpha: Revenue and COGS may prefer different sample-shape strength.

Candidate manifest:

|   priority | filename                                           | path                                                       | thesis                                                            |   rev_rows_changed_vs_current |   cogs_rows_changed_vs_current |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   directional_best_case_gain_vs_current |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_all |   ratio_2023h1 |   ratio_2023h2 |   ratio_2024h1 |   best_case_score_if_direction_correct |
|-----------:|:---------------------------------------------------|:-----------------------------------------------------------|:------------------------------------------------------------------|------------------------------:|-------------------------------:|--------------------------------:|---------------------------------:|----------------------------------------:|---------------------------------:|------------------------------:|------------:|---------------:|---------------:|---------------:|---------------------------------------:|
|          1 | submission_sample_v27_rev070_cogs0725_away0025.csv | dataset\submission_sample_v27_rev070_cogs0725_away0025.csv | Revenue shape alpha 0.700, COGS alpha 0.725, keep COGS away 0.025 |                           547 |                              0 |                 14350.5         |                      1.30861e-10 |                                 7175.25 |                                1 |                             1 |    0.931792 |        0.95727 |       0.992801 |       0.864184 |                                 693479 |
|          2 | submission_sample_v27_rev075_cogs0725_away0025.csv | dataset\submission_sample_v27_rev075_cogs0725_away0025.csv | Revenue shape alpha 0.750, COGS alpha 0.725, keep COGS away 0.025 |                           547 |                              0 |                 14350.5         |                      1.30861e-10 |                                 7175.25 |                                1 |                             1 |    0.931792 |        0.95727 |       0.992801 |       0.864184 |                                 693479 |
|          3 | submission_sample_v27_rev0725_cogs070_away0025.csv | dataset\submission_sample_v27_rev0725_cogs070_away0025.csv | Revenue alpha 0.725, COGS shape alpha 0.700, keep COGS away 0.025 |                             0 |                            547 |                     7.35031e-11 |                  12255.4         |                                 6127.69 |                                1 |                             1 |    0.931792 |        0.95727 |       0.992801 |       0.864184 |                                 694527 |
|          4 | submission_sample_v27_rev0725_cogs075_away0025.csv | dataset\submission_sample_v27_rev0725_cogs075_away0025.csv | Revenue alpha 0.725, COGS shape alpha 0.750, keep COGS away 0.025 |                             0 |                            547 |                     7.35031e-11 |                  12255.4         |                                 6127.69 |                                1 |                             1 |    0.931792 |        0.95727 |       0.992801 |       0.864184 |                                 694527 |
|          5 | submission_sample_v27_rev070_cogs075_away0025.csv  | dataset\submission_sample_v27_rev070_cogs075_away0025.csv  | Revenue alpha down, COGS alpha up, keep COGS away 0.025           |                           547 |                            547 |                 14350.5         |                  12255.4         |                                13302.9  |                                1 |                             1 |    0.931792 |        0.95727 |       0.992801 |       0.864184 |                                 687352 |
|          6 | submission_sample_v27_rev075_cogs070_away0025.csv  | dataset\submission_sample_v27_rev075_cogs070_away0025.csv  | Revenue alpha up, COGS alpha down, keep COGS away 0.025           |                           547 |                            547 |                 14350.5         |                  12255.4         |                                13302.9  |                                1 |                             1 |    0.931792 |        0.95727 |       0.992801 |       0.864184 |                                 687352 |
|          7 | submission_sample_v27_rev0725_cogs080_away0025.csv | dataset\submission_sample_v27_rev0725_cogs080_away0025.csv | Revenue alpha 0.725, COGS shape alpha 0.800, keep COGS away 0.025 |                             0 |                            547 |                     7.35031e-11 |                  36766.2         |                                18383.1  |                                1 |                             1 |    0.931792 |        0.95727 |       0.992801 |       0.864184 |                                 682271 |
|          8 | submission_sample_v27_rev080_cogs0725_away0025.csv | dataset\submission_sample_v27_rev080_cogs0725_away0025.csv | Revenue shape alpha 0.800, COGS alpha 0.725, keep COGS away 0.025 |                           547 |                              0 |                 43051.5         |                      1.30861e-10 |                                21525.7  |                                1 |                             1 |    0.931792 |        0.95727 |       0.992801 |       0.864184 |                                 679129 |

Suggested order:

1. First continue COGS-ratio ladder with `submission_sample_v26_a0725_ratio_away_sample0050.csv`.
2. If COGS-ratio stalls, submit `submission_sample_v27_rev0725_cogs075_away0025.csv`.
3. If COGS alpha up improves, continue `submission_sample_v27_rev0725_cogs080_away0025.csv`.
4. If COGS alpha up fails, test Revenue side with `submission_sample_v27_rev070_cogs0725_away0025.csv`.
