# Quarantine Blackbox 60x V3 Anchor 682

Run directory: `logs\20260423_122429_quarantine_blackbox60_v3_anchor682`

## Status

This is **not clean**. It reads `sample_submission.csv` and uses public-leaderboard feedback. Do not include it in a final legal source package.

Current true blackbox best:

- `submission_sample_v40_h2p0100_2024h1p1000_2024h1p1000_c0650_away0250.csv` = `682039.2831`

Important correction:

- This file is identical to `submission_qbb60v2_rev2024h1_p1000.csv`.
- Therefore all follow-ups must be anchored on `2024H1 Revenue alpha = 1.000`, not the older `0.800`.

## Candidate Manifest

|   priority | filename                                           | thesis                                                                   |   rev_2023H1 |   rev_2023H2 |   rev_2024H1 |   cogs_2023H1 |   cogs_2023H2 |   cogs_2024H1 |   away_alpha |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   movement |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_total |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |
|-----------:|:---------------------------------------------------|:-------------------------------------------------------------------------|-------------:|-------------:|-------------:|--------------:|--------------:|--------------:|-------------:|--------------------------------:|---------------------------------:|-----------:|---------------------------------:|------------------------------:|--------------:|---------------:|---------------:|---------------:|
|          1 | submission_qbb60v3_2024h1p1100.csv                 | Continue 2024H1 Revenue-shape direction beyond current p1000.            |          0.8 |          0.1 |          1.1 |          0.65 |          0.65 |          0.65 |         0.25 |                  24116.6        |                      6.41559e-11 |   12058.3  |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|          2 | submission_qbb60v3_2024h1p1200.csv                 | Larger 2024H1 Revenue-shape extrapolation.                               |          0.8 |          0.1 |          1.2 |          0.65 |          0.65 |          0.65 |         0.25 |                  48233.1        |                      6.41559e-11 |   24116.6  |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|          3 | submission_qbb60v3_2024h1p0900.csv                 | Check if optimum is below current p1000.                                 |          0.8 |          0.1 |          0.9 |          0.65 |          0.65 |          0.65 |         0.25 |                  24116.6        |                      6.41559e-11 |   12058.3  |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|          4 | submission_qbb60v3_2023h1p0900_2024h1p1000.csv     | Add modest 2023H1 Revenue-shape strength on top of current best.         |          0.9 |          0.1 |          1   |          0.65 |          0.65 |          0.65 |         0.25 |                  18805.5        |                      6.41559e-11 |    9402.77 |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|          5 | submission_qbb60v3_2023h1p1000_2024h1p1000.csv     | Add full 2023H1 Revenue-shape strength on top of current best.           |          1   |          0.1 |          1   |          0.65 |          0.65 |          0.65 |         0.25 |                  37611.1        |                      6.41559e-11 |   18805.5  |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|          6 | submission_qbb60v3_2023h1p0700_2024h1p1000.csv     | Opposite 2023H1 Revenue-shape direction on top of current best.          |          0.7 |          0.1 |          1   |          0.65 |          0.65 |          0.65 |         0.25 |                  18805.5        |                      6.41559e-11 |    9402.77 |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|          7 | submission_qbb60v3_cogs2024h1_c0500.csv            | COGS 2024H1 sample-shape down on top of current best.                    |          0.8 |          0.1 |          1   |          0.65 |          0.65 |          0.5  |         0.25 |                      6.3731e-11 |                  27724.2         |   13862.1  |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|          8 | submission_qbb60v3_cogs2024h1_c0800.csv            | COGS 2024H1 sample-shape up on top of current best.                      |          0.8 |          0.1 |          1   |          0.65 |          0.65 |          0.8  |         0.25 |                      6.3731e-11 |                  27724.2         |   13862.1  |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|          9 | submission_qbb60v3_cogsall_c0600.csv               | Global COGS-shape down re-tested on the true 682k anchor.                |          0.8 |          0.1 |          1   |          0.6  |          0.6  |          0.6  |         0.25 |                      6.3731e-11 |                  24928.7         |   12464.4  |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|         10 | submission_qbb60v3_away0300.csv                    | COGS ratio-away stronger on top of current best.                         |          0.8 |          0.1 |          1   |          0.65 |          0.65 |          0.65 |         0.3  |                      6.3731e-11 |                  14869.8         |    7434.89 |                                1 |                      1.00382  |      0.951733 |       0.990196 |        1.01288 |       0.872478 |
|         11 | submission_qbb60v3_away0200.csv                    | COGS ratio-away softer on top of current best.                           |          0.8 |          0.1 |          1   |          0.65 |          0.65 |          0.65 |         0.2  |                      6.3731e-11 |                  14869.8         |    7434.89 |                                1 |                      0.996176 |      0.944482 |       0.978223 |        1.00558 |       0.869462 |
|         12 | submission_qbb60v3_2024h1p1100_cogs2024h1c0500.csv | Combined continuation: 2024H1 Revenue p1100 plus 2024H1 COGS-shape down. |          0.8 |          0.1 |          1.1 |          0.65 |          0.65 |          0.5  |         0.25 |                  24116.6        |                  27724.2         |   25920.4  |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |

## Submit Order

1. `submission_qbb60v3_2024h1p1100.csv`
2. If p1100 improves, submit `submission_qbb60v3_2024h1p1200.csv`
3. If p1100 worsens, submit `submission_qbb60v3_2024h1p0900.csv`
4. If 2024H1 is flat, test `submission_qbb60v3_2023h1p0900_2024h1p1000.csv`
5. If Revenue shape stalls, test COGS on true anchor: `submission_qbb60v3_cogs2024h1_c0500.csv`
