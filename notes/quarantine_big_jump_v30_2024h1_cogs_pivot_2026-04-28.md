# Quarantine Big Jump V30 2024H1 COGS Pivot

Run directory: `logs\20260428_123905_quarantine_big_jump_v30_2024h1_cogs_pivot`

## Status

This branch is **quarantine blackbox**, not clean.

## Current Read

- Current best anchor: `submission_qbb69_h1_q1_cogs_down120_keeprev.csv` = `655838.51372`.
- Q1 2023 uniform COGS-down is nearly exhausted.
- Pivot axis: 2024H1 COGS month structure. Current 2024 Jan-Mar ratios are above sample, while June is below sample.
- This batch preserves all 2023 values and Revenue; only 2024H1 COGS moves.

## Anchor 2024H1 Month Ratios

| month   |   days |     Revenue |        COGS |    ratio |
|:--------|-------:|------------:|------------:|---------:|
| 2024-01 |     31 | 7.58981e+07 | 6.4322e+07  | 0.847478 |
| 2024-02 |     29 | 9.39311e+07 | 8.35516e+07 | 0.889499 |
| 2024-03 |     31 | 1.46117e+08 | 1.35873e+08 | 0.92989  |
| 2024-04 |     30 | 1.87919e+08 | 1.58123e+08 | 0.841441 |
| 2024-05 |     31 | 1.94494e+08 | 1.57171e+08 | 0.808098 |
| 2024-06 |     30 | 1.84823e+08 | 1.49075e+08 | 0.806578 |

## Sample 2024H1 Month Ratios

| month   |   days |     Revenue |        COGS |    ratio |
|:--------|-------:|------------:|------------:|---------:|
| 2024-01 |     31 | 5.5396e+07  | 4.51e+07    | 0.814138 |
| 2024-02 |     29 | 6.93506e+07 | 5.64284e+07 | 0.813669 |
| 2024-03 |     31 | 1.0773e+08  | 9.28028e+07 | 0.861439 |
| 2024-04 |     30 | 1.35398e+08 | 1.1508e+08  | 0.849945 |
| 2024-05 |     31 | 1.40246e+08 | 1.12763e+08 | 0.804035 |
| 2024-06 |     30 | 1.31921e+08 | 1.11153e+08 | 0.842572 |

## Candidate Manifest

