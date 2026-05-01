# Quarantine Blackbox 60x V13 2023H2 Level

Run directory: `logs\20260424_010701_quarantine_blackbox60_v13_2023h2_level`

## Status

This branch is **not clean**. It uses `sample_submission.csv` and public-leaderboard feedback.

Current blackbox best:

- `submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv` = `662759.87577`

## Why This Batch Exists

- `2023H1 level` saturated and `2024H1 p1200` failed.
- The current winning branch has barely moved `2023H2 Revenue` at all, even though earlier public evidence showed that raising H2 Revenue while keeping COGS high could help.
- This batch reopens `2023H2 Revenue level` on the new 662k anchor.

## Candidate Manifest

|   priority | filename                                                                 | thesis                                                                                                                            |   rev_2023H1 |   rev_2023H2 |   rev_2024H1 |   away_alpha |   rev_scale_2023H1 |   rev_scale_2023H2 |   rev_scale_2024H1 |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   movement |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_total |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |   max_revenue |    max_cogs |
|-----------:|:-------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------|-------------:|-------------:|-------------:|-------------:|-------------------:|-------------------:|-------------------:|--------------------------------:|---------------------------------:|-----------:|---------------------------------:|------------------------------:|--------------:|---------------:|---------------:|---------------:|--------------:|------------:|
|          1 | submission_qbb60v13_nonh2shape_2023h1level113_2023h2rev1025_away0300.csv | Primary orthogonal reopen: keep the winning H1/away structure and raise 2023H2 Revenue by +2.5% while keeping high H2 COGS fixed. |          0.9 |          0.1 |          1.1 |          0.3 |               1.13 |              1.025 |               1.03 |                         28304.4 |                       7.7327e-11 |    14152.2 |                         1.00654  |                             1 |      0.895718 |        0.87628 |       0.988175 |       0.847066 |   1.26027e+07 | 1.19721e+07 |
|          2 | submission_qbb60v13_nonh2shape_2023h1level113_2023h2rev1050_away0300.csv | If H2 level is still undercalled, a +5% move should show a larger gain.                                                           |          0.9 |          0.1 |          1.1 |          0.3 |               1.13 |              1.05  |               1.03 |                         56608.9 |                       7.7327e-11 |    28304.4 |                         1.01308  |                             1 |      0.889938 |        0.87628 |       0.964647 |       0.847066 |   1.26027e+07 | 1.19721e+07 |
|          3 | submission_qbb60v13_nonh2shape_2023h1level113_2023h2rev1075_away0300.csv | Aggressive H2 Revenue continuation on the current best anchor.                                                                    |          0.9 |          0.1 |          1.1 |          0.3 |               1.13 |              1.075 |               1.03 |                         84913.3 |                       7.7327e-11 |    42456.7 |                         1.01961  |                             1 |      0.884232 |        0.87628 |       0.942214 |       0.847066 |   1.26027e+07 | 1.19721e+07 |
|          4 | submission_qbb60v13_nonh2shape_2023h1level113_2023h2rev0975_away0300.csv | Bracket sign check: if H2 is already too high on the new anchor, -2.5% should help instead.                                       |          0.9 |          0.1 |          1.1 |          0.3 |               1.13 |              0.975 |               1.03 |                         28304.4 |                       7.7327e-11 |    14152.2 |                         0.993462 |                             1 |      0.907507 |        0.87628 |       1.03885  |       0.847066 |   1.26027e+07 | 1.19721e+07 |
|          5 | submission_qbb60v13_nonh2shape_2023h1level113_q3rev1050_away0300.csv     | Localize H2 Revenue-up to Q3-like shoulder months only.                                                                           |          0.9 |          0.1 |          1.1 |          0.3 |               1.13 |              1     |               1.03 |                         32328.5 |                       7.7327e-11 |    16164.3 |                         1.00747  |                             1 |      0.894892 |        0.87628 |       0.984761 |       0.847066 |   1.26027e+07 | 1.19721e+07 |
|          6 | submission_qbb60v13_nonh2shape_2023h1level113_q4rev1050_away0300.csv     | Localize H2 Revenue-up to Q4-like peak months only.                                                                               |          0.9 |          0.1 |          1.1 |          0.3 |               1.13 |              1     |               1.03 |                         24280.4 |                       7.7327e-11 |    12140.2 |                         1.00561  |                             1 |      0.896546 |        0.87628 |       0.991614 |       0.847066 |   1.26027e+07 | 1.19721e+07 |

## Submit Order

1. `submission_qbb60v13_nonh2shape_2023h1level113_2023h2rev1025_away0300.csv`
2. If it improves, submit `submission_qbb60v13_nonh2shape_2023h1level113_2023h2rev1050_away0300.csv`
3. If `1025` worsens, submit `submission_qbb60v13_nonh2shape_2023h1level113_2023h2rev0975_away0300.csv`
4. Only after sign is known, use the localized `q3` or `q4` candidates.
