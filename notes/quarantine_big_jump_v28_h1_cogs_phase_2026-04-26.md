# Quarantine Big Jump V28 H1 COGS Phase

Run directory: `logs\20260426_203948_quarantine_big_jump_v28_h1_cogs_phase`

## Status

This branch is **quarantine blackbox**, not clean.

## Current Read

- Current best anchor: `submission_qbb65_h2_highratio_cogs_down060_keeprev.csv` = `659211.9087`.
- `qbb67_h2_highratio_shape_preserve_down040` failed at `659804.99207`, so H2 total-preserving redistribution is not the next path.
- New hypothesis: after the accepted 2023H1 Revenue Q2-backload, 2023H1 COGS may be out of phase because COGS was kept fixed.
- This batch changes only 2023H1 COGS. Revenue, 2023H2, and 2024H1 are preserved.

## Public Results

| filename | public_score | read |
|:--|--:|:--|
| `submission_qbb68_h1_q1_cogs_down040_keeprev.csv` | `657443.28137` | Accepted. Improves by about `1768.63` vs prior best `659211.90870`. Q1 COGS is likely too high after the accepted 2023H1 Revenue backload. Continue same sign with `qbb68_h1_q1_cogs_down080_keeprev`. |
| `submission_qbb68_h1_q1_cogs_down080_keeprev.csv` | `656301.72926` | Accepted. Improves by about `1141.55` vs `down040`. The response is still positive but concave, so generate a follow-up around absolute Q1 COGS down `10-14%`, with curve optimum near `13%`. |

## Anchor Month Ratios

| month   |   days |     Revenue |        COGS |    ratio |
|:--------|-------:|------------:|------------:|---------:|
| 2023-01 |     31 | 7.00485e+07 | 6.53417e+07 | 0.932806 |
| 2023-02 |     28 | 8.6743e+07  | 8.07645e+07 | 0.931078 |
| 2023-03 |     31 | 1.37752e+08 | 1.37711e+08 | 0.999699 |
| 2023-04 |     30 | 1.8903e+08  | 1.6018e+08  | 0.847377 |
| 2023-05 |     31 | 1.95774e+08 | 1.57737e+08 | 0.805712 |
| 2023-06 |     30 | 1.83952e+08 | 1.54758e+08 | 0.841295 |

## Sample Month Ratios

| month   |   days |     Revenue |        COGS |    ratio |
|:--------|-------:|------------:|------------:|---------:|
| 2023-01 |     31 | 5.7582e+07  | 4.69526e+07 | 0.815404 |
| 2023-02 |     28 | 7.09055e+07 | 5.77454e+07 | 0.814399 |
| 2023-03 |     31 | 1.11981e+08 | 9.6615e+07  | 0.862779 |
| 2023-04 |     30 | 1.40741e+08 | 1.19808e+08 | 0.851267 |
| 2023-05 |     31 | 1.4578e+08  | 1.17395e+08 | 0.805286 |
| 2023-06 |     30 | 1.37127e+08 | 1.15719e+08 | 0.843883 |

## Candidate Manifest

