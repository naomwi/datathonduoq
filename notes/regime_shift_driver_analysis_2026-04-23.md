# Regime Shift Driver Analysis

Run directory: `logs\20260423_125219_regime_shift_drivers`

## Key Finding

The train data has a strong structural break starting in `2019`, before the COVID period. So the low recent regime is not purely a 2020 COVID artifact.

Annual driver summary:

|   year |   days |     revenue |        cogs |   orders |    sessions |   units |   discount_amount |   gross_item_value |   refund_amount |   cogs_ratio |   orders_per_day |     aov |   conversion |   discount_rate |   refund_rate |
|-------:|-------:|------------:|------------:|---------:|------------:|--------:|------------------:|-------------------:|----------------:|-------------:|-----------------:|--------:|-------------:|----------------:|--------------:|
|   2012 |    181 | 7.41498e+08 | 5.87462e+08 |    32051 | 0           |  166286 |       0           |        7.41498e+08 |     2.11221e+07 |     0.792264 |         177.077  | 23134.9 | inf          |       0         |     0.0284857 |
|   2013 |    365 | 1.65717e+09 | 1.46598e+09 |    76849 | 6.80194e+06 |  392522 |       8.70042e+07 |        1.65717e+09 |     5.23356e+07 |     0.884629 |         210.545  | 21564   |   0.0112981  |       0.0525017 |     0.0315813 |
|   2014 |    365 | 1.87185e+09 | 1.57461e+09 |    80645 | 7.34096e+06 |  410283 |       8.65032e+07 |        1.87185e+09 |     5.7928e+07  |     0.841206 |         220.945  | 23210.9 |   0.0109856  |       0.0462128 |     0.030947  |
|   2015 |    365 | 1.88993e+09 | 1.66544e+09 |    82622 | 7.86194e+06 |  415509 |       9.79239e+07 |        1.88993e+09 |     6.07923e+07 |     0.881217 |         226.362  | 22874.5 |   0.0105091  |       0.0518134 |     0.0321664 |
|   2016 |    366 | 2.10464e+09 | 1.78056e+09 |    82247 | 8.4034e+06  |  409893 |       9.22762e+07 |        2.10464e+09 |     6.62371e+07 |     0.846016 |         224.719  | 25589.3 |   0.00978735 |       0.0438442 |     0.0314719 |
|   2017 |    365 | 1.91116e+09 | 1.69439e+09 |    76010 | 8.9926e+06  |  375640 |       9.56177e+07 |        1.91116e+09 |     5.97525e+07 |     0.886573 |         208.247  | 25143.6 |   0.0084525  |       0.0500311 |     0.031265  |
|   2018 |    365 | 1.85012e+09 | 1.54218e+09 |    69510 | 9.41508e+06 |  337646 |       8.03993e+07 |        1.85012e+09 |     5.67254e+07 |     0.833553 |         190.438  | 26616.6 |   0.00738283 |       0.0434562 |     0.0306603 |
|   2019 |    365 | 1.1368e+09  | 1.0052e+09  |    41601 | 9.99015e+06 |  202653 |       5.52119e+07 |        1.1368e+09  |     3.53161e+07 |     0.884238 |         113.975  | 27326.3 |   0.0041642  |       0.0485677 |     0.0310662 |
|   2020 |    366 | 1.05451e+09 | 8.86085e+08 |    34881 | 1.05911e+07 |  166880 |       4.84036e+07 |        1.05451e+09 |     3.24305e+07 |     0.84028  |          95.3033 | 30231.7 |   0.00329343 |       0.0459014 |     0.030754  |
|   2021 |    365 | 1.04304e+09 | 9.4113e+08  |    34525 | 1.09917e+07 |  164743 |       5.18256e+07 |        1.04304e+09 |     3.22466e+07 |     0.902295 |          94.589  | 30211.1 |   0.003141   |       0.0496871 |     0.030916  |
|   2022 |    365 | 1.16975e+09 | 1.02042e+09 |    36004 | 1.10637e+07 |  171088 |       5.44417e+07 |        1.16975e+09 |     3.57122e+07 |     0.872341 |          98.6411 | 32489.4 |   0.00325426 |       0.0465414 |     0.0305298 |

Half-year percent deltas, recent `2019-2022` versus pre-2019 high regime `2013-2018`:

