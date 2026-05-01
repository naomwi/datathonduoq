# Quarantine Blackbox 60x V14 2023H2 Down Follow-Up

Run directory: `logs\20260424_011059_quarantine_blackbox60_v14_2023h2_down_followup`

## Status

This branch is **not clean**. It uses `sample_submission.csv` and public-leaderboard feedback.

Current anchor:

- `submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv` = `662759.87577`

## Why This Batch Exists

- `2023H2 +2.5%` worsened, so the next step is to bracket the opposite sign.
- If `2023H2 -2.5%` improves, the follow-up should not wait; we need immediate stronger and localized H2-down candidates.

## Candidate Manifest

|   priority | filename                                                                 | thesis                                                                                                           |   rev_2023H1 |   rev_2023H2 |   rev_2024H1 |   away_alpha |   rev_scale_2023H1 |   rev_scale_2023H2 |   rev_scale_2024H1 |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   movement |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_total |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |
|-----------:|:-------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------|-------------:|-------------:|-------------:|-------------:|-------------------:|-------------------:|-------------------:|--------------------------------:|---------------------------------:|-----------:|---------------------------------:|------------------------------:|--------------:|---------------:|---------------:|---------------:|
|          1 | submission_qbb60v14_nonh2shape_2023h1level113_2023h2rev0950_away0300.csv | If -2.5% helps, continue the H2-down sign to -5% on the same anchor.                                             |          0.9 |          0.1 |          1.1 |        0.3   |               1.13 |               0.95 |               1.03 |                         56608.9 |                       7.7327e-11 |   28304.4  |                         0.986925 |                      1        |      0.913518 |       0.87628  |        1.06619 |       0.847066 |
|          2 | submission_qbb60v14_nonh2shape_2023h1level113_q3rev0975_away0300.csv     | Localize the H2-down sign to Q3/shoulder months only.                                                            |          0.9 |          0.1 |          1.1 |        0.3   |               1.13 |               1    |               1.03 |                         16164.3 |                       7.7327e-11 |    8082.13 |                         0.996266 |                      1        |      0.904953 |       0.87628  |        1.02755 |       0.847066 |
|          3 | submission_qbb60v14_nonh2shape_2023h1level113_q4rev0975_away0300.csv     | Localize the H2-down sign to Q4/peak months only.                                                                |          0.9 |          0.1 |          1.1 |        0.3   |               1.13 |               1    |               1.03 |                         12140.2 |                       7.7327e-11 |    6070.09 |                         0.997196 |                      1        |      0.904109 |       0.87628  |        1.02386 |       0.847066 |
|          4 | submission_qbb60v14_nonh2shape_2023h1level113_2023h2rev0950_away0275.csv | Combine H2-down with a slightly softer away, in case part of the H2 excess came from global cost-ratio pressure. |          0.9 |          0.1 |          1.1 |        0.275 |               1.13 |               0.95 |               1.03 |                         56608.9 |                    7434.89       |   32021.9  |                         0.986925 |                      0.998095 |      0.911778 |       0.873631 |        1.06427 |       0.846334 |
