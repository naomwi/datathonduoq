# Clean V2 H1 Follow-Up

Run directory: `logs\20260424_112628_clean_v2_h1_followup`

## Boundary

This is a clean-input public-guided follow-up after:

- `submission_cleanv2_h1funnel_b045_r0876.csv = 673785.31754`
- `submission_cleanv2_h1funnel_b050_r0876.csv = 676153.29609`

No `sample_submission.csv`, previous submissions, or test targets are read as inputs. The public scores only determine which train-derived scenario neighborhood to probe next.

## Train H1 Ratio Reference

|   h1_mean |   h1_p90 |   h1_p95 |   h1_max |   h1_recovery_stress |   h1_recovery_high |
|----------:|---------:|---------:|---------:|---------------------:|-------------------:|
|  0.830609 | 0.837463 | 0.847519 | 0.857575 |                0.876 |               0.89 |

## Candidate Manifest

|   priority | filename                                               |   h1_beta |   h1_revenue |   h1_cogs_ratio |     h1_cogs |   ratio_shape_gamma |   revenue_total |   cogs_total |   ratio_total |   rev_2023H1 |   cogs_2023H1 |   ratio_2023H1 |   rev_2023H2 |   cogs_2023H2 |   ratio_2023H2 |   rev_2024H1 |   cogs_2024H1 |   ratio_2024H1 | note                                                                                               |
|-----------:|:-------------------------------------------------------|----------:|-------------:|----------------:|------------:|--------------------:|----------------:|-------------:|--------------:|-------------:|--------------:|---------------:|-------------:|--------------:|---------------:|-------------:|--------------:|---------------:|:---------------------------------------------------------------------------------------------------|
|          1 | submission_cleanv2_h1fine_b043_r0876.csv               |      0.43 |  8.48216e+08 |           0.876 | 7.43037e+08 |                0    |     2.36072e+09 |  2.12245e+09 |      0.899067 |  8.48216e+08 |   7.43037e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |  8.83831e+08 |   7.46735e+08 |       0.844885 | Map lower side around public-best b045; same COGS ratio.                                           |
|          2 | submission_cleanv2_h1fine_b044_r0876.csv               |      0.44 |  8.52667e+08 |           0.876 | 7.46937e+08 |                0    |     2.36518e+09 |  2.12635e+09 |      0.899023 |  8.52667e+08 |   7.46937e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |  8.83831e+08 |   7.46735e+08 |       0.844885 | Near-best H1 level, slightly below b045.                                                           |
|          3 | submission_cleanv2_h1fine_b046_r0876.csv               |      0.46 |  8.61571e+08 |           0.876 | 7.54736e+08 |                0    |     2.37408e+09 |  2.13415e+09 |      0.898937 |  8.61571e+08 |   7.54736e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |  8.83831e+08 |   7.46735e+08 |       0.844885 | Near-best H1 level, slightly above b045 without H2 reshape.                                        |
|          4 | submission_cleanv2_h1fine_b047_r0876.csv               |      0.47 |  8.66023e+08 |           0.876 | 7.58636e+08 |                0    |     2.37853e+09 |  2.13805e+09 |      0.898894 |  8.66023e+08 |   7.58636e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |  8.83831e+08 |   7.46735e+08 |       0.844885 | Upper-side H1 level map before the known b050 degradation.                                         |
|          5 | submission_cleanv2_h1fine_b045_r0865.csv               |      0.45 |  8.57119e+08 |           0.865 | 7.41408e+08 |                0    |     2.36963e+09 |  2.12082e+09 |      0.895001 |  8.57119e+08 |   7.41408e+08 |          0.865 |  6.21578e+08 |   6.24991e+08 |        1.00549 |  8.83831e+08 |   7.46735e+08 |       0.844885 | Same public-best H1 revenue level, lower H1 COGS ratio between train max and public-guided stress. |
|          6 | submission_cleanv2_h1fine_b045_r0885.csv               |      0.45 |  8.57119e+08 |           0.885 | 7.58551e+08 |                0    |     2.36963e+09 |  2.13796e+09 |      0.902235 |  8.57119e+08 |   7.58551e+08 |          0.885 |  6.21578e+08 |   6.24991e+08 |        1.00549 |  8.83831e+08 |   7.46735e+08 |       0.844885 | Same public-best H1 revenue level, higher H1 COGS ratio stress.                                    |
|          7 | submission_cleanv2_h1fine_b046_r0876_augpromo_g025.csv |      0.46 |  8.61571e+08 |           0.876 | 7.54736e+08 |                0.25 |     2.37408e+09 |  2.13415e+09 |      0.898937 |  8.61571e+08 |   7.54736e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |  8.83831e+08 |   7.46735e+08 |       0.844885 | Small H2 COGS daily reshape from recurring promo priors; weaker than previous g045.                |

## Submit Order

1. `submission_cleanv2_h1fine_b046_r0876.csv`
2. `submission_cleanv2_h1fine_b044_r0876.csv`
3. `submission_cleanv2_h1fine_b045_r0865.csv`
4. `submission_cleanv2_h1fine_b045_r0885.csv`
5. `submission_cleanv2_h1fine_b043_r0876.csv`
6. `submission_cleanv2_h1fine_b047_r0876.csv`
7. `submission_cleanv2_h1fine_b046_r0876_augpromo_g025.csv`
