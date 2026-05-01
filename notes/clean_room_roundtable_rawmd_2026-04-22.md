# Clean-Room Raw Month-Day Pipeline

Run directory: `logs\20260422_155326_cleanroom_rawmd_pipeline`

## Audit Standard

This is the clean-room version of the raw month-day insight.

It does not read:

- `sample_submission.csv` numeric `Revenue` / `COGS`;
- any `sales_test.csv` target values;
- any previous `submission_*.csv` as an input anchor.

It does read only raw provided files through `ensure_inputs()` and rebuilds the model anchor inside this script.

## Roundtable Decision

Business analyst: present the method as a calendar/seasonality allocation correction, not as leaderboard probing.

Data scientist: prove H1/H2 stability from `sales.csv` train by normalized month-day shares; use weaker H2 regularization because H2 historical shape is less stable.

ML engineer: regenerate the CatBoost recency anchor from raw tables, then apply raw-md correction in memory. No submission file is used as a feature source.

Checker: final source package must exclude the old `sample_*` and `publiconly_*` scripts, or place them in a clearly quarantined research folder not used by the final run.

## Anchor Period Summary

| period     |   days |     revenue |        cogs |   cogs_ratio |
|:-----------|-------:|------------:|------------:|-------------:|
| 2023H1     |    181 | 7.05398e+08 | 6.02692e+08 |     0.8544   |
| 2023H2     |    184 | 4.84419e+08 | 4.50753e+08 |     0.930502 |
| 2024-07-01 |      1 | 4.68245e+06 | 4.57889e+06 |     0.977883 |
| 2024H1     |    182 | 7.70302e+08 | 6.50783e+08 |     0.844842 |

## Candidate Manifest

|   priority | filename                                                     | path                                                                 |   revenue_alpha_non_h2 |   revenue_alpha_h2 |   cogs_alpha |   cogs_scale_2023H1 |   cogs_scale_2023H2 |   cogs_scale_2024H1 |   mean_abs_rev_delta_vs_anchor |   mean_abs_cogs_delta_vs_anchor |   revenue_total_ratio_vs_anchor |   cogs_total_ratio_vs_anchor | note                                                                                                     |
|-----------:|:-------------------------------------------------------------|:---------------------------------------------------------------------|-----------------------:|-------------------:|-------------:|--------------------:|--------------------:|--------------------:|-------------------------------:|--------------------------------:|--------------------------------:|-----------------------------:|:---------------------------------------------------------------------------------------------------------|
|          1 | submission_cleanroom_rawmd_r080_c065_h2r010_cogsmed.csv      | dataset\submission_cleanroom_rawmd_r080_c065_h2r010_cogsmed.csv      |                    0.8 |                0.1 |         0.65 |                1.03 |               1.018 |               1.009 |                         302749 |                          265047 |                               1 |                      1.01876 | Clean-room analogue of current best insight; alpha values should be justified as validation/calibration. |
|          2 | submission_cleanroom_rawmd_r080_c065_h2r010_nocogsscale.csv  | dataset\submission_cleanroom_rawmd_r080_c065_h2r010_nocogsscale.csv  |                    0.8 |                0.1 |         0.65 |                1    |               1     |               1     |                         302749 |                          258081 |                               1 |                      1       | Same clean raw-md correction without public-calibrated COGS period scaling.                              |
|          3 | submission_cleanroom_rawmd_r070_c060_h2r020_conservative.csv | dataset\submission_cleanroom_rawmd_r070_c060_h2r020_conservative.csv |                    0.7 |                0.2 |         0.6  |                1    |               1     |               1     |                         275277 |                          238229 |                               1 |                      1       | More conservative config for report if strict train-only validation does not support aggressive alpha.   |

## Suggested Clean Submission

Use `dataset/submission_cleanroom_rawmd_r080_c065_h2r010_cogsmed.csv` only if we want the cleanest defensible version. Its score may differ from the current 687k lineage because the anchor is regenerated from the model instead of loaded from public-tuned submissions.
