# Public-Only 2024 Split V14

Run directory: `logs\20260422_025447_publiconly_2024_split_v14`

Base: `submission_publiconly_segment_v8_h2best_2024h1_down100.csv` scored `807504.66276`.

Known results:

|                                                                             |   public_score |
|:----------------------------------------------------------------------------|---------------:|
| submission_publiconly_segment_v8_h2best_2024h1_down100.csv                  |         807505 |
| submission_top10_v12_rev2024highscale_down100_cogs2024highscale_down100.csv |         841263 |
| submission_top10_v13_rev2024highscale_up100_cogsdown100.csv                 |         830171 |
| submission_top10_v13_rev2024highscale_up100_keepcogs.csv                    |         812154 |

Inference:

- `Revenue Mar-Jun 2024 +10%, keep COGS` scored `812154.38787`, only `+4649.73` worse than best.
- `Revenue Mar-Jun 2024 +10%, COGS Mar-Jun -10%` scored `830171.46835`.
- Because the Revenue change is identical in both files, the COGS-down component accounts for about `18017.08` score damage.
- Therefore current best likely has Mar-Jun 2024 COGS too low or near lower bound. The next test should raise COGS in Mar-Jun/Q2, not lower it.

|   priority | filename                                                 | path                                                             | thesis                                                                                 |   rows_changed |   mean_cogs_delta |   mean_abs_cogs_delta |   directional_best_case_gain |   score_if_direction_correct |   cogs_total_ratio_vs_best |   ratio_2023h1 |   ratio_2023h2 |   ratio_2024h1 |   ratio_2024_janfeb |   ratio_2024_marjun |   ratio_2024_q2 |
|-----------:|:---------------------------------------------------------|:-----------------------------------------------------------------|:---------------------------------------------------------------------------------------|---------------:|------------------:|----------------------:|-----------------------------:|-----------------------------:|---------------------------:|---------------:|---------------:|---------------:|--------------------:|--------------------:|----------------:|
|          1 | submission_2024split_v14_marjun_cogs_up050.csv           | dataset\submission_2024split_v14_marjun_cogs_up050.csv           | undo part of 2024H1 down where combo inference says extra Mar-Jun COGS-down is harmful |            122 |           53283.5 |               53283.5 |                      26641.8 |                       780863 |                   1.01397  |       0.954276 |        1.09007 |       0.897483 |            0.82508  |            0.918027 |        0.923913 |
|          2 | submission_2024split_v14_marjun_cogs_up075.csv           | dataset\submission_2024split_v14_marjun_cogs_up075.csv           | stronger Mar-Jun COGS raise from current best                                          |            122 |           79925.3 |               79925.3 |                      39962.6 |                       767542 |                   1.02095  |       0.954276 |        1.09007 |       0.91451  |            0.82508  |            0.939885 |        0.945911 |
|          3 | submission_2024split_v14_marjun_cogs_up100.csv           | dataset\submission_2024split_v14_marjun_cogs_up100.csv           | full Mar-Jun COGS raise, roughly undoing prior 10% down for high-scale months          |            122 |          106567   |              106567   |                      53283.5 |                       754221 |                   1.02794  |       0.954276 |        1.09007 |       0.931537 |            0.82508  |            0.961742 |        0.967908 |
|          4 | submission_2024split_v14_q2_cogs_up075.csv               | dataset\submission_2024split_v14_q2_cogs_up075.csv               | localize COGS re-raise to 2024Q2 only                                                  |             91 |           60089.8 |               60089.8 |                      30044.9 |                       777460 |                   1.01575  |       0.954276 |        1.09007 |       0.901833 |            0.82508  |            0.923611 |        0.945911 |
|          5 | submission_2024split_v14_q2_cogs_up100.csv               | dataset\submission_2024split_v14_q2_cogs_up100.csv               | strong 2024Q2 COGS re-raise                                                            |             91 |           80119.7 |               80119.7 |                      40059.8 |                       767445 |                   1.02101  |       0.954276 |        1.09007 |       0.914634 |            0.82508  |            0.940044 |        0.967908 |
|          6 | submission_2024split_v14_march_cogs_up100.csv            | dataset\submission_2024split_v14_march_cogs_up100.csv            | March-only COGS re-raise; checks if Q1 high-scale is the issue                         |             31 |           26447.4 |               26447.4 |                      13223.7 |                       794281 |                   1.00693  |       0.954276 |        1.09007 |       0.880332 |            0.82508  |            0.89601  |        0.879917 |
|          7 | submission_2024split_v14_janfeb_cogs_down100.csv         | dataset\submission_2024split_v14_janfeb_cogs_down100.csv         | Jan-Feb COGS further down; tests whether all-H1-down improvement came from early 2024  |             60 |          -28534.4 |               28534.4 |                      14267.2 |                       793237 |                   0.992519 |       0.954276 |        1.09007 |       0.845194 |            0.742572 |            0.874311 |        0.879917 |
|          8 | submission_2024split_v14_janfeb_down100_marjun_up075.csv | dataset\submission_2024split_v14_janfeb_down100_marjun_up075.csv | split 2024H1: early months lower, Mar-Jun higher                                       |            182 |           51390.9 |              108460   |                      54229.9 |                       753275 |                   1.01347  |       0.954276 |        1.09007 |       0.896274 |            0.742572 |            0.939885 |        0.945911 |
|          9 | submission_2024split_v14_janfeb_down150_marjun_up100.csv | dataset\submission_2024split_v14_janfeb_down150_marjun_up100.csv | aggressive split: Jan-Feb lower, Mar-Jun restored                                      |            182 |           63765.4 |              149369   |                      74684.3 |                       732820 |                   1.01672  |       0.954276 |        1.09007 |       0.904182 |            0.701318 |            0.961742 |        0.967908 |
|         10 | submission_2024split_v14_h1_cogs_up050.csv               | dataset\submission_2024split_v14_h1_cogs_up050.csv               | diagnostic: current full 2024H1 may be too low after v8 down                           |            182 |           67550.7 |               67550.7 |                      33775.4 |                       773729 |                   1.01771  |       0.954276 |        1.09007 |       0.906601 |            0.866334 |            0.918027 |        0.923913 |

Suggested order:

1. `submission_2024split_v14_marjun_cogs_up075.csv`
2. If improves: `submission_2024split_v14_marjun_cogs_up100.csv`
3. If weak/fails: `submission_2024split_v14_q2_cogs_up075.csv`
4. If Mar-Jun up improves but Jan-Feb still suspect: `submission_2024split_v14_janfeb_down100_marjun_up075.csv`
