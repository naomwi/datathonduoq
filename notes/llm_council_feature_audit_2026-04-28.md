# LLM Council Feature Audit

Run directory: `logs\20260428_131343_llm_council_feature_audit`

## Boundary

This is a clean-feature discovery audit. It does not use `sample_submission.csv`, previous submissions, public-blackbox files, or test target values as inputs.

The method follows a practical LLM-council style:

- Business analyst: convert the PDF into business mechanisms.
- Data scientist: quantify train evidence and regime shifts.
- ML engineer: map mechanisms to model layers.
- Checker: classify clean legality and leakage risk.

## Current Clean Status

- Current clean best public: `submission_cleanv2_h1fine_b044_r0876.csv = 673757.34993`.
- Latest operational COGS-ratio probe failed: `submission_cleanv4_opratio_g020.csv = 677137.31895`.
- Interpretation: daily operational COGS-ratio priors are not the missing clean signal; focus should move back to period-total/funnel features.

## Driver Decomposition

| metric     |   pre2019_monthly_avg |   post2018_monthly_avg |   post_vs_pre_pct |
|:-----------|----------------------:|-----------------------:|------------------:|
| revenue    |           1.56734e+08 |            9.17521e+07 |        -0.414601  |
| cogs       |           1.35044e+08 |            8.02675e+07 |        -0.405619  |
| sessions   |      677999           |       888263           |         0.310124  |
| orders     |        6498.38        |         3062.73        |        -0.528693  |
| conversion |           0.00985198  |            0.00348071  |        -0.646699  |
| aov        |       24190           |        30083.5         |         0.243636  |
| cogs_ratio |           0.872475    |            0.88559     |         0.0150322 |

## Top Raw-Derived Feature Signals

| feature                                | group           | future_policy                       |   abs_max_corr |   corr_revenue |   corr_cogs |   corr_cogs_ratio |   post_vs_pre_pct |   monthday_cv |
|:---------------------------------------|:----------------|:------------------------------------|---------------:|---------------:|------------:|------------------:|------------------:|--------------:|
| gross_cogs_reconstructed               | price_basket    | unknown_future_use_train_prior_only |       1        |      0.976022  |   1         |         0.0206875 |      -0.405754    |     0.508368  |
| gross_rev_reconstructed                | price_basket    | unknown_future_use_train_prior_only |       1        |      1         |   0.976022  |        -0.166735  |      -0.414735    |     0.514284  |
| margin_rate                            | price_basket    | unknown_future_use_train_prior_only |       1        |      0.166735  |  -0.0206875 |        -1         |      -0.0991681   |     0.742338  |
| unique_customers                       | funnel          | unknown_future_use_train_prior_only |       0.965337 |      0.938689  |   0.965337  |         0.0346962 |      -0.527182    |     0.542019  |
| order_count                            | funnel          | unknown_future_use_train_prior_only |       0.964407 |      0.937662  |   0.964407  |         0.0349482 |      -0.528801    |     0.543139  |
| total_units                            | other           | audit_before_public_use             |       0.949842 |      0.92159   |   0.949842  |         0.0411217 |      -0.548235    |     0.545247  |
| active_promo_discount_value_mean       | promo           | known_or_policy_future              |       0.917759 |     -0.150296  |   0.0278894 |         0.917759  |       0.0010735   |     1.03857   |
| promo_category_cogs_ratio_te           | promo           | known_or_policy_future              |       0.915618 |     -0.116953  |   0.0553158 |         0.915618  |       0.00566202  |     0.0912431 |
| promo_type_cogs_ratio_te               | promo           | known_or_policy_future              |       0.8985   |     -0.130674  |   0.0368195 |         0.8985    |       0.00905579  |     0.087092  |
| active_promo_category_streetwear_count | promo           | known_or_policy_future              |       0.787578 |     -0.061262  |   0.0880397 |         0.787578  |      -0.000228154 |     3.07946   |
| active_promo_type_fixed_count          | promo           | known_or_policy_future              |       0.787578 |     -0.061262  |   0.0880397 |         0.787578  |      -0.000228154 |     3.07946   |
| active_promo_discount_value_fixed_mean | promo           | known_or_policy_future              |       0.787578 |     -0.061262  |   0.0880397 |         0.787578  |      -0.000228154 |     3.07946   |
| active_promo_category_streetwear_share | promo           | known_or_policy_future              |       0.786572 |     -0.0692323 |   0.074607  |         0.786572  |      -0.000228154 |     3.12755   |
| active_promo_type_fixed_share          | promo           | known_or_policy_future              |       0.786572 |     -0.0692323 |   0.074607  |         0.786572  |      -0.000228154 |     3.12755   |
| shipping_fee_total                     | logistics       | unknown_future_use_train_prior_only |       0.773351 |      0.708041  |   0.773351  |         0.193708  |      -0.624929    |     0.587565  |
| promo_channel_cogs_ratio_te            | promo           | known_or_policy_future              |       0.749894 |     -0.0719773 |   0.0822075 |         0.749894  |       0.00856898  |     0.0807882 |
| gross_margin                           | price_basket    | unknown_future_use_train_prior_only |       0.726722 |      0.687238  |   0.512635  |        -0.726722  |      -0.470645    |     0.887784  |
| conversion_proxy                       | funnel          | unknown_future_use_train_prior_only |       0.656304 |      0.626526  |   0.656304  |         0.0297273 |      -0.646617    |     0.407235  |
| promo_duration_days_mean               | promo           | known_or_policy_future              |       0.651598 |     -0.165936  |  -0.0330663 |         0.651598  |      -0.00446796  |     1.02957   |
| active_promo_count                     | promo           | known_or_policy_future              |       0.645899 |     -0.100873  |   0.0418425 |         0.645899  |       0.000254361 |     0.986775  |
| active_promo_min_order_value_mean      | promo           | known_or_policy_future              |       0.626448 |     -0.0513851 |   0.0735269 |         0.626448  |      -0.0700274   |     2.10706   |
| active_promo_channel_online_count      | promo           | known_or_policy_future              |       0.602555 |      0.0154562 |   0.143553  |         0.602555  |       0.269447    |     3.21526   |
| review_count                           | returns_reviews | unknown_future_use_train_prior_only |       0.599693 |      0.571525  |   0.56502   |        -0.0450378 |      -0.555873    |     0.344678  |
| promo_line_share                       | promo           | known_or_policy_future              |       0.593691 |     -0.117435  |   0.0113158 |         0.593691  |      -0.0079649   |     1.17732   |
| active_promo_channel_online_share      | promo           | known_or_policy_future              |       0.589333 |      0.012336  |   0.134737  |         0.589333  |       0.276736    |     3.07946   |

