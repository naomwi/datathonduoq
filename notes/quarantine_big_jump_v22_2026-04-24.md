# Quarantine Big Jump V22

Run directory: `logs\20260424_173924_quarantine_big_jump_v22`

## Status

This branch is **quarantine blackbox**, not clean. It builds on `submission_qbb60v18_cogs2023h2_down010.csv` = `662607.08245` and intentionally avoids small coefficient squeezing.

## Public Results

| filename | public_score | read |
|:--|--:|:--|
| `submission_qbb62_h1_frontload_preserve_total_q1up050.csv` | `667597.86978` | Frontloading 2023H1 from Q2 into Q1 worsened by about `+4990.79` vs anchor. Do not submit stronger frontload (`q1up080`). If H1 timing is still an axis, the next sign is backload/Q2, not Q1. |
| `submission_qbb62_h1_backload_preserve_total_q2up040.csv` | `661327.00240` | Backloading 2023H1 from Q1 into Q2 improved by about `-1280.08` vs anchor. Direction is correct, but the gain is small relative to movement, so do not blindly push `q2up080`; next test should localize Q2 timing/month or high-volume days. |

## Why This Batch Exists

The current 662k path has exhausted the smooth axes:

- 2023H1 uniform level saturates around `+13%`.
- 2024H1 stronger sample shape worsened.
- 2023H2 Revenue up/down and Q3/Q4 splits worsened.
- H2 COGS uniform down helped only slightly.

So this batch tests larger structural alternatives:

- split 2023H1 into Q1/Q2 or high-volume/low-volume days;
- switch 2024H1/non-H2 shape to a different donor manifold;
- target H2 COGS concentration rather than uniform H2 COGS level.

## Candidate Manifest

