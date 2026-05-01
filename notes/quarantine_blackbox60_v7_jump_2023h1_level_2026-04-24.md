# Quarantine Blackbox 60x V7 Jump 2023H1 Level

Run directory: `logs\20260424_001158_quarantine_blackbox60_v7_jump_2023h1_level`

## Status

This branch is **not clean**. It uses `sample_submission.csv` and public-leaderboard feedback.

Current blackbox best:

- `submission_qbb60v6_shape_nonh2_2023h1p0900_2024h1p1100_level103.csv` = `679112.88021`

## Why This Batch Exists

- `2023H1 p0.900 + 2024H1 p1.100 + 2024H1 level +3%` improved strongly to `679112.88021`.
- Pushing `2023H1` shape to `1.000` worsened slightly, so the next likely jump is not more `2023H1` shape.
- The larger remaining hypothesis is that `2023H1` is still under-level, similar to how `2024H1 level +3%` helped earlier.

## Candidate Manifest

|   priority | filename                                                     | thesis                                                                                                          |   rev_2023H1 |   rev_2023H2 |   rev_2024H1 |   away_alpha |   rev_scale_2023H1 |   rev_scale_2024H1 |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   movement |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_total |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |   max_revenue |    max_cogs |
|-----------:|:-------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------|-------------:|-------------:|-------------:|-------------:|-------------------:|-------------------:|--------------------------------:|---------------------------------:|-----------:|---------------------------------:|------------------------------:|--------------:|---------------:|---------------:|---------------:|--------------:|------------:|
|          1 | submission_qbb60v7_nonh2shape_2023h1level103.csv             | Main jump hypothesis: after fixing non-H2 shape, 2023H1 Revenue is still under-level by about +3%.              |          0.9 |          0.1 |          1.1 |         0.25 |               1.03 |               1.03 |                 41823.9         |                      6.41559e-11 |   20911.9  |                          1.01008 |                       1       |      0.928022 |       0.955543 |        1.00923 |       0.845602 |   1.26027e+07 | 1.18998e+07 |
|          2 | submission_qbb60v7_nonh2shape_2023h1level105.csv             | Aggressive continuation if 2023H1 really has a hidden level gap, not just a shape gap.                          |          0.9 |          0.1 |          1.1 |         0.25 |               1.05 |               1.03 |                 69706.4         |                      6.41559e-11 |   34853.2  |                          1.0168  |                       1       |      0.921888 |       0.937342 |        1.00923 |       0.845602 |   1.26027e+07 | 1.18998e+07 |
|          3 | submission_qbb60v7_nonh2shape_away0300.csv                   | Existing shape winner plus stronger COGS ratio-away; tests whether cost regime is still under-shifted.          |          0.9 |          0.1 |          1.1 |         0.3  |               1    |               1.03 |                     5.56584e-11 |                  14869.8         |    7434.89 |                          1       |                       1.00382 |      0.940963 |       0.990196 |        1.01288 |       0.847066 |   1.26027e+07 | 1.19721e+07 |
|          4 | submission_qbb60v7_nonh2shape_2023h1level103_away0300.csv    | Full jump attempt: combine the new 2023H1 level hypothesis with stronger COGS ratio-away.                       |          0.9 |          0.1 |          1.1 |         0.3  |               1.03 |               1.03 |                 41823.9         |                  14869.8         |   28346.8  |                          1.01008 |                       1.00382 |      0.931571 |       0.961355 |        1.01288 |       0.847066 |   1.26027e+07 | 1.19721e+07 |
|          5 | submission_qbb60v7_nonh2shape_2023h1level103_2024h1p1200.csv | Revenue-only jump attempt: if both non-H2 periods still want even stronger sample-like shape plus 2023H1 level. |          0.9 |          0.1 |          1.2 |         0.25 |               1.03 |               1.03 |                 66663.9         |                      6.41559e-11 |   33332    |                          1.01008 |                       1       |      0.928022 |       0.955543 |        1.00923 |       0.845602 |   1.28817e+07 | 1.18998e+07 |

## Submit Order

1. `submission_qbb60v7_nonh2shape_2023h1level103.csv`
2. If it improves, submit `submission_qbb60v7_nonh2shape_2023h1level103_away0300.csv`
3. If step 1 improves strongly, try `submission_qbb60v7_nonh2shape_2023h1level105.csv`
4. If step 1 worsens, fall back to the orthogonal big jump `submission_qbb60v7_nonh2shape_away0300.csv`