## Council Candidate Backlog

|   rank | hypothesis                        | missing_mechanism                                                                                                               | evidence                                                                          | raw_sources                                             | model_layer                                     | clean_status                                                                                                          | next_experiment                                                                                                                         |
|-------:|:----------------------------------|:--------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------|:--------------------------------------------------------|:------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------|
|      1 | period_total_funnel_head_v1       | The clean winner tunes period totals, but not through an explicit sessions x conversion x AOV decomposition.                    | sessions +31.0%, orders -52.9%, conversion -64.7%, AOV +24.4% post2018 vs pre2019 | web_traffic.csv, orders.csv, order_items.csv, sales.csv | period-total head                               | strict clean if weights selected by rolling folds; clean-input public-guided if using public to choose regime weights | Train/validate period totals for Revenue and COGS via sessions_prior, conversion_regime, AOV_regime; daily shape stays raw-md/calendar. |
|      2 | source_quality_conversion_head_v1 | Traffic volume is not equal to buying intent; source-specific conversion/revenue per session may explain regime shift.          | post2018 rev/session social=121.38, organic=89.35                                 | web_traffic.csv, orders.csv, order_items.csv            | period-total/funnel head, not daily postprocess | strict clean if future source mix is month/era prior; no future actual source shares                                  | Forecast effective_sessions = sum(source_sessions_prior * source_revenue_per_session_regime), then blend into period totals.            |
|      3 | customer_cohort_repeat_head_v1    | Feature pipeline has new/customers counts but not repeat-customer share, tenure, age/gender/acquisition mix as a regime driver. | repeat_order_share 82.3%->95.6%, tenure 95->749 days                              | orders.csv, customers.csv                               | period-total head and validation segmentation   | strict clean with historical cohort priors; future actual customers/orders are not allowed                            | Build repeat/tenure monthly priors and test if they explain conversion collapse on rolling folds.                                       |
|      4 | orderdate_return_leakage_head_v1  | Current return features are by return_date; revenue leakage is more naturally attached to original order_date/category/size.    | top refund reason/category: wrong_size / Streetwear = 134,706,817                 | returns.csv, orders.csv, order_items.csv, products.csv  | COGS/Revenue netting or COGS-ratio head         | strict clean using train return-rate priors by category/size/month; no future return actuals                          | Re-align refunds to order_date and create expected_refund_rate prior; test period-level net revenue/COGS adjustment.                    |
|      5 | sku_size_stockout_pressure_v1     | Existing inventory features are category-level; PDF says stockouts are concentrated in high-demand Streetwear SKUs/sizes.       | Streetwear stockout_days=35,082, fill_rate=96.06%                                 | inventory.csv, products.csv, order_items.csv            | period-total head or product-mix constraint     | strict clean only as historical stockout-pressure prior; do not use future actual inventory                           | Build SKU/size/color stockout_pressure x historical demand share; test if it improves COGS ratio or level folds.                        |
|      6 | cod_effective_order_quality_v1    | COD can inflate gross order intent while producing cancellations; better modeled as effective_orders.                           | COD cancel 16.0% vs non-COD 8.0%                                                  | orders.csv, payments.csv                                | funnel conversion head                          | strict clean with train COD risk priors by month/source/region                                                        | orders_effective = orders_prior * (1 - cod_share_prior * excess_cod_cancel_rate); validate on post2018 folds.                           |

