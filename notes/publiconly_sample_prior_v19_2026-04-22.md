# Public-Only Sample Prior V19

Run directory: `logs\20260422_094650_publiconly_sample_prior_v19`

Current best: `submission_top10_v13_rev2023h2_up100_keepcogs.csv` scored `797595.9641`.

Recent rejected probes:

|                                                         |   public_score |
|:--------------------------------------------------------|---------------:|
| submission_h2rev_v15_current_h2_rev_up050.csv           |         800572 |
| submission_h2shape_v16_cogs_oddmean_preserve.csv        |         802116 |
| submission_h2antishape_v17_cogs_antiodd025_preserve.csv |         800579 |
| submission_h2revshape_v18_rev_odd050_preserve.csv       |         798085 |
| submission_h2revshape_v18_rev_antiodd050_preserve.csv   |         801642 |

Observation:

- `sample_submission.csv` is not a zero template; it contains a complete 548-day Revenue/COGS forecast.
- Its total scale is much lower than the current best, so direct blending is risky.
- A safer test is to borrow only its day-level shape while preserving current period totals.

Current best period summary:

| period     |   days |     Revenue |        COGS |    ratio |
|:-----------|-------:|------------:|------------:|---------:|
| 2023H1     |    181 | 7.63982e+08 | 7.2905e+08  | 0.954276 |
| 2023H2     |    184 | 6.20433e+08 | 6.14834e+08 | 0.990975 |
| 2024-07-01 |      1 | 5.65516e+06 | 5.91672e+06 | 1.04625  |
| 2024H1     |    182 | 8.57459e+08 | 7.40356e+08 | 0.86343  |

Sample submission period summary:

| period     |   days |     Revenue |        COGS |    ratio |
|:-----------|-------:|------------:|------------:|---------:|
| 2023H1     |    181 | 6.64116e+08 | 5.54234e+08 | 0.834544 |
| 2023H2     |    184 | 4.71673e+08 | 4.32977e+08 | 0.917959 |
| 2024-07-01 |      1 | 5.05761e+06 | 4.98975e+06 | 0.986583 |
| 2024H1     |    182 | 6.40041e+08 | 5.33327e+08 | 0.83327  |

Candidate manifest:

|   priority | filename                                                    | path                                                                | thesis                                                                                         |   rev_rows_changed |   cogs_rows_changed |   mean_abs_rev_delta |   mean_abs_cogs_delta |   directional_best_case_gain |   revenue_total_ratio_vs_best |   cogs_total_ratio_vs_best |   revenue_total_ratio_vs_sample |   cogs_total_ratio_vs_sample |   ratio_all |   ratio_2023h1 |   ratio_2023h2 |   ratio_2024h1 |   sample_ratio_2023h1 |   sample_ratio_2023h2 |   sample_ratio_2024h1 |   base_ratio_2023h1 |   base_ratio_2023h2 |   base_ratio_2024h1 |
|-----------:|:------------------------------------------------------------|:--------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------|-------------------:|--------------------:|---------------------:|----------------------:|-----------------------------:|------------------------------:|---------------------------:|--------------------------------:|-----------------------------:|------------:|---------------:|---------------:|---------------:|----------------------:|----------------------:|----------------------:|--------------------:|--------------------:|--------------------:|
|          1 | submission_sampleprior_v19_periodshape_both_a025.csv        | dataset\submission_sampleprior_v19_periodshape_both_a025.csv        | blend 25% toward sample day-level shape, preserving current period totals for Revenue and COGS |                547 |                 547 |             143505   |                122322 |                     132913   |                      1        |                   1        |                         1.26203 |                      1.37012 |    0.92998  |       0.954276 |       0.990975 |       0.86343  |              0.834544 |              0.917959 |               0.83327 |            0.954276 |            0.990975 |             0.86343 |
|          2 | submission_sampleprior_v19_periodshape_both_a050.csv        | dataset\submission_sampleprior_v19_periodshape_both_a050.csv        | blend 50% toward sample day-level shape, preserving current period totals for Revenue and COGS |                547 |                 547 |             287010   |                244643 |                     265827   |                      1        |                   1        |                         1.26203 |                      1.37012 |    0.92998  |       0.954276 |       0.990975 |       0.86343  |              0.834544 |              0.917959 |               0.83327 |            0.954276 |            0.990975 |             0.86343 |
|          3 | submission_sampleprior_v19_periodshape_both_a100.csv        | dataset\submission_sampleprior_v19_periodshape_both_a100.csv        | replace day-level shape with sample shape, preserving current period totals                    |                547 |                 547 |             574020   |                489287 |                     531653   |                      1        |                   1        |                         1.26203 |                      1.37012 |    0.92998  |       0.954276 |       0.990975 |       0.86343  |              0.834544 |              0.917959 |               0.83327 |            0.954276 |            0.990975 |             0.86343 |
|          4 | submission_sampleprior_v19_revshape_a050_keepcogs.csv       | dataset\submission_sampleprior_v19_revshape_a050_keepcogs.csv       | blend 50% toward sample Revenue shape only, keep current COGS                                  |                547 |                   0 |             287010   |                     0 |                     143505   |                      1        |                   1        |                         1.26203 |                      1.37012 |    0.92998  |       0.954276 |       0.990975 |       0.86343  |              0.834544 |              0.917959 |               0.83327 |            0.954276 |            0.990975 |             0.86343 |
|          5 | submission_sampleprior_v19_cogsshape_a050_keeprev.csv       | dataset\submission_sampleprior_v19_cogsshape_a050_keeprev.csv       | blend 50% toward sample COGS shape only, keep current Revenue                                  |                  0 |                 547 |                  0   |                244643 |                     122322   |                      1        |                   1        |                         1.26203 |                      1.37012 |    0.92998  |       0.954276 |       0.990975 |       0.86343  |              0.834544 |              0.917959 |               0.83327 |            0.954276 |            0.990975 |             0.86343 |
|          6 | submission_sampleprior_v19_revshape_a050_preserve_ratio.csv | dataset\submission_sampleprior_v19_revshape_a050_preserve_ratio.csv | blend 50% toward sample Revenue shape and preserve current daily COGS/Revenue ratio            |                547 |                 547 |             287010   |                266155 |                     276583   |                      1        |                   1.00173  |                         1.26203 |                      1.37249 |    0.931586 |       0.954783 |       0.994137 |       0.864901 |              0.834544 |              0.917959 |               0.83327 |            0.954276 |            0.990975 |             0.86343 |
|          7 | submission_sampleprior_v19_direct_a010.csv                  | dataset\submission_sampleprior_v19_direct_a010.csv                  | direct 10% blend toward sample_submission values; tests sample as true low-scale prior         |                548 |                 548 |              93219.4 |                104692 |                      98955.6 |                      0.979238 |                   0.972986 |                         1.23583 |                      1.33311 |    0.924043 |       0.94373  |       0.985288 |       0.86112  |              0.834544 |              0.917959 |               0.83327 |            0.954276 |            0.990975 |             0.86343 |
|          8 | submission_sampleprior_v19_direct_a020.csv                  | dataset\submission_sampleprior_v19_direct_a020.csv                  | direct 20% blend toward sample_submission values                                               |                548 |                 548 |             186439   |                209384 |                     197911   |                      0.958475 |                   0.945973 |                         1.20962 |                      1.2961  |    0.917849 |       0.932901 |       0.979314 |       0.858687 |              0.834544 |              0.917959 |               0.83327 |            0.954276 |            0.990975 |             0.86343 |
|          9 | submission_sampleprior_v19_direct_a035.csv                  | dataset\submission_sampleprior_v19_direct_a035.csv                  | direct 35% blend toward sample_submission values                                               |                548 |                 548 |             326268   |                366421 |                     346345   |                      0.927331 |                   0.905452 |                         1.17032 |                      1.24058 |    0.908038 |       0.916101 |       0.969767 |       0.854783 |              0.834544 |              0.917959 |               0.83327 |            0.954276 |            0.990975 |             0.86343 |

Suggested order:

1. `submission_sampleprior_v19_periodshape_both_a025.csv`
2. If it improves: `submission_sampleprior_v19_periodshape_both_a050.csv`
3. If shape fails but close: `submission_sampleprior_v19_revshape_a050_keepcogs.csv`
4. Direct sample blend is a separate low-scale prior probe; only submit `direct_a010` if shape signal is not terrible.
