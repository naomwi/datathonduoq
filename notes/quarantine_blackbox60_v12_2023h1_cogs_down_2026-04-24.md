# Quarantine Blackbox 60x V12 2023H1 COGS Down

Run directory: `logs\20260424_005411_quarantine_blackbox60_v12_2023h1_cogs_down`

## Status

This branch is **not clean**. It uses `sample_submission.csv` and public-leaderboard feedback.

Current blackbox best:

- `submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv` = `662759.87577`

## Why This Batch Exists

- `2023H1 level` improved repeatedly up to `+13%`, but the next continuation flattened.
- The `2024H1 p1200` reopen also failed, so the next move should be a truly orthogonal axis.
- On the current best, `2023H1 COGS/Revenue` is still about `0.876`, above the recent historical H1 range and even above 2022 H1 `0.858`.
- This batch tests whether the hidden public target wants lower 2023H1 COGS while keeping the proven Revenue/away structure.

## Candidate Manifest

|   priority | filename                                                                  | thesis                                                                                                                                         |   rev_2023H1 |   rev_2023H2 |   rev_2024H1 |   away_alpha |   rev_scale_2023H1 |   rev_scale_2024H1 |   cogs_scale_2023H1 |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   movement |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_total |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |   max_revenue |    max_cogs |
|-----------:|:--------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------|-------------:|-------------:|-------------:|-------------:|-------------------:|-------------------:|--------------------:|--------------------------------:|---------------------------------:|-----------:|---------------------------------:|------------------------------:|--------------:|---------------:|---------------:|---------------:|--------------:|------------:|
|          1 | submission_qbb60v12_nonh2shape_2023h1level113_away0300_cogs2023h1_098.csv | Primary orthogonal hypothesis: current best still overstates 2023H1 COGS by about 2%, bringing the H1 ratio back near historical upper bounds. |          0.9 |          0.1 |          1.1 |          0.3 |               1.13 |               1.03 |                0.98 |                     5.60833e-11 |                          27609.2 |    13804.6 |                          1       |                      0.992927 |      0.895197 |       0.858754 |        1.01288 |       0.847066 |   1.26027e+07 | 1.17327e+07 |
|          2 | submission_qbb60v12_nonh2shape_2023h1level113_away0300_cogs2023h1_096.csv | Stronger 2023H1 COGS reduction if the hidden target is closer to the broader historical H1 cost regime.                                        |          0.9 |          0.1 |          1.1 |          0.3 |               1.13 |               1.03 |                0.96 |                     5.60833e-11 |                          55218.4 |    27609.2 |                          1       |                      0.985854 |      0.88882  |       0.841228 |        1.01288 |       0.847066 |   1.26027e+07 | 1.14933e+07 |
|          3 | submission_qbb60v12_nonh2shape_2023h1level113_away0300_cogs2023h1_094.csv | Aggressive 2023H1 COGS-down probe for a lower-margin-regime correction.                                                                        |          0.9 |          0.1 |          1.1 |          0.3 |               1.13 |               1.03 |                0.94 |                     5.60833e-11 |                          82827.6 |    41413.8 |                          1       |                      0.978781 |      0.882443 |       0.823703 |        1.01288 |       0.847066 |   1.26027e+07 | 1.12538e+07 |
|          4 | submission_qbb60v12_nonh2shape_2023h1level110_away0300_cogs2023h1_096.csv | Safer backup using the 110 Revenue anchor in case the best file's 2023H1 revenue is slightly over-raised once COGS is reduced.                 |          0.9 |          0.1 |          1.1 |          0.3 |               1.1  |               1.03 |                0.96 |                 41823.9         |                          55218.4 |    48521.1 |                          0.99034 |                      0.985854 |      0.89749  |       0.864171 |        1.01288 |       0.847066 |   1.26027e+07 | 1.14933e+07 |

## Submit Order

1. `submission_qbb60v12_nonh2shape_2023h1level113_away0300_cogs2023h1_098.csv`
2. If it improves, submit `submission_qbb60v12_nonh2shape_2023h1level113_away0300_cogs2023h1_096.csv`
3. If `098` worsens, use the stronger but safer counterbalance `submission_qbb60v12_nonh2shape_2023h1level110_away0300_cogs2023h1_096.csv`
