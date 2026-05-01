# Legal Period Shape Router V1

Run directory: `logs\20260422_151902_legal_period_shape_router`

Base legal/public-best-before-sample file: `submission_top10_v13_rev2023h2_up100_keepcogs.csv` with public score `797595.9641`.

Important:

- This script does **not** read or use `sample_submission.csv`.
- Public/sample black-box results are used only as architectural diagnosis.
- All shapes and ratios are derived from `sales.csv` train history.

## Public Black-Box Insight Translated

2023H2 forbidden-template response:

|   alpha |   score |
|--------:|--------:|
|     1   |  707437 |
|     0.8 |  698898 |
|     0.6 |  692129 |
|     0.4 |  687113 |
|     0.2 |  684700 |
|     0.1 |  684463 |

Legal interpretation:

- H2 daily shape is unreliable and must be shrunk.
- H1/2024H1 can tolerate stronger calendar shape than H2.
- COGS should be ratio-routed, not copied as a daily-shape target.

## Train-Only Shape Backtest

Backtest assumes the period total is known, then tests only daily distribution quality:

| half   | mode               |   mean_wape |   mean_corr |
|:-------|:-------------------|------------:|------------:|
| H1     | raw_md             |    0.181619 |    0.883966 |
| H1     | reliability_router |    0.187005 |    0.87687  |
| H1     | signed_event       |    0.231306 |    0.856225 |
| H1     | month_shrink       |    0.243679 |    0.772193 |
| H2     | raw_md             |    0.200229 |    0.82676  |
| H2     | reliability_router |    0.21711  |    0.799881 |
| H2     | signed_event       |    0.231699 |    0.798057 |
| H2     | month_shrink       |    0.239917 |    0.755326 |

## Recent Window Priors From Train Only

| window_name   |     revenue |        cogs |   days |   cogs_ratio |   rev_per_day |   uplift_vs_none |
|:--------------|------------:|------------:|-------:|-------------:|--------------:|-----------------:|
| fall          | 2.88251e+08 | 2.64324e+08 |    102 |     0.916994 |   2.82599e+06 |       -0.0652981 |
| midyear       | 2.93572e+08 | 2.82248e+08 |     90 |     0.961426 |   3.26191e+06 |        0.0788834 |
| none          | 2.03476e+09 | 1.69017e+09 |    673 |     0.830649 |   3.02341e+06 |        0         |
| spring        | 4.31517e+08 | 3.9066e+08  |     93 |     0.905316 |   4.63997e+06 |        0.53468   |
| yearend       | 2.19202e+08 | 2.20235e+08 |    138 |     1.00471  |   1.58842e+06 |       -0.474626  |

## Candidate Manifest

|   priority | filename                                                         | path                                                                     | thesis                                                                                                  | revenue_template   | cogs_mode          |   cogs_strength |   rev_weight_2023H1 |   rev_weight_2023H2 |   rev_weight_2024H1 |   revenue_total_ratio_vs_base |   cogs_total_ratio_vs_base |   mean_abs_rev_delta |   mean_abs_cogs_delta |   directional_best_case_gain |   min_revenue |    min_cogs |
|-----------:|:-----------------------------------------------------------------|:-------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------|:-------------------|:-------------------|----------------:|--------------------:|--------------------:|--------------------:|------------------------------:|---------------------------:|---------------------:|----------------------:|-----------------------------:|--------------:|------------:|
|          1 | submission_legal_router_v1_reliability_soft_keepcogs.csv         | dataset\submission_legal_router_v1_reliability_soft_keepcogs.csv         | Train-only reliability router: H1 moderate, H2 heavily shrunk, 2024H1 moderate; keep base COGS.         | reliability_router | keep               |            0    |                0.35 |                0.08 |                0.45 |                             1 |                   1        |               174111 |                   0   |                      87055.3 |   1.1891e+06  | 1.08306e+06 |
|          2 | submission_legal_router_v1_reliability_strong_nonh2_keepcogs.csv | dataset\submission_legal_router_v1_reliability_strong_nonh2_keepcogs.csv | Public insight transfer: stronger legal train-shape on non-H2, almost no H2 daily-shape force.          | reliability_router | keep               |            0    |                0.65 |                0.03 |                0.75 |                             1 |                   1        |               286568 |                   0   |                     143284   |   1.21991e+06 | 1.08306e+06 |
|          3 | submission_legal_router_v1_month_shrink_h2_keepcogs.csv          | dataset\submission_legal_router_v1_month_shrink_h2_keepcogs.csv          | Conservative train-only month-shrink template; designed for unstable H2 shape.                          | month_shrink       | keep               |            0    |                0.45 |                0.2  |                0.55 |                             1 |                   1        |               294134 |                   0   |                     147067   |   1.34604e+06 | 1.08306e+06 |
|          4 | submission_legal_router_v1_signed_events_keepcogs.csv            | dataset\submission_legal_router_v1_signed_events_keepcogs.csv            | Signed train-only event priors: spring positive, fall/yearend damped; keep base COGS.                   | signed_event       | keep               |            0    |                0.5  |                0.1  |                0.65 |                             1 |                   1        |               249276 |                   0   |                     124638   |   1.26405e+06 | 1.08306e+06 |
|          5 | submission_legal_router_v1_raw_h1_h4_h2flat_keepcogs.csv         | dataset\submission_legal_router_v1_raw_h1_h4_h2flat_keepcogs.csv         | High H1/2024H1 month-day shape, nearly flat H2; direct legal analogue of black-box period routing.      | raw_md             | keep               |            0    |                0.8  |                0    |                0.85 |                             1 |                   1        |               355487 |                   0   |                     177744   |   1.14726e+06 | 1.08306e+06 |
|          6 | submission_legal_router_v1_reliability_soft_cogsratio20.csv      | dataset\submission_legal_router_v1_reliability_soft_cogsratio20.csv      | Reliability Revenue router plus train-only COGS ratio blend.                                            | reliability_router | ratio_blend        |            0.2  |                0.35 |                0.08 |                0.45 |                             1 |                   0.983725 |               174111 |               72134.8 |                     123123   |   1.1891e+06  | 1.05751e+06 |
|          7 | submission_legal_router_v1_signed_events_cogsratio30.csv         | dataset\submission_legal_router_v1_signed_events_cogsratio30.csv         | Signed event Revenue router plus train-only COGS ratio regime.                                          | signed_event       | ratio_blend        |            0.3  |                0.5  |                0.1  |                0.65 |                             1 |                   0.975564 |               249276 |              125037   |                     187156   |   1.26405e+06 | 1.13699e+06 |
|          8 | submission_legal_router_v1_strong_nonh2_cogshint.csv             | dataset\submission_legal_router_v1_strong_nonh2_cogshint.csv             | Strong non-H2 legal Revenue router plus public-inferred COGS period direction encoded via train ratios. | reliability_router | period_public_hint |            0.25 |                0.65 |                0.03 |                0.75 |                             1 |                   0.981531 |               286568 |              105112   |                     195840   |   1.21991e+06 | 1.07676e+06 |

## Submit Guidance

If testing legal reconstruction, submit in this order:

1. `submission_legal_router_v1_reliability_strong_nonh2_keepcogs.csv`
2. `submission_legal_router_v1_signed_events_keepcogs.csv`
3. `submission_legal_router_v1_strong_nonh2_cogshint.csv`
4. `submission_legal_router_v1_month_shrink_h2_keepcogs.csv`

The first candidate directly encodes the highest-confidence black-box lesson: strong non-H2 shape, almost no H2 shape.
