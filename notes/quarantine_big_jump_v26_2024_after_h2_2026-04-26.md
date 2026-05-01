# Quarantine Big Jump V26 2024H1 After H2

Run directory: `logs\20260426_202055_quarantine_big_jump_v26_2024_after_h2`

## Status

This branch is **quarantine blackbox**, not clean.

## Current Read

- Current best anchor: `submission_qbb65_h2_highratio_cogs_down060_keeprev.csv` = `659211.9087`.
- `h2_highratio_down100` overshot, so do not continue H2 intensity blindly.
- This batch changes 2024H1 Revenue while preserving the current H1 backload and H2 high-ratio COGS down060 gains.

## Public Results

| filename | public_score | read |
|:--|--:|:--|
| `submission_qbb66_2024h1_recency_revshape_a030_keep_h2cogs.csv` | `661604.13161` | Rejected. 2024H1 recency-shape worsened by about `+2392.22` vs current best `h2_highratio_down060`. Do not submit `a040/a060`; pivot to 2024H1 frontload sign test or back to H2 COGS response-fit. |
| `submission_qbb66_2024h1_frontload_q1up030_keep_h2cogs.csv` | `659485.66889` | Slight reject. 2024H1 frontload worsened by about `+273.76` vs current best. Do not escalate `q1up040/q1up060`; return to H2 COGS structure after `down060`. |

## Candidate Manifest

|   priority | filename                                                         | family                       | thesis                                                                                                                 |   rev_rows_changed |   cogs_rows_changed |   h1_max_abs_delta_vs_anchor |   h2_cogs_max_abs_delta_vs_anchor |   mean_abs_rev_delta_vs_anchor |   mean_abs_cogs_delta_vs_anchor |   movement_vs_anchor |   best_case_score_if_direction_perfect |   revenue_total_ratio_vs_anchor |   cogs_total_ratio_vs_anchor |   ratio_all |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |   max_revenue |    max_cogs |
|-----------:|:-----------------------------------------------------------------|:-----------------------------|:-----------------------------------------------------------------------------------------------------------------------|-------------------:|--------------------:|-----------------------------:|----------------------------------:|-------------------------------:|--------------------------------:|---------------------:|---------------------------------------:|--------------------------------:|-----------------------------:|------------:|---------------:|---------------:|---------------:|--------------:|------------:|
|          1 | submission_qbb66_2024h1_recency_revshape_a030_keep_h2cogs.csv    | 2024h1_recency_revenue_shape | Keep H2 high-ratio COGS down060; blend 30% period-aligned recency Revenue shape into 2024H1.                           |                182 |                   0 |                            0 |                                 0 |                        82608.7 |                               0 |              41304.4 |                                 617908 |                               1 |                            1 |    0.891542 |        0.87628 |       0.974516 |       0.847066 |   1.232e+07   | 1.19721e+07 |
|          2 | submission_qbb66_2024h1_recency_revshape_a040_keep_h2cogs.csv    | 2024h1_recency_revenue_shape | Keep H2 high-ratio COGS down060; blend 40% period-aligned recency Revenue shape into 2024H1.                           |                182 |                   0 |                            0 |                                 0 |                       110145   |                               0 |              55072.5 |                                 604139 |                               1 |                            1 |    0.891542 |        0.87628 |       0.974516 |       0.847066 |   1.232e+07   | 1.19721e+07 |
|          3 | submission_qbb66_2024h1_recency_revshape_a060_keep_h2cogs.csv    | 2024h1_recency_revenue_shape | Keep H2 high-ratio COGS down060; blend 60% period-aligned recency Revenue shape into 2024H1.                           |                182 |                   0 |                            0 |                                 0 |                       165217   |                               0 |              82608.7 |                                 576603 |                               1 |                            1 |    0.891542 |        0.87628 |       0.974516 |       0.847066 |   1.232e+07   | 1.19721e+07 |
|          4 | submission_qbb66_2024h1_frontload_q1up030_keep_h2cogs.csv        | 2024h1_frontload_revenue     | Keep H2 high-ratio COGS down060; preserve 2024H1 total and move Revenue from Apr-Jun into Jan-Mar with Q1 scale 1.030. |                182 |                   0 |                            0 |                                 0 |                        34592.7 |                               0 |              17296.3 |                                 641916 |                               1 |                            1 |    0.891542 |        0.87628 |       0.974516 |       0.847066 |   1.25332e+07 | 1.19721e+07 |
|          5 | submission_qbb66_2024h1_frontload_q1up040_keep_h2cogs.csv        | 2024h1_frontload_revenue     | Keep H2 high-ratio COGS down060; preserve 2024H1 total and move Revenue from Apr-Jun into Jan-Mar with Q1 scale 1.040. |                182 |                   0 |                            0 |                                 0 |                        46123.5 |                               0 |              23061.8 |                                 636150 |                               1 |                            1 |    0.891542 |        0.87628 |       0.974516 |       0.847066 |   1.26549e+07 | 1.19721e+07 |
|          6 | submission_qbb66_2024h1_frontload_q1up060_keep_h2cogs.csv        | 2024h1_frontload_revenue     | Keep H2 high-ratio COGS down060; preserve 2024H1 total and move Revenue from Apr-Jun into Jan-Mar with Q1 scale 1.060. |                182 |                   0 |                            0 |                                 0 |                        69185.3 |                               0 |              34592.7 |                                 624619 |                               1 |                            1 |    0.891542 |        0.87628 |       0.974516 |       0.847066 |   1.28982e+07 | 1.19721e+07 |
|          7 | submission_qbb66_2024h1_janfeb_from_mayjun_up050_keep_h2cogs.csv | 2024h1_frontload_revenue     | More concentrated frontload: preserve Jan-Feb + May-Jun total and move Revenue from May-Jun into Jan-Feb.              |                121 |                   0 |                            0 |                                 0 |                        30990.7 |                               0 |              15495.4 |                                 643717 |                               1 |                            1 |    0.891542 |        0.87628 |       0.974516 |       0.847066 |   1.23897e+07 | 1.19721e+07 |
|          8 | submission_qbb66_2024h1_march_from_june_up080_keep_h2cogs.csv    | 2024h1_month_transition      | March-June contrast test: preserve Mar+Jun total and move Revenue from June into March.                                |                 61 |                   0 |                            0 |                                 0 |                        42661.9 |                               0 |              21331   |                                 637881 |                               1 |                            1 |    0.891542 |        0.87628 |       0.974516 |       0.847066 |   1.31416e+07 | 1.19721e+07 |

## Suggested Submit Order

1. `submission_qbb66_2024h1_recency_revshape_a030_keep_h2cogs.csv`
2. If it improves, submit `submission_qbb66_2024h1_recency_revshape_a040_keep_h2cogs.csv`
3. If recency shape fails, submit `submission_qbb66_2024h1_frontload_q1up030_keep_h2cogs.csv`
4. Escalate only after a positive sign: `a060`, `q1up060`, or the Jan-Feb/March concentrated variants.

## Do Not Use As Clean

These candidates are public-guided/quarantine probes and must not be presented as clean model outputs.
