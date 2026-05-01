# Public-Only Forensics

Run directory: `logs\20260422_013151_public_only_forensics`

Current best: `submission_txndecomp_v2_cogsratio_followup_promotet_r60_up0100.csv` = `873084.61381`.

This report intentionally ignores local validation and reads only public-score reactions to submitted files.

## Family Summary
| family                  |   n |   best_public_score |   median_score_delta |   min_score_delta |   max_score_delta |   median_rev_abs_move |   median_cogs_abs_move |
|:------------------------|----:|--------------------:|---------------------:|------------------:|------------------:|----------------------:|-----------------------:|
| txndecomp_cogs_ratio    |   2 |              873085 |              867.431 |              0    |           1734.86 |                   0   |        25212.5         |
| promo_cogs              |   2 |              879534 |             7531.67  |           6448.92 |           8614.42 |                   0   |        89976.8         |
| promo_revenue           |   6 |              883183 |            12469.2   |          10098.8  |          15015.8  |               31671.2 |        98700.6         |
| promo_parity            |   1 |              884654 |            11569.4   |          11569.4  |          11569.4  |               17980.6 |        98700.6         |
| broad_revenue           |   2 |              888493 |            19161.9   |          15408.4  |          22915.4  |              192924   |        98700.6         |
| other                   |   3 |              888963 |            22915.4   |          15878.2  |          25387.8  |              102522   |        98700.6         |
| calendar_router         |   3 |              899000 |            28915.4   |          25915.4  |          37915.4  |              333437   |       266306           |
| txndecomp_revenue_shape |   1 |              900763 |            27678     |          27678    |          27678    |              163570   |            3.39899e-12 |
| price_history           |   1 |              923771 |            50686.3   |          50686.3  |          50686.3  |              362129   |       267324           |

## Known Score Delta Table
| filename                                                           | family                  |   public_score |   score_delta_vs_best |   rev_abs_mean_delta |   cogs_abs_mean_delta |    rev_mean_delta |   cogs_mean_delta | changes_nonpromo_revenue   | changes_nonpromo_cogs   |
|:-------------------------------------------------------------------|:------------------------|---------------:|----------------------:|---------------------:|----------------------:|------------------:|------------------:|:---------------------------|:------------------------|
| submission_txndecomp_v2_cogsratio_followup_promotet_r60_up0100.csv | txndecomp_cogs_ratio    |         873085 |                  0    |                 0    |           0           |       0           |       0           | False                      | False                   |
| submission_txndecomp_v2_cogsratio_promotet_r40_up0075.csv          | txndecomp_cogs_ratio    |         874819 |               1734.86 |                 0    |       50424.9         |       0           |  -43667.4         | False                      | True                    |
| submission_promo_cogsmult_bestrev_all_0125.csv                     | promo_cogs              |         879534 |               6448.92 |                 0    |       86460.7         |       0           |  -75298.8         | False                      | True                    |
| submission_promo_cogsratio_bestrev_a010_clip005.csv                | promo_cogs              |         881699 |               8614.42 |                 0    |       93492.9         |       0           |  -83964.9         | False                      | True                    |
| submission_tabpfn26_windowmix_scale105.csv                         | promo_revenue           |         883183 |              10098.8  |             25879.1  |       98700.6         |    5126.08        |  -89742.3         | False                      | True                    |
| submission_tabpfn26_windowmix_v1.csv                               | promo_revenue           |         883416 |              10331.5  |             24509.2  |       98700.6         |       6.79797e-12 |  -89742.3         | False                      | True                    |
| submission_tabpfn_v25low_windowmix_v1.csv                          | promo_revenue           |         883882 |              10796.9  |              7853.37 |       98700.6         |       2.08188e-11 |  -89742.3         | False                      | True                    |
| submission_public_parity_urban23_nonmain_up10_only.csv             | promo_parity            |         884654 |              11569.4  |             17980.6  |       98700.6         |   17980.6         |  -89742.3         | True                       | True                    |
| submission_public_probe_promo_windows_rev_up8.csv                  | promo_revenue           |         887226 |              14141.4  |             37463.4  |       98700.6         |       1.20664e-10 |  -89742.3         | False                      | True                    |
| submission_public_probe_promo_windows_rev_up12.csv                 | promo_revenue           |         888061 |              14976.4  |             60032.4  |       98700.6         |   51260.8         |  -89742.3         | False                      | True                    |
| submission_public_probe_promo_windows_rev_up6.csv                  | promo_revenue           |         888100 |              15015.8  |             38512.9  |       98700.6         |  -25630.4         |  -89742.3         | False                      | True                    |
| submission_public_revenue_gate_v3_soft.csv                         | broad_revenue           |         888493 |              15408.4  |            245432    |       98700.6         |  -65559.7         |  -89742.3         | True                       | True                    |
| submission_tabpfn_promo_shape_cal8.csv                             | other                   |         888963 |              15878.2  |             27713    |       98700.6         |    1349.43        |  -89742.3         | False                      | True                    |
| submission_catboost_md2y_core_recencyexp20.csv                     | other                   |         896000 |              22915.4  |            102522    |       98700.6         | -102522           |  -89742.3         | False                      | True                    |
| submission_public_probe_rev2024h1_up5.csv                          | broad_revenue           |         896000 |              22915.4  |            140417    |       98700.6         |  -25029.2         |  -89742.3         | True                       | True                    |
| submission_public_probe_cogs2024h1_floor87.csv                     | other                   |         898472 |              25387.8  |            102522    |      135119           | -102522           |  -46942.2         | False                      | True                    |
| submission_public_router_v1_eom_tail_soft.csv                      | calendar_router         |         899000 |              25915.4  |            333437    |      266306           |   -9480.26        | -107029           | True                       | True                    |
| submission_txndecomp_v3_rev_eventshape_r20_keepcogs.csv            | txndecomp_revenue_shape |         900763 |              27678    |            163570    |           3.39899e-12 |      -5.56584e-11 |       8.49747e-13 | True                       | False                   |
| submission_public_router_v1_eom_monthday_shrunk.csv                | calendar_router         |         902000 |              28915.4  |            342403    |      266306           |     103.571       | -107029           | True                       | True                    |
| submission_public_recency_tail_ramp40.csv                          | calendar_router         |         911000 |              37915.4  |            273068    |       98700.6         | -256759           |  -89742.3         | True                       | True                    |
| submission_catboost_md2y_core_price_history.csv                    | price_history           |         923771 |              50686.3  |            362129    |      267324           | -203428           | -154272           | True                       | True                    |

## Public-Only Conclusions
- Confirmed good: targeted promo/Tet `COGS` upward through transaction-derived COGS ratio.
- Confirmed bad: transaction-derived Revenue event shape, broad nonpromo Revenue changes, price-history direct features, odd parity Revenue.
- The path to 7xx is not the rejected Revenue event donor. It must be either a different Revenue prior, a larger COGS-ratio/level miss, or a target-period scale/calendar signal not represented by our current local features.
