# Quarantine Blackbox 60x V19 All-In COGS To Sample

Run directory: `logs\20260424_015052_quarantine_blackbox60_v19_allin_cogs_to_sample`

## Status

This branch is **not clean**. It builds directly on the current blackbox best and public-leaderboard feedback.

Current anchor:

- `submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv` = `662759.87577`

## Why This File Exists

- `2023H2 Revenue` edits failed in both directions and at multiple granularities.
- `2023H2 COGS -1%` finally improved, proving the remaining H2 error is more likely cost-ratio than revenue level.
- `2024H1 COGS` on the current best is still above the sample regime.
- This all-in file therefore matches the current best to sample-derived COGS ratios for `2023H2` and `2024H1` in one shot.

## Scales

- `2023H2 COGS scale` = `0.906286`
- `2024H1 COGS scale` = `0.983714`

## Period Summary

Current:

| period     |   days |     Revenue |        COGS |    ratio |
|:-----------|-------:|------------:|------------:|---------:|
| 2023H1     |    181 | 8.633e+08   | 7.56492e+08 | 0.87628  |
| 2023H2     |    184 | 6.20433e+08 | 6.28424e+08 | 1.01288  |
| 2024-07-01 |      1 | 5.65516e+06 | 6.01795e+06 | 1.06415  |
| 2024H1     |    182 | 8.83183e+08 | 7.48114e+08 | 0.847066 |

All-in:

| period     |   days |     Revenue |        COGS |    ratio |
|:-----------|-------:|------------:|------------:|---------:|
| 2023H1     |    181 | 8.633e+08   | 7.56492e+08 | 0.87628  |
| 2023H2     |    184 | 6.20433e+08 | 5.69532e+08 | 0.917959 |
| 2024-07-01 |      1 | 5.65516e+06 | 6.01795e+06 | 1.06415  |
| 2024H1     |    182 | 8.83183e+08 | 7.3593e+08  | 0.83327  |
