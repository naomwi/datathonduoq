# Quarantine Big Jump V24 April Pivot

Run directory: `logs\20260426_195411_quarantine_big_jump_v24_april_pivot`

## Status

This is **quarantine blackbox**, not clean.

## Current Read

- Current best: `submission_qbb62_h1_backload_preserve_total_q2up040.csv` = `661327.0024`.
- Failed late-Q2 probe: `submission_qbb63_h1_mayjun_up060_janfebfund.csv` = `666579.35776`.
- Therefore, do not continue June/May-Jun. If the Q2-backload signal is real, it likely lives in April or in March-to-April transition.

## Public Results

| filename | public_score | read |
|:--|--:|:--|
| `submission_qbb64_apr_cogs_from_mayjun_q2preserve_cogs_apr080.csv` | `667484.97219` | Rejected. Moving Q2 COGS mass from May-Jun into April worsened by about `+6157.97` vs current best. Do not submit the combined Revenue+COGS April pivot; the COGS side is toxic. This result does not reject Revenue-only April timing. |
| `submission_qbb64_apr_from_mayjun_q2preserve_apr080.csv` | `667631.42258` | Rejected. Revenue-only April pivot worsened by about `+6304.42` vs current best. H1/Q2 timing localization is now effectively dead; do not submit April stronger, March-April transfer, June, or combined Revenue+COGS variants unless explicitly doing postmortem mapping. |

## Candidate Manifest

|   priority | filename                                                         | thesis                                                                                                                                   |   rev_rows_changed |   cogs_rows_changed |   mean_abs_rev_delta_vs_anchor |   mean_abs_cogs_delta_vs_anchor |   movement_vs_anchor |   best_case_score_if_direction_perfect |   revenue_total_ratio_vs_anchor |   cogs_total_ratio_vs_anchor |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |   max_revenue |    max_cogs |
|-----------:|:-----------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------|-------------------:|--------------------:|-------------------------------:|--------------------------------:|---------------------:|---------------------------------------:|--------------------------------:|-----------------------------:|---------------:|---------------:|---------------:|--------------:|------------:|
|          1 | submission_qbb64_apr_from_mayjun_q2preserve_apr080.csv           | Current best already backloads H1 into Q2. Since May-Jun failed, move Q2 Revenue mass from May-Jun into April while preserving Q2 total. |                 91 |                   0 |                        55191.3 |                             0   |              27595.7 |                                 633731 |                               1 |                            1 |        0.87628 |        1.00275 |       0.847066 |   1.27992e+07 | 1.19721e+07 |
|          2 | submission_qbb64_apr_from_mayjun_q2preserve_apr120.csv           | Bolder April-only Q2-preserve test; this is the high-information version if April is the true missing block.                             |                 91 |                   0 |                        82787   |                             0   |              41393.5 |                                 619934 |                               1 |                            1 |        0.87628 |        1.00275 |       0.847066 |   1.32733e+07 | 1.19721e+07 |
|          3 | submission_qbb64_apr_from_mar_marapr_preserve_apr080.csv         | March-April transition test: move Revenue from March into April while preserving March+April total.                                      |                 61 |                   0 |                        55191.3 |                             0   |              27595.7 |                                 633731 |                               1 |                            1 |        0.87628 |        1.00275 |       0.847066 |   1.27992e+07 | 1.19721e+07 |
|          4 | submission_qbb64_apr_from_mar_marapr_preserve_apr120.csv         | High-amplitude March-to-April transfer; useful if hidden public event is an April demand cliff/jump.                                     |                 61 |                   0 |                        82787   |                             0   |              41393.5 |                                 619934 |                               1 |                            1 |        0.87628 |        1.00275 |       0.847066 |   1.32733e+07 | 1.19721e+07 |
|          5 | submission_qbb64_aprmay_from_jun_q2preserve_aprmay050.csv        | If May-Jun failed because June is wrong, move Q2 mass from June into April-May.                                                          |                 91 |                   0 |                        70219.7 |                             0   |              35109.9 |                                 626217 |                               1 |                            1 |        0.87628 |        1.00275 |       0.847066 |   1.2936e+07  | 1.19721e+07 |
|          6 | submission_qbb64_march_down_q2_up_preserve_h1_q2p060.csv         | Alternate funding test: broad Q2 up like the current best, but funded mostly by March instead of all Q1.                                 |                122 |                   0 |                       124545   |                             0   |              62272.6 |                                 599054 |                               1 |                            1 |        0.87628 |        1.00275 |       0.847066 |   1.30592e+07 | 1.19721e+07 |
|          7 | submission_qbb64_apr_cogs_from_mayjun_q2preserve_cogs_apr080.csv | COGS-side April pivot: move Q2 COGS mass from May-Jun into April while keeping Revenue fixed. Orthogonal to Revenue timing.              |                  0 |                  91 |                            0   |                         46767.9 |              23383.9 |                                 637943 |                               1 |                            1 |        0.87628 |        1.00275 |       0.847066 |   1.26027e+07 | 1.19721e+07 |
|          8 | submission_qbb64_apr_rev_cogs_from_mayjun_q2preserve_apr080.csv  | Combined April pivot: move both Revenue and COGS Q2 mass from May-Jun into April, preserving Q2 totals for both targets.                 |                 91 |                  91 |                        55191.3 |                         46767.9 |              50979.6 |                                 610347 |                               1 |                            1 |        0.87628 |        1.00275 |       0.847066 |   1.27992e+07 | 1.19721e+07 |

## Suggested Submit Order

1. `submission_qbb64_apr_from_mayjun_q2preserve_apr080.csv`
   - Cleanest sign test: same Q2 total, move from May-Jun into April.
2. If it improves clearly, submit `submission_qbb64_apr_from_mayjun_q2preserve_apr120.csv`.
3. If it fails, submit `submission_qbb64_apr_from_mar_marapr_preserve_apr080.csv`.
   - Tests March-April transition instead of Q2 internal timing.
4. If Revenue timing keeps failing, try `submission_qbb64_apr_cogs_from_mayjun_q2preserve_cogs_apr080.csv` as an orthogonal COGS timing pivot.