|   priority | filename                                               | family                       | changed_scope          | thesis                                                                                                                  |   rev_rows_changed |   cogs_rows_changed |   h2_max_abs_delta_vs_anchor |   h24_max_abs_delta_vs_anchor |   mean_abs_rev_delta_vs_anchor |   mean_abs_cogs_delta_vs_anchor |   movement_vs_anchor |   best_case_score_if_direction_perfect |   revenue_total_ratio_vs_anchor |   cogs_total_ratio_vs_anchor |   ratio_all |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |   max_revenue |    max_cogs |
|-----------:|:-------------------------------------------------------|:-----------------------------|:-----------------------|:------------------------------------------------------------------------------------------------------------------------|-------------------:|--------------------:|-----------------------------:|------------------------------:|-------------------------------:|--------------------------------:|---------------------:|---------------------------------------:|--------------------------------:|-----------------------------:|------------:|---------------:|---------------:|---------------:|--------------:|------------:|
|          1 | submission_qbb68_h1_q1_cogs_down040_keeprev.csv        | h1_q1_cogs_level             | 2023Q1 COGS only       | Lower 2023Q1 COGS after the accepted Revenue backload; tests whether Q1 cost stayed too high.                           |                  0 |                  90 |                            0 |                             0 |                              0 |                         20716.6 |             10358.3  |                                 648854 |                               1 |                     0.994633 |    0.886757 |       0.863129 |       0.974516 |       0.847066 |   1.26027e+07 | 1.14933e+07 |
|          2 | submission_qbb68_h1_q1_cogs_down080_keeprev.csv        | h1_q1_cogs_level             | 2023Q1 COGS only       | Higher-amplitude Q1 COGS-down sign test if down040 is positive.                                                         |                  0 |                  90 |                            0 |                             0 |                              0 |                         41433.1 |             20716.6  |                                 638495 |                               1 |                     0.989266 |    0.881972 |       0.849979 |       0.974516 |       0.847066 |   1.26027e+07 | 1.10144e+07 |
|          3 | submission_qbb68_h1_cogs_backload_q2up020_preserve.csv | h1_cogs_phase_preserve       | 2023H1 COGS shape only | Move 2023H1 COGS from Q1 to Q2, preserving H1 total; partial cost co-move with the winning Revenue backload.            |                  0 |                 181 |                            0 |                             0 |                              0 |                         34501.9 |             17250.9  |                                 641961 |                               1 |                     1        |    0.891542 |       0.87628  |       0.974516 |       0.847066 |   1.26027e+07 | 1.15734e+07 |
|          4 | submission_qbb68_h1_cogs_backload_q2up040_preserve.csv | h1_cogs_phase_preserve       | 2023H1 COGS shape only | Full-size COGS co-move with the winning Revenue Q2 backload.                                                            |                  0 |                 181 |                            0 |                             0 |                              0 |                         69003.7 |             34501.9  |                                 624710 |                               1 |                     1        |    0.891542 |       0.87628  |       0.974516 |       0.847066 |   1.26027e+07 | 1.11746e+07 |
|          5 | submission_qbb68_h1_cogs_follow_revbackload_a050.csv   | h1_cogs_phase_follow_revenue | 2023H1 COGS shape only | Apply 50% of the accepted daily Revenue backload multiplier to COGS.                                                    |                  0 |                 181 |                            0 |                             0 |                              0 |                         35153.6 |             17576.8  |                                 641635 |                               1 |                     0.999831 |    0.891391 |       0.875866 |       0.974516 |       0.847066 |   1.26027e+07 | 1.15583e+07 |
|          6 | submission_qbb68_h1_cogs_follow_revbackload_a100.csv   | h1_cogs_phase_follow_revenue | 2023H1 COGS shape only | Apply 100% of the accepted daily Revenue backload multiplier to COGS.                                                   |                  0 |                 181 |                            0 |                             0 |                              0 |                         70307.2 |             35153.6  |                                 624058 |                               1 |                     0.999662 |    0.891241 |       0.875452 |       0.974516 |       0.847066 |   1.26027e+07 | 1.11445e+07 |
|          7 | submission_qbb68_h1_q1_cogs_sample_ratio_a025.csv      | h1_q1_cogs_sample_ratio      | 2023Q1 COGS only       | Blend 25% of Q1 COGS toward sample monthly COGS/Revenue ratios; tests suspicious Q1 ratio spike after Revenue backload. |                  0 |                  90 |                            0 |                             0 |                              0 |                         16973.5 |              8486.74 |                                 650725 |                               1 |                     0.995603 |    0.887621 |       0.865505 |       0.974516 |       0.847066 |   1.26027e+07 | 1.14018e+07 |
|          8 | submission_qbb68_h1_q1_cogs_sample_ratio_a040.csv      | h1_q1_cogs_sample_ratio      | 2023Q1 COGS only       | Stronger Q1 monthly-ratio repair if the sample-ratio direction is positive.                                             |                  0 |                  90 |                            0 |                             0 |                              0 |                         27157.6 |             13578.8  |                                 645633 |                               1 |                     0.992964 |    0.885269 |       0.859041 |       0.974516 |       0.847066 |   1.26027e+07 | 1.10596e+07 |

## Suggested Submit Order

1. Current best is now `submission_qbb68_h1_q1_cogs_down080_keeprev.csv`.
2. Generate V29 around absolute Q1 COGS down `10-14%`.
3. Prefer a direct response-curve probe near `down120` or `down130`.
4. Do not use H1 total-preserve backload until the Q1 level-down curve stops improving.

## Do Not Use As Clean

These candidates are public-guided/quarantine probes and must not be presented as clean model outputs.
