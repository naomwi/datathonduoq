# Transaction Decomposition V2

Run directory: `logs\20260422_001621_transaction_decomposition_v2`

Base public best: `submission_promo_cogsmult_bestrev_all_0125.csv`.

## Thesis
Historical targets are transaction aggregates:

- `Revenue = sum(quantity * unit_price)`.
- `COGS = sum(quantity * product.cogs)`.

This sprint does not replace the current public winner with raw bottom-up forecasts. It uses transaction decomposition as a shape donor around the public winner.

## Candidate Manifest
| filename                                                  | path                                                              | thesis                                                                                              |   revenue_total_ratio_vs_best |   cogs_total_ratio_vs_best |   mean_abs_revenue_delta |   mean_abs_cogs_delta |   max_abs_revenue_delta |   max_abs_cogs_delta | changed_nonpromo_revenue   | changed_nonpromo_cogs   |
|:----------------------------------------------------------|:------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------|------------------------------:|---------------------------:|-------------------------:|----------------------:|------------------------:|---------------------:|:---------------------------|:------------------------|
| submission_txndecomp_v2_monthshape_r10_c10.csv            | dataset\submission_txndecomp_v2_monthshape_r10_c10.csv            | transaction component intra-month shape, month totals preserved                                     |                             1 |                    1       |                112323    |              99604.7  |             1.71794e+06 |          1.5444e+06  | True                       | True                    |
| submission_txndecomp_v2_monthshape_r18_c12.csv            | dataset\submission_txndecomp_v2_monthshape_r18_c12.csv            | transaction component intra-month shape, month totals preserved                                     |                             1 |                    1       |                200663    |             119286    |             3.05152e+06 |          1.84619e+06 | True                       | True                    |
| submission_txndecomp_v2_eventshape_r20.csv                | dataset\submission_txndecomp_v2_eventshape_r20.csv                | transaction component shape only on promo/Tet/same-day-sale windows, month totals preserved         |                             1 |                    1       |                163570    |             157947    |             3.91891e+06 |          3.55513e+06 | True                       | True                    |
| submission_txndecomp_v2_eventshape_r35.csv                | dataset\submission_txndecomp_v2_eventshape_r35.csv                | transaction component shape only on promo/Tet/same-day-sale windows, month totals preserved         |                             1 |                    1       |                282508    |             273509    |             6.85809e+06 |          6.22148e+06 | True                       | True                    |
| submission_txndecomp_v2_tetshift_r25.csv                  | dataset\submission_txndecomp_v2_tetshift_r25.csv                  | exact lunar Tet offset profile instead of Gregorian Jan/Feb-only calendar                           |                             1 |                    1       |                  7401.38 |               5480.17 |        204466           |     202134           | True                       | True                    |
| submission_txndecomp_v2_tetshift_r40.csv                  | dataset\submission_txndecomp_v2_tetshift_r40.csv                  | exact lunar Tet offset profile instead of Gregorian Jan/Feb-only calendar                           |                             1 |                    1       |                 11851    |               8773.83 |        327820           |     323948           | True                       | True                    |
| submission_txndecomp_v2_cogsratio_promotet_r25_up005.csv  | dataset\submission_txndecomp_v2_cogsratio_promotet_r25_up005.csv  | component-derived COGS ratio on promo/Tet plus continuation of confirmed promo COGS public gradient |                             1 |                    1.00595 |                     0    |              22764    |             0           |     279821           | False                      | True                    |
| submission_txndecomp_v2_cogsratio_promotet_r40_up0075.csv | dataset\submission_txndecomp_v2_cogsratio_promotet_r40_up0075.csv | component-derived COGS ratio on promo/Tet plus continuation of confirmed promo COGS public gradient |                             1 |                    1.00937 |                     0    |              36036.4  |             0           |     445686           | False                      | True                    |
| submission_txndecomp_v2_combo_event25_cogs35.csv          | dataset\submission_txndecomp_v2_combo_event25_cogs35.csv          | combined event transaction-shape revenue and component COGS-ratio correction                        |                             1 |                    1.00764 |                203282    |              30095.5  |             4.89864e+06 |     379666           | True                       | True                    |

## Donor Shape Summary
| metric | value |
|:--|--:|
| revenue_shape_min | 0.3509 |
| revenue_shape_max | 2.5669 |
| cogs_shape_min | 0.3519 |
| cogs_shape_max | 2.7148 |
| event_rows | 264 |
| promo_rows | 183 |
| tet_rows | 72 |

## Submit Guidance
These are higher-variance breakthrough probes. Submit after the pure COGS-gradient probe unless you want to spend a slot on the structural hypothesis immediately.

Recommended structural order:

1. `submission_txndecomp_v2_eventshape_r20.csv`
2. `submission_txndecomp_v2_cogsratio_promotet_r25_up005.csv`
3. `submission_txndecomp_v2_tetshift_r25.csv`
4. `submission_txndecomp_v2_combo_event25_cogs35.csv`
5. `submission_txndecomp_v2_monthshape_r10_c10.csv`
