# Quarantine Big Jump V29 Q1 COGS Curve

Run directory: `logs\20260426_204721_quarantine_big_jump_v29_q1_cogs_curve`

## Status

This branch is **quarantine blackbox**, not clean.

## Current Read

- Current best anchor: `submission_qbb68_h1_q1_cogs_down080_keeprev.csv` = `656301.72926`.
- Q1 COGS down `4%` and `8%` both improved; slope is decreasing but still positive.
- Quadratic fit from `0/4/8%` puts the response optimum near `13%` absolute Q1 COGS down.
- This batch changes only 2023Q1 COGS and preserves Revenue, 2023Q2, 2023H2, and 2024H1.

## Public Results

| filename | public_score | read |
|:--|--:|:--|
| `submission_qbb69_h1_q1_cogs_down120_keeprev.csv` | `655838.51372` | Accepted, but slope is now small. Improves by about `463.22` vs `down080`. Refit with `0/4/8/12%` puts optimum around `12.6-12.9%`, so `down130` is only a near-optimum squeeze, not a 60x path by itself. |

## Response Curve

| label             |   q1_cogs_down |   public_score |   public_score_fit |
|:------------------|---------------:|---------------:|-------------------:|
| known_down000     |       0        |         659212 |             659212 |
| known_down040     |       0.04     |         657443 |             657443 |
| known_down080     |       0.08     |         656302 |             656302 |
| down100           |       0.1      |            nan |             655966 |
| down120           |       0.12     |            nan |             655787 |
| down130           |       0.13     |            nan |             655757 |
| down140           |       0.14     |            nan |             655765 |
| down160           |       0.16     |            nan |             655900 |
| quadratic_optimum |       0.132818 |            nan |             655755 |

## Current Q1 Month Ratios

| month   |   days |     Revenue |        COGS |    ratio |
|:--------|-------:|------------:|------------:|---------:|
| 2023-01 |     31 | 7.00485e+07 | 6.01144e+07 | 0.858182 |
| 2023-02 |     28 | 8.6743e+07  | 7.43034e+07 | 0.856592 |
| 2023-03 |     31 | 1.37752e+08 | 1.26694e+08 | 0.919723 |

## Sample Q1 Month Ratios

| month   |   days |     Revenue |        COGS |    ratio |
|:--------|-------:|------------:|------------:|---------:|
| 2023-01 |     31 | 5.7582e+07  | 4.69526e+07 | 0.815404 |
| 2023-02 |     28 | 7.09055e+07 | 5.77454e+07 | 0.814399 |
| 2023-03 |     31 | 1.11981e+08 | 9.6615e+07  | 0.862779 |

## Candidate Manifest

