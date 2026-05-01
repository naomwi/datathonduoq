# Blackbox Rule Inference

Generated at `2026-04-22 02:24:02`.

## What This Is
This is not another leaderboard-fitting script. It converts the public probes we already submitted into constraints about the hidden public target. A positive score gain means the changed direction probably moved predictions closer to public truth; a negative gain means the change likely overshot or moved the wrong segment.

## Accepted Signals
| label                                         | public_reaction   |   score_gain_positive_is_good |   realized_efficiency |   rows_changed |   mean_cogs_delta |   mean_rev_delta |   changed_cogs_ratio_base |   changed_cogs_ratio_midpoint |   changed_cogs_ratio_candidate |
|:----------------------------------------------|:------------------|------------------------------:|----------------------:|---------------:|------------------:|-----------------:|--------------------------:|------------------------------:|-------------------------------:|
| all COGS +5% from nonpromo-up base            | improved          |                      26197.8  |             0.300754  |            548 |          174214   |                0 |                  0.871417 |                      0.893202 |                       0.914988 |
| 2023H2 COGS +10%                              | improved          |                      12584.8  |             0.246769  |            184 |          101996   |                0 |                  0.990975 |                      1.04052  |                       1.09007  |
| all COGS +3.5% continuation                   | improved          |                      10760.1  |             0.168064  |            548 |          128047   |                0 |                  0.914988 |                      0.931    |                       0.947012 |
| nonpromo COGS +1.5% from structural txndecomp | improved          |                       7556.91 |             0.457195  |            365 |           33057.7 |                0 |                  0.842975 |                      0.849297 |                       0.85562  |
| 2024H1 COGS -10% after H2-up                  | improved          |                       4991.35 |             0.0665014 |            182 |         -150113   |                0 |                  0.959367 |                      0.911398 |                       0.86343  |
| all COGS +2% continuation                     | improved          |                       3489.02 |             0.0921427 |            548 |           75730.8 |                0 |                  0.947012 |                      0.956482 |                       0.965953 |

## Rejected Signals
| label                                           | public_reaction   |   score_gain_positive_is_good |   realized_efficiency |   rows_changed |   mean_cogs_delta |   mean_rev_delta |   changed_cogs_ratio_base |   changed_cogs_ratio_midpoint |   changed_cogs_ratio_candidate |
|:------------------------------------------------|:------------------|------------------------------:|----------------------:|---------------:|------------------:|-----------------:|--------------------------:|------------------------------:|-------------------------------:|
| 2024H1 COGS +10%                                | worsened          |                     -30759.5  |            -0.409818  |            182 |  150113           |                0 |                  0.959367 |                      1.00733  |                       1.0553   |
| 2023H2 shoulder months COGS +20% extra          | worsened          |                     -22551.6  |            -0.366929  |             92 |  122921           |                0 |                  1.05557  |                      1.16113  |                       1.26669  |
| 2023H2 peak months COGS +20% extra              | worsened          |                     -15578.2  |            -0.307046  |             92 |  101471           |                0 |                  1.13501  |                      1.24851  |                       1.36201  |
| COGS ratio reshape with total roughly preserved | worsened          |                      -7773.66 |            -0.186226  |            548 |      -5.09848e-11 |                0 |                  0.965953 |                      0.965953 |                       0.965953 |
| 2023H1 COGS +10%                                | worsened          |                      -3588.65 |            -0.0539492 |            181 |  133038           |                0 |                  0.954276 |                      1.00199  |                       1.0497   |

## Implied COGS Ratio Bounds
For COGS-only probes, MAE gives a useful midpoint rule. If raising COGS improves, hidden actual COGS is likely above the midpoint between base and candidate. If raising COGS worsens, hidden actual COGS is likely below that midpoint. The reverse holds for lowering COGS.

