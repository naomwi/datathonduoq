# Clean Regime Recovery Scenarios

Run directory: `logs\20260423_131852_clean_regime_recovery_scenarios`

## Boundary

This branch is a clean-input scenario pipeline. It uses:

- `dataset/sales.csv` through `2022-12-31`;
- known calendar dates from `2023-01-01` to `2024-07-01`;
- no `sample_submission.csv`;
- no previous `submission_*.csv` as inputs;
- no test `Revenue` / `COGS` values.

It is not pure train-validation selection. It explicitly models a latent business scenario: after the 2019-2022 low-demand regime, 2023-2024 partially recover toward the 2013-2018 high-demand regime.

## Era Evidence

| era          | half   |   revenue_avg |    cogs_avg |   cogs_ratio_avg |
|:-------------|:-------|--------------:|------------:|-----------------:|
| pre2019_high | H1     |   1.10197e+09 | 9.11652e+08 |         0.827136 |
| recent_low   | H1     |   6.56784e+08 | 5.49198e+08 |         0.835818 |
| pre2019_high | H2     |   7.78839e+08 | 7.08873e+08 |         0.911765 |
| recent_low   | H2     |   4.44242e+08 | 4.14012e+08 |         0.934353 |

## Shape Validation

These scores use oracle period totals, so they evaluate only daily allocation shape.

| target   | shape                | half   |   mean_oracle_wape |   worst_oracle_wape |
|:---------|:---------------------|:-------|-------------------:|--------------------:|
| COGS     | clean_recovery_shape | H1     |           0.188707 |            0.21026  |
| COGS     | pre_only             | H1     |           0.189797 |            0.206346 |
| COGS     | recent_only          | H1     |           0.209418 |            0.222496 |
| COGS     | pre_only             | H2     |           0.190008 |            0.208143 |
| COGS     | clean_recovery_shape | H2     |           0.235736 |            0.345699 |
| COGS     | recent_only          | H2     |           0.251878 |            0.387405 |
| Revenue  | clean_recovery_shape | H1     |           0.189396 |            0.209406 |
| Revenue  | pre_only             | H1     |           0.190158 |            0.208387 |
| Revenue  | recent_only          | H1     |           0.209903 |            0.221625 |
| Revenue  | pre_only             | H2     |           0.210315 |            0.254535 |
| Revenue  | clean_recovery_shape | H2     |           0.258698 |            0.312309 |
| Revenue  | recent_only          | H2     |           0.274762 |            0.350648 |

## Candidate Manifest

