# Public-Only Sample 2023H2 Micro V39

Run directory: `logs\20260422_110458_publiconly_sample_2023h2_micro_v39`

Current best: `submission_sample_v37_rev2023H2_p0200_c0650_away0250.csv` scored `684699.6885`.

Known 2023H2 results:

|   rev_alpha_2023H2 | filename                                                        |   public_score |
|-------------------:|:----------------------------------------------------------------|---------------:|
|                0.2 | submission_sample_v37_rev2023H2_p0200_c0650_away0250.csv        |         684700 |
|                0.4 | submission_sample_v36_rev2023H2_r0400_c0650_away0250.csv        |         687113 |
|                0.6 | submission_sample_v36_rev2023H2_r0600_c0650_away0250.csv        |         692129 |
|                0.8 | submission_sample_v34_rev08000_cogs06500_away0250.csv           |         698898 |
|                1   | submission_sample_v35_rev2023H2_up1000_r1000_c0650_away0250.csv |         707437 |

Fit predictions:

| fit            |   rev_alpha_2023H2 |   pred_score |
|:---------------|-------------------:|-------------:|
| poly2          |             0.175  |       684404 |
| poly2          |             0.15   |       684235 |
| poly2          |             0.125  |       684098 |
| poly2          |             0.1    |       683992 |
| poly2          |             0.075  |       683917 |
| poly2          |             0.05   |       683873 |
| poly2          |             0.025  |       683861 |
| poly2          |             0      |       683880 |
| poly2_grid_opt |             0.0275 |       683861 |
| poly3          |             0.175  |       684569 |
| poly3          |             0.15   |       684495 |
| poly3          |             0.125  |       684468 |
| poly3          |             0.1    |       684487 |
| poly3          |             0.075  |       684554 |
| poly3          |             0.05   |       684669 |
| poly3          |             0.025  |       684833 |
| poly3          |             0      |       685047 |
| poly3_grid_opt |             0.1225 |       684468 |
| poly4          |             0.175  |       684657 |
| poly4          |             0.15   |       684685 |
| poly4          |             0.125  |       684788 |
| poly4          |             0.1    |       684972 |
| poly4          |             0.075  |       685240 |
| poly4          |             0.05   |       685598 |
| poly4          |             0.025  |       686051 |
| poly4          |             0      |       686605 |
| poly4_grid_opt |             0.172  |       684657 |

Interpretation:

- `2023H2` alpha `0.200` is still best, but the improvement from `0.400 -> 0.200` is much smaller than `0.600 -> 0.400`.
- Fits disagree: quadratic wants near `0.03`, cubic/quartic prefer around `0.12-0.17`.
- Submit `0.100` for higher information, or `0.150` if you want lower risk.

Candidate manifest:

|   priority | filename                                                  | path                                                              | thesis                                                             |   rev_alpha_2023H2 |   base_rev_alpha_other_periods |   base_cogs_alpha_all_periods |   rev_rows_changed_vs_current |   cogs_rows_changed_vs_current |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   h2_mean_abs_rev_delta |   directional_best_case_gain_vs_current |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_all |   ratio_2023h1 |   ratio_2023h2 |   ratio_2024h1 |   poly2_pred_score |   best_case_score_if_direction_correct |
|-----------:|:----------------------------------------------------------|:------------------------------------------------------------------|:-------------------------------------------------------------------|-------------------:|-------------------------------:|------------------------------:|------------------------------:|-------------------------------:|--------------------------------:|---------------------------------:|------------------------:|----------------------------------------:|---------------------------------:|------------------------------:|------------:|---------------:|---------------:|---------------:|-------------------:|---------------------------------------:|
|          1 | submission_sample_v39_rev2023H2_p01750_c0650_away0250.csv | dataset\submission_sample_v39_rev2023H2_p01750_c0650_away0250.csv | small step below current p0200; tests whether optimum is near 0.17 |              0.175 |                            0.8 |                          0.65 |                           184 |                              0 |                         3619.97 |                      6.41559e-11 |                 10781.2 |                                 1809.99 |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |             684404 |                                 682890 |
|          2 | submission_sample_v39_rev2023H2_p01500_c0650_away0250.csv | dataset\submission_sample_v39_rev2023H2_p01500_c0650_away0250.csv | midpoint toward p0100; conservative next probe                     |              0.15  |                            0.8 |                          0.65 |                           184 |                              0 |                         7239.95 |                      6.41559e-11 |                 21562.5 |                                 3619.97 |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |             684235 |                                 681080 |
|          3 | submission_sample_v39_rev2023H2_p01250_c0650_away0250.csv | dataset\submission_sample_v39_rev2023H2_p01250_c0650_away0250.csv | between p0150 and p0100                                            |              0.125 |                            0.8 |                          0.65 |                           184 |                              0 |                        10859.9  |                      6.41559e-11 |                 32343.7 |                                 5429.96 |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |             684098 |                                 679270 |
|          4 | submission_sample_v39_rev2023H2_p01000_c0650_away0250.csv | dataset\submission_sample_v39_rev2023H2_p01000_c0650_away0250.csv | existing v37 p0100 equivalent; tests low side                      |              0.1   |                            0.8 |                          0.65 |                           184 |                              0 |                        14479.9  |                      6.41559e-11 |                 43124.9 |                                 7239.95 |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |             683992 |                                 677460 |
|          5 | submission_sample_v39_rev2023H2_p00750_c0650_away0250.csv | dataset\submission_sample_v39_rev2023H2_p00750_c0650_away0250.csv | lower-side micro toward p0050                                      |              0.075 |                            0.8 |                          0.65 |                           184 |                              0 |                        18099.9  |                      6.41559e-11 |                 53906.1 |                                 9049.94 |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |             683917 |                                 675650 |
|          6 | submission_sample_v39_rev2023H2_p00500_c0650_away0250.csv | dataset\submission_sample_v39_rev2023H2_p00500_c0650_away0250.csv | near quadratic optimum zone                                        |              0.05  |                            0.8 |                          0.65 |                           184 |                              0 |                        21719.8  |                      6.41559e-11 |                 64687.4 |                                10859.9  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |             683873 |                                 673840 |
|          7 | submission_sample_v39_rev2023H2_p00250_c0650_away0250.csv | dataset\submission_sample_v39_rev2023H2_p00250_c0650_away0250.csv | very low 2023H2 alpha                                              |              0.025 |                            0.8 |                          0.65 |                           184 |                              0 |                        25339.8  |                      6.41559e-11 |                 75468.6 |                                12669.9  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |             683861 |                                 672030 |
|          8 | submission_sample_v39_rev2023H2_p00000_c0650_away0250.csv | dataset\submission_sample_v39_rev2023H2_p00000_c0650_away0250.csv | existing v37 p0000 equivalent                                      |              0     |                            0.8 |                          0.65 |                           184 |                              0 |                        28959.8  |                      6.41559e-11 |                 86249.8 |                                14479.9  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |             683880 |                                 670220 |

Suggested order:

1. Submit `submission_sample_v37_rev2023H2_p0100_c0650_away0250.csv` or equivalent v39 p0100.
2. If it improves, submit `submission_sample_v39_rev2023H2_p00500_c0650_away0250.csv`.
3. If `p0100` worsens, submit `submission_sample_v39_rev2023H2_p01500_c0650_away0250.csv`.
4. Only submit `p0000` if `p0100` improves or stays very close.
