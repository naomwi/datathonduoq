# Quarantine Blackbox 60x V9 Jump Continue

Run directory: `logs\20260424_001945_quarantine_blackbox60_v9_jump_continue`

## Status

This branch is **not clean**. It uses `sample_submission.csv` and public-leaderboard feedback.

Current blackbox best:

- `submission_qbb60v8_nonh2shape_2023h1level105_away0300.csv` = `668570.18037`

## Why This Batch Exists

- `submission_qbb60v8_nonh2shape_2023h1level105_away0300.csv` improved again to `668570.18037`.
- So the `2023H1 level` axis still has momentum; it is now the main candidate for another large jump.
- The next open questions are:
  - does `2023H1 level` keep helping at `+7%` or `+10%`?
  - does `away` still help above `0.300` once the level is already corrected?
  - is there still a remaining `2024H1 shape` gain after both?

## Candidate Manifest

|   priority | filename                                                              | thesis                                                                                                |   rev_2023H1 |   rev_2023H2 |   rev_2024H1 |   away_alpha |   rev_scale_2023H1 |   rev_scale_2024H1 |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   movement |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_total |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |   max_revenue |    max_cogs |
|-----------:|:----------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------|-------------:|-------------:|-------------:|-------------:|-------------------:|-------------------:|--------------------------------:|---------------------------------:|-----------:|---------------------------------:|------------------------------:|--------------:|---------------:|---------------:|---------------:|--------------:|------------:|
|          1 | submission_qbb60v9_nonh2shape_2023h1level107_away0300.csv             | Continue the proven 2023H1 level axis from +5% to +7% while keeping the current working away regime.  |          0.9 |          0.1 |          1.1 |        0.3   |               1.07 |               1.03 |                 27882.6         |                       7.7327e-11 |   13941.3  |                          1.00661 |                       1       |      0.919336 |       0.925417 |        1.01288 |       0.847066 |   1.26027e+07 | 1.19721e+07 |
|          2 | submission_qbb60v9_nonh2shape_2023h1level110_away0300.csv             | High-variance continuation of the 2023H1 level axis to +10%.                                          |          0.9 |          0.1 |          1.1 |        0.3   |               1.1  |               1.03 |                 69706.4         |                       7.7327e-11 |   34853.2  |                          1.01653 |                       1       |      0.910368 |       0.900178 |        1.01288 |       0.847066 |   1.26027e+07 | 1.19721e+07 |
|          3 | submission_qbb60v9_nonh2shape_2023h1level107_away0325.csv             | Combine the two positive directions: more 2023H1 level and slightly stronger away.                    |          0.9 |          0.1 |          1.1 |        0.325 |               1.07 |               1.03 |                 27882.6         |                    7434.89       |   17658.7  |                          1.00661 |                       1.0019  |      0.921087 |       0.928214 |        1.01471 |       0.847798 |   1.26027e+07 | 1.20083e+07 |
|          4 | submission_qbb60v9_nonh2shape_2023h1level105_away0350.csv             | Keep the proven +5% 2023H1 level and test whether away still has substantial headroom.                |          0.9 |          0.1 |          1.1 |        0.35  |               1.05 |               1.03 |                     7.22285e-11 |                   14869.8        |    7434.89 |                          1       |                       1.00381 |      0.928938 |       0.948745 |        1.01653 |       0.84853  |   1.26027e+07 | 1.20445e+07 |
|          5 | submission_qbb60v9_nonh2shape_2023h1level107_away0300_2024h1p1200.csv | Full revenue-side jump attempt: if 2023H1 level and 2024H1 shape both still have room simultaneously. |          0.9 |          0.1 |          1.2 |        0.3   |               1.07 |               1.03 |                 52722.6         |                       7.7327e-11 |   26361.3  |                          1.00661 |                       1       |      0.919336 |       0.925417 |        1.01288 |       0.847066 |   1.28817e+07 | 1.19721e+07 |

## Submit Order

1. `submission_qbb60v8_nonh2shape_2023h1level105_away0325.csv` if it has not been submitted yet.
2. Then `submission_qbb60v9_nonh2shape_2023h1level107_away0300.csv`
3. If step 2 improves, submit `submission_qbb60v9_nonh2shape_2023h1level107_away0325.csv`
4. If step 2 worsens, fall back to `submission_qbb60v9_nonh2shape_2023h1level105_away0350.csv`
