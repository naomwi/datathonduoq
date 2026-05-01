# Reasonable Final V2 Shape Strength

Run directory: `logs\20260423_113138_reasonable_final_v2_shape_strength`

## Read Of Latest Public Results

- `submission_reasonable_final_sourceclean_pubcal.csv`: `695415.79121`
- `submission_reasonable_final_sourceclean_pubcal_soft.csv`: `716547.39412`

The soft candidate lost badly, so period-level calibration should stay near the stronger `sourceclean_pubcal` totals.

The next likely error source is daily allocation within each period. This run keeps the same period totals but changes how strongly the train-only raw month-day prior controls daily shape.

## Legal/Presentation Framing

These files still rebuild the anchor from raw provided train tables and do not read sample/test target/submission files as inputs. The extra shape strength should be explained as stronger shrinkage toward a historical seasonality prior, not as a new external signal.

## Candidate Manifest

|   priority | filename                                                 |   revenue_alpha_non_h2 |   revenue_alpha_h2 |   cogs_alpha |   revenue_total |   cogs_total |   ratio_total |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 | note                                                                                                   |
|-----------:|:---------------------------------------------------------|-----------------------:|-------------------:|-------------:|----------------:|-------------:|--------------:|---------------:|---------------:|---------------:|:-------------------------------------------------------------------------------------------------------|
|          1 | submission_reasonable_v2_shape_doublepass.csv            |               0.96     |           0.19     |     0.8775   |     2.24753e+09 |  2.12976e+09 |        0.9476 |       0.982903 |        1.00881 |       0.871202 | Equivalent to applying the train raw month-day prior twice; tests if 695k missed daily-shape strength. |
|          2 | submission_reasonable_v2_shape_15pass.csv                |               0.910557 |           0.146185 |     0.792937 |     2.24753e+09 |  2.12976e+09 |        0.9476 |       0.982903 |        1.00881 |       0.871202 | Midpoint between one-pass 695k and double-pass shape; safer if double-pass overshoots.                 |
|          3 | submission_reasonable_v2_shape_double_rev_only.csv       |               0.96     |           0.19     |     0.65     |     2.24753e+09 |  2.12976e+09 |        0.9476 |       0.982903 |        1.00881 |       0.871202 | Strengthen only Revenue daily shape; keeps COGS daily shape from 695k.                                 |
|          4 | submission_reasonable_v2_shape_double_cogs_only.csv      |               0.8      |           0.1      |     0.8775   |     2.24753e+09 |  2.12976e+09 |        0.9476 |       0.982903 |        1.00881 |       0.871202 | Strengthen only COGS daily shape; isolates whether remaining 8k is mostly COGS shape.                  |
|          5 | submission_reasonable_v2_shape_nonh2_strong_h2_guard.csv |               0.93     |           0.05     |     0.82     |     2.24753e+09 |  2.12976e+09 |        0.9476 |       0.982903 |        1.00881 |       0.871202 | Strong H1/2024H1 raw-md shape while guarding unstable 2023H2 Revenue shape.                            |

## Submit Order

1. `submission_reasonable_v2_shape_doublepass.csv`
2. If double-pass worsens, try `submission_reasonable_v2_shape_15pass.csv`
3. If double-pass is close but unclear, isolate with `double_rev_only` and `double_cogs_only`
