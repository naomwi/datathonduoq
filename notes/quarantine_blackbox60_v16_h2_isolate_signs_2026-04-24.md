# Quarantine Blackbox 60x V16 H2 Isolate Signs

Run directory: `logs\20260424_012140_quarantine_blackbox60_v16_h2_isolate_signs`

## Status

This branch is **not clean**. It builds directly on the current blackbox best and public-leaderboard feedback.

Current anchor:

- `submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv` = `662759.87577`

## Why This Batch Exists

- Broad `Q3 up / Q4 down` failed.
- That does not kill the H2 hypothesis; it means the correction is probably more localized.
- The next useful step is to isolate `Q4 down` from `Jul-Aug up`, then split `Jul` versus `Aug`.

## Candidate Manifest

|   priority | filename                                         | thesis                                                                                        |   jul_scale |   aug_scale |   q4_scale |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   movement |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_total |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |     rev_jul |   ratio_jul |     rev_aug |   ratio_aug |     rev_sep |   ratio_sep |     rev_oct |   ratio_oct |     rev_nov |   ratio_nov |     rev_dec |   ratio_dec |
|-----------:|:-------------------------------------------------|:----------------------------------------------------------------------------------------------|------------:|------------:|-----------:|--------------------------------:|---------------------------------:|-----------:|---------------------------------:|------------------------------:|--------------:|---------------:|---------------:|---------------:|------------:|------------:|------------:|------------:|------------:|------------:|------------:|------------:|------------:|------------:|------------:|------------:|
|          1 | submission_qbb60v16_h2iso_q4down025_only.csv     | Isolate whether the failure came mainly from Q4 being too high on the current anchor.         |        1    |        1    |      0.975 |                         12140.2 |                                0 |    6070.09 |                         0.997196 |                             1 |      0.904109 |        0.87628 |       1.02386  |       0.847066 | 1.28692e+08 |     1.05171 | 1.1277e+08  |     1.21653 | 1.12859e+08 |    0.965155 | 1.05863e+08 |    0.877777 | 8.13562e+07 |    0.930674 | 7.22406e+07 |     1.08421 |
|          2 | submission_qbb60v16_h2iso_julaugup050_only.csv   | Isolate whether the missing H2 signal is concentrated in Jul-Aug without touching Q4.         |        1.05 |        1.05 |      1     |                         22031.2 |                                0 |   11015.6  |                         1.00509  |                             1 |      0.897009 |        0.87628 |       0.993546 |       0.847066 | 1.35126e+08 |     1.00163 | 1.18408e+08 |     1.1586  | 1.12859e+08 |    0.965155 | 1.08578e+08 |    0.855832 | 8.34422e+07 |    0.907407 | 7.40929e+07 |     1.0571  |
|          3 | submission_qbb60v16_h2iso_julup050_q4down025.csv | If only July is undercalled while Q4 is high, this should outperform the broad Q3-up version. |        1.05 |        1    |      0.975 |                         23882.1 |                                0 |   11941.1  |                         0.999908 |                             1 |      0.901657 |        0.87628 |       1.01324  |       0.847066 | 1.35126e+08 |     1.00163 | 1.1277e+08  |     1.21653 | 1.12859e+08 |    0.965155 | 1.05863e+08 |    0.877777 | 8.13562e+07 |    0.930674 | 7.22406e+07 |     1.08421 |
|          4 | submission_qbb60v16_h2iso_augup050_q4down025.csv | If August is the real undercalled month, this should beat July-only and broad Q3-up.          |        1    |        1.05 |      0.975 |                         22429.4 |                                0 |   11214.7  |                         0.999572 |                             1 |      0.90196  |        0.87628 |       1.01454  |       0.847066 | 1.28692e+08 |     1.05171 | 1.18408e+08 |     1.1586  | 1.12859e+08 |    0.965155 | 1.05863e+08 |    0.877777 | 8.13562e+07 |    0.930674 | 7.22406e+07 |     1.08421 |
