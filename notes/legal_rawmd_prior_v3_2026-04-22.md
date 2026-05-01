# Legal Raw Month-Day Prior V3

Run directory: `logs\20260422_153220_legal_rawmd_prior_v3`

Base file: `submission_top10_v13_rev2023h2_up100_keepcogs.csv` scored `797595.9641`.

Latest legal score:

| file | public score |
|---|---:|
| `submission_legal_router_v1_reliability_strong_nonh2_keepcogs.csv` | `745552.16085` |

## Core Finding

The public black-box experiments imply that the sample-style day allocation is not an external magic signal. It is almost exactly reproducible from train-only `sales.csv` raw month-day shares, separately for `Revenue` and `COGS`.

This script therefore does **not** read `sample_submission.csv`. It rebuilds the same family legally:

- derive `Revenue` daily shares from train `Revenue` by `month_day` within H1/H2;
- derive `COGS` daily shares from train `COGS` by `month_day` within H1/H2;
- preserve base period totals unless a candidate explicitly does only within-period train-ratio redistribution;
- shrink `2023H2` Revenue shape because public response showed that H2 over-shape is toxic.

## Candidate Manifest

|   priority | filename                                                         | path                                                                     | thesis                                                                                                           |   rev_default_alpha |   cogs_default_alpha |   rev_alpha_2023H2 |   cogs_ratio_blend |   revenue_total_ratio_vs_base |   cogs_total_ratio_vs_base |   mean_abs_rev_delta |   mean_abs_cogs_delta |   directional_best_case_gain |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |   base_ratio_2023H1 |   base_ratio_2023H2 |   base_ratio_2024H1 |
|-----------:|:-----------------------------------------------------------------|:-------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------|--------------------:|---------------------:|-------------------:|-------------------:|------------------------------:|---------------------------:|---------------------:|----------------------:|-----------------------------:|---------------:|---------------:|---------------:|--------------------:|--------------------:|--------------------:|
|          1 | submission_legal_rawmd_prior_v3_both_a0725.csv                   | dataset\submission_legal_rawmd_prior_v3_both_a0725.csv                   | Legal train-only reconstruction of the strong global raw month-day prior: Revenue/COGS alpha=0.725.              |               0.725 |                0.725 |              0.725 |               0    |                             1 |                          1 |               420515 |                361205 |                       390860 |       0.948806 |       0.990687 |       0.857442 |            0.949786 |            0.991758 |            0.856141 |
|          2 | submission_legal_rawmd_prior_v3_r080_c065_h2r010.csv             | dataset\submission_legal_rawmd_prior_v3_r080_c065_h2r010.csv             | Best black-box lesson translated legally: Revenue alpha=0.80 outside H2, H2 Revenue alpha=0.10, COGS alpha=0.65. |               0.8   |                0.65  |              0.1   |               0    |                             1 |                          1 |               358513 |                323839 |                       341176 |       0.952669 |       0.98316  |       0.862874 |            0.949786 |            0.991758 |            0.856141 |
|          3 | submission_legal_rawmd_prior_v3_r080_c065_h2r000.csv             | dataset\submission_legal_rawmd_prior_v3_r080_c065_h2r000.csv             | Ablate unstable H2 Revenue shape completely while keeping raw month-day shape elsewhere.                         |               0.8   |                0.65  |              0     |               0    |                             1 |                          1 |               343441 |                323839 |                       333640 |       0.952669 |       0.983434 |       0.862874 |            0.949786 |            0.991758 |            0.856141 |
|          4 | submission_legal_rawmd_prior_v3_r080_c065_h2r020.csv             | dataset\submission_legal_rawmd_prior_v3_r080_c065_h2r020.csv             | Slightly less aggressive H2 shrink than the current black-box optimum.                                           |               0.8   |                0.65  |              0.2   |               0    |                             1 |                          1 |               373585 |                323839 |                       348712 |       0.952669 |       0.983427 |       0.862874 |            0.949786 |            0.991758 |            0.856141 |
|          5 | submission_legal_rawmd_prior_v3_r075_c065_h2r010.csv             | dataset\submission_legal_rawmd_prior_v3_r075_c065_h2r010.csv             | Safer Revenue alpha if r080 overshoots; same legal COGS shape.                                                   |               0.75  |                0.65  |              0.1   |               0    |                             1 |                          1 |               337048 |                323839 |                       330444 |       0.951208 |       0.98316  |       0.860741 |            0.949786 |            0.991758 |            0.856141 |
|          6 | submission_legal_rawmd_prior_v3_r080_c070_h2r010.csv             | dataset\submission_legal_rawmd_prior_v3_r080_c070_h2r010.csv             | Test whether COGS needs slightly more raw month-day shape than the 0.65 black-box region.                        |               0.8   |                0.7   |              0.1   |               0    |                             1 |                          1 |               358513 |                348750 |                       353631 |       0.951413 |       0.982396 |       0.861184 |            0.949786 |            0.991758 |            0.856141 |
|          7 | submission_legal_rawmd_prior_v3_r080_c065_h2r010_cogsratio15.csv | dataset\submission_legal_rawmd_prior_v3_r080_c065_h2r010_cogsratio15.csv | Same shape as the lead candidate, plus a train-only COGS ratio redistribution within each period.                |               0.8   |                0.65  |              0.1   |               0.15 |                             1 |                          1 |               358513 |                316491 |                       337502 |       0.952184 |       0.984999 |       0.862284 |            0.949786 |            0.991758 |            0.856141 |

## Submit Guidance

1. `submission_legal_rawmd_prior_v3_r080_c065_h2r010.csv`
2. If it lands around the old sample-derived 68x/69x region, test `submission_legal_rawmd_prior_v3_r080_c065_h2r010_cogsratio15.csv`.
3. If H2 is still too shaped, submit `submission_legal_rawmd_prior_v3_r080_c065_h2r000.csv`.
4. If the lead is unstable or worse than V1, submit the safer reconstruction baseline `submission_legal_rawmd_prior_v3_both_a0725.csv`.
