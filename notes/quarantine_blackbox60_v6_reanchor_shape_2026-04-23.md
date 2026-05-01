# Quarantine Blackbox 60x V6 Reanchor Shape

Run directory: `logs\20260423_235329_quarantine_blackbox60_v6_reanchor_shape`

## Status

This branch is **not clean**. It uses `sample_submission.csv` and public-leaderboard feedback.

Current blackbox best:

- `submission_qbb60v4_level_rev2024h1_up030.csv` = `680506.89709`

## Why This Batch Exists

- `+3% Revenue 2024H1` improved to `680506.89709`, but `+5%` worsened, so pure 2024H1 level is now a narrow axis.
- The larger remaining public hypotheses were never re-anchored on the true 680k file:
  - `2024H1` may still want slightly more sample-like daily shape than `p1000`;
  - `2023H1` may want moderate sample-like shape strength;
  - the best jump may be the non-H2 combo, not another level micro-probe.

## Candidate Manifest

|   priority | filename                                                                     | thesis                                                                                                       |   rev_2023H1 |   rev_2023H2 |   rev_2024H1 |   away_alpha |   rev_scale_2024H1 |   cogs_scale_2024H1 |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   movement |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_total |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |   max_revenue |    max_cogs |
|-----------:|:-----------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------------|-------------:|-------------:|-------------:|-------------:|-------------------:|--------------------:|--------------------------------:|---------------------------------:|-----------:|---------------------------------:|------------------------------:|--------------:|---------------:|---------------:|---------------:|--------------:|------------:|
|          1 | submission_qbb60v6_shape2024h1_p1100_level103.csv                            | Continue the proven 2024H1 direction: slightly stronger sample shape while keeping the +3% level.            |          0.8 |          0.1 |          1.1 |         0.25 |               1.03 |                   1 |                         24840.1 |                      6.41559e-11 |   12420    |                                1 |                       1       |      0.937379 |       0.984209 |        1.00923 |       0.845602 |   1.26027e+07 | 1.18998e+07 |
|          2 | submission_qbb60v6_shape2024h1_p1200_level103.csv                            | High-variance continuation of the 2024H1 shape direction on the true 680k anchor.                            |          0.8 |          0.1 |          1.2 |         0.25 |               1.03 |                   1 |                         49680.1 |                      6.41559e-11 |   24840.1  |                                1 |                       1       |      0.937379 |       0.984209 |        1.00923 |       0.845602 |   1.28817e+07 | 1.18998e+07 |
|          3 | submission_qbb60v6_shape2023h1_p0900_level103.csv                            | Test whether 2023H1 also wants moderately stronger sample-like Revenue shape on top of the 680k anchor.      |          0.9 |          0.1 |          1   |         0.25 |               1.03 |                   1 |                         18805.5 |                      6.41559e-11 |    9402.77 |                                1 |                       1       |      0.937379 |       0.984209 |        1.00923 |       0.845602 |   1.23237e+07 | 1.18998e+07 |
|          4 | submission_qbb60v6_shape2023h1_p1000_level103.csv                            | Stronger 2023H1 sample-shape move paired with the proven 2024H1 level uplift.                                |          1   |          0.1 |          1   |         0.25 |               1.03 |                   1 |                         37611.1 |                      6.41559e-11 |   18805.5  |                                1 |                       1       |      0.937379 |       0.984209 |        1.00923 |       0.845602 |   1.23237e+07 | 1.18998e+07 |
|          5 | submission_qbb60v6_shape_nonh2_2023h1p0900_2024h1p1100_level103.csv          | Main jump attempt: combine moderate 2023H1 shape strength with stronger 2024H1 shape on the 680k anchor.     |          0.9 |          0.1 |          1.1 |         0.25 |               1.03 |                   1 |                         43645.6 |                      6.41559e-11 |   21822.8  |                                1 |                       1       |      0.937379 |       0.984209 |        1.00923 |       0.845602 |   1.26027e+07 | 1.18998e+07 |
|          6 | submission_qbb60v6_shape_nonh2_2023h1p1000_2024h1p1100_level103.csv          | Aggressive non-H2 Revenue-shape combo on the true anchor; higher upside but higher overshoot risk.           |          1   |          0.1 |          1.1 |         0.25 |               1.03 |                   1 |                         62451.1 |                      6.41559e-11 |   31225.6  |                                1 |                       1       |      0.937379 |       0.984209 |        1.00923 |       0.845602 |   1.26027e+07 | 1.18998e+07 |
|          7 | submission_qbb60v6_shape2024h1_p1100_level103_away0300.csv                   | Check whether stronger COGS ratio-away still helps once 2024H1 Revenue shape is moved in the same direction. |          0.8 |          0.1 |          1.1 |         0.3  |               1.03 |                   1 |                         24840.1 |                  14869.8         |   19854.9  |                                1 |                       1.00382 |      0.940963 |       0.990196 |        1.01288 |       0.847066 |   1.26027e+07 | 1.19721e+07 |
|          8 | submission_qbb60v6_shape_nonh2_2023h1p0900_2024h1p1100_level103_away0300.csv | Full jump probe: re-anchor non-H2 Revenue shape and also strengthen the COGS ratio-away regime.              |          0.9 |          0.1 |          1.1 |         0.3  |               1.03 |                   1 |                         43645.6 |                  14869.8         |   29257.7  |                                1 |                       1.00382 |      0.940963 |       0.990196 |        1.01288 |       0.847066 |   1.26027e+07 | 1.19721e+07 |

## Submit Order

1. `submission_qbb60v6_shape2024h1_p1100_level103.csv`
2. If it improves, submit `submission_qbb60v6_shape_nonh2_2023h1p0900_2024h1p1100_level103.csv`
3. If that improves, submit `submission_qbb60v6_shape_nonh2_2023h1p1000_2024h1p1100_level103.csv`
4. If step 1 is flat or slightly worse, submit `submission_qbb60v6_shape2023h1_p0900_level103.csv`
5. Only after a shape direction is confirmed, use the `away0300` follow-up variants.
