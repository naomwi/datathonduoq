# Legal Period Shape Router V2

Run directory: `logs\20260422_152641_legal_period_shape_router_v2`

Base legal file: `submission_top10_v13_rev2023h2_up100_keepcogs.csv` scored `797595.9641`.

V1 legal result:

| file | public score |
|---|---:|
| `submission_legal_router_v1_reliability_strong_nonh2_keepcogs.csv` | `745552.16085` |

## Why V2

V1 proved that the legal reconstruction is directionally correct: it gained about `52k` versus the pre-sample legal base.

The remaining gap suggests the legal donor needs to be more organizer-like:

- recent-weighted, not equal-weight 2013-2022;
- Tet/lunar-aware in H1/2024H1;
- almost no H2 daily shape force;
- COGS handled separately by train-only ratio regime.

## Candidate Manifest

|   priority | filename                                                             | path                                                                         | thesis                                                                                                       | cogs_mode         |   cogs_strength |   rev_weight_2023H1 |   rev_weight_2023H2 |   rev_weight_2024H1 |   revenue_total_ratio_vs_base |   cogs_total_ratio_vs_base |   mean_abs_rev_delta |   mean_abs_cogs_delta |   directional_best_case_gain |      min_revenue |         min_cogs |
|-----------:|:---------------------------------------------------------------------|:-----------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------------|:------------------|----------------:|--------------------:|--------------------:|--------------------:|------------------------------:|---------------------------:|---------------------:|----------------------:|-----------------------------:|-----------------:|-----------------:|
|          1 | submission_legal_router_v2_recent_raw_nonh2_h2flat_keepcogs.csv      | dataset\submission_legal_router_v2_recent_raw_nonh2_h2flat_keepcogs.csv      | Recent-weighted raw month-day/Tet shape on H1/2024H1, H2 flat; strongest legal analogue of black-box router. | keep              |            0    |                0.95 |                0    |                0.95 |                             1 |                   1        |               383705 |                   0   |                       191852 | 869530           |      1.08306e+06 |
|          2 | submission_legal_router_v2_recent3_raw_nonh2_h2flat_keepcogs.csv     | dataset\submission_legal_router_v2_recent3_raw_nonh2_h2flat_keepcogs.csv     | Sharper recent-3y non-H2 shape, H2 flat.                                                                     | keep              |            0    |                0.9  |                0    |                0.9  |                             1 |                   1        |               392257 |                   0   |                       196128 | 798161           |      1.08306e+06 |
|          3 | submission_legal_router_v2_recent_reliable_nonh2_h2tiny_keepcogs.csv | dataset\submission_legal_router_v2_recent_reliable_nonh2_h2tiny_keepcogs.csv | Recent reliability router with tiny H2 weight, safer than raw.                                               | keep              |            0    |                0.75 |                0.02 |                0.85 |                             1 |                   1        |               301824 |                   0   |                       150912 |      1.0912e+06  |      1.08306e+06 |
|          4 | submission_legal_router_v2_event_nonh2_h2tiny_keepcogs.csv           | dataset\submission_legal_router_v2_event_nonh2_h2tiny_keepcogs.csv           | Recent signed-event/Tet template on non-H2, tiny H2.                                                         | keep              |            0    |                0.7  |                0.05 |                0.85 |                             1 |                   1        |               289981 |                   0   |                       144990 |      1.21389e+06 |      1.08306e+06 |
|          5 | submission_legal_router_v2_raw_nonh2_h2flat_ratio20.csv              | dataset\submission_legal_router_v2_raw_nonh2_h2flat_ratio20.csv              | Recent raw non-H2 legal router plus train-only COGS ratio blend.                                             | ratio             |            0.2  |                0.95 |                0    |                0.95 |                             1 |                   0.983773 |               383705 |               97976.4 |                       240841 | 869530           |      1.00759e+06 |
|          6 | submission_legal_router_v2_raw_nonh2_h2flat_cogshint.csv             | dataset\submission_legal_router_v2_raw_nonh2_h2flat_cogshint.csv             | Recent raw non-H2 legal router plus public-inferred COGS period direction via train ratios.                  | ratio_h2up_h4down |            0.25 |                0.95 |                0    |                0.95 |                             1 |                   0.981972 |               383705 |              118411   |                       251058 | 869530           | 988725           |

## Submit Guidance

1. `submission_legal_router_v2_recent_raw_nonh2_h2flat_keepcogs.csv`
2. If it improves over V1: `submission_legal_router_v2_recent3_raw_nonh2_h2flat_keepcogs.csv`
3. If raw overdoes it: `submission_legal_router_v2_recent_reliable_nonh2_h2tiny_keepcogs.csv`
4. Only after Revenue-shape improves, test COGS: `submission_legal_router_v2_raw_nonh2_h2flat_cogshint.csv`
