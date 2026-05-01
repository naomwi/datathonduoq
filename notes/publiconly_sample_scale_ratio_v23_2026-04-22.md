# Public-Only Sample Scale Ratio V23

Run directory: `logs\20260422_095954_publiconly_sample_scale_ratio_v23`

Current best: `submission_sampleprior_v22_periodshape_both_a0725.csv` scored `701005.1247`.

Known results:

|                                                       |   public_score |
|:------------------------------------------------------|---------------:|
| submission_sampleprior_v20_periodshape_both_a070.csv  |         701103 |
| submission_sampleprior_v22_periodshape_both_a0725.csv |         701005 |
| submission_sampleprior_v21_periodshape_both_a075.csv  |         701145 |

Interpretation:

- Alpha-only sample shape has plateaued around `701k`; local fit predicts only tiny alpha gains.
- To reach `699.x`, test a second axis: period totals and COGS ratios slightly toward `sample_submission`.
- These are intentionally small moves from the current best.

Current best period summary:

| period     |   days |     Revenue |        COGS |    ratio |
|:-----------|-------:|------------:|------------:|---------:|
| 2023H1     |    181 | 7.63982e+08 | 7.2905e+08  | 0.954276 |
| 2023H2     |    184 | 6.20433e+08 | 6.14834e+08 | 0.990975 |
| 2024-07-01 |      1 | 5.65516e+06 | 5.91672e+06 | 1.04625  |
| 2024H1     |    182 | 8.57459e+08 | 7.40356e+08 | 0.86343  |

Sample period summary:

| period     |   days |     Revenue |        COGS |    ratio |
|:-----------|-------:|------------:|------------:|---------:|
| 2023H1     |    181 | 6.64116e+08 | 5.54234e+08 | 0.834544 |
| 2023H2     |    184 | 4.71673e+08 | 4.32977e+08 | 0.917959 |
| 2024-07-01 |      1 | 5.05761e+06 | 4.98975e+06 | 0.986583 |
| 2024H1     |    182 | 6.40041e+08 | 5.33327e+08 | 0.83327  |

Candidate manifest:

|   priority | filename                                           | path                                                       | thesis                                                                          |   rev_rows_changed_vs_current |   cogs_rows_changed_vs_current |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   directional_best_case_gain_vs_current |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   revenue_total_ratio_vs_sample |   cogs_total_ratio_vs_sample |   ratio_all |   ratio_2023h1 |   ratio_2023h2 |   ratio_2024h1 |
|-----------:|:---------------------------------------------------|:-----------------------------------------------------------|:--------------------------------------------------------------------------------|------------------------------:|-------------------------------:|--------------------------------:|---------------------------------:|----------------------------------------:|---------------------------------:|------------------------------:|--------------------------------:|-----------------------------:|------------:|---------------:|---------------:|---------------:|
|          1 | submission_sample_v23_a0725_ratio_to_sample005.csv | dataset\submission_sample_v23_a0725_ratio_to_sample005.csv | keep a0725 shape and Revenue, move period COGS/Revenue ratios 5% toward sample  |                             0 |                            548 |                             0   |                          14869.8 |                                 7434.89 |                         1        |                      0.996101 |                         1.26203 |                      1.36478 |    0.926354 |       0.94829  |       0.987324 |       0.861922 |
|          2 | submission_sample_v23_a0725_ratio_to_sample010.csv | dataset\submission_sample_v23_a0725_ratio_to_sample010.csv | keep a0725 shape and Revenue, move period COGS/Revenue ratios 10% toward sample |                             0 |                            548 |                             0   |                          29739.6 |                                14869.8  |                         1        |                      0.992203 |                         1.26203 |                      1.35944 |    0.922728 |       0.942303 |       0.983674 |       0.860414 |
|          3 | submission_sample_v23_a0725_scale_to_sample005.csv | dataset\submission_sample_v23_a0725_scale_to_sample005.csv | keep a0725 shape, move period Revenue and COGS totals 5% toward sample totals   |                           548 |                            548 |                         42576.9 |                          51517.3 |                                47047.1  |                         0.989619 |                      0.986493 |                         1.24893 |                      1.35161 |    0.927042 |       0.949038 |       0.988166 |       0.86229  |
|          4 | submission_sample_v23_a0725_scale_to_sample010.csv | dataset\submission_sample_v23_a0725_scale_to_sample010.csv | keep a0725 shape, move period Revenue and COGS totals 10% toward sample totals  |                           548 |                            548 |                         85153.7 |                         103035   |                                94094.1  |                         0.979238 |                      0.972986 |                         1.23583 |                      1.33311 |    0.924043 |       0.94373  |       0.985288 |       0.86112  |
|          5 | submission_sample_v23_a0725_revscale_down005.csv   | dataset\submission_sample_v23_a0725_revscale_down005.csv   | micro global Revenue -0.5%, keep COGS                                           |                           548 |                              0 |                         20506.7 |                              0   |                                10253.3  |                         0.995    |                      1        |                         1.25572 |                      1.37012 |    0.934653 |       0.959072 |       0.995955 |       0.867769 |
|          6 | submission_sample_v23_a0725_cogsscale_down005.csv  | dataset\submission_sample_v23_a0725_cogsscale_down005.csv  | micro global COGS -0.5%, keep Revenue                                           |                             0 |                            548 |                             0   |                          19070.8 |                                 9535.39 |                         1        |                      0.995    |                         1.26203 |                      1.36327 |    0.92533  |       0.949505 |       0.98602  |       0.859113 |
|          7 | submission_sample_v23_a0725_bothscale_down005.csv  | dataset\submission_sample_v23_a0725_bothscale_down005.csv  | micro global Revenue and COGS -0.5%                                             |                           548 |                            548 |                         20506.7 |                          19070.8 |                                19788.7  |                         0.995    |                      0.995    |                         1.25572 |                      1.36327 |    0.92998  |       0.954276 |       0.990975 |       0.86343  |

Suggested order:

1. `submission_sample_v23_a0725_ratio_to_sample005.csv`
2. If it improves: `submission_sample_v23_a0725_ratio_to_sample010.csv`
3. If ratio move fails: `submission_sample_v23_a0725_scale_to_sample005.csv`
4. Use global micro-scale probes only if both sample-ratio and sample-scale fail.