| half   |   revenue_delta_recent_vs_pre2019 |   orders_delta |   sessions_delta |   aov_delta |   conversion_delta |   cogs_ratio_delta |
|:-------|----------------------------------:|---------------:|-----------------:|------------:|-------------------:|-------------------:|
| H1     |                         -0.403993 |      -0.516321 |         0.317804 |    0.234823 |          -0.635426 |          0.0104968 |
| H2     |                         -0.42961  |      -0.544029 |         0.300619 |    0.247914 |          -0.655261 |          0.0247737 |

Era summary:

| era          | half   |     revenue |        cogs |   orders |    sessions |     aov |   orders_per_day |   conversion |   revenue_per_unit |   units_per_order |   cogs_ratio |   discount_rate |   promo_line_share |   refund_rate |   avg_active_promo_count |   avg_fill_rate |   avg_stockout_flag |
|:-------------|:-------|------------:|------------:|---------:|------------:|--------:|-----------------:|-------------:|-------------------:|------------------:|-------------:|----------------:|-------------------:|--------------:|-------------------------:|----------------:|--------------------:|
| pre2019_high | H1     | 1.10197e+09 | 9.11652e+08 |  43160.8 | 4.50005e+06 | 25510.2 |         238.225  |   0.00969724 |            5140.81 |           4.96684 |     0.827136 |       0.0309792 |           0.273009 |     0.0293363 |                 0.309185 |        0.959798 |            0.676802 |
| pre2019_high | H2     | 7.78839e+08 | 7.08873e+08 |  34819.7 | 3.63594e+06 | 22586.5 |         189.237  |   0.00978396 |            4488.51 |           5.04286 |     0.911765 |       0.0719711 |           0.566523 |     0.0342652 |                 0.634058 |        0.960797 |            0.67347  |
| recent_low   | H1     | 6.56784e+08 | 5.49198e+08 |  20876   | 5.93018e+06 | 31500.6 |         115.189  |   0.00353536 |            6592.61 |           4.78028 |     0.835818 |       0.0322064 |           0.28459  |     0.0284951 |                 0.310462 |        0.963381 |            0.670934 |
| recent_low   | H2     | 4.44242e+08 | 4.14012e+08 |  15876.8 | 4.72898e+06 | 28185.9 |          86.2867 |   0.00337291 |            5860.19 |           4.8142  |     0.934353 |       0.0707068 |           0.57196  |     0.0342785 |                 0.633152 |        0.964555 |            0.667033 |

Seasonality shape stability:

| half   |   pairwise_shape_corr_mean |   pairwise_shape_corr_median |   pairwise_shape_corr_min |   pairwise_shape_corr_max |
|:-------|---------------------------:|-----------------------------:|--------------------------:|--------------------------:|
| H1     |                   0.81526  |                     0.796975 |                  0.703679 |                  0.926871 |
| H2     |                   0.707719 |                     0.700258 |                  0.550647 |                  0.903723 |

Prediction/public-inferred half-year position versus train history:

| candidate                    | status                         | period   |   days |     revenue |        cogs |   cogs_ratio |   revenue_vs_recent_low_avg |   revenue_vs_pre2019_high_avg |   cogs_vs_recent_low_avg |   cogs_vs_pre2019_high_avg |   train_revenue_rank_from_low |   train_revenue_period_count_plus_candidate |   train_max_revenue_same_half |   train_cogs_rank_from_low |   train_max_cogs_same_half |
|:-----------------------------|:-------------------------------|:---------|-------:|------------:|------------:|-------------:|----------------------------:|------------------------------:|-------------------------:|---------------------------:|------------------------------:|--------------------------------------------:|------------------------------:|---------------------------:|---------------------------:|
| strictlegal_tv               | train_validated                | 2023H1   |    181 | 6.2351e+08  | 5.35334e+08 |     0.858582 |                   0.949338  |                    0.565812   |                0.974757  |                 0.587213   |                             2 |                                          11 |                   1.21523e+09 |                          3 |                1.01091e+09 |
| strictlegal_tv               | train_validated                | 2023H2   |    184 | 4.30929e+08 | 3.96618e+08 |     0.92038  |                   0.970033  |                    0.553296   |                0.957987  |                 0.559505   |                             2 |                                          11 |                   8.8941e+08  |                          2 |                7.69651e+08 |
| strictlegal_tv               | train_validated                | 2024H1   |    182 | 6.10327e+08 | 5.2572e+08  |     0.861373 |                   0.929266  |                    0.553849   |                0.95725   |                 0.576667   |                             2 |                                          11 |                   1.21523e+09 |                          2 |                1.01091e+09 |
| strictlegal_tv               | train_validated                | 2024H2   |      1 | 4.68245e+06 | 4.57889e+06 |     0.977883 |                   0.0105403 |                    0.0060121  |                0.0110598 |                 0.0064594  |                             1 |                                          11 |                   8.8941e+08  |                          1 |                7.69651e+08 |
| sourceclean_pubcal           | source_clean_public_calibrated | 2023H1   |    181 | 7.63984e+08 | 7.50922e+08 |     0.982903 |                   1.16322   |                    0.693287   |                1.36731   |                 0.823693   |                             5 |                                          11 |                   1.21523e+09 |                          5 |                1.01091e+09 |
| sourceclean_pubcal           | source_clean_public_calibrated | 2023H2   |    184 | 6.20433e+08 | 6.25901e+08 |     1.00881  |                   1.39661   |                    0.796613   |                1.51179   |                 0.882952   |                             5 |                                          11 |                   8.8941e+08  |                          6 |                7.69651e+08 |
| sourceclean_pubcal           | source_clean_public_calibrated | 2024H1   |    182 | 8.57457e+08 | 7.47018e+08 |     0.871202 |                   1.30554   |                    0.77811    |                1.3602    |                 0.819412   |                             5 |                                          11 |                   1.21523e+09 |                          5 |                1.01091e+09 |
| sourceclean_pubcal           | source_clean_public_calibrated | 2024H2   |      1 | 5.65517e+06 | 5.91672e+06 |     1.04625  |                   0.0127299 |                    0.00726103 |                0.0142912 |                 0.00834665 |                             1 |                                          11 |                   8.8941e+08  |                          1 |                7.69651e+08 |
| public_inferred_current_best | quarantine_public_inferred     | 2023H1   |    181 | 7.63982e+08 | 7.51919e+08 |     0.984209 |                   1.16322   |                    0.693285   |                1.36912   |                 0.824787   |                             5 |                                          11 |                   1.21523e+09 |                          5 |                1.01091e+09 |
| public_inferred_current_best | quarantine_public_inferred     | 2023H2   |    184 | 6.20433e+08 | 6.26159e+08 |     1.00923  |                   1.39661   |                    0.796613   |                1.51242   |                 0.883317   |                             5 |                                          11 |                   8.8941e+08  |                          6 |                7.69651e+08 |
| public_inferred_current_best | quarantine_public_inferred     | 2024H1   |    182 | 8.83183e+08 | 7.46821e+08 |     0.845602 |                   1.34471   |                    0.801456   |                1.35984   |                 0.819195   |                             5 |                                          11 |                   1.21523e+09 |                          5 |                1.01091e+09 |
| public_inferred_current_best | quarantine_public_inferred     | 2024H2   |      1 | 5.65516e+06 | 6.00108e+06 |     1.06117  |                   0.0127299 |                    0.00726102 |                0.0144949 |                 0.00846567 |                             1 |                                          11 |                   8.8941e+08  |                          1 |                7.69651e+08 |

## Interpretation

1. Revenue level is strongly seasonal: `H1` is consistently higher than `H2`, with the strongest months around April-June.
2. The major level drop is mostly a demand/order-volume regime shift, not a pure daily-seasonality issue.
3. The break starts in `2019`, so blaming only COVID is too simple. COVID may sustain the low regime in `2020-2021`, but the series already fell sharply in `2019`.
4. Public-best submissions imply `2023-2024` recover above the recent low regime, especially `2024H1`, but not above the historical `2014-2018` high regime.
5. `H2` shape is less reliable than `H1`; this matches the black-box finding that `2023H2` should be heavily shrunk.
6. COGS ratio is regime-sensitive, especially in `H2`, so COGS should be modeled as a ratio/regime layer rather than copied from Revenue shape.

## Modeling Insight

The missing public signal is probably a **regime recovery level**:

```text
2013-2018: high demand regime
2019-2022: low demand regime / structural break
2023-2024 public: partial recovery toward old high regime
```

So a clean model should not extrapolate only from `2020-2022`. It should include a latent regime/scenario component that can blend recent low regime with pre-2019 high-regime seasonal totals.