|   priority | filename                                                    | family                     | changed_scope          | thesis                                                                                                        |   rev_rows_changed |   cogs_rows_changed |   non_2024h1_max_abs_delta_vs_anchor |   y2023_max_abs_delta_vs_anchor |   mean_abs_rev_delta_vs_anchor |   mean_abs_cogs_delta_vs_anchor |   movement_vs_anchor |   best_case_score_if_direction_perfect |   revenue_total_ratio_vs_anchor |   cogs_total_ratio_vs_anchor |   ratio_all |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |   max_revenue |    max_cogs |
|-----------:|:------------------------------------------------------------|:---------------------------|:-----------------------|:--------------------------------------------------------------------------------------------------------------|-------------------:|--------------------:|-------------------------------------:|--------------------------------:|-------------------------------:|--------------------------------:|---------------------:|---------------------------------------:|--------------------------------:|-----------------------------:|------------:|---------------:|---------------:|---------------:|--------------:|------------:|
|          1 | submission_qbb70_2024q1_cogs_down030_keeprev.csv            | 2024q1_cogs_level          | 2024Q1 COGS only       | Sign test: lower 2024Q1 COGS by 3%. Monthly ratios show Jan-Mar are above sample while Q2 is not.             |                  0 |                  91 |                                    0 |                               0 |                              0 |                         15533.6 |              7766.78 |                                 648072 |                               1 |                     0.99591  |    0.873599 |       0.836829 |       0.974516 |       0.837428 |   1.26027e+07 | 1.05928e+07 |
|          2 | submission_qbb70_2024q1_cogs_down060_keeprev.csv            | 2024q1_cogs_level          | 2024Q1 COGS only       | Stronger 2024Q1 COGS-down test if Q1 2024 is the remaining high-ratio block.                                  |                  0 |                  91 |                                    0 |                               0 |                              0 |                         31067.1 |             15533.6  |                                 640305 |                               1 |                     0.99182  |    0.870011 |       0.836829 |       0.974516 |       0.827789 |   1.26027e+07 | 1.05355e+07 |
|          3 | submission_qbb70_2024h1_cogs_monthratio_a050_keeprev.csv    | 2024h1_cogs_month_ratio    | 2024H1 COGS only       | Blend 50% toward sample monthly COGS/Revenue ratios: lowers Jan-Mar, leaves May near-neutral, raises June.    |                  0 |                 182 |                                    0 |                               0 |                              0 |                         54351.4 |             27175.7  |                                 628663 |                               1 |                     0.99707  |    0.874617 |       0.836829 |       0.974516 |       0.840162 |   1.26027e+07 | 1.07013e+07 |
|          4 | submission_qbb70_2024h1_cogs_monthratio_a100_keeprev.csv    | 2024h1_cogs_month_ratio    | 2024H1 COGS only       | Full 2024H1 monthly-ratio repair toward sample shape; high-information structured pivot.                      |                  0 |                 182 |                                    0 |                               0 |                              0 |                        108703   |             54351.4  |                                 601487 |                               1 |                     0.99414  |    0.872047 |       0.836829 |       0.974516 |       0.833258 |   1.26027e+07 | 1.05355e+07 |
|          5 | submission_qbb70_2024q1_cogs_monthratio_a100_keeprev.csv    | 2024q1_cogs_month_ratio    | 2024Q1 COGS only       | Only Jan-Mar 2024 toward sample ratios; isolates the high-ratio Q1 block without touching Q2.                 |                  0 |                  91 |                                    0 |                               0 |                              0 |                         40489.8 |             20244.9  |                                 635594 |                               1 |                     0.990556 |    0.868902 |       0.836829 |       0.974516 |       0.824811 |   1.26027e+07 | 1.05355e+07 |
|          6 | submission_qbb70_2024h1_cogs_q1down040_q2fund_preserve.csv  | 2024h1_cogs_phase_preserve | 2024H1 COGS shape only | Preserve 2024H1 COGS total but shift cost mass from high-ratio Q1 into Q2.                                    |                  0 |                 182 |                                    0 |                               0 |                              0 |                         41422.9 |             20711.4  |                                 635127 |                               1 |                     1        |    0.877187 |       0.836829 |       0.974516 |       0.847066 |   1.26027e+07 | 1.05355e+07 |
|          7 | submission_qbb70_2024h1_cogs_q1down040_junfund_preserve.csv | 2024h1_cogs_phase_preserve | 2024H1 COGS shape only | Preserve 2024H1 COGS total but move Q1 cost mass specifically into June, whose current ratio is below sample. |                  0 |                 121 |                                    0 |                               0 |                              0 |                         41422.9 |             20711.4  |                                 635127 |                               1 |                     1        |    0.877187 |       0.836829 |       0.974516 |       0.847066 |   1.26027e+07 | 1.05355e+07 |
|          8 | submission_qbb70_2024_janfeb_cogs_down040_keeprev.csv       | 2024q1_month_concentration | 2024 Jan-Feb COGS only | Lower Jan-Feb 2024 only; tests whether Tet/early-year COGS is the high-ratio residual.                        |                  0 |                  60 |                                    0 |                               0 |                              0 |                         10793.7 |              5396.85 |                                 650442 |                               1 |                     0.997158 |    0.874694 |       0.836829 |       0.974516 |       0.840369 |   1.26027e+07 | 1.09204e+07 |
|          9 | submission_qbb70_2024_mar_cogs_down050_keeprev.csv          | 2024q1_month_concentration | 2024 March COGS only   | Lower March 2024 only; March has the largest 2024H1 COGS/Revenue ratio.                                       |                  0 |                  31 |                                    0 |                               0 |                              0 |                         12397.2 |              6198.58 |                                 649640 |                               1 |                     0.996736 |    0.874323 |       0.836829 |       0.974516 |       0.839374 |   1.26027e+07 | 1.05355e+07 |

## Suggested Submit Order

1. `submission_qbb70_2024h1_cogs_monthratio_a050_keeprev.csv`
2. If it improves, submit `submission_qbb70_2024h1_cogs_monthratio_a100_keeprev.csv`
3. If it worsens, submit `submission_qbb70_2024h1_cogs_q1down040_q2fund_preserve.csv`
4. Use `2024q1_cogs_down030` only as a simpler sign-check if structured month-ratio is unclear.
5. Do not submit 2024H1 COGS-up; earlier evidence rejected 2024H1 COGS +10% strongly.

## Do Not Use As Clean

These candidates are public-guided/quarantine probes and must not be presented as clean model outputs.
