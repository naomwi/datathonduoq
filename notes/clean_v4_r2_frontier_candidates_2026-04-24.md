# Clean V4 R2 Frontier Candidates

Run directory: `logs\20260424_164714_clean_v4_r2_frontier_candidates`

## Goal

Improve final-score safety by lifting public-like R2 and reducing RMSE while keeping public MAE close to the current clean best.

## Base

- Base file: `submission_cleanv3_funnel_c110_h1r0876.csv`
- R2 level donor: `submission_cleanv3_head_funnel_last_c10_h1only_r0876.csv`

## Candidate Manifest

|   priority | filename                                                 | status   | mode                        | donor_file                                                   |   alpha |   rows |   revenue_total |   cogs_total |   ratio_total |   max_revenue |    max_cogs | note                                                                                                      |
|-----------:|:---------------------------------------------------------|:---------|:----------------------------|:-------------------------------------------------------------|--------:|-------:|----------------:|-------------:|--------------:|--------------:|------------:|:----------------------------------------------------------------------------------------------------------|
|          1 | submission_cleanv4_r2_level_c110_to_c10_a025.csv         | written  | level_blend                 | submission_cleanv3_head_funnel_last_c10_h1only_r0876.csv     |    0.25 |    548 |     2.36007e+09 |  2.12188e+09 |      0.899073 |   1.21442e+07 | 1.18331e+07 | Small move from public-best c110 toward c10, which has better public-like RMSE/R2.                        |
|          2 | submission_cleanv4_r2_level_c110_to_c10_a050.csv         | written  | level_blend                 | submission_cleanv3_head_funnel_last_c10_h1only_r0876.csv     |    0.5  |    548 |     2.35668e+09 |  2.11891e+09 |      0.899106 |   1.20956e+07 | 1.17857e+07 | Midpoint on MAE/R2 frontier between c110 and c10.                                                         |
|          3 | submission_cleanv4_r2_level_c110_to_c10_a075.csv         | written  | level_blend                 | submission_cleanv3_head_funnel_last_c10_h1only_r0876.csv     |    0.75 |    548 |     2.35329e+09 |  2.11594e+09 |      0.89914  |   1.20471e+07 | 1.17384e+07 | Aggressive R2 move toward c10 while staying inside the known clean-public band.                           |
|          4 | submission_cleanv4_r2_shape_legalrawmd_a010_preserve.csv | written  | shape_preserve_both         | submission_legal_rawmd_prior_v3_r080_c065_h2r010.csv         |    0.1  |    548 |     2.36346e+09 |  2.12485e+09 |      0.89904  |   1.21843e+07 | 1.18721e+07 | Borrow only daily shape from legal raw-md prior; preserve c110 period totals.                             |
|          5 | submission_cleanv4_r2_shape_legalrawmd_a020_preserve.csv | written  | shape_preserve_both         | submission_legal_rawmd_prior_v3_r080_c065_h2r010.csv         |    0.2  |    548 |     2.36346e+09 |  2.12485e+09 |      0.89904  |   1.21759e+07 | 1.18638e+07 | Stronger daily-shape borrow from legal raw-md prior; preserve period totals.                              |
|          6 | submission_cleanv4_r2_shape_cleanroom_a010_preserve.csv  | written  | shape_preserve_both         | submission_cleanroom_rawmd_r070_c060_h2r020_conservative.csv |    0.1  |    548 |     2.36346e+09 |  2.12485e+09 |      0.89904  |   1.22197e+07 | 1.18898e+07 | Strict-clean raw-md daily-shape borrow; preserve c110 period totals.                                      |
|          7 | submission_cleanv4_r2_shape_cleanroom_a020_preserve.csv  | written  | shape_preserve_both         | submission_cleanroom_rawmd_r070_c060_h2r020_conservative.csv |    0.2  |    548 |     2.36346e+09 |  2.12485e+09 |      0.89904  |   1.22467e+07 | 1.18992e+07 | Stronger strict-clean shape borrow; preserve c110 period totals.                                          |
|          8 | submission_cleanv4_r2_shape_txnmonth_a010_preserve.csv   | written  | shape_preserve_both         | submission_txndecomp_v2_monthshape_r18_c12.csv               |    0.1  |    548 |     2.36346e+09 |  2.12485e+09 |      0.89904  |   1.27062e+07 | 1.21234e+07 | Research shape donor with strong public-like R2; preserve c110 period totals.                             |
|          9 | submission_cleanv4_r2_shape_txnmonth_a020_preserve.csv   | written  | shape_preserve_both         | submission_txndecomp_v2_monthshape_r18_c12.csv               |    0.2  |    548 |     2.36346e+09 |  2.12485e+09 |      0.89904  |   1.32197e+07 | 1.23664e+07 | Stronger transaction-month shape borrow; preserve c110 period totals.                                     |
|         10 | submission_cleanv4_r2_level025_shape_cleanroom015.csv    | written  | level025_shape_cleanroom015 | submission_cleanroom_rawmd_r070_c060_h2r020_conservative.csv |    0.15 |    548 |     2.36007e+09 |  2.12188e+09 |      0.899073 |   1.21845e+07 | 1.18472e+07 | Hybrid: small c10 level move plus strict-clean shape smoothing, period totals after level move preserved. |

## Suggested Test Order

1. `submission_cleanv4_r2_level_c110_to_c10_a025.csv`
2. `submission_cleanv4_r2_level025_shape_cleanroom015.csv`
3. `submission_cleanv4_r2_shape_cleanroom_a010_preserve.csv`
4. `submission_cleanv4_r2_level_c110_to_c10_a050.csv`

Interpretation: if level blend improves or holds MAE, move toward c10. If shape-preserve improves, R2 is coming from daily allocation rather than period level.
