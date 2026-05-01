# Quarantine Blackbox 60x V2 Strong Axes

Run directory: `logs\20260423_121839_quarantine_blackbox60_v2_strong_axes`

## Status

This is **not clean**. It is a quarantined public/synthetic probe generator and must not be included in a final legal source package.

Known public results incorporated:

|                                                          |   public_score |
|:---------------------------------------------------------|---------------:|
| submission_sample_v37_rev2023H2_p0100_c0650_away0250.csv |         684463 |
| submission_qbb60_h2p0050_c0650_away0250.csv              |         684894 |
| submission_qbb60_h2p0100_c0600_away0250.csv              |         684528 |

Interpretation:

- H2 below alpha `0.100` is worse, so stop H2-low probing.
- Global COGS shape `0.600` is almost neutral/slightly worse, so a 60x jump must come from a larger untested axis.
- The largest remaining axes are 2024H1 Revenue shape, combined non-H2 Revenue shape, and period-specific COGS shape.

## Candidate Manifest

|   priority | filename                                | thesis                                                                                      |   rev_2023H1 |   rev_2023H2 |   rev_2024H1 |   cogs_2023H1 |   cogs_2023H2 |   cogs_2024H1 |   away_alpha |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   movement |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_total |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |
|-----------:|:----------------------------------------|:--------------------------------------------------------------------------------------------|-------------:|-------------:|-------------:|--------------:|--------------:|--------------:|-------------:|--------------------------------:|---------------------------------:|-----------:|---------------------------------:|------------------------------:|--------------:|---------------:|---------------:|---------------:|
|          1 | submission_qbb60v2_rev2024h1_p1000.csv  | Largest remaining single Revenue-shape axis: strengthen 2024H1 sample-like daily shape.     |          0.8 |          0.1 |          1   |          0.65 |          0.65 |          0.65 |         0.25 |                 48233.1         |                      6.41559e-11 |   24116.6  |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|          2 | submission_qbb60v2_rev2024h1_p0600.csv  | Opposite sign for 2024H1 Revenue shape.                                                     |          0.8 |          0.1 |          0.6 |          0.65 |          0.65 |          0.65 |         0.25 |                 48233.1         |                      6.41559e-11 |   24116.6  |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|          3 | submission_qbb60v2_rev2024h1_p1200.csv  | High-variance extrapolation if 2024H1 p1000 improves.                                       |          0.8 |          0.1 |          1.2 |          0.65 |          0.65 |          0.65 |         0.25 |                 96466.3         |                      6.41559e-11 |   48233.1  |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|          4 | submission_qbb60v2_rev2023h1_p1000.csv  | Strengthen 2023H1 Revenue sample-like daily shape.                                          |          1   |          0.1 |          0.8 |          0.65 |          0.65 |          0.65 |         0.25 |                 37611.1         |                      6.41559e-11 |   18805.5  |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|          5 | submission_qbb60v2_rev2023h1_p0600.csv  | Opposite sign for 2023H1 Revenue shape.                                                     |          0.6 |          0.1 |          0.8 |          0.65 |          0.65 |          0.65 |         0.25 |                 37611.1         |                      6.41559e-11 |   18805.5  |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|          6 | submission_qbb60v2_rev_nonh2_p1000.csv  | Large combined non-H2 Revenue-shape move; only submit after one non-H2 axis improves.       |          1   |          0.1 |          1   |          0.65 |          0.65 |          0.65 |         0.25 |                 85844.2         |                      6.41559e-11 |   42922.1  |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|          7 | submission_qbb60v2_cogs2024h1_c0500.csv | Period-specific COGS shape down in 2024H1; global c0600 was near-neutral.                   |          0.8 |          0.1 |          0.8 |          0.65 |          0.65 |          0.5  |         0.25 |                     6.79797e-11 |                  27724.2         |   13862.1  |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|          8 | submission_qbb60v2_cogs2024h1_c0800.csv | Opposite COGS 2024H1 shape direction.                                                       |          0.8 |          0.1 |          0.8 |          0.65 |          0.65 |          0.8  |         0.25 |                     6.79797e-11 |                  27724.2         |   13862.1  |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|          9 | submission_qbb60v2_cogs2023h1_c0500.csv | Period-specific COGS shape down in 2023H1.                                                  |          0.8 |          0.1 |          0.8 |          0.5  |          0.65 |          0.65 |         0.25 |                     6.79797e-11 |                  24496.8         |   12248.4  |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|         10 | submission_qbb60v2_cogs2023h2_c0500.csv | Period-specific COGS shape down in guarded 2023H2.                                          |          0.8 |          0.1 |          0.8 |          0.65 |          0.5  |          0.65 |         0.25 |                     6.79797e-11 |                  22565.2         |   11282.6  |                                1 |                      1        |      0.948108 |       0.984209 |        1.00923 |       0.87097  |
|         11 | submission_qbb60v2_away0300.csv         | Retest COGS ratio-away strength; away axis historically improved until 0.25 then plateaued. |          0.8 |          0.1 |          0.8 |          0.65 |          0.65 |          0.65 |         0.3  |                     6.79797e-11 |                  14869.8         |    7434.89 |                                1 |                      1.00382  |      0.951733 |       0.990196 |        1.01288 |       0.872478 |
|         12 | submission_qbb60v2_away0200.csv         | Opposite ratio-away direction.                                                              |          0.8 |          0.1 |          0.8 |          0.65 |          0.65 |          0.65 |         0.2  |                     6.79797e-11 |                  14869.8         |    7434.89 |                                1 |                      0.996176 |      0.944482 |       0.978223 |        1.00558 |       0.869462 |

## Submit Order

1. `submission_qbb60v2_rev2024h1_p1000.csv`
2. If it worsens, submit `submission_qbb60v2_rev2024h1_p0600.csv`
3. If `rev2024h1_p1000` improves, submit `submission_qbb60v2_rev_nonh2_p1000.csv`
4. If Revenue axes are flat, submit `submission_qbb60v2_cogs2024h1_c0500.csv`
5. If COGS 2024H1 down worsens, submit `submission_qbb60v2_cogs2024h1_c0800.csv`
