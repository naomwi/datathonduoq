# Public-Only H2 Shape V16

Run directory: `logs\20260422_092018_publiconly_h2_shape_v16`

Current best: `submission_top10_v13_rev2023h2_up100_keepcogs.csv` scored `797595.9641`.

Latest failed scale probe: `submission_h2rev_v15_current_h2_rev_up050.csv` scored `800572.16096`.

Known results:

|                                                            |   public_score |
|:-----------------------------------------------------------|---------------:|
| submission_publiconly_segment_v8_h2best_2024h1_down100.csv |         807505 |
| submission_top10_v13_rev2023h2_up100_keepcogs.csv          |         797596 |
| submission_h2rev_v15_current_h2_rev_up050.csv              |         800572 |

Interpretation:

- Extra H2 Revenue +5% worsened from `797595.9641` to `800572.16096`, so broad H2 scale is near saturation.
- The next high-leverage hypothesis is H2 monthly shape, especially COGS timing.
- Historical odd-year H2 puts more COGS mass into Jul-Aug/Dec and less into Oct-Nov than the current best.
- These candidates preserve H2 totals unless explicitly stated otherwise, so they test shape rather than another broad leaderboard scale knob.

Current best H2 monthly profile:

|   month |     Revenue |        COGS |   rev_share |   cogs_share |    ratio |
|--------:|------------:|------------:|------------:|-------------:|---------:|
|       7 | 1.27778e+08 | 1.27656e+08 |    0.20595  |     0.207627 | 0.999048 |
|       8 | 1.10809e+08 | 1.21994e+08 |    0.1786   |     0.198418 | 1.10094  |
|       9 | 1.13336e+08 | 1.08122e+08 |    0.182673 |     0.175856 | 0.953991 |
|      10 | 1.09864e+08 | 1.01024e+08 |    0.177076 |     0.164312 | 0.919543 |
|      11 | 8.45073e+07 | 8.19661e+07 |    0.136207 |     0.133314 | 0.96993  |
|      12 | 7.41388e+07 | 7.40715e+07 |    0.119495 |     0.120474 | 0.999093 |

Odd-year mean H2 monthly shares:

|   month |   rev_share |   cogs_share |
|--------:|------------:|-------------:|
|       7 |    0.234159 |     0.22168  |
|       8 |    0.164443 |     0.226878 |
|       9 |    0.185178 |     0.174011 |
|      10 |    0.167253 |     0.138847 |
|      11 |    0.127733 |     0.114624 |
|      12 |    0.121233 |     0.12396  |

Candidate manifest:

|   priority | filename                                              | path                                                          | thesis                                                                               |   rev_rows_changed |   cogs_rows_changed |   mean_abs_rev_delta |   mean_abs_cogs_delta |   directional_best_case_gain |   h2_revenue_total_ratio_vs_current |   h2_cogs_total_ratio_vs_current |   h2_ratio |   h2_jul_rev_share |   h2_aug_cogs_share |   h2_oct_cogs_share |   h2_dec_cogs_share |
|-----------:|:------------------------------------------------------|:--------------------------------------------------------------|:-------------------------------------------------------------------------------------|-------------------:|--------------------:|---------------------:|----------------------:|-----------------------------:|------------------------------------:|---------------------------------:|-----------:|-------------------:|--------------------:|--------------------:|--------------------:|
|          1 | submission_h2shape_v16_cogs_oddmean_preserve.csv      | dataset\submission_h2shape_v16_cogs_oddmean_preserve.csv      | preserve total H2 COGS, reshape monthly COGS to odd-year mean shares                 |                  0 |                 184 |                  0   |              103219   |                      51609.3 |                                   1 |                                1 |   0.990975 |           0.20595  |            0.226878 |            0.138847 |            0.12396  |
|          2 | submission_h2shape_v16_revcogs_oddmean_preserve.csv   | dataset\submission_h2shape_v16_revcogs_oddmean_preserve.csv   | preserve H2 totals, reshape both Revenue and COGS to odd-year mean shares            |                184 |                 184 |              73484.7 |              103219   |                      88351.6 |                                   1 |                                1 |   0.990975 |           0.234159 |            0.226878 |            0.138847 |            0.12396  |
|          3 | submission_h2shape_v16_cogs_2021_preserve.csv         | dataset\submission_h2shape_v16_cogs_2021_preserve.csv         | preserve total H2 COGS, use 2021 H2 COGS monthly shares as nearest odd-year analogue |                  0 |                 184 |                  0   |              130619   |                      65309.5 |                                   1 |                                1 |   0.990975 |           0.20595  |            0.231537 |            0.133121 |            0.124537 |
|          4 | submission_h2shape_v16_revcogs_2021_preserve.csv      | dataset\submission_h2shape_v16_revcogs_2021_preserve.csv      | preserve H2 totals, use 2021 H2 monthly shares as nearest odd-year analogue          |                184 |                 184 |              97516.1 |              130619   |                     114068   |                                   1 |                                1 |   0.990975 |           0.245831 |            0.231537 |            0.133121 |            0.124537 |
|          5 | submission_h2shape_v16_cogs_q3up_preserve.csv         | dataset\submission_h2shape_v16_cogs_q3up_preserve.csv         | preserve total H2 COGS, move COGS mass from Q4 into Q3                               |                  0 |                 184 |                  0   |               41731.6 |                      20865.8 |                                   1 |                                1 |   0.990975 |           0.20595  |            0.204759 |            0.157003 |            0.115115 |
|          6 | submission_h2shape_v16_cogs_augdec_up_preserve.csv    | dataset\submission_h2shape_v16_cogs_augdec_up_preserve.csv    | preserve total H2 COGS, emphasize August and December odd-year cost spikes           |                  0 |                 184 |                  0   |               57935.2 |                      28967.6 |                                   1 |                                1 |   0.990975 |           0.20595  |            0.219531 |            0.158083 |            0.12518  |
|          7 | submission_h2shape_v16_rev_oddmean_preserve.csv       | dataset\submission_h2shape_v16_rev_oddmean_preserve.csv       | preserve total H2 Revenue, reshape monthly Revenue to odd-year mean shares           |                184 |                   0 |              73484.7 |                   0   |                      36742.3 |                                   1 |                                1 |   0.990975 |           0.234159 |            0.198418 |            0.164312 |            0.120474 |
|          8 | submission_h2shape_v16_rev_q3up_preserve.csv          | dataset\submission_h2shape_v16_rev_q3up_preserve.csv          | preserve total H2 Revenue, move Revenue mass from Q4 into Q3                         |                184 |                   0 |              27026.3 |                   0   |                      13513.2 |                                   1 |                                1 |   0.990975 |           0.210283 |            0.198418 |            0.164312 |            0.120474 |
|          9 | submission_h2shape_v16_rev_julup_preserve.csv         | dataset\submission_h2shape_v16_rev_julup_preserve.csv         | preserve total H2 Revenue, test odd-year July Revenue underprediction                |                184 |                   0 |              43364.3 |                   0   |                      21682.1 |                                   1 |                                1 |   0.990975 |           0.2251   |            0.198418 |            0.164312 |            0.120474 |
|         10 | submission_h2shape_v16_revjul_cogsaugdec_preserve.csv | dataset\submission_h2shape_v16_revjul_cogsaugdec_preserve.csv | preserve H2 totals, combine July Revenue shift with Aug/Dec COGS shift               |                184 |                 184 |              36282.7 |               46009.8 |                      41146.2 |                                   1 |                                1 |   0.990975 |           0.221973 |            0.215538 |            0.159365 |            0.123858 |

Suggested order:

1. `submission_h2shape_v16_cogs_oddmean_preserve.csv`
2. If it improves: `submission_h2shape_v16_revcogs_oddmean_preserve.csv`
3. If COGS oddmean is too aggressive: `submission_h2shape_v16_cogs_q3up_preserve.csv`
4. Only after COGS-shape signal: test Revenue shape with `submission_h2shape_v16_rev_oddmean_preserve.csv`
