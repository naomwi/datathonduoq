# Clean V11 Train-Selected Regime Shape

Run directory: `logs\20260428_213249_clean_v11_trainselected_regime_shape`

## Boundary

This run selects the H1 regime-shape calibration by rolling validation on train years only (`2018-2022` H1). It does not use public leaderboard scores, `sample_submission.csv`, prior submissions, quarantine files, or test targets to select parameters.

The generated submission still builds on the existing clean-input forecast base, but the post-processing choice is train-selected rather than leaderboard-selected.

## Selected Candidate

| name                                        | revenue_mode    | ratio_mode   |   alpha |    mae |        rmse |      r2 | filename                                                                      |
|:--------------------------------------------|:----------------|:-------------|--------:|-------:|------------:|--------:|:------------------------------------------------------------------------------|
| rev-recovery_141617__ratio-all_median__a025 | recovery_141617 | all_median   |    0.25 | 738682 | 1.03645e+06 | 0.80165 | submission_cleanv11_trainselected_revrecovery_141617_ratioall_median_a025.csv |

## Top Validation Rows

| name                                                 | revenue_mode    | ratio_mode          |   alpha |    mae |        rmse |       r2 |
|:-----------------------------------------------------|:----------------|:--------------------|--------:|-------:|------------:|---------:|
| rev-recovery_141617__ratio-all_median__a025          | recovery_141617 | all_median          |    0.25 | 738682 | 1.03645e+06 | 0.80165  |
| rev-recovery_141617__ratio-ratio_low_mae_proxy__a025 | recovery_141617 | ratio_low_mae_proxy |    0.25 | 738725 | 1.0365e+06  | 0.801631 |
| rev-all_median__ratio-all_median__a025               | all_median      | all_median          |    0.25 | 738729 | 1.03716e+06 | 0.80138  |
| rev-all_median__ratio-ratio_low_mae_proxy__a025      | all_median      | ratio_low_mae_proxy |    0.25 | 738765 | 1.03719e+06 | 0.801366 |
| rev-recovery_141617__ratio-pre2019__a025             | recovery_141617 | pre2019             |    0.25 | 738772 | 1.03648e+06 | 0.801637 |
| rev-all_median__ratio-pre2019__a025                  | all_median      | pre2019             |    0.25 | 738812 | 1.03719e+06 | 0.801367 |
| rev-all_median__ratio-all_median__a050               | all_median      | all_median          |    0.5  | 738827 | 1.03747e+06 | 0.801261 |
| rev-all_median__ratio-ratio_low_mae_proxy__a050      | all_median      | ratio_low_mae_proxy |    0.5  | 738886 | 1.03755e+06 | 0.801228 |
| rev-recovery_141617__ratio-all_median__a050          | recovery_141617 | all_median          |    0.5  | 738887 | 1.03635e+06 | 0.801689 |
| rev-recovery_141617__ratio-ratio_low_mae_proxy__a050 | recovery_141617 | ratio_low_mae_proxy |    0.5  | 738980 | 1.03649e+06 | 0.801635 |
| rev-all_median__ratio-pre2019__a050                  | all_median      | pre2019             |    0.5  | 738985 | 1.03753e+06 | 0.801238 |
| rev-recovery_141617__ratio-recovery_141617__a025     | recovery_141617 | recovery_141617     |    0.25 | 738990 | 1.0366e+06  | 0.801593 |
| rev-all_median__ratio-recovery_141617__a025          | all_median      | recovery_141617     |    0.25 | 738993 | 1.03727e+06 | 0.801336 |
| rev-recovery_141617__ratio-pre2019__a050             | recovery_141617 | pre2019             |    0.5  | 739060 | 1.0364e+06  | 0.801668 |
| rev-all_median__ratio-recovery_141617__a050          | all_median      | recovery_141617     |    0.5  | 739272 | 1.03768e+06 | 0.801178 |
| rev-recovery_141617__ratio-recovery_141617__a050     | recovery_141617 | recovery_141617     |    0.5  | 739514 | 1.0367e+06  | 0.801553 |
| rev-all_median__ratio-all_median__a075               | all_median      | all_median          |    0.75 | 740484 | 1.0398e+06  | 0.800365 |
| rev-all_median__ratio-ratio_low_mae_proxy__a075      | all_median      | ratio_low_mae_proxy |    0.75 | 740562 | 1.03995e+06 | 0.800307 |
| rev-pre2019__ratio-all_median__a025                  | pre2019         | all_median          |    0.25 | 740686 | 1.03899e+06 | 0.800677 |
| rev-all_median__ratio-pre2019__a075                  | all_median      | pre2019             |    0.75 | 740710 | 1.03988e+06 | 0.800337 |

## Fold Metrics For Selected

| name                                        |   year | revenue_mode    | ratio_mode   |   alpha |              mae |             rmse |       r2 |
|:--------------------------------------------|-------:|:----------------|:-------------|--------:|-----------------:|-----------------:|---------:|
| rev-recovery_141617__ratio-all_median__a025 |   2018 | recovery_141617 | all_median   |    0.25 |      1.20117e+06 |      1.60624e+06 | 0.752508 |
| rev-recovery_141617__ratio-all_median__a025 |   2019 | recovery_141617 | all_median   |    0.25 | 638068           | 812120           | 0.77266  |
| rev-recovery_141617__ratio-all_median__a025 |   2020 | recovery_141617 | all_median   |    0.25 | 613296           | 850260           | 0.749204 |
| rev-recovery_141617__ratio-all_median__a025 |   2021 | recovery_141617 | all_median   |    0.25 | 558847           | 747708           | 0.827564 |
| rev-recovery_141617__ratio-all_median__a025 |   2022 | recovery_141617 | all_median   |    0.25 | 682722           | 922772           | 0.7237   |

## Test Metrics Caveat

Only public leaderboard MAE is observable from Kaggle. Test RMSE and R2 cannot be known without hidden labels or an official leaderboard that reports those metrics.