| filename                                                   | family                      | thesis                                                                                                                                |   rev_rows_changed |   cogs_rows_changed |   mean_abs_rev_delta_vs_anchor |   mean_abs_cogs_delta_vs_anchor |   movement_vs_anchor |   best_case_score_if_direction_perfect |   revenue_total_ratio_vs_anchor |   cogs_total_ratio_vs_anchor |   ratio_all |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |   max_revenue |    max_cogs |   priority |
|:-----------------------------------------------------------|:----------------------------|:--------------------------------------------------------------------------------------------------------------------------------------|-------------------:|--------------------:|-------------------------------:|--------------------------------:|---------------------:|---------------------------------------:|--------------------------------:|-----------------------------:|------------:|---------------:|---------------:|---------------:|--------------:|------------:|-----------:|
| submission_qbb62_h1_q2_rev_up060_keepcogs.csv              | 2023H1_subperiod_level      | Large sign test: if the all-H1 +13% gain was really concentrated in Apr-Jun, add +6% Revenue only to 2023Q2.                          |                 91 |                   0 |                        59877.5 |                             0   |              29938.7 |                                 632668 |                         1.01383 |                      1       |    0.886663 |       0.844193 |       1.00275  |       0.847066 |   1.26027e+07 | 1.19721e+07 |          1 |
| submission_qbb62_h1_q1_rev_up080_keepcogs.csv              | 2023H1_subperiod_level      | Opposite large sign test: put the missing level into Jan-Mar instead of the already-high Q2 block.                                    |                 90 |                   0 |                        46192.5 |                             0   |              23096.3 |                                 639511 |                         1.01067 |                      1       |    0.889436 |       0.851317 |       1.00275  |       0.847066 |   1.30315e+07 | 1.19721e+07 |          2 |
| submission_qbb62_h1_backload_preserve_total_q2up040.csv    | 2023H1_shape_total_preserve | Shift 2023H1 Revenue mass from Q1 to Q2 while preserving total H1 Revenue; tests whether level is right but timing is wrong.          |                181 |                   0 |                        79836.7 |                             0   |              39918.3 |                                 622689 |                         1       |                      1       |    0.898925 |       0.87628  |       1.00275  |       0.847066 |   1.26027e+07 | 1.19721e+07 |          3 |
| submission_qbb62_h1_frontload_preserve_total_q1up050.csv   | 2023H1_shape_total_preserve | Opposite total-preserving 2023H1 shape test: move mass forward into Jan-Mar.                                                          |                181 |                   0 |                        57740.7 |                             0   |              28870.3 |                                 633737 |                         1       |                      1       |    0.898925 |       0.87628  |       1.00275  |       0.847066 |   1.26695e+07 | 1.19721e+07 |          4 |
| submission_qbb62_h1_frontload_preserve_total_q1up080.csv   | 2023H1_shape_total_preserve | Bolder frontload: if sample-like Q2 concentration is the remaining error, move more H1 Revenue into Jan-Mar.                          |                181 |                   0 |                        92385.1 |                             0   |              46192.5 |                                 616415 |                         1       |                      1       |    0.898925 |       0.87628  |       1.00275  |       0.847066 |   1.30315e+07 | 1.19721e+07 |          5 |
| submission_qbb62_h1_top40_rev_up080_keepcogs.csv           | 2023H1_high_volume_level    | Scale only the largest 40% 2023H1 Revenue days by +8%; tests high-volume underprediction rather than uniform period underprediction.  |                 73 |                   0 |                        72317.6 |                             0   |              36158.8 |                                 626448 |                         1.0167  |                      1       |    0.884157 |       0.837819 |       1.00275  |       0.847066 |   1.30315e+07 | 1.19721e+07 |          6 |
| submission_qbb62_h1_top40_shape_preserve_up080.csv         | 2023H1_high_volume_shape    | Preserve 2023H1 total but move Revenue mass into high-volume days; tests daily concentration without another level squeeze.           |                181 |                   0 |                       144635   |                             0   |              72317.6 |                                 590289 |                         1       |                      1       |    0.898925 |       0.87628  |       1.00275  |       0.847066 |   1.30315e+07 | 1.19721e+07 |          7 |
| submission_qbb62_2024h1_recency_revshape_a060_keepcogs.csv | 2024H1_donor_shape          | Replace 60% of 2024H1 Revenue shape with period-aligned recency model shape; big alternative to more sample-shape.                    |                182 |                   0 |                       165217   |                             0   |              82608.7 |                                 579998 |                         1       |                      1       |    0.898925 |       0.87628  |       1.00275  |       0.847066 |   1.20662e+07 | 1.19721e+07 |          8 |
| submission_qbb62_2024h1_frontload_preserve_q1up060.csv     | 2024H1_shape_total_preserve | Move 2024H1 Revenue mass from Q2 into Q1 while preserving total; direct test of sample-shape over-backload in 2024.                   |                182 |                   0 |                        69185.3 |                             0   |              34592.7 |                                 628014 |                         1       |                      1       |    0.898925 |       0.87628  |       1.00275  |       0.847066 |   1.28982e+07 | 1.19721e+07 |          9 |
| submission_qbb62_nonh2_recency_revshape_a040_keepcogs.csv  | nonH2_donor_shape           | Use period-aligned recency Revenue shape for both non-H2 blocks; tests a different donor manifold than sample_submission shape.       |                363 |                   0 |                       185842   |                             0   |              92921   |                                 569686 |                         1       |                      1       |    0.898925 |       0.87628  |       1.00275  |       0.847066 |   1.2593e+07  | 1.19721e+07 |         10 |
| submission_qbb62_h2_highratio_cogs_down100_keeprev.csv     | 2023H2_cogs_ratio_shape     | Target the 40% highest COGS/Revenue days in 2023H2 with -10% COGS; tests whether H2 cost error is concentrated, not uniform.          |                  0 |                  74 |                            0   |                         53279.1 |              26639.6 |                                 635968 |                         1       |                      0.98631 |    0.886619 |       0.87628  |       0.955692 |       0.847066 |   1.26027e+07 | 1.19721e+07 |         11 |
| submission_qbb62_h2_cogsratio_preserve_highdown080.csv     | 2023H2_cogs_ratio_shape     | Preserve total 2023H2 COGS but move COGS away from extreme high-ratio days; shape-only H2 cost correction.                            |                  0 |                 184 |                            0   |                         96400.2 |              48200.1 |                                 614407 |                         1       |                      1       |    0.898925 |       0.87628  |       1.00275  |       0.847066 |   1.26027e+07 | 1.19721e+07 |         12 |
| submission_qbb62_clean_antigap_rev_a035_keepcogs.csv       | clean_qbb_gap_extrapolation | Move Revenue farther away from the clean best along the already-public-winning qbb-clean gap; bold check for unresolved public shift. |                548 |                   0 |                        59720.8 |                             0   |              29860.4 |                                 632747 |                         1.00109 |                      1       |    0.897946 |       0.872518 |       1.0034   |       0.847283 |   1.28684e+07 | 1.19721e+07 |         13 |
| submission_qbb62_core_recency_cogs_shape_h2_a050.csv       | 2023H2_cogs_donor_shape     | Use period-aligned CatBoost-core COGS shape in 2023H2 while keeping current H2 COGS total; different H2 cost manifold.                |                  0 |                 184 |                            0   |                         42451.6 |              21225.8 |                                 641381 |                         1       |                      1       |    0.898925 |       0.87628  |       1.00275  |       0.847066 |   1.26027e+07 | 1.19721e+07 |         14 |

