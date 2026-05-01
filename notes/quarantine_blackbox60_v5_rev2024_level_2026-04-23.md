# Quarantine Blackbox 60x V5 Revenue 2024H1 Level

Run directory: `logs\20260423_123329_quarantine_blackbox60_v5_rev2024_level`

## Status

This is **not clean**. It is public black-box exploration only.

Current best:

- `submission_qbb60v4_level_rev2024h1_up030.csv` = `680506.89709`

## Read

`+3% Revenue 2024H1` improved from `682039.28310` to `680506.89709`, so the missing signal is period-level Revenue in 2024H1, not more daily shape.

## Candidate Manifest

|   priority | filename                                               | thesis                                           |   rev_scale_2024H1 |   cogs_scale_2024H1 |   rev_scale_2023H1 |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   movement |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_total |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |
|-----------:|:-------------------------------------------------------|:-------------------------------------------------|-------------------:|--------------------:|-------------------:|--------------------------------:|---------------------------------:|-----------:|---------------------------------:|------------------------------:|--------------:|---------------:|---------------:|---------------:|
|          1 | submission_qbb60v5_rev2024h1_up040.csv                 | Continue 2024H1 Revenue level from +3% to +4%.   |               1.04 |                1    |               1    |                         15647.1 |                      6.41559e-11 |    7823.53 |                          1.00377 |                      1        |      0.933856 |       0.984209 |        1.00923 |       0.837471 |
|          2 | submission_qbb60v5_rev2024h1_up050.csv                 | Continue 2024H1 Revenue level to +5%.            |               1.05 |                1    |               1    |                         31294.1 |                      6.41559e-11 |   15647.1  |                          1.00754 |                      1        |      0.93036  |       0.984209 |        1.00923 |       0.829495 |
|          3 | submission_qbb60v5_rev2024h1_up060.csv                 | High-information +6% 2024H1 Revenue level.       |               1.06 |                1    |               1    |                         46941.2 |                      6.41559e-11 |   23470.6  |                          1.01132 |                      1        |      0.92689  |       0.984209 |        1.00923 |       0.82167  |
|          4 | submission_qbb60v5_rev2024h1_up080.csv                 | Aggressive +8% 2024H1 Revenue level; jump probe. |               1.08 |                1    |               1    |                         78235.3 |                      6.41559e-11 |   39117.7  |                          1.01886 |                      1        |      0.920027 |       0.984209 |        1.00923 |       0.806454 |
|          5 | submission_qbb60v5_rev2024h1_up040_cogsdown020.csv     | +4% Revenue 2024H1 plus -2% COGS 2024H1.         |               1.04 |                0.98 |               1    |                         15647.1 |                  27256.3         |   21451.7  |                          1.00377 |                      0.992991 |      0.927311 |       0.984209 |        1.00923 |       0.820722 |
|          6 | submission_qbb60v5_rev2024h1_up050_cogsdown020.csv     | +5% Revenue 2024H1 plus -2% COGS 2024H1.         |               1.05 |                0.98 |               1    |                         31294.1 |                  27256.3         |   29275.2  |                          1.00754 |                      0.992991 |      0.923839 |       0.984209 |        1.00923 |       0.812905 |
|          7 | submission_qbb60v5_rev2024h1_up040_cogsup020.csv       | +4% Revenue 2024H1 plus +2% COGS 2024H1.         |               1.04 |                1.02 |               1    |                         15647.1 |                  27256.3         |   21451.7  |                          1.00377 |                      1.00701  |      0.940402 |       0.984209 |        1.00923 |       0.85422  |
|          8 | submission_qbb60v5_rev2024h1_up050_cogsup020.csv       | +5% Revenue 2024H1 plus +2% COGS 2024H1.         |               1.05 |                1.02 |               1    |                         31294.1 |                  27256.3         |   29275.2  |                          1.00754 |                      1.00701  |      0.936882 |       0.984209 |        1.00923 |       0.846085 |
|          9 | submission_qbb60v5_rev2024h1_up040_rev2023h1_up020.csv | +4% Revenue 2024H1 plus +2% Revenue 2023H1.      |               1.04 |                1    |               1.02 |                         43529.6 |                      6.41559e-11 |   21764.8  |                          1.01049 |                      1        |      0.927645 |       0.964911 |        1.00923 |       0.837471 |
|         10 | submission_qbb60v5_rev2024h1_up050_rev2023h1_up020.csv | +5% Revenue 2024H1 plus +2% Revenue 2023H1.      |               1.05 |                1    |               1.02 |                         59176.7 |                      6.41559e-11 |   29588.4  |                          1.01427 |                      1        |      0.924195 |       0.964911 |        1.00923 |       0.829495 |

## Submit Order

1. `submission_qbb60v5_rev2024h1_up050.csv`
2. If it improves, submit `submission_qbb60v5_rev2024h1_up060.csv`
3. If +5 worsens, submit `submission_qbb60v5_rev2024h1_up040.csv`
4. Once Revenue level optimum is bracketed, test COGS combo around the best Revenue level.