## Source Quality Snapshot

| era      | source         |   orders |   order_value |   cancelled_share |   sessions |   unique_visitors |   orders_per_session |   revenue_per_session |
|:---------|:---------------|---------:|--------------:|------------------:|-----------:|------------------:|---------------------:|----------------------:|
| post2018 | social_media   |    29578 |   8.42451e+08 |         0.0920279 |    6940517 |           5283250 |           0.00426164 |              121.382  |
| post2018 | direct         |    11727 |   3.35278e+08 |         0.0927774 |    3016627 |           2281321 |           0.00388745 |              111.143  |
| post2018 | paid_search    |    32298 |   9.25332e+08 |         0.0908106 |    8990983 |           6835212 |           0.00359227 |              102.918  |
| post2018 | referral       |    14665 |   4.21247e+08 |         0.0925332 |    4451629 |           3395344 |           0.0032943  |               94.6277 |
| post2018 | organic_search |    41158 |   1.17025e+09 |         0.0957287 |   13098029 |           9950829 |           0.0031423  |               89.3455 |
| post2018 | email_campaign |    17585 |   4.99661e+08 |         0.0913278 |    6138828 |           4676270 |           0.00286455 |               81.3935 |
| pre2019  | direct         |    37715 |   8.70563e+08 |         0.0928013 |    3554922 |           2705329 |           0.0106092  |              244.89   |
| pre2019  | social_media   |    93683 |   2.15053e+09 |         0.0912225 |    8875709 |           6764815 |           0.010555   |              242.293  |
| pre2019  | paid_search    |   102370 |   2.35141e+09 |         0.0911009 |   10607288 |           8087174 |           0.00965091 |              221.679  |
| pre2019  | organic_search |   131316 |   3.00724e+09 |         0.0913065 |   14098947 |          10674278 |           0.00931389 |              213.295  |
| pre2019  | referral       |    46691 |   1.07181e+09 |         0.0937654 |    5025216 |           3824675 |           0.00929134 |              213.285  |
| pre2019  | email_campaign |    56108 |   1.2936e+09  |         0.0922863 |    6653842 |           5024192 |           0.00843242 |              194.415  |

## Payment Cancellation Snapshot

| payment_method   |   orders |   cancelled |   returned_status |   cancel_rate |   returned_status_rate |
|:-----------------|---------:|------------:|------------------:|--------------:|-----------------------:|
| credit_card      |   338551 |       27047 |             16896 |     0.0798905 |              0.0499068 |
| paypal           |    92345 |        7454 |              4617 |     0.080719  |              0.0499973 |
| cod              |    91941 |       14753 |              8176 |     0.160462  |              0.0889266 |
| apple_pay        |    61496 |        4908 |              3114 |     0.0798101 |              0.0506374 |
| bank_transfer    |    30561 |        2402 |              1520 |     0.0785969 |              0.0497366 |

## Customer Cohort Snapshot

| era      |   orders |   unique_customers |   repeat_order_share |   avg_customer_tenure_days |   mobile_order_share |   cod_order_share |
|:---------|---------:|-------------------:|---------------------:|---------------------------:|---------------------:|------------------:|
| post2018 |   147011 |              55039 |             0.956139 |                   749.424  |             0.450783 |          0.149758 |
| pre2019  |   467883 |              82615 |             0.823428 |                    94.6373 |             0.450393 |          0.14945  |

## Council Decision

The highest-value clean route is not another daily shape or COGS-ratio tweak. The missing layer is an explicit period-total funnel model:

`period Revenue = sessions_prior x conversion_regime x AOV_regime`

The next clean implementation should build this head first, then add source-quality and cohort/repeat-customer priors only if rolling folds show they improve MAE without hurting RMSE/R2.