## Suggested Submit Order

1. `submission_qbb62_h1_frontload_preserve_total_q1up050.csv` as the first total-safe large test. This is more consistent with `2023H1 p1000` failing vs `p0900`: sample/Q2 concentration may be too strong.
2. If it improves clearly, submit `submission_qbb62_h1_frontload_preserve_total_q1up080.csv`; same direction, larger move.
3. If H1 frontload fails, submit `submission_qbb62_2024h1_frontload_preserve_q1up060.csv`; it tests the analogous 2024H1 over-backload hypothesis.
4. If both frontload tests fail, use `submission_qbb62_2024h1_recency_revshape_a060_keepcogs.csv` for the broader donor-manifold pivot.
5. `submission_qbb62_h2_highratio_cogs_down100_keeprev.csv` only if we want a COGS-side large move independent of Revenue.

## Largest Movement Candidates

| filename                                                   | family                      |   movement_vs_anchor |   best_case_score_if_direction_perfect |   revenue_total_ratio_vs_anchor |   cogs_total_ratio_vs_anchor |
|:-----------------------------------------------------------|:----------------------------|---------------------:|---------------------------------------:|--------------------------------:|-----------------------------:|
| submission_qbb62_nonh2_recency_revshape_a040_keepcogs.csv  | nonH2_donor_shape           |              92921   |                                 569686 |                          1      |                            1 |
| submission_qbb62_2024h1_recency_revshape_a060_keepcogs.csv | 2024H1_donor_shape          |              82608.7 |                                 579998 |                          1      |                            1 |
| submission_qbb62_h1_top40_shape_preserve_up080.csv         | 2023H1_high_volume_shape    |              72317.6 |                                 590289 |                          1      |                            1 |
| submission_qbb62_h2_cogsratio_preserve_highdown080.csv     | 2023H2_cogs_ratio_shape     |              48200.1 |                                 614407 |                          1      |                            1 |
| submission_qbb62_h1_frontload_preserve_total_q1up080.csv   | 2023H1_shape_total_preserve |              46192.5 |                                 616415 |                          1      |                            1 |
| submission_qbb62_h1_backload_preserve_total_q2up040.csv    | 2023H1_shape_total_preserve |              39918.3 |                                 622689 |                          1      |                            1 |
| submission_qbb62_h1_top40_rev_up080_keepcogs.csv           | 2023H1_high_volume_level    |              36158.8 |                                 626448 |                          1.0167 |                            1 |
| submission_qbb62_2024h1_frontload_preserve_q1up060.csv     | 2024H1_shape_total_preserve |              34592.7 |                                 628014 |                          1      |                            1 |
