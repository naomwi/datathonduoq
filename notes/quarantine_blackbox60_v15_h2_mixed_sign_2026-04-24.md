# Quarantine Blackbox 60x V15 H2 Mixed Sign

Run directory: `logs\20260424_011728_quarantine_blackbox60_v15_h2_mixed_sign`

## Status

This branch is **not clean**. It builds directly on the current blackbox best and public-leaderboard feedback.

Current anchor:

- `submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv` = `662759.87577`

## Why This Batch Exists

- `2023H2 +2.5%` failed.
- `2023H2 -2.5%` also failed.
- That strongly suggests `2023H2` is not a one-sign mistake.
- The current best still looks low in `Q3` but high in `Q4`, so the next real jump hypothesis is a mixed-sign H2 split: `Q3 up / Q4 down`.

## Candidate Manifest

|   priority | filename                                              | thesis                                                                                                 |   q3_scale |   q4_scale |   jul_aug_scale |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   movement |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_total |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |      rev_q3 |      rev_q4 |   ratio_q3 |   ratio_q4 |   q3_share_of_h2 |   q4_share_of_h2 |
|-----------:|:------------------------------------------------------|:-------------------------------------------------------------------------------------------------------|-----------:|-----------:|----------------:|--------------------------------:|---------------------------------:|-----------:|---------------------------------:|------------------------------:|--------------:|---------------:|---------------:|---------------:|------------:|------------:|-----------:|-----------:|-----------------:|-----------------:|
|          1 | submission_qbb60v15_h2split_q3up050_q4down025.csv     | Primary mixed-sign test: Q3 looks undercalled while Q4 looks overcalled on the current best anchor.    |      1.05  |      0.975 |           1     |                         44468.7 |                                0 |    22234.3 |                          1.00466 |                             1 |      0.897389 |        0.87628 |       0.995135 |       0.847066 | 3.72036e+08 | 2.5946e+08  |    1.02533 |   0.951839 |         0.589135 |         0.410865 |
|          2 | submission_qbb60v15_h2split_q3up075_q4down050.csv     | Stronger mixed-sign continuation toward the sample-like H2 internal split.                             |      1.075 |      0.95  |           1     |                         72773.1 |                                0 |    36386.6 |                          1.00559 |                             1 |      0.89656  |        0.87628 |       0.991672 |       0.847066 | 3.80894e+08 | 2.52807e+08 |    1.00149 |   0.976888 |         0.601063 |         0.398937 |
|          3 | submission_qbb60v15_h2split_julaugup050_q4down025.csv | Localize the H2-up sign to Jul-Aug only, where both share and ratio look most misaligned.              |      1     |      0.975 |           1.05  |                         34171.3 |                                0 |    17085.7 |                          1.00228 |                             1 |      0.899519 |        0.87628 |       1.00411  |       0.847066 | 3.66394e+08 | 2.5946e+08  |    1.04112 |   0.951839 |         0.58543  |         0.41457  |
|          4 | submission_qbb60v15_h2split_julaugup075_q4down050.csv | Aggressive Jul-Aug recovery with Q4 down, if the real error is concentrated in summer shoulder months. |      1     |      0.95  |           1.075 |                         57327.1 |                                0 |    28663.6 |                          1.00202 |                             1 |      0.899752 |        0.87628 |       1.0051   |       0.847066 | 3.7243e+08  | 2.52807e+08 |    1.02425 |   0.976888 |         0.595662 |         0.404338 |
