# Clean V5 R2 Target Sweep

Run directory: `logs\20260424_165055_clean_v5_r2_target_sweep`

## Goal

Map how far we must move from `c110` toward transaction-month shape/level to reach public-like R2 around 0.72.

## Boundary

This is a research sweep. The transaction-month donor uses provided transaction tables and preserves or partially moves period totals depending on mode. Do not present the `level_blend` candidates as strict clean final without explaining their calibration source.

## Candidate Manifest

|   priority | filename                                            | mode                   |   alpha |   revenue_total |   cogs_total |   ratio_total |   max_revenue |    max_cogs | note                                                                                          |
|-----------:|:----------------------------------------------------|:-----------------------|--------:|----------------:|-------------:|--------------:|--------------:|------------:|:----------------------------------------------------------------------------------------------|
|          1 | submission_cleanv5_r2_txnshape_preserve_a350.csv    | shape_preserve         |    0.35 |     2.36346e+09 |  2.12485e+09 |      0.89904  |   1.39899e+07 | 1.27309e+07 | Increase transaction-derived intra-period shape while preserving c110 period totals.          |
|          2 | submission_cleanv5_r2_txnshape_preserve_a500.csv    | shape_preserve         |    0.5  |     2.36346e+09 |  2.12485e+09 |      0.89904  |   1.47601e+07 | 1.30955e+07 | Increase transaction-derived intra-period shape while preserving c110 period totals.          |
|          3 | submission_cleanv5_r2_txnshape_preserve_a650.csv    | shape_preserve         |    0.65 |     2.36346e+09 |  2.12485e+09 |      0.89904  |   1.55303e+07 | 1.346e+07   | Increase transaction-derived intra-period shape while preserving c110 period totals.          |
|          4 | submission_cleanv5_r2_txnshape_preserve_a800.csv    | shape_preserve         |    0.8  |     2.36346e+09 |  2.12485e+09 |      0.89904  |   1.63006e+07 | 1.38245e+07 | Increase transaction-derived intra-period shape while preserving c110 period totals.          |
|          5 | submission_cleanv5_r2_txnshape_preserve_a1000.csv   | shape_preserve         |    1    |     2.36346e+09 |  2.12485e+09 |      0.89904  |   1.73275e+07 | 1.43106e+07 | Increase transaction-derived intra-period shape while preserving c110 period totals.          |
|          6 | submission_cleanv5_r2_level_to_txnmonth_a100.csv    | level_blend            |    0.1  |     2.34623e+09 |  2.09736e+09 |      0.89393  |   1.25291e+07 | 1.19135e+07 | Blend c110 directly toward txn-month donor to map the R2-vs-level tradeoff.                   |
|          7 | submission_cleanv5_r2_level_to_txnmonth_a200.csv    | level_blend            |    0.2  |     2.32899e+09 |  2.06988e+09 |      0.888743 |   1.28655e+07 | 1.19467e+07 | Blend c110 directly toward txn-month donor to map the R2-vs-level tradeoff.                   |
|          8 | submission_cleanv5_r2_level_to_txnmonth_a300.csv    | level_blend            |    0.3  |     2.31176e+09 |  2.04239e+09 |      0.88348  |   1.32019e+07 | 1.19798e+07 | Blend c110 directly toward txn-month donor to map the R2-vs-level tradeoff.                   |
|          9 | submission_cleanv5_r2_level_to_txnmonth_a400.csv    | level_blend            |    0.4  |     2.29453e+09 |  2.01491e+09 |      0.878137 |   1.35383e+07 | 1.2013e+07  | Blend c110 directly toward txn-month donor to map the R2-vs-level tradeoff.                   |
|         10 | submission_cleanv5_r2_level_to_txnmonth_a500.csv    | level_blend            |    0.5  |     2.27729e+09 |  1.98743e+09 |      0.872714 |   1.38747e+07 | 1.20462e+07 | Blend c110 directly toward txn-month donor to map the R2-vs-level tradeoff.                   |
|         11 | submission_cleanv5_r2_periodlevel_txnshape_a100.csv | period_total_shape_mix |    0.1  |     2.34623e+09 |  2.09736e+09 |      0.89393  |   1.71504e+07 | 1.41007e+07 | Use full txn-month daily shape, but move only period totals gradually toward txn-month donor. |
|         12 | submission_cleanv5_r2_periodlevel_txnshape_a200.csv | period_total_shape_mix |    0.2  |     2.32899e+09 |  2.06988e+09 |      0.888743 |   1.69733e+07 | 1.38908e+07 | Use full txn-month daily shape, but move only period totals gradually toward txn-month donor. |
|         13 | submission_cleanv5_r2_periodlevel_txnshape_a300.csv | period_total_shape_mix |    0.3  |     2.31176e+09 |  2.04239e+09 |      0.88348  |   1.67962e+07 | 1.3681e+07  | Use full txn-month daily shape, but move only period totals gradually toward txn-month donor. |
|         14 | submission_cleanv5_r2_periodlevel_txnshape_a400.csv | period_total_shape_mix |    0.4  |     2.29453e+09 |  2.01491e+09 |      0.878137 |   1.66191e+07 | 1.34711e+07 | Use full txn-month daily shape, but move only period totals gradually toward txn-month donor. |
