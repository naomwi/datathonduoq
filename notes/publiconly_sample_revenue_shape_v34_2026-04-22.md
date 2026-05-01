# Public-Only Sample Revenue Shape V34

Run directory: `logs\20260422_104336_publiconly_sample_revenue_shape_v34`

Current best: `submission_sample_v32_rev0725_cogs0650_away0250.csv` scored `698994.05843`.

Known results:

|                                                       |   public_score |
|:------------------------------------------------------|---------------:|
| submission_sample_v30_a0725_ratio_away_sample0250.csv |         699376 |
| submission_sample_v31_rev0725_cogs0750_away0250.csv   |         699662 |
| submission_sample_v32_rev0725_cogs0700_away0250.csv   |         699168 |
| submission_sample_v32_rev0725_cogs0650_away0250.csv   |         698994 |

Interpretation:

- COGS-shape down from `0.700` to `0.650` improved only `173.74155`, so the COGS-shape axis is becoming low-yield.
- To reach `67x`, we need a target-wise Revenue-shape move because it can change roughly `7k-50k` score-equivalent if the direction is right.
- These candidates preserve period totals and keep the current best COGS setup: `COGS alpha=0.650`, `COGS-away=0.250`.

Candidate manifest:

|   priority | filename                                              | path                                                          | thesis                                                                   |   rev_alpha |   cogs_alpha |   cogs_away_alpha |   rev_rows_changed_vs_current |   cogs_rows_changed_vs_current |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   directional_best_case_gain_vs_current |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_all |   ratio_2023h1 |   ratio_2023h2 |   ratio_2024h1 |   best_case_score_if_direction_correct |
|-----------:|:------------------------------------------------------|:--------------------------------------------------------------|:-------------------------------------------------------------------------|------------:|-------------:|------------------:|------------------------------:|-------------------------------:|--------------------------------:|---------------------------------:|----------------------------------------:|---------------------------------:|------------------------------:|------------:|---------------:|---------------:|---------------:|---------------------------------------:|
|          1 | submission_sample_v34_rev07000_cogs06500_away0250.csv | dataset\submission_sample_v34_rev07000_cogs06500_away0250.csv | Revenue sample-shape alpha down; tests if current Revenue is over-shaped |       0.7   |         0.65 |              0.25 |                           547 |                              0 |                         14350.5 |                      6.41559e-11 |                                 7175.25 |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 691819 |
|          2 | submission_sample_v34_rev07500_cogs06500_away0250.csv | dataset\submission_sample_v34_rev07500_cogs06500_away0250.csv | Revenue sample-shape alpha up one step                                   |       0.75  |         0.65 |              0.25 |                           547 |                              0 |                         14350.5 |                      6.41559e-11 |                                 7175.25 |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 691819 |
|          3 | submission_sample_v34_rev07750_cogs06500_away0250.csv | dataset\submission_sample_v34_rev07750_cogs06500_away0250.csv | Revenue sample-shape alpha up two steps                                  |       0.775 |         0.65 |              0.25 |                           547 |                              0 |                         28701   |                      6.41559e-11 |                                14350.5  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 684644 |
|          4 | submission_sample_v34_rev08000_cogs06500_away0250.csv | dataset\submission_sample_v34_rev08000_cogs06500_away0250.csv | high-variance Revenue sample-shape alpha up                              |       0.8   |         0.65 |              0.25 |                           547 |                              0 |                         43051.5 |                      6.41559e-11 |                                21525.7  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 677468 |
|          5 | submission_sample_v34_rev08500_cogs06500_away0250.csv | dataset\submission_sample_v34_rev08500_cogs06500_away0250.csv | very high-variance Revenue sample-shape alpha up                         |       0.85  |         0.65 |              0.25 |                           547 |                              0 |                         71752.5 |                      6.41559e-11 |                                35876.2  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 663118 |
|          6 | submission_sample_v34_rev06500_cogs06500_away0250.csv | dataset\submission_sample_v34_rev06500_cogs06500_away0250.csv | high-variance Revenue alpha down                                         |       0.65  |         0.65 |              0.25 |                           547 |                              0 |                         43051.5 |                      6.41559e-11 |                                21525.7  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 677468 |
|          7 | submission_sample_v34_rev06000_cogs06500_away0250.csv | dataset\submission_sample_v34_rev06000_cogs06500_away0250.csv | extreme Revenue alpha down diagnostic                                    |       0.6   |         0.65 |              0.25 |                           547 |                              0 |                         71752.5 |                      6.41559e-11 |                                35876.2  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 663118 |
|          8 | submission_sample_v34_rev09000_cogs06500_away0250.csv | dataset\submission_sample_v34_rev09000_cogs06500_away0250.csv | extreme Revenue alpha up diagnostic                                      |       0.9   |         0.65 |              0.25 |                           547 |                              0 |                        100453   |                      6.41559e-11 |                                50226.7  |                                1 |                             1 |    0.948108 |       0.984209 |        1.00923 |        0.87097 |                                 648767 |

Suggested order:

1. Submit `submission_sample_v34_rev08000_cogs06500_away0250.csv` if prioritizing a real jump toward `67x`.
2. Submit `submission_sample_v34_rev07500_cogs06500_away0250.csv` if prioritizing lower risk.
3. If Revenue-up fails, test the opposite with `submission_sample_v34_rev07000_cogs06500_away0250.csv`.
4. Do not continue COGS-shape micro unless Revenue-shape fails both directions.