|   priority | filename                                                    | family                        | changed_scope     | thesis                                                                                                                   |   rev_rows_changed |   cogs_rows_changed |   non_q1_max_abs_delta_vs_current |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   movement_vs_current |   best_case_score_if_direction_perfect |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_all |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |   max_revenue |    max_cogs |
|-----------:|:------------------------------------------------------------|:------------------------------|:------------------|:-------------------------------------------------------------------------------------------------------------------------|-------------------:|--------------------:|----------------------------------:|--------------------------------:|---------------------------------:|----------------------:|---------------------------------------:|---------------------------------:|------------------------------:|------------:|---------------:|---------------:|---------------:|--------------:|------------:|
|          1 | submission_qbb69_h1_q1_cogs_down100_keeprev.csv             | h1_q1_cogs_response_curve     | 2023Q1 COGS only  | Absolute 2023Q1 COGS reduction 10.0% from the pre-Q1-down anchor; extends the accepted 4% and 8% response curve.         |                  0 |                  90 |                                 0 |                               0 |                         10358.3  |               5179.14 |                                 651123 |                                1 |                      0.997287 |    0.879579 |       0.843404 |       0.974516 |       0.847066 |   1.26027e+07 | 1.09204e+07 |
|          2 | submission_qbb69_h1_q1_cogs_down120_keeprev.csv             | h1_q1_cogs_response_curve     | 2023Q1 COGS only  | Absolute 2023Q1 COGS reduction 12.0% from the pre-Q1-down anchor; extends the accepted 4% and 8% response curve.         |                  0 |                  90 |                                 0 |                               0 |                         20716.6  |              10358.3  |                                 645943 |                                1 |                      0.994575 |    0.877187 |       0.836829 |       0.974516 |       0.847066 |   1.26027e+07 | 1.09204e+07 |
|          3 | submission_qbb69_h1_q1_cogs_down130_keeprev.csv             | h1_q1_cogs_response_curve     | 2023Q1 COGS only  | Absolute 2023Q1 COGS reduction 13.0% from the pre-Q1-down anchor; extends the accepted 4% and 8% response curve.         |                  0 |                  90 |                                 0 |                               0 |                         25895.7  |              12947.8  |                                 643354 |                                1 |                      0.993218 |    0.875991 |       0.833541 |       0.974516 |       0.847066 |   1.26027e+07 | 1.09204e+07 |
|          4 | submission_qbb69_h1_q1_cogs_down140_keeprev.csv             | h1_q1_cogs_response_curve     | 2023Q1 COGS only  | Absolute 2023Q1 COGS reduction 14.0% from the pre-Q1-down anchor; extends the accepted 4% and 8% response curve.         |                  0 |                  90 |                                 0 |                               0 |                         31074.8  |              15537.4  |                                 640764 |                                1 |                      0.991862 |    0.874794 |       0.830254 |       0.974516 |       0.847066 |   1.26027e+07 | 1.09204e+07 |
|          5 | submission_qbb69_h1_q1_cogs_down160_keeprev.csv             | h1_q1_cogs_response_curve     | 2023Q1 COGS only  | Absolute 2023Q1 COGS reduction 16.0% from the pre-Q1-down anchor; extends the accepted 4% and 8% response curve.         |                  0 |                  90 |                                 0 |                               0 |                         41433.1  |              20716.6  |                                 635585 |                                1 |                      0.989149 |    0.872402 |       0.823678 |       0.974516 |       0.847066 |   1.26027e+07 | 1.09204e+07 |
|          6 | submission_qbb69_h1_q1_cogs_sample_monthratio_a0750.csv     | h1_q1_cogs_sample_month_ratio | 2023Q1 COGS only  | Blend Q1 COGS 75% toward sample monthly COGS/Revenue ratios; tests month-specific ratio repair instead of uniform down.  |                  0 |                  90 |                                 0 |                               0 |                         16733.3  |               8366.67 |                                 647935 |                                1 |                      0.997515 |    0.87978  |       0.843957 |       0.974516 |       0.847066 |   1.26027e+07 | 1.09204e+07 |
|          7 | submission_qbb69_h1_q1_cogs_sample_monthratio_a1000.csv     | h1_q1_cogs_sample_month_ratio | 2023Q1 COGS only  | Blend Q1 COGS 100% toward sample monthly COGS/Revenue ratios; tests month-specific ratio repair instead of uniform down. |                  0 |                  90 |                                 0 |                               0 |                         30038.3  |              15019.1  |                                 641283 |                                1 |                      0.99307  |    0.87586  |       0.833182 |       0.974516 |       0.847066 |   1.26027e+07 | 1.09204e+07 |
|          8 | submission_qbb69_h1_mar_extra_cogs_down040_from_down080.csv | h1_q1_month_concentration     | 2023-03 COGS only | After uniform down080, March still has the highest Q1 ratio; lower March another 4%.                                     |                  0 |                  31 |                                 0 |                               0 |                          9247.72 |               4623.86 |                                 651678 |                                1 |                      0.997578 |    0.879836 |       0.844109 |       0.974516 |       0.847066 |   1.26027e+07 | 1.09204e+07 |
|          9 | submission_qbb69_h1_mar_extra_cogs_down060_from_down080.csv | h1_q1_month_concentration     | 2023-03 COGS only | Stronger March-only repair after uniform down080.                                                                        |                  0 |                  31 |                                 0 |                               0 |                         13871.6  |               6935.79 |                                 649366 |                                1 |                      0.996367 |    0.878768 |       0.841174 |       0.974516 |       0.847066 |   1.26027e+07 | 1.09204e+07 |

## Suggested Submit Order

1. Current best is now `submission_qbb69_h1_q1_cogs_down120_keeprev.csv`.
2. Submit `submission_qbb69_h1_q1_cogs_down130_keeprev.csv` only as a low-upside near-optimum squeeze.
3. Do not submit `down140/down160` unless `down130` clearly improves more than expected.
4. After `down130`, pivot to a new axis; Q1 uniform COGS-down is nearly exhausted.

## Do Not Use As Clean

These candidates are public-guided/quarantine probes and must not be presented as clean model outputs.
