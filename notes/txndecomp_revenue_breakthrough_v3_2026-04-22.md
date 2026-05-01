# Transaction Revenue Breakthrough V3

Run directory: `logs\20260422_012055_txndecomp_revenue_breakthrough_v3`

Base: `submission_txndecomp_v2_cogsratio_followup_promotet_r60_up0100.csv` scored `873084.61381`.

## Why This Exists
COGS-only has improved public, but it is too small to reach 7xx. A 7xx jump requires Revenue daily-shape improvement on the order of `100k+` average absolute movement. These candidates keep current-best COGS fixed and only test Revenue shape from transaction decomposition.

## Candidate Manifest
| filename                                                       | path                                                                   | thesis                                                                                                     |   revenue_total_ratio_vs_best |   cogs_total_ratio_vs_best |   mean_abs_revenue_delta |   max_abs_revenue_delta |   mean_revenue_delta |   mean_abs_cogs_delta | changed_cogs   |
|:---------------------------------------------------------------|:-----------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------|------------------------------:|---------------------------:|-------------------------:|------------------------:|---------------------:|----------------------:|:---------------|
| submission_txndecomp_v3_rev_tetshift_r70_keepcogs.csv          | dataset\submission_txndecomp_v3_rev_tetshift_r70_keepcogs.csv          | Exact lunar Tet Revenue profile, monthly total preserved, COGS fixed                                       |                       1       |                          1 |                  20770.2 |        576061           |          6.79797e-12 |                     0 | False          |
| submission_txndecomp_v3_rev_monthshape_r08_keepcogs.csv        | dataset\submission_txndecomp_v3_rev_monthshape_r08_keepcogs.csv        | All-day transaction intra-month Revenue shape, monthly totals preserved, COGS fixed                        |                       1       |                          1 |                  90028.6 |             1.37895e+06 |          0           |                     0 | False          |
| submission_txndecomp_v3_rev_eventshape_r12_keepcogs.csv        | dataset\submission_txndecomp_v3_rev_eventshape_r12_keepcogs.csv        | Revenue-only event/promo/Tet transaction shape, monthly total preserved, COGS fixed                        |                       1       |                          1 |                  98474.7 |             2.35135e+06 |         -5.09848e-11 |                     0 | False          |
| submission_txndecomp_v3_rev_promoshape_r25_nocomp_keepcogs.csv | dataset\submission_txndecomp_v3_rev_promoshape_r25_nocomp_keepcogs.csv | Revenue-only promo shape without nonpromo compensation; tests whether promo total itself is wrong          |                       1.01293 |                          1 |                 105333   |             4.89864e+06 |      51686.2         |                     0 | False          |
| submission_txndecomp_v3_rev_monthshape_r14_keepcogs.csv        | dataset\submission_txndecomp_v3_rev_monthshape_r14_keepcogs.csv        | Aggressive all-day transaction intra-month Revenue shape, monthly totals preserved, COGS fixed             |                       1       |                          1 |                 156659   |             2.38915e+06 |          2.25183e-11 |                     0 | False          |
| submission_txndecomp_v3_rev_eventshape_r20_keepcogs.csv        | dataset\submission_txndecomp_v3_rev_eventshape_r20_keepcogs.csv        | High-upside Revenue-only event/promo/Tet transaction shape, monthly total preserved, COGS fixed            |                       1       |                          1 |                 163570   |             3.91891e+06 |         -7.22285e-11 |                     0 | False          |
| submission_txndecomp_v3_rev_promoshape_r40_nocomp_keepcogs.csv | dataset\submission_txndecomp_v3_rev_promoshape_r40_nocomp_keepcogs.csv | Aggressive Revenue-only promo shape without nonpromo compensation                                          |                       1.02068 |                          1 |                 168533   |             7.83782e+06 |      82697.9         |                     0 | False          |
| submission_txndecomp_v3_rev_eventshape_r28_clip_keepcogs.csv   | dataset\submission_txndecomp_v3_rev_eventshape_r28_clip_keepcogs.csv   | Aggressive but clipped Revenue-only event/promo/Tet transaction shape, monthly total preserved, COGS fixed |                       1       |                          1 |                 227076   |             5.48647e+06 |          8.32752e-11 |                     0 | False          |

## Suggested Order
1. `submission_txndecomp_v3_rev_eventshape_r20_keepcogs.csv`
2. `submission_txndecomp_v3_rev_eventshape_r12_keepcogs.csv`
3. `submission_txndecomp_v3_rev_monthshape_r08_keepcogs.csv`
4. `submission_txndecomp_v3_rev_promoshape_r25_nocomp_keepcogs.csv`
5. `submission_txndecomp_v3_rev_eventshape_r28_clip_keepcogs.csv`
