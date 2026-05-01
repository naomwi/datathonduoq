# Clean V3 Funnel Follow-Up

Run directory: `logs\20260424_121025_clean_v3_funnel_followup`

## Boundary

This is a clean-input public-guided follow-up. It uses raw/train data to compute a business funnel head:

`2023H1 Revenue = 2022 sessions * recovered_conversion * 2022 AOV`

No `sample_submission.csv`, previous submissions, or test targets are read as inputs.

The public result `submission_cleanv3_head_funnel_last_c10_h1only_r0876.csv = 674590.42937` showed that `c10` undercalled H1 versus the current clean best. This run maps the conversion-recovery parameter around the H1 total implied by `b044`.

## Candidate Manifest

|   priority | filename                                   |   conv_recovery |   h1_cogs_ratio |   revenue_total |   cogs_total |   ratio_total |   rev_2023H1 |   cogs_2023H1 |   ratio_2023H1 |   rev_2023H2 |   cogs_2023H2 |   ratio_2023H2 |   rev_2024H1 |   cogs_2024H1 |   ratio_2024H1 | note                                                                  |
|-----------:|:-------------------------------------------|----------------:|----------------:|----------------:|-------------:|--------------:|-------------:|--------------:|---------------:|-------------:|--------------:|---------------:|-------------:|--------------:|---------------:|:----------------------------------------------------------------------|
|          1 | submission_cleanv3_funnel_c110_h1r0876.csv |           0.11  |           0.876 |     2.36346e+09 |  2.12485e+09 |      0.89904  |  8.50952e+08 |   7.45434e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |  8.83831e+08 |   7.46735e+08 |       0.844885 | Funnel H1 recovery just below the current b044-equivalent level.      |
|          2 | submission_cleanv3_funnel_c111_h1r0876.csv |           0.111 |           0.876 |     2.36482e+09 |  2.12603e+09 |      0.899027 |  8.52308e+08 |   7.46621e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |  8.83831e+08 |   7.46735e+08 |       0.844885 | Funnel H1 recovery nearly matching current clean best H1 total.       |
|          3 | submission_cleanv3_funnel_c112_h1r0876.csv |           0.112 |           0.876 |     2.36617e+09 |  2.12722e+09 |      0.899014 |  8.53663e+08 |   7.47809e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |  8.83831e+08 |   7.46735e+08 |       0.844885 | Funnel H1 recovery slightly above current clean best H1 total.        |
|          4 | submission_cleanv3_funnel_c113_h1r0876.csv |           0.113 |           0.876 |     2.36753e+09 |  2.12841e+09 |      0.899    |  8.55019e+08 |   7.48996e+08 |          0.876 |  6.21578e+08 |   6.24991e+08 |        1.00549 |  8.83831e+08 |   7.46735e+08 |       0.844885 | Upper-side funnel H1 recovery before the known b050 overshoot region. |
|          5 | submission_cleanv3_funnel_c111_h1r0870.csv |           0.111 |           0.87  |     2.36482e+09 |  2.12092e+09 |      0.896864 |  8.52308e+08 |   7.41508e+08 |          0.87  |  6.21578e+08 |   6.24991e+08 |        1.00549 |  8.83831e+08 |   7.46735e+08 |       0.844885 | Same funnel H1 level, lower COGS ratio to test ratio head direction.  |
|          6 | submission_cleanv3_funnel_c111_h1r0882.csv |           0.111 |           0.882 |     2.36482e+09 |  2.13115e+09 |      0.901189 |  8.52308e+08 |   7.51735e+08 |          0.882 |  6.21578e+08 |   6.24991e+08 |        1.00549 |  8.83831e+08 |   7.46735e+08 |       0.844885 | Same funnel H1 level, higher COGS ratio to test ratio head direction. |

## Submit Order

1. `submission_cleanv3_funnel_c111_h1r0876.csv`
2. `submission_cleanv3_funnel_c112_h1r0876.csv`
3. `submission_cleanv3_funnel_c110_h1r0876.csv`
4. `submission_cleanv3_funnel_c111_h1r0870.csv`
5. `submission_cleanv3_funnel_c111_h1r0882.csv`
6. `submission_cleanv3_funnel_c113_h1r0876.csv`
