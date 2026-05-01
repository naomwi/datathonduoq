# Quarantine Blackbox 60x V10 Level Push

Run directory: `logs\20260424_004636_quarantine_blackbox60_v10_level_push`

## Status

This branch is **not clean**. It uses `sample_submission.csv` and public-leaderboard feedback.

Current blackbox best:

- `submission_qbb60v9_nonh2shape_2023h1level110_away0300.csv` = `663346.24664`

## Why This Batch Exists

- `submission_qbb60v9_nonh2shape_2023h1level110_away0300.csv` improved again to `663346.24664`.
- This means the main positive axis still has momentum: `2023H1 level`.
- The next question is not whether this axis is real; it is whether it saturates around `+13%` or keeps going toward `+15%`.
- A secondary backup is that `2024H1` may still have a residual shape gain once the stronger 2023H1 level is in place.

## Candidate Manifest

|   priority | filename                                                               | thesis                                                                                                       |   rev_2023H1 |   rev_2023H2 |   rev_2024H1 |   away_alpha |   rev_scale_2023H1 |   rev_scale_2024H1 |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   movement |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_total |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |   max_revenue |    max_cogs |
|-----------:|:-----------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------------|-------------:|-------------:|-------------:|-------------:|-------------------:|-------------------:|--------------------------------:|---------------------------------:|-----------:|---------------------------------:|------------------------------:|--------------:|---------------:|---------------:|---------------:|--------------:|------------:|
|          1 | submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv             | Continue the proven 2023H1 level axis from +10% to +13% while holding away at the working peak.              |          0.9 |          0.1 |          1.1 |        0.3   |               1.13 |               1.03 |                         41823.9 |                       7.7327e-11 |    20911.9 |                          1.00975 |                        1      |      0.901574 |       0.87628  |        1.01288 |       0.847066 |   1.26027e+07 | 1.19721e+07 |
|          2 | submission_qbb60v10_nonh2shape_2023h1level115_away0300.csv             | High-variance continuation of the 2023H1 level axis to +15%.                                                 |          0.9 |          0.1 |          1.1 |        0.3   |               1.15 |               1.03 |                         69706.4 |                       7.7327e-11 |    34853.2 |                          1.01626 |                        1      |      0.895805 |       0.86104  |        1.01288 |       0.847066 |   1.26027e+07 | 1.19721e+07 |
|          3 | submission_qbb60v10_nonh2shape_2023h1level113_away0300_2024h1p1200.csv | Orthogonal backup: if 2023H1 level still helps but pure level starts to flatten, add stronger 2024H1 shape.  |          0.9 |          0.1 |          1.2 |        0.3   |               1.13 |               1.03 |                         66663.9 |                       7.7327e-11 |    33332   |                          1.00975 |                        1      |      0.901574 |       0.87628  |        1.01288 |       0.847066 |   1.28817e+07 | 1.19721e+07 |
|          4 | submission_qbb60v10_nonh2shape_2023h1level110_away0300_2024h1p1200.csv | Check whether the new 663k anchor still has a remaining 2024H1 shape gain without further 2023H1 escalation. |          0.9 |          0.1 |          1.2 |        0.3   |               1.1  |               1.03 |                         24840.1 |                       7.7327e-11 |    12420   |                          1       |                        1      |      0.910368 |       0.900178 |        1.01288 |       0.847066 |   1.28817e+07 | 1.19721e+07 |
|          5 | submission_qbb60v10_nonh2shape_2023h1level113_away0325.csv             | Aggressive combo only if both level continuation and slight away continuation are still aligned.             |          0.9 |          0.1 |          1.1 |        0.325 |               1.13 |               1.03 |                         41823.9 |                    7434.89       |    24629.4 |                          1.00975 |                        1.0019 |      0.903291 |       0.878929 |        1.01471 |       0.847798 |   1.26027e+07 | 1.20083e+07 |

## Submit Order

1. `submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv`
2. If it improves, submit `submission_qbb60v10_nonh2shape_2023h1level115_away0300.csv`
3. If `113` worsens, submit `submission_qbb60v10_nonh2shape_2023h1level113_away0300_2024h1p1200.csv`
4. Only after that, use `submission_qbb60v10_nonh2shape_2023h1level110_away0300_2024h1p1200.csv`
