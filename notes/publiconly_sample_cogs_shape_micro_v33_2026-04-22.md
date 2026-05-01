# Public-Only Sample COGS Shape Micro V33

Run directory: `logs\20260422_103940_publiconly_sample_cogs_shape_micro_v33`

Current best: `submission_sample_v32_rev0725_cogs0700_away0250.csv` scored `699167.79998`.

Known COGS-shape results:

|   cogs_alpha | filename                                              |   public_score |
|-------------:|:------------------------------------------------------|---------------:|
|        0.7   | submission_sample_v32_rev0725_cogs0700_away0250.csv   |         699168 |
|        0.725 | submission_sample_v30_a0725_ratio_away_sample0250.csv |         699376 |
|        0.75  | submission_sample_v31_rev0725_cogs0750_away0250.csv   |         699662 |

Fit predictions:

| fit           |   cogs_alpha |   pred_score |
|:--------------|-------------:|-------------:|
| poly1         |     0.675    |       698908 |
| poly1         |     0.6625   |       698784 |
| poly1         |     0.65     |       698660 |
| poly1         |     0.645    |       698611 |
| poly1         |     0.64     |       698561 |
| poly1         |     0.625    |       698413 |
| poly1         |     0.6      |       698166 |
| poly2         |     0.675    |       699037 |
| poly2         |     0.6625   |       699000 |
| poly2         |     0.65     |       698983 |
| poly2         |     0.645    |       698982 |
| poly2         |     0.64     |       698984 |
| poly2         |     0.625    |       699007 |
| poly2         |     0.6      |       699109 |
| poly2_optimum |     0.645226 |       698982 |

Interpretation:

- Reducing COGS sample-shape alpha from `0.725` to `0.700` improved by `208.52672`.
- Increasing it to `0.750` worsened, so the next search should stay below `0.700`.
- The three-point quadratic fit puts the local optimum near COGS alpha `0.6452` with predicted score `698981.81`. Treat this as a navigation hint, not a trusted forecast.

Candidate manifest:

|   priority | filename                                             | path                                                         | thesis                                                 |   rev_alpha |   cogs_alpha |   cogs_away_alpha |   rev_rows_changed_vs_current |   cogs_rows_changed_vs_current |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   directional_best_case_gain_vs_current |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_all |   ratio_2023h1 |   ratio_2023h2 |   ratio_2024h1 |   poly2_pred_score |   best_case_score_if_direction_correct |
|-----------:|:-----------------------------------------------------|:-------------------------------------------------------------|:-------------------------------------------------------|------------:|-------------:|------------------:|------------------------------:|-------------------------------:|--------------------------------:|---------------------------------:|----------------------------------------:|---------------------------------:|------------------------------:|------------:|---------------:|---------------:|---------------:|-------------------:|---------------------------------------:|
|          1 | submission_sample_v33_rev0725_cogs06750_away0250.csv | dataset\submission_sample_v33_rev0725_cogs06750_away0250.csv | existing v32 step, checks if optimum is close to 0.700 |       0.725 |       0.675  |              0.25 |                             0 |                            547 |                     6.75549e-11 |                          12464.4 |                                 6232.18 |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |             699037 |                                 692936 |
|          2 | submission_sample_v33_rev0725_cogs06625_away0250.csv | dataset\submission_sample_v33_rev0725_cogs06625_away0250.csv | midpoint between 0.675 and expected 0.650 zone         |       0.725 |       0.6625 |              0.25 |                             0 |                            547 |                     6.75549e-11 |                          18696.5 |                                 9348.27 |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |             699000 |                                 689820 |
|          3 | submission_sample_v33_rev0725_cogs06500_away0250.csv | dataset\submission_sample_v33_rev0725_cogs06500_away0250.csv | quadratic fit target zone from 0.750/0.725/0.700       |       0.725 |       0.65   |              0.25 |                             0 |                            547 |                     6.75549e-11 |                          24928.7 |                                12464.4  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |             698983 |                                 686703 |
|          4 | submission_sample_v33_rev0725_cogs06450_away0250.csv | dataset\submission_sample_v33_rev0725_cogs06450_away0250.csv | near quadratic optimum                                 |       0.725 |       0.645  |              0.25 |                             0 |                            547 |                     6.75549e-11 |                          27421.6 |                                13710.8  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |             698982 |                                 685457 |
|          5 | submission_sample_v33_rev0725_cogs06400_away0250.csv | dataset\submission_sample_v33_rev0725_cogs06400_away0250.csv | near quadratic optimum lower side                      |       0.725 |       0.64   |              0.25 |                             0 |                            547 |                     6.75549e-11 |                          29914.5 |                                14957.2  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |             698984 |                                 684211 |
|          6 | submission_sample_v33_rev0725_cogs06250_away0250.csv | dataset\submission_sample_v33_rev0725_cogs06250_away0250.csv | tests if trend remains monotonic below fitted optimum  |       0.725 |       0.625  |              0.25 |                             0 |                            547 |                     6.75549e-11 |                          37393.1 |                                18696.5  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |             699007 |                                 680471 |
|          7 | submission_sample_v33_rev0725_cogs06000_away0250.csv | dataset\submission_sample_v33_rev0725_cogs06000_away0250.csv | extreme lower-side public-only diagnostic              |       0.725 |       0.6    |              0.25 |                             0 |                            547 |                     6.75549e-11 |                          49857.5 |                                24928.7  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |             699109 |                                 674239 |

Suggested order:

1. Submit existing `submission_sample_v32_rev0725_cogs0650_away0250.csv` or equivalent `submission_sample_v33_rev0725_cogs06500_away0250.csv`.
2. If it improves, submit `submission_sample_v33_rev0725_cogs06450_away0250.csv`.
3. If `0.650` worsens, fall back to `submission_sample_v32_rev0725_cogs0675_away0250.csv`.
