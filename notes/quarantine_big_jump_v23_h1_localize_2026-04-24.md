# Quarantine Big Jump V23 H1 Localize

Run directory: `logs\20260424_181141_quarantine_big_jump_v23_h1_localize`

## Status

This is **quarantine blackbox**, not clean.

Confirmed result:

- `submission_qbb62_h1_backload_preserve_total_q2up040.csv` = `661327.0024`
- Improvement vs anchor `submission_qbb60v18_cogs2023h2_down010.csv` = `662607.08245` is `1280.08005`.

## Public Results

| filename | public_score | read |
|:--|--:|:--|
| `submission_qbb63_h1_mayjun_up060_janfebfund.csv` | `666579.35776` | Rejected. Late-Q2 / May-Jun localization worsened by about `+5252.36` vs current best `qbb62_h1_backload_preserve_total_q2up040`. Do not submit `jun_up120`; it is the same late-Q2 hypothesis. If H1 timing still matters, it is more likely April / March-April transition / source-funding structure. |

## Read

Frontload Q1 failed, Q2 backload improved. The direction is real, but the response is weak versus movement. Therefore this batch does not simply squeeze Q2; it localizes the Q2 gain into month/peak structures.

## Backload Response Curve

|   signed_movement |   public_score | label             |
|------------------:|---------------:|:------------------|
|          -28870.3 |         667598 | frontload_q1up050 |
|               0   |         662607 | anchor            |
|           39918.3 |         661327 | backload_q2up040  |
|           27792.5 |         661026 | quadratic_optimum |

## Candidate Manifest

|   priority | filename                                        | thesis                                                                                                                                                 |   rev_rows_changed |   cogs_rows_changed |   mean_abs_rev_delta_vs_anchor |   mean_abs_cogs_delta_vs_anchor |   movement_vs_anchor |   best_case_score_if_direction_perfect |   revenue_total_ratio_vs_anchor |   cogs_total_ratio_vs_anchor |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |   max_revenue |    max_cogs |
|-----------:|:------------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------:|--------------------:|-------------------------------:|--------------------------------:|---------------------:|---------------------------------------:|--------------------------------:|-----------------------------:|---------------:|---------------:|---------------:|--------------:|------------:|
|          1 | submission_qbb63_h1_mayjun_up060_janfebfund.csv | Localize the confirmed Q2-backload gain into May-Jun, funded by Jan-Feb. This avoids moving March/April if the public error is late-spring demand.     |                120 |                   0 |                        79953.6 |                               0 |              39976.8 |                                 622630 |                               1 |                            1 |        0.87628 |        1.00275 |       0.847066 |   1.26027e+07 | 1.19721e+07 |
|          2 | submission_qbb63_h1_jun_up120_janfebfund.csv    | High-amplitude June-only test: if the hidden error is end-of-H1 ramp, this is a real jump rather than a Q2 average.                                    |                 89 |                   0 |                        77464.4 |                               0 |              38732.2 |                                 623875 |                               1 |                            1 |        0.87628 |        1.00275 |       0.847066 |   1.26027e+07 | 1.19721e+07 |
|          3 | submission_qbb63_h1_aprmay_up060_janfebfund.csv | Alternative Q2 localization: spring promo/April-May block, funded by Jan-Feb.                                                                          |                120 |                   0 |                        81022.8 |                               0 |              40511.4 |                                 622096 |                               1 |                            1 |        0.87628 |        1.00275 |       0.847066 |   1.26027e+07 | 1.19721e+07 |
|          4 | submission_qbb63_h1_apr_up120_janfebfund.csv    | April-only large move; tests whether the Q2 gain is actually the March-April transition/event shoulder.                                                |                 89 |                   0 |                        79602.9 |                               0 |              39801.4 |                                 622806 |                               1 |                            1 |        0.87628 |        1.00275 |       0.847066 |   1.27627e+07 | 1.19721e+07 |
|          5 | submission_qbb63_h1_q2_up080_q1fund.csv         | Bolder version of the confirmed Q2 direction. Included as a stress test, not first priority, because the first response curve was weak.                |                181 |                   0 |                       159673   |                               0 |              79836.7 |                                 582770 |                               1 |                            1 |        0.87628 |        1.00275 |       0.847066 |   1.27939e+07 | 1.19721e+07 |
|          6 | submission_qbb63_h1_q2_top35_shape_up100.csv    | Within Q2 only, preserve Q2 Revenue total but move mass into the top 35% Q2 Revenue days. Tests concentrated Q2 peaks rather than Q2 monthly level.    |                 91 |                   0 |                       919026   |                               0 |             459513   |                                 203094 |                               1 |                            1 |        0.87628 |        1.00275 |       0.847066 |   2.36924e+07 | 1.19721e+07 |
|          7 | submission_qbb63_h1_h1_top35_shape_up060.csv    | Within all 2023H1, preserve H1 total but concentrate Revenue into the top 35% days. Different from Q2 average and can reveal peak-day underprediction. |                181 |                   0 |                       978766   |                               0 |             489383   |                                 173224 |                               1 |                            1 |        0.87628 |        1.00275 |       0.847066 |   1.93059e+07 | 1.19721e+07 |

## Suggested Submit Order

1. `submission_qbb63_h1_mayjun_up060_janfebfund.csv` for the most plausible localized version of the confirmed Q2 signal.
2. If it improves, submit `submission_qbb63_h1_jun_up120_janfebfund.csv` to test end-of-H1 concentration.
3. If May-Jun fails, submit `submission_qbb63_h1_aprmay_up060_janfebfund.csv`.
4. Use `submission_qbb63_h1_q2_top35_shape_up100.csv` only as a high-variance peak-day test.
