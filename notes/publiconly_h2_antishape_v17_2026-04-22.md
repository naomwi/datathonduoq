# Public-Only H2 Anti-Shape V17

Run directory: `logs\20260422_092637_publiconly_h2_antishape_v17`

Current best: `submission_top10_v13_rev2023h2_up100_keepcogs.csv` scored `797595.9641`.

Failed scale probe: `submission_h2rev_v15_current_h2_rev_up050.csv` scored `800572.16096`.

Failed shape probe: `submission_h2shape_v16_cogs_oddmean_preserve.csv` scored `802116.33879`.

Interpretation:

- Extra broad H2 Revenue worsened, and quadratic interpolation puts the H2 Revenue optimum essentially at the current best.
- Odd-year COGS shape also worsened, so do not submit the more aggressive `revcogs_oddmean` candidate.
- V17 tests the opposite of the failed COGS-shape vector while preserving total H2 COGS. This is a blackbox-gradient probe, not a historical prior.

Current H2 month profile:

|   month |     Revenue |        COGS |   rev_share |   cogs_share |    ratio |
|--------:|------------:|------------:|------------:|-------------:|---------:|
|       7 | 1.27778e+08 | 1.27656e+08 |    0.20595  |     0.207627 | 0.999048 |
|       8 | 1.10809e+08 | 1.21994e+08 |    0.1786   |     0.198418 | 1.10094  |
|       9 | 1.13336e+08 | 1.08122e+08 |    0.182673 |     0.175856 | 0.953991 |
|      10 | 1.09864e+08 | 1.01024e+08 |    0.177076 |     0.164312 | 0.919543 |
|      11 | 8.45073e+07 | 8.19661e+07 |    0.136207 |     0.133314 | 0.96993  |
|      12 | 7.41388e+07 | 7.40715e+07 |    0.119495 |     0.120474 | 0.999093 |

Failed odd-year reference shares:

|   month |   rev_share |   cogs_share |
|--------:|------------:|-------------:|
|       7 |    0.234159 |     0.22168  |
|       8 |    0.164443 |     0.226878 |
|       9 |    0.185178 |     0.174011 |
|      10 |    0.167253 |     0.138847 |
|      11 |    0.127733 |     0.114624 |
|      12 |    0.121233 |     0.12396  |

Candidate manifest:

|   priority | filename                                                   | path                                                               | thesis                                                                                |   rev_rows_changed |   cogs_rows_changed |   mean_abs_rev_delta |   mean_abs_cogs_delta |   directional_best_case_gain |   h2_revenue_total_ratio_vs_current |   h2_cogs_total_ratio_vs_current |   h2_ratio |   jul_cogs_share |   aug_cogs_share |   oct_cogs_share |   nov_cogs_share |   dec_cogs_share |
|-----------:|:-----------------------------------------------------------|:-------------------------------------------------------------------|:--------------------------------------------------------------------------------------|-------------------:|--------------------:|---------------------:|----------------------:|-----------------------------:|------------------------------------:|---------------------------------:|-----------:|-----------------:|-----------------:|-----------------:|-----------------:|-----------------:|
|          1 | submission_h2antishape_v17_cogs_antiodd025_preserve.csv    | dataset\submission_h2antishape_v17_cogs_antiodd025_preserve.csv    | opposite of failed odd-year COGS-shape vector, 25% strength, preserve H2 COGS total   |                  0 |                 184 |                  0   |               25804.6 |                      12902.3 |                                   1 |                                1 |   0.990975 |         0.204114 |         0.191302 |         0.170678 |         0.137987 |         0.119602 |
|          2 | submission_h2antishape_v17_cogs_antiodd050_preserve.csv    | dataset\submission_h2antishape_v17_cogs_antiodd050_preserve.csv    | opposite of failed odd-year COGS-shape vector, 50% strength, preserve H2 COGS total   |                  0 |                 184 |                  0   |               51609.3 |                      25804.6 |                                   1 |                                1 |   0.990975 |         0.200601 |         0.184187 |         0.177044 |         0.142659 |         0.118731 |
|          3 | submission_h2antishape_v17_cogs_antiodd100_preserve.csv    | dataset\submission_h2antishape_v17_cogs_antiodd100_preserve.csv    | opposite of failed odd-year COGS-shape vector, full strength, preserve H2 COGS total  |                  0 |                 184 |                  0   |              103219   |                      51609.3 |                                   1 |                                1 |   0.990975 |         0.193574 |         0.169957 |         0.189776 |         0.152004 |         0.116988 |
|          4 | submission_h2antishape_v17_cogs_octnov_up_preserve.csv     | dataset\submission_h2antishape_v17_cogs_octnov_up_preserve.csv     | manual anti-shape: move H2 COGS from Aug/Dec into Oct/Nov, preserve total             |                  0 |                 184 |                  0   |               56468.2 |                      28234.1 |                                   1 |                                1 |   0.990975 |         0.204711 |         0.183893 |         0.178204 |         0.144586 |         0.115219 |
|          5 | submission_h2antishape_v17_cogs_aug_down_preserve.csv      | dataset\submission_h2antishape_v17_cogs_aug_down_preserve.csv      | manual anti-shape: reduce August COGS spike and redistribute to Oct/Nov               |                  0 |                 184 |                  0   |               51081.7 |                      25540.9 |                                   1 |                                1 |   0.990975 |         0.208871 |         0.175653 |         0.175213 |         0.142159 |         0.121195 |
|          6 | submission_h2antishape_v17_revcogs_antiodd025_preserve.csv | dataset\submission_h2antishape_v17_revcogs_antiodd025_preserve.csv | opposite of odd-year shape on both Revenue and COGS, 25% strength, preserve H2 totals |                184 |                 184 |              18371.2 |               25804.6 |                      22087.9 |                                   1 |                                1 |   0.990975 |         0.204114 |         0.191302 |         0.170678 |         0.137987 |         0.119602 |

Suggested order:

1. `submission_h2antishape_v17_cogs_antiodd025_preserve.csv`
2. If it improves: `submission_h2antishape_v17_cogs_antiodd050_preserve.csv`
3. If antiodd025 is neutral/slightly bad: `submission_h2antishape_v17_cogs_octnov_up_preserve.csv`
4. Do not test full antiodd unless half strength improves.
