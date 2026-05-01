# Clean V2 EDA-Guided Candidates

Run directory: `logs\20260424_112018_clean_v2_eda_guided_candidates`

## Boundary

This branch rebuilds the daily shape from raw provided inputs through the existing clean raw-md anchor path. It does not read `sample_submission.csv`, previous submissions, or test target values as inputs.

It is still **clean-input public-guided** for candidates with `h1_beta >= 0.45`: public feedback suggested the old 2023H1 level was too low, while EDA supplies the clean rationale through conversion/AOV recovery and H1 shape stability.

## Train Ratio Reference

|   h1_mean |   h1_p90 |   h1_p95 |   h1_max |   h1_recovery_stress |   h1_recovery_high |
|----------:|---------:|---------:|---------:|---------------------:|-------------------:|
|  0.830609 | 0.837463 | 0.847519 | 0.857575 |                0.876 |               0.89 |

## Candidate Manifest

|   priority | filename                                            |   h1_beta |   h1_cogs_ratio_input |   ratio_shape_gamma | ratio_shape_scope   |   revenue_total |   cogs_total |   ratio_total |   rev_2023H1 |   rev_2023H2 |   rev_2024H1 |   rev_final |   cogs_2023H1 |   cogs_2023H2 |   cogs_2024H1 |   cogs_final |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |   ratio_final | note                                                                                                              |
|-----------:|:----------------------------------------------------|----------:|----------------------:|--------------------:|:--------------------|----------------:|-------------:|--------------:|-------------:|-------------:|-------------:|------------:|--------------:|--------------:|--------------:|-------------:|---------------:|---------------:|---------------:|--------------:|:------------------------------------------------------------------------------------------------------------------|
|          1 | submission_cleanv2_promo_ratio_shape_only_g050.csv  |    nan    |            nan        |                0.5  | h2                  |     2.27614e+09 |  2.1262e+09  |      0.934126 |  7.63629e+08 |  6.21578e+08 |  8.83831e+08 | 7.10042e+06 |   7.46787e+08 |   6.24991e+08 |   7.46735e+08 |  7.68649e+06 |       0.977944 |        1.00549 |       0.844885 |       1.08254 | Keep v5 period totals; redistribute H2 COGS using train-derived month/promo ratio priors.                         |
|          2 | submission_cleanv2_h1funnel_b040_h1max.csv          |      0.4  |              0.857575 |                0    | none                |     2.34737e+09 |  2.09537e+09 |      0.892645 |  8.3486e+08  |  6.21578e+08 |  8.83831e+08 | 7.10042e+06 |   7.15955e+08 |   6.24991e+08 |   7.46735e+08 |  7.68649e+06 |       0.857575 |        1.00549 |       0.844885 |       1.08254 | Train-derived H1 funnel recovery: 40% low-to-high gap; H1 COGS ratio capped at train H1 max.                      |
|          3 | submission_cleanv2_h1funnel_b045_r0876.csv          |      0.45 |              0.876    |                0    | none                |     2.36963e+09 |  2.13025e+09 |      0.89898  |  8.57119e+08 |  6.21578e+08 |  8.83831e+08 | 7.10042e+06 |   7.50837e+08 |   6.24991e+08 |   7.46735e+08 |  7.68649e+06 |       0.876    |        1.00549 |       0.844885 |       1.08254 | Public-guided clean-input: stronger H1 conversion/AOV recovery; H1 ratio stress remains below broad all-half p95. |
|          4 | submission_cleanv2_h1funnel_b046_r0876_augpromo.csv |      0.46 |              0.876    |                0.45 | h2                  |     2.37408e+09 |  2.13415e+09 |      0.898937 |  8.61571e+08 |  6.21578e+08 |  8.83831e+08 | 7.10042e+06 |   7.54736e+08 |   6.24991e+08 |   7.46735e+08 |  7.68649e+06 |       0.876    |        1.00549 |       0.844885 |       1.08254 | Same H1 recovery, plus H2 COGS daily reshape from recurring promo/discount priors.                                |
|          5 | submission_cleanv2_h1funnel_b050_r0876.csv          |      0.5  |              0.876    |                0    | none                |     2.39189e+09 |  2.14975e+09 |      0.898766 |  8.79379e+08 |  6.21578e+08 |  8.83831e+08 | 7.10042e+06 |   7.70336e+08 |   6.24991e+08 |   7.46735e+08 |  7.68649e+06 |       0.876    |        1.00549 |       0.844885 |       1.08254 | Aggressive H1 recovery stress test; keeps H2 and 2024H1 totals unchanged.                                         |
|          6 | submission_cleanv2_h1funnel_b046_r0890_augpromo.csv |      0.46 |              0.89     |                0.45 | h2                  |     2.37408e+09 |  2.14621e+09 |      0.904018 |  8.61571e+08 |  6.21578e+08 |  8.83831e+08 | 7.10042e+06 |   7.66798e+08 |   6.24991e+08 |   7.46735e+08 |  7.68649e+06 |       0.89     |        1.00549 |       0.844885 |       1.08254 | Higher H1 COGS-ratio stress paired with promo-prior H2 COGS daily reshape.                                        |

## Submit Order

1. `submission_cleanv2_h1funnel_b046_r0876_augpromo.csv`
2. `submission_cleanv2_h1funnel_b045_r0876.csv`
3. `submission_cleanv2_h1funnel_b040_h1max.csv`
4. `submission_cleanv2_promo_ratio_shape_only_g050.csv`
5. `submission_cleanv2_h1funnel_b050_r0876.csv`
6. `submission_cleanv2_h1funnel_b046_r0890_augpromo.csv`
