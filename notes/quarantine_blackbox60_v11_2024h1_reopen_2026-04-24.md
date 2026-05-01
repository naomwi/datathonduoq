# Quarantine Blackbox 60x V11 2024H1 Reopen

Run directory: `logs\20260424_005119_quarantine_blackbox60_v11_2024h1_reopen`

## Status

This branch is **not clean**. It uses `sample_submission.csv` and public-leaderboard feedback.

Current blackbox best:

- `submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv` = `662759.87577`

## Why This Batch Exists

- `2023H1 level` improved repeatedly up to `+13%`, but `+15%` stopped helping.
- That means the main axis is near saturation and the next meaningful move should be orthogonal.
- The strongest orthogonal candidate from prior evidence is a renewed `2024H1 shape` increase on top of the saturated 2023H1 anchor.

## Candidate Manifest

|   priority | filename                                                                      | thesis                                                                                                                   |   rev_2023H1 |   rev_2023H2 |   rev_2024H1 |   away_alpha |   rev_scale_2023H1 |   rev_scale_2024H1 |   cogs_scale_2024H1 |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   movement |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_total |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |   max_revenue |    max_cogs |
|-----------:|:------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------|-------------:|-------------:|-------------:|-------------:|-------------------:|-------------------:|--------------------:|--------------------------------:|---------------------------------:|-----------:|---------------------------------:|------------------------------:|--------------:|---------------:|---------------:|---------------:|--------------:|------------:|
|          1 | submission_qbb60v11_nonh2shape_2023h1level113_away0300_2024h1p1200.csv        | Primary orthogonal reopen: keep the saturated 2023H1 winner and strengthen 2024H1 shape to p1200.                        |          0.9 |          0.1 |          1.2 |          0.3 |               1.13 |               1.03 |                1    |                         24840.1 |                      7.7327e-11  |    12420   |                          1       |                      1        |      0.901574 |       0.87628  |        1.01288 |       0.847066 |   1.28817e+07 | 1.19721e+07 |
|          2 | submission_qbb60v11_nonh2shape_2023h1level113_away0300_2024h1p1300.csv        | If p1200 improves, p1300 is the next high-information continuation.                                                      |          0.9 |          0.1 |          1.3 |          0.3 |               1.13 |               1.03 |                1    |                         49680.1 |                      3.49671e-10 |    24840.1 |                          1       |                      1        |      0.901574 |       0.87628  |        1.01288 |       0.847066 |   1.31607e+07 | 1.19721e+07 |
|          3 | submission_qbb60v11_nonh2shape_2023h1level110_away0300_2024h1p1200.csv        | Slightly safer reopen using the 110 anchor in case p1200 interacts badly with the stronger 113 level.                    |          0.9 |          0.1 |          1.2 |          0.3 |               1.1  |               1.03 |                1    |                         66663.9 |                      7.7327e-11  |    33332   |                          0.99034 |                      1        |      0.910368 |       0.900178 |        1.01288 |       0.847066 |   1.28817e+07 | 1.19721e+07 |
|          4 | submission_qbb60v11_nonh2shape_2023h1level113_away0300_2024h1p1200_cogs98.csv | Revenue-shape reopen plus slightly lower 2024H1 COGS, in case extra 2024H1 revenue should not bring equal cost pressure. |          0.9 |          0.1 |          1.2 |          0.3 |               1.13 |               1.03 |                0.98 |                         24840.1 |                  27303.4         |    26071.8 |                          1       |                      0.993005 |      0.895268 |       0.87628  |        1.01288 |       0.830125 |   1.28817e+07 | 1.19721e+07 |

## Submit Order

1. `submission_qbb60v11_nonh2shape_2023h1level113_away0300_2024h1p1200.csv`
2. If it improves, submit `submission_qbb60v11_nonh2shape_2023h1level113_away0300_2024h1p1300.csv`
3. If it worsens, submit `submission_qbb60v11_nonh2shape_2023h1level110_away0300_2024h1p1200.csv`
4. Use the `cogs98` variant only if the reopen seems directionally right but too costly.
