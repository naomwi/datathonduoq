# Data Relationship Analysis

## Target Summary
|         |   count |        mean |         std |    min |         25% |         50% |         75% |         max |
|:--------|--------:|------------:|------------:|-------:|------------:|------------:|------------:|------------:|
| Revenue |    3833 | 4.28658e+06 | 2.62484e+06 | 279814 | 2.47109e+06 | 3.6473e+06  | 5.35088e+06 | 2.09053e+07 |
| COGS    |    3833 | 3.69513e+06 | 2.21979e+06 | 236576 | 2.15058e+06 | 3.16111e+06 | 4.63729e+06 | 1.65359e+07 |

## Strongest Same-day Relationships with Revenue
|                               |   corr_with_revenue |
|:------------------------------|--------------------:|
| COGS                          |            0.975994 |
| unique_customers              |            0.936999 |
| order_count                   |            0.935941 |
| total_units                   |            0.917849 |
| gross_margin                  |            0.687996 |
| review_count                  |            0.559834 |
| units_sold                    |            0.53232  |
| units_received                |            0.532126 |
| segment_rev_share_performance |            0.49593  |
| return_qty                    |            0.415174 |
| refund_amt                    |            0.408631 |
| sell_through_rate_avg         |            0.39886  |
| segment_rev_share_everyday    |            0.362298 |
| sessions                      |            0.305164 |
| unique_visitors               |            0.302956 |

## Weakest / Negative Same-day Relationships with Revenue
|                               |   corr_with_revenue |
|:------------------------------|--------------------:|
| promo_line_share              |           -0.111382 |
| segment_rev_share_all_weather |           -0.114095 |
| avg_discount_rate             |           -0.129772 |
| segment_rev_share_activewear  |           -0.134652 |
| category_rev_share_casual     |           -0.147732 |
| category_rev_share_outdoor    |           -0.151112 |
| stock_on_hand                 |           -0.164541 |
| segment_rev_share_premium     |           -0.183216 |
| fill_rate_avg                 |           -0.252253 |
| overstock_rate                |           -0.318465 |
| segment_rev_share_balanced    |           -0.365548 |
| days_of_supply_avg            |           -0.403297 |

## Best Lag per Signal
| signal                |   lag |   corr_with_revenue |
|:----------------------|------:|--------------------:|
| unique_customers      |     0 |            0.936999 |
| order_count           |     0 |            0.935941 |
| total_units           |     0 |            0.917849 |
| review_count          |     0 |            0.559834 |
| return_qty            |    10 |            0.479191 |
| refund_amt            |    11 |            0.456455 |
| days_of_supply_avg    |     0 |           -0.403297 |
| sell_through_rate_avg |     0 |            0.39886  |
| sessions              |     1 |            0.305645 |
| unique_visitors       |     0 |            0.302956 |
| page_views            |     1 |            0.291522 |
| fill_rate_avg         |     0 |           -0.252253 |
| total_discount        |     0 |            0.232    |
| promo_line_share      |     7 |           -0.143252 |
| stockout_rate         |     0 |            0.11191  |

## Revenue / COGS Autocorrelation
|   lag |   revenue_autocorr |   cogs_autocorr |
|------:|-------------------:|----------------:|
|     1 |         0.865494   |       0.856523  |
|     2 |         0.735113   |       0.717642  |
|     3 |         0.621556   |       0.596166  |
|     4 |         0.520726   |       0.486832  |
|     5 |         0.440454   |       0.398609  |
|     6 |         0.467571   |       0.424216  |
|     7 |         0.492042   |       0.44944   |
|    14 |         0.496429   |       0.469763  |
|    21 |         0.436866   |       0.404574  |
|    28 |         0.603399   |       0.597331  |
|    35 |         0.438783   |       0.417972  |
|    42 |         0.36676    |       0.3432    |
|    56 |         0.309784   |       0.296172  |
|    84 |         0.115327   |       0.120496  |
|    91 |         0.351522   |       0.404406  |
|   182 |         0.00823523 |       0.0294144 |
|   364 |         0.748311   |       0.777411  |
|   365 |         0.789784   |       0.827716  |
|   728 |         0.596304   |       0.567166  |
|   730 |         0.717905   |       0.701336  |

## Seasonality
### Average Revenue by Month
|   Date |   avg_revenue |
|-------:|--------------:|
|      1 |   2.59115e+06 |
|      2 |   3.4808e+06  |
|      3 |   4.92819e+06 |
|      4 |   6.53295e+06 |
|      5 |   6.57542e+06 |
|      6 |   6.42711e+06 |
|      7 |   4.65979e+06 |
|      8 |   4.44119e+06 |
|      9 |   3.79783e+06 |
|     10 |   3.30273e+06 |
|     11 |   2.6113e+06  |
|     12 |   2.52435e+06 |

### Average Revenue by Day of Week
|   Date |   avg_revenue |
|-------:|--------------:|
|      0 |   4.31103e+06 |
|      1 |   4.4651e+06  |
|      2 |   4.68006e+06 |
|      3 |   4.52304e+06 |
|      4 |   4.04639e+06 |
|      5 |   3.90658e+06 |
|      6 |   4.07385e+06 |

## Feature Engineering Decisions
- Keep dense target-history features: short lags, 4-week lags, and yearly lags.
- Add lagged order / customer / unit signals because they are the strongest business-side drivers.
- Add short-horizon traffic lag and rolling features because traffic has weak but consistent leading signal.
- Add delayed return / refund features because the relationship peaks after about 10 days.
- Add category and segment revenue-share history to capture product-mix shifts.
- Add inventory regime features with as-of alignment because inventory is monthly and should not leak future snapshots.
- Keep promotions as intensity / share features, but use them as lagged history rather than same-day realized promo usage.