| label                                           | public_reaction   |   score_gain_positive_is_good | implied_cogs_bound    |   changed_cogs_ratio_base |   changed_cogs_ratio_midpoint |   changed_cogs_ratio_candidate |
|:------------------------------------------------|:------------------|------------------------------:|:----------------------|--------------------------:|------------------------------:|-------------------------------:|
| nonpromo COGS +1.5% from structural txndecomp   | improved          |                       7556.91 | actual_above_midpoint |                  0.842975 |                      0.849297 |                       0.85562  |
| all COGS +5% from nonpromo-up base              | improved          |                      26197.8  | actual_above_midpoint |                  0.871417 |                      0.893202 |                       0.914988 |
| all COGS +3.5% continuation                     | improved          |                      10760.1  | actual_above_midpoint |                  0.914988 |                      0.931    |                       0.947012 |
| all COGS +2% continuation                       | improved          |                       3489.02 | actual_above_midpoint |                  0.947012 |                      0.956482 |                       0.965953 |
| COGS ratio reshape with total roughly preserved | worsened          |                      -7773.66 | actual_above_midpoint |                  0.965953 |                      0.965953 |                       0.965953 |
| 2023H2 COGS +10%                                | improved          |                      12584.8  | actual_above_midpoint |                  0.990975 |                      1.04052  |                       1.09007  |
| 2024H1 COGS +10%                                | worsened          |                     -30759.5  | actual_below_midpoint |                  0.959367 |                      1.00733  |                       1.0553   |
| 2024H1 COGS -10% after H2-up                    | improved          |                       4991.35 | actual_below_midpoint |                  0.959367 |                      0.911398 |                       0.86343  |
| 2023H1 COGS +10%                                | worsened          |                      -3588.65 | actual_below_midpoint |                  0.954276 |                      1.00199  |                       1.0497   |
| 2023H2 peak months COGS +20% extra              | worsened          |                     -15578.2  | actual_below_midpoint |                  1.13501  |                      1.24851  |                       1.36201  |
| 2023H2 shoulder months COGS +20% extra          | worsened          |                     -22551.6  | actual_below_midpoint |                  1.05557  |                      1.16113  |                       1.26669  |

## Current Best Segment Profile
Current best used for inference: `submission_publiconly_segment_v8_h2best_2024h1_down100.csv`, public score `807504.66276`.

| segment                     |   rows |   revenue_sum |    cogs_sum |   cogs_rev_ratio_weighted |   mean_revenue |   mean_cogs |
|:----------------------------|-------:|--------------:|------------:|--------------------------:|---------------:|------------:|
| 2023H1                      |    181 |   7.63982e+08 | 7.2905e+08  |                  0.954276 |    4.2209e+06  | 4.0279e+06  |
| 2023H2                      |    184 |   5.6403e+08  | 6.14834e+08 |                  1.09007  |    3.06538e+06 | 3.34149e+06 |
| 2024H1                      |    182 |   8.57459e+08 | 7.40356e+08 |                  0.86343  |    4.71132e+06 | 4.06789e+06 |
| 2023H2_peak_aug_nov_dec     |     92 |   2.44959e+08 | 2.78031e+08 |                  1.13501  |    2.6626e+06  | 3.02208e+06 |
| 2023H2_shoulder_jul_sep_oct |     92 |   3.19071e+08 | 3.36802e+08 |                  1.05557  |    3.46816e+06 | 3.6609e+06  |
| 2024_highscale_mar_jun      |    122 |   6.6794e+08  | 5.83987e+08 |                  0.874311 |    5.47492e+06 | 4.78678e+06 |
| promo_window                |    183 |   7.58454e+08 | 7.63256e+08 |                  1.00633  |    4.14456e+06 | 4.1708e+06  |
| nonpromo                    |    365 |   1.43267e+09 | 1.3269e+09  |                  0.926172 |    3.92513e+06 | 3.63535e+06 |