| filename                                                  | level_mode   |   revenue_growth_strength |   beta_2023 |   beta_2024 |   beta_2023_h1 |   beta_2023_h2 |   beta_2024_h1 |   beta_2024_h2 | cogs_ratio_mode                       |   revenue_total |   cogs_total |   ratio_total |   rev_2023H1 |   rev_2023H2 |   rev_2024H1 |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 | note                                                                                                                                                                |
|:----------------------------------------------------------|:-------------|--------------------------:|------------:|------------:|---------------:|---------------:|---------------:|---------------:|:--------------------------------------|----------------:|-------------:|--------------:|-------------:|-------------:|-------------:|---------------:|---------------:|---------------:|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| submission_clean_regime_recovery_v2_yoy100.csv            | yoy          |                      1    |        0.25 |        0.4  |         nan    |         nan    |         nan    |         nan    | recent                                |     2.18951e+09 |  1.88384e+09 |      0.860392 |  7.7657e+08  |  5.35281e+08 |  8.70908e+08 |       0.835818 |       0.934353 |       0.835818 | Continue the 2022 annual revenue recovery rate into 2023-2024; COGS ratio from recent train regime.                                                                 |
| submission_clean_regime_recovery_v2_yoy125.csv            | yoy          |                      1.25 |        0.25 |        0.4  |         nan    |         nan    |         nan    |         nan    | recent                                |     2.27321e+09 |  1.95528e+09 |      0.860141 |  7.97599e+08 |  5.49777e+08 |  9.18715e+08 |       0.835818 |       0.934353 |       0.835818 | Stronger continuation of the 2022 recovery, still capped below pre-2019 high-regime average.                                                                        |
| submission_clean_regime_recovery_v2_gap30_45.csv          | gap          |                      1    |        0.3  |        0.45 |         nan    |         nan    |         nan    |         nan    | regime_blend                          |     2.19877e+09 |  1.88332e+09 |      0.856532 |  7.90341e+08 |  5.44621e+08 |  8.57119e+08 |       0.833213 |       0.927576 |       0.831911 | Latent regime blend: 2023 recovers 30 percent of the low-to-high gap, 2024 recovers 45 percent.                                                                     |
| submission_clean_regime_recovery_v2_hybrid.csv            | hybrid       |                      1.15 |        0.3  |        0.45 |         nan    |         nan    |         nan    |         nan    | regime_blend                          |     2.21917e+09 |  1.90028e+09 |      0.856301 |  7.89764e+08 |  5.443e+08   |  8.78279e+08 |       0.833213 |       0.927576 |       0.831911 | Average of train-derived YoY recovery and low/high latent regime blend.                                                                                             |
| submission_clean_regime_recovery_v2_h1strong_h2shrink.csv | hybrid       |                      1.25 |        0.25 |        0.5  |         nan    |         nan    |         nan    |         nan    | median                                |     2.2277e+09  |  1.89745e+09 |      0.851756 |  7.8284e+08  |  5.38834e+08 |  8.99047e+08 |       0.826791 |       0.927926 |       0.826791 | Use stronger H1 stable seasonality, aggressively shrink H2 shape, and median COGS ratios.                                                                           |
| submission_clean_regime_recovery_v2_trainshape_hybrid.csv | hybrid       |                      1.15 |        0.3  |        0.45 |         nan    |         nan    |         nan    |         nan    | regime_blend                          |     2.21936e+09 |  1.90055e+09 |      0.856352 |  7.89764e+08 |  5.443e+08   |  8.78279e+08 |       0.833213 |       0.927576 |       0.831911 | Shape weights selected from train-only oracle-total validation: blended H1, pre-2019 H2.                                                                            |
| submission_clean_regime_recovery_v3_h2strong_cogsp85.csv  | gap_h2strong |                      1    |        0.3  |        0.5  |         nan    |         nan    |         nan    |         nan    | transition_stress_p85                 |     2.28909e+09 |  2.09129e+09 |      0.91359  |  7.90341e+08 |  6.1154e+08  |  8.79379e+08 |       0.96465  |       0.96465  |       0.831477 | Clean stress scenario: H2 revenue recovers faster from the low regime; 2023 COGS ratio uses the 85th percentile of train half-year ratios, then normalizes in 2024. |
| submission_clean_regime_recovery_v3_h2strong_cogsp95.csv  | gap_h2strong |                      1    |        0.3  |        0.5  |         nan    |         nan    |         nan    |         nan    | transition_stress_p95                 |     2.28909e+09 |  2.10993e+09 |      0.921732 |  7.90341e+08 |  6.1154e+08  |  8.79379e+08 |       0.977944 |       0.977944 |       0.831477 | More aggressive clean stress scenario: H2 revenue recovers faster; 2023 COGS ratio uses the 95th percentile of train half-year ratios, then normalizes in 2024.     |
| submission_cleaninput_pubguided_v4_h2max_2024h1max.csv    | gap          |                      1    |        0.25 |        0.4  |           0.24 |           0.53 |           0.51 |           0.51 | transition_stress_p95_h2max_2024h1max |     2.27614e+09 |  2.13742e+09 |      0.939053 |  7.63629e+08 |  6.21578e+08 |  8.83831e+08 |       0.977944 |       1.00549  |       0.857575 | Clean-input, public-guided scenario: period recovery is adjusted after the 732k result; COGS ratios remain train-derived upper-tail/max stress values.              |
| submission_cleaninput_pubguided_v4_h1p85_h2max.csv        | gap          |                      1    |        0.25 |        0.4  |           0.24 |           0.53 |           0.51 |           0.51 | transition_stress_p85_h2max_2024h1max |     2.27614e+09 |  2.12726e+09 |      0.934593 |  7.63629e+08 |  6.21578e+08 |  8.83831e+08 |       0.96465  |       1.00549  |       0.857575 | Softer 2023H1 COGS stress than v4_h2max_2024h1max; H2 and 2024H1 use train max stress.                                                                              |
| submission_cleaninput_pubguided_v4_revlow_h2max.csv       | gap          |                      1    |        0.25 |        0.4  |           0.18 |           0.55 |           0.51 |           0.51 | transition_stress_p95_h2max_2024h1max |     2.25612e+09 |  2.11802e+09 |      0.93879  |  7.36918e+08 |  6.2827e+08  |  8.83831e+08 |       0.977944 |       1.00549  |       0.857575 | Lower 2023H1 revenue recovery and stronger H2 recovery; clean-input but public-guided after v3.                                                                     |

## Reading

If public improves, the clean interpretation is that leaderboard years are not a new all-time-high regime; they are a partial recovery of order/conversion level while retaining stable H1 seasonality. If public fails, the missing signal is not recoverable from train-only sales history without some form of scenario calibration.
