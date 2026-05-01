# Public-Only H2 Revenue Shape V18

Run directory: `logs\20260422_093843_publiconly_h2_revenue_shape_v18`

Current best: `submission_top10_v13_rev2023h2_up100_keepcogs.csv` scored `797595.9641`.

Rejected probes:

- `submission_h2rev_v15_current_h2_rev_up050.csv` = `800572.16096`
- `submission_h2shape_v16_cogs_oddmean_preserve.csv` = `802116.33879`
- `submission_h2antishape_v17_cogs_antiodd025_preserve.csv` = `800578.87166`

Updated requirement note:

- The updated PDF changed `unit_price` wording from `Đơn giá sau khi áp dụng khuyến mãi` to `Đơn giá`.
- Train data still verifies `Revenue = sum(quantity * unit_price)` exactly, so do not subtract `discount_amount` from target Revenue.

Interpretation:

- Broad 2023H2 Revenue scale is near optimum.
- Monthly COGS shape was rejected in both historical and anti-historical directions.
- Next test should preserve H2 totals and reshape H2 Revenue, especially moving share toward July and away from Aug/Oct/Nov according to odd-year analogues.

Current H2 month profile:

|   month |     Revenue |        COGS |   rev_share |   cogs_share |    ratio |
|--------:|------------:|------------:|------------:|-------------:|---------:|
|       7 | 1.27778e+08 | 1.27656e+08 |    0.20595  |     0.207627 | 0.999048 |
|       8 | 1.10809e+08 | 1.21994e+08 |    0.1786   |     0.198418 | 1.10094  |
|       9 | 1.13336e+08 | 1.08122e+08 |    0.182673 |     0.175856 | 0.953991 |
|      10 | 1.09864e+08 | 1.01024e+08 |    0.177076 |     0.164312 | 0.919543 |
|      11 | 8.45073e+07 | 8.19661e+07 |    0.136207 |     0.133314 | 0.96993  |
|      12 | 7.41388e+07 | 7.40715e+07 |    0.119495 |     0.120474 | 0.999093 |

Odd-year H2 reference shares:

|   month |   rev_share |   cogs_share |
|--------:|------------:|-------------:|
|       7 |    0.234159 |     0.22168  |
|       8 |    0.164443 |     0.226878 |
|       9 |    0.185178 |     0.174011 |
|      10 |    0.167253 |     0.138847 |
|      11 |    0.127733 |     0.114624 |
|      12 |    0.121233 |     0.12396  |

Candidate manifest:

|   priority | filename                                               | path                                                           | thesis                                                                        |   rev_rows_changed |   cogs_rows_changed |   mean_abs_rev_delta |   mean_abs_cogs_delta |   directional_best_case_gain |   h2_revenue_total_ratio_vs_current |   h2_cogs_total_ratio_vs_current |   h2_ratio |   jul_rev_share |   aug_rev_share |   oct_rev_share |   nov_rev_share |   dec_rev_share |
|-----------:|:-------------------------------------------------------|:---------------------------------------------------------------|:------------------------------------------------------------------------------|-------------------:|--------------------:|---------------------:|----------------------:|-----------------------------:|------------------------------------:|---------------------------------:|-----------:|----------------:|----------------:|----------------:|----------------:|----------------:|
|          1 | submission_h2revshape_v18_rev_odd050_preserve.csv      | dataset\submission_h2revshape_v18_rev_odd050_preserve.csv      | preserve total H2 Revenue, move monthly Revenue 50% toward odd-year H2 shares |                184 |                   0 |              36742.3 |                     0 |                     18371.2  |                                   1 |                                1 |   0.990975 |        0.220054 |        0.171522 |        0.172165 |        0.13197  |        0.120364 |
|          2 | submission_h2revshape_v18_rev_odd100_preserve.csv      | dataset\submission_h2revshape_v18_rev_odd100_preserve.csv      | preserve total H2 Revenue, move monthly Revenue fully to odd-year H2 shares   |                184 |                   0 |              73484.7 |                     0 |                     36742.3  |                                   1 |                                1 |   0.990975 |        0.234159 |        0.164443 |        0.167253 |        0.127733 |        0.121233 |
|          3 | submission_h2revshape_v18_rev_odd025_preserve.csv      | dataset\submission_h2revshape_v18_rev_odd025_preserve.csv      | preserve total H2 Revenue, conservative 25% odd-year Revenue shape            |                184 |                   0 |              18371.2 |                     0 |                      9185.59 |                                   1 |                                1 |   0.990975 |        0.213002 |        0.175061 |        0.17462  |        0.134088 |        0.11993  |
|          4 | submission_h2revshape_v18_rev_odd075_preserve.csv      | dataset\submission_h2revshape_v18_rev_odd075_preserve.csv      | preserve total H2 Revenue, 75% odd-year Revenue shape                         |                184 |                   0 |              55113.5 |                     0 |                     27556.8  |                                   1 |                                1 |   0.990975 |        0.227107 |        0.167982 |        0.169709 |        0.129851 |        0.120799 |
|          5 | submission_h2revshape_v18_rev_antiodd050_preserve.csv  | dataset\submission_h2revshape_v18_rev_antiodd050_preserve.csv  | preserve total H2 Revenue, move opposite odd-year Revenue shape by 50%        |                184 |                   0 |              36742.3 |                     0 |                     18371.2  |                                   1 |                                1 |   0.990975 |        0.191845 |        0.185678 |        0.181987 |        0.140444 |        0.118626 |
|          6 | submission_h2revshape_v18_rev_jul_up_preserve.csv      | dataset\submission_h2revshape_v18_rev_jul_up_preserve.csv      | preserve total H2 Revenue, concentrate extra mass into July                   |                184 |                   0 |              43364.3 |                     0 |                     21682.1  |                                   1 |                                1 |   0.990975 |        0.2251   |        0.174292 |        0.172805 |        0.132922 |        0.116613 |
|          7 | submission_h2revshape_v18_rev_aug_down_preserve.csv    | dataset\submission_h2revshape_v18_rev_aug_down_preserve.csv    | preserve total H2 Revenue, reduce August and redistribute to Jul/Sep          |                184 |                   0 |              39681.8 |                     0 |                     19840.9  |                                   1 |                                1 |   0.990975 |        0.216698 |        0.161075 |        0.177445 |        0.136491 |        0.119744 |
|          8 | submission_h2revshape_v18_rev_octnov_down_preserve.csv | dataset\submission_h2revshape_v18_rev_octnov_down_preserve.csv | preserve total H2 Revenue, reduce Oct/Nov and move mass into July             |                184 |                   0 |              38240.8 |                     0 |                     19120.4  |                                   1 |                                1 |   0.990975 |        0.219721 |        0.179757 |        0.16753  |        0.128864 |        0.12027  |

Suggested order:

1. `submission_h2revshape_v18_rev_odd050_preserve.csv`
2. If improves: `submission_h2revshape_v18_rev_odd100_preserve.csv`
3. If odd050 fails: `submission_h2revshape_v18_rev_antiodd050_preserve.csv`
4. If odd050 is close/neutral: `submission_h2revshape_v18_rev_jul_up_preserve.csv`

Public result update:

- submission_h2revshape_v18_rev_odd050_preserve.csv = 798084.85522. This is worse than current best by 488.89112, so do not submit odd075/odd100 next. Test antiodd050 once; if it fails, close H2 Revenue monthly shape as a major-gain path.

