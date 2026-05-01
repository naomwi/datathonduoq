# Strict Legal Train-Validated Pipeline

Run directory: `logs\20260423_114439_strict_legal_trainvalidated_pipeline`

## Audit Boundary

This branch is intended for clean explanation. It does **not** use public leaderboard scores, `sample_submission.csv`, `sales_test` target values, or previous `submission_*.csv` files as inputs.

Signals used:

- CatBoost anchor rebuilt from provided raw/feature tables;
- historical `sales.csv` through `2022-12-31`;
- train-only rolling validation on `2018-2022`;
- known future calendar dates only.

## Selected Revenue Params

| target   | share_mode   | total_method   |   alpha_h1 |   alpha_h2 |   level_gamma |
|:---------|:-------------|:---------------|-----------:|-----------:|--------------:|
| Revenue  | raw_md       | trend_log      |          1 |       0.75 |          0.75 |

Top revenue validation rows:

| target   | share_mode   | total_method   |   alpha_h1 |   alpha_h2 |   level_gamma |     avg_mae |   worst_mae |   avg_wape |   worst_wape |   mean_bias |
|:---------|:-------------|:---------------|-----------:|-----------:|--------------:|------------:|------------:|-----------:|-------------:|------------:|
| Revenue  | raw_md       | trend_log      |       1    |       0.75 |          0.75 | 1.10193e+06 | 2.58705e+06 |   0.329463 |     0.671689 |      394874 |
| Revenue  | raw_md       | trend_log      |       0.75 |       0.75 |          0.75 | 1.10529e+06 | 2.58786e+06 |   0.330416 |     0.671899 |      394874 |
| Revenue  | raw_md       | trend_log      |       1    |       0.75 |          0.5  | 1.10568e+06 | 2.54878e+06 |   0.331785 |     0.666375 |      495673 |
| Revenue  | raw_md       | trend_log      |       0.75 |       0.75 |          0.5  | 1.10771e+06 | 2.54939e+06 |   0.332366 |     0.666375 |      495673 |
| Revenue  | median       | trend_log      |       1    |       0.75 |          0.75 | 1.10947e+06 | 2.58577e+06 |   0.331382 |     0.671357 |      394874 |
| Revenue  | median       | trend_log      |       0.75 |       0.75 |          0.75 | 1.11144e+06 | 2.58714e+06 |   0.332032 |     0.671712 |      394874 |
| Revenue  | raw_md       | trend_log      |       0.5  |       0.75 |          0.75 | 1.11278e+06 | 2.58904e+06 |   0.332322 |     0.672204 |      394874 |
| Revenue  | median       | trend_log      |       1    |       0.75 |          0.5  | 1.11484e+06 | 2.54697e+06 |   0.334236 |     0.667416 |      495673 |
| Revenue  | median       | trend_log      |       0.75 |       0.75 |          0.5  | 1.11511e+06 | 2.54833e+06 |   0.334404 |     0.667416 |      495673 |
| Revenue  | raw_md       | trend_log      |       0.5  |       0.75 |          0.5  | 1.11543e+06 | 2.55123e+06 |   0.334342 |     0.666375 |      495673 |

## Selected COGS Params

| target   | share_mode   | total_method   |   alpha_h1 |   alpha_h2 |   level_gamma |
|:---------|:-------------|:---------------|-----------:|-----------:|--------------:|
| COGS     | raw_md       | trend_log      |          1 |       0.75 |          0.75 |

Top COGS validation rows:

| target   | share_mode   | total_method   |   alpha_h1 |   alpha_h2 |   level_gamma |   avg_mae |   worst_mae |   avg_wape |   worst_wape |   mean_bias |
|:---------|:-------------|:---------------|-----------:|-----------:|--------------:|----------:|------------:|-----------:|-------------:|------------:|
| COGS     | raw_md       | trend_log      |       1    |       0.75 |          0.75 |    920316 | 2.12571e+06 |   0.311821 |     0.668127 |      354338 |
| COGS     | raw_md       | trend_log      |       1    |       0.75 |          0.5  |    923184 | 2.10012e+06 |   0.314866 |     0.660084 |      435933 |
| COGS     | raw_md       | trend_log      |       0.75 |       0.75 |          0.75 |    923410 | 2.12576e+06 |   0.312782 |     0.668141 |      354338 |
| COGS     | raw_md       | trend_log      |       0.75 |       0.75 |          0.5  |    925677 | 2.09994e+06 |   0.315649 |     0.660028 |      435933 |
| COGS     | raw_md       | trend_log      |       1    |       0.5  |          0.75 |    926800 | 2.12571e+06 |   0.314333 |     0.668127 |      354338 |
| COGS     | median       | trend_log      |       1    |       0.75 |          0.75 |    926920 | 2.12518e+06 |   0.313755 |     0.66796  |      354338 |
| COGS     | median       | trend_log      |       0.75 |       0.75 |          0.75 |    927618 | 2.12599e+06 |   0.314153 |     0.668215 |      354338 |
| COGS     | raw_md       | trend_log      |       0.5  |       0.75 |          0.75 |    929544 | 2.12775e+06 |   0.314625 |     0.668768 |      354338 |
| COGS     | raw_md       | trend_log      |       0.75 |       0.5  |          0.75 |    929895 | 2.12576e+06 |   0.315294 |     0.668141 |      354338 |
| COGS     | raw_md       | trend_log      |       1    |       0.75 |          1    |    930863 | 2.1513e+06  |   0.314058 |     0.67617  |      272743 |

## Candidate Manifest

|   priority | filename                                   | note                                                                   | rev_share_mode   | rev_total_method   |   rev_alpha_h1 |   rev_alpha_h2 |   rev_level_gamma | cogs_share_mode   | cogs_total_method   |   cogs_alpha_h1 |   cogs_alpha_h2 |   cogs_level_gamma |   revenue_total |   cogs_total |   ratio_total |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |
|-----------:|:-------------------------------------------|:-----------------------------------------------------------------------|:-----------------|:-------------------|---------------:|---------------:|------------------:|:------------------|:--------------------|----------------:|----------------:|-------------------:|----------------:|-------------:|--------------:|---------------:|---------------:|---------------:|
|          1 | submission_strictlegal_tv_selected.csv     | Fully train-validated shape and period-level model.                    | raw_md           | trend_log          |            1   |          0.75  |             0.75  | raw_md            | trend_log           |             1   |           0.75  |              0.75  |     1.66945e+09 |  1.46225e+09 |      0.875889 |       0.858582 |       0.92038  |       0.861373 |
|          2 | submission_strictlegal_tv_shapeonly.csv    | Same selected shape parameters, no period-level total correction.      | raw_md           | trend_log          |            1   |          0.75  |             0     | raw_md            | trend_log           |             1   |           0.75  |              0     |     1.9648e+09  |  1.70881e+09 |      0.86971  |       0.8544   |       0.930502 |       0.844842 |
|          3 | submission_strictlegal_tv_levelonly.csv    | Only train-validated period-level correction; keep anchor daily shape. | raw_md           | trend_log          |            0   |          0     |             0.75  | raw_md            | trend_log           |             0   |           0     |              0.75  |     1.66945e+09 |  1.46225e+09 |      0.875889 |       0.858582 |       0.92038  |       0.861373 |
|          4 | submission_strictlegal_tv_conservative.csv | Half-strength version for lower variance.                              | raw_md           | trend_log          |            0.5 |          0.375 |             0.375 | raw_md            | trend_log           |             0.5 |           0.375 |              0.375 |     1.81712e+09 |  1.58553e+09 |      0.872548 |       0.856362 |       0.925737 |       0.85215  |

## Recommendation

Submit `submission_strictlegal_tv_selected.csv` only if the priority is defensibility. It may score worse than public-calibrated files, but its parameters have a clean provenance story.
