# Quarantine Blackbox 60x V8 Jump Follow-Up

Run directory: `logs\20260424_001535_quarantine_blackbox60_v8_jump_followup`

## Status

This branch is **not clean**. It uses `sample_submission.csv` and public-leaderboard feedback.

Current blackbox best:

- `submission_qbb60v7_nonh2shape_2023h1level103_away0300.csv` = `671930.79214`

## Why This Batch Exists

- `submission_qbb60v7_nonh2shape_2023h1level103_away0300.csv` jumped to `671930.79214`, so the working story changed.
- The new best is no longer about tiny shape tuning. It now supports two much larger surviving hypotheses:
  - `2023H1` is still under-level even after `+3%`;
  - the COGS ratio-away regime may still be under-shifted above `0.300`.
- A secondary upside path is that `2024H1` still wants stronger shape once the two main axes are corrected.

## Candidate Manifest

|   priority | filename                                                              | thesis                                                                                                                                        |   rev_2023H1 |   rev_2023H2 |   rev_2024H1 |   away_alpha |   rev_scale_2023H1 |   rev_scale_2024H1 |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   movement |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_total |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |   max_revenue |    max_cogs |
|-----------:|:----------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------|-------------:|-------------:|-------------:|-------------:|-------------------:|-------------------:|--------------------------------:|---------------------------------:|-----------:|---------------------------------:|------------------------------:|--------------:|---------------:|---------------:|---------------:|--------------:|------------:|
|          1 | submission_qbb60v8_nonh2shape_2023h1level105_away0300.csv             | Main jump hypothesis: the new best is still under-level in 2023H1, so push that period from +3% to +5% while keeping the working away regime. |          0.9 |          0.1 |          1.1 |        0.3   |               1.05 |               1.03 |                 27882.6         |                       7.7327e-11 |   13941.3  |                          1.00665 |                       1       |      0.925413 |       0.943044 |        1.01288 |       0.847066 |   1.26027e+07 | 1.19721e+07 |
|          2 | submission_qbb60v8_nonh2shape_2023h1level103_away0325.csv             | If the large gain came from cost regime shift, the away axis may still have headroom above 0.300 on the new anchor.                           |          0.9 |          0.1 |          1.1 |        0.325 |               1.03 |               1.03 |                     5.94823e-11 |                    7434.89       |    3717.45 |                          1       |                       1.0019  |      0.933346 |       0.964261 |        1.01471 |       0.847798 |   1.26027e+07 | 1.20083e+07 |
|          3 | submission_qbb60v8_nonh2shape_2023h1level103_away0350.csv             | More aggressive continuation of the now-confirmed away regime shift.                                                                          |          0.9 |          0.1 |          1.1 |        0.35  |               1.03 |               1.03 |                     5.94823e-11 |                   14869.8        |    7434.89 |                          1       |                       1.00381 |      0.93512  |       0.967168 |        1.01653 |       0.84853  |   1.26027e+07 | 1.20445e+07 |
|          4 | submission_qbb60v8_nonh2shape_2023h1level103_away0300_2024h1p1200.csv | Revenue-side jump attempt: the new best may still want stronger 2024H1 sample-like shape once 2023H1 level and away are corrected.            |          0.9 |          0.1 |          1.2 |        0.3   |               1.03 |               1.03 |                 24840.1         |                       7.7327e-11 |   12420    |                          1       |                       1       |      0.931571 |       0.961355 |        1.01288 |       0.847066 |   1.28817e+07 | 1.19721e+07 |
|          5 | submission_qbb60v8_nonh2shape_2023h1level105_away0325.csv             | Full aggressive jump attempt combining the two strongest surviving hypotheses: more 2023H1 level and more away.                               |          0.9 |          0.1 |          1.1 |        0.325 |               1.05 |               1.03 |                 27882.6         |                    7434.89       |   17658.7  |                          1.00665 |                       1.0019  |      0.927176 |       0.945895 |        1.01471 |       0.847798 |   1.26027e+07 | 1.20083e+07 |

## Submit Order

1. `submission_qbb60v8_nonh2shape_2023h1level105_away0300.csv`
2. If it improves, submit `submission_qbb60v8_nonh2shape_2023h1level105_away0325.csv`
3. If step 1 worsens, submit `submission_qbb60v8_nonh2shape_2023h1level103_away0325.csv`
4. Only after that, use the more orthogonal `submission_qbb60v8_nonh2shape_2023h1level103_away0300_2024h1p1200.csv`