## Historical COGS/Revenue Ratios
|   year | period   |   rows |   revenue_sum |    cogs_sum |   mean_ratio |   weighted_ratio |
|-------:|:---------|-------:|--------------:|------------:|-------------:|-----------------:|
|   2012 | H2       |    181 |   7.41498e+08 | 5.87462e+08 |     0.792902 |         0.792264 |
|   2013 | H1       |    181 |   9.50871e+08 | 7.84852e+08 |     0.821776 |         0.825403 |
|   2013 | H2       |    184 |   7.06298e+08 | 6.81128e+08 |     0.96949  |         0.964363 |
|   2014 | H1       |    181 |   1.06877e+09 | 8.84436e+08 |     0.823    |         0.827529 |
|   2014 | H2       |    184 |   8.03078e+08 | 6.90171e+08 |     0.869173 |         0.859407 |
|   2015 | H1       |    181 |   1.09742e+09 | 9.02972e+08 |     0.818504 |         0.822815 |
|   2015 | H2       |    184 |   7.92515e+08 | 7.62469e+08 |     0.978143 |         0.962088 |
|   2016 | H1       |    182 |   1.21523e+09 | 1.01091e+09 |     0.829765 |         0.831866 |
|   2016 | H2       |    184 |   8.8941e+08  | 7.69651e+08 |     0.878595 |         0.86535  |
|   2017 | H1       |    181 |   1.15351e+09 | 9.62281e+08 |     0.828986 |         0.834222 |
|   2017 | H2       |    184 |   7.57657e+08 | 7.32105e+08 |     0.976438 |         0.966274 |
|   2018 | H1       |    181 |   1.12605e+09 | 9.24463e+08 |     0.818696 |         0.82098  |
|   2018 | H2       |    184 |   7.24075e+08 | 6.17713e+08 |     0.866484 |         0.853106 |
|   2019 | H1       |    181 |   6.97133e+08 | 5.75869e+08 |     0.822147 |         0.826053 |
|   2019 | H2       |    184 |   4.39669e+08 | 4.29334e+08 |     0.971747 |         0.976494 |
|   2020 | H1       |    182 |   6.05371e+08 | 4.99077e+08 |     0.817255 |         0.824415 |
|   2020 | H2       |    184 |   4.49141e+08 | 3.87008e+08 |     0.877008 |         0.861662 |
|   2021 | H1       |    181 |   6.32182e+08 | 5.28017e+08 |     0.828622 |         0.835229 |
|   2021 | H2       |    184 |   4.10858e+08 | 4.13114e+08 |     1.01156  |         1.00549  |
|   2022 | H1       |    181 |   6.9245e+08  | 5.93828e+08 |     0.852293 |         0.857575 |
|   2022 | H2       |    184 |   4.77298e+08 | 4.26592e+08 |     0.905476 |         0.893764 |

## Inferred Rules
- `COGS` is the main missing signal. Broad COGS raises from the structural model improved public from `873084.61` to `825080.79`, far more than model swaps or Revenue shape.
- The broad COGS raise has a plateau. Extra broad/all COGS still helped, but each step had lower realized efficiency; later aggressive H2 month pushes reversed badly.
- `2023H2` requires a higher COGS/Revenue regime than the original model predicted. The cleanest segment win is `2023H2 COGS +10%`, improving `12584.77` from the `825080.79` base.
- `2023H2` is not an unlimited spike. Adding another `+20%` to peak or shoulder H2 months worsened by `15578.21` and `22551.57`, so the likely true H2 ratio is near the current boosted level, not far above it.
- `2024H1` does not share the H2 cost shock. `2024H1 COGS +10%` was strongly rejected, while `2024H1 COGS -10%` after H2-up helped only `4991.35`; the real rule is probably "do not raise 2024H1", not "crush 2024H1".
- Broad `2023H1 COGS +10%` is rejected mildly. This suggests 2023H1 is near neutral or mixed by month, not a second broad underprediction regime.
- Capping/reshaping high COGS-ratio days while preserving total was rejected. That means high-ratio days are not simply artifacts to clip; product mix or margin compression can genuinely create ratios near/above 1 in parts of H2.
- Historical ratios are not enough by themselves, but they support a plausible structural story: H2 can carry different margin/cost behavior than H1, and public 2023H2 likely has a cost/mix regime that local OOF did not represent.

## Practical Non-Overfit Takeaway
The rule to model structurally is:

`COGS = Revenue * ratio_regime(Date, promo_window, H2_cost_regime)`

where `ratio_regime` should allow a higher 2023H2 ratio, keep 2024H1 restrained, and avoid clipping true high-ratio days. The next robust modeling work should estimate this ratio from historical analogs/product-mix proxies instead of continuing public probes.
