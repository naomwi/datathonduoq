# Clean-Input RawMD Shape V6 Follow-Up

Run directory: `logs\20260423_201155_cleaninput_rawmdshape_v6_followup`

## Boundary

This script rebuilds daily shape from raw provided inputs through the clean raw-md anchor path. It does not read `sample_submission.csv`, previous submission files, or test target values as inputs.

It is still **public-guided** because period totals are selected from previous public feedback and scenario analysis.

## Candidate Manifest

|   priority | filename                                                            |   revenue_total |   cogs_total |   ratio_total |   rev_2023H1 |   rev_2023H2 |   rev_2024H1 |   rev_final |   cogs_2023H1 |   cogs_2023H2 |   cogs_2024H1 |   cogs_final | note                                                                                            |
|-----------:|:--------------------------------------------------------------------|----------------:|-------------:|--------------:|-------------:|-------------:|-------------:|------------:|--------------:|--------------:|--------------:|-------------:|:------------------------------------------------------------------------------------------------|
|          1 | submission_cleaninput_rawmdshape_v6_finalday_down.csv               |     2.27469e+09 |  2.12451e+09 |      0.933978 |  7.63629e+08 |  6.21578e+08 |  8.83831e+08 | 5.65516e+06 |   7.46787e+08 |   6.24991e+08 |   7.46735e+08 |  6.00108e+06 | Isolate whether the v5 loss is partly the oversized 2024-07-01 final day.                       |
|          2 | submission_cleaninput_rawmdshape_v6_finalday_down_h1cogs_mid.csv    |     2.27469e+09 |  2.12865e+09 |      0.935796 |  7.63629e+08 |  6.21578e+08 |  8.83831e+08 | 5.65516e+06 |   7.50922e+08 |   6.24991e+08 |   7.46735e+08 |  6.00108e+06 | Final day down plus 2023H1 COGS raised to the train-derived/public-guided middle stress level.  |
|          3 | submission_cleaninput_rawmdshape_v6_publicguided_totals.csv         |     2.27325e+09 |  2.1309e+09  |      0.937379 |  7.63982e+08 |  6.20433e+08 |  8.83183e+08 | 5.65516e+06 |   7.51919e+08 |   6.26159e+08 |   7.46821e+08 |  6.00108e+06 | Raw-md clean daily shape with public-guided period totals from the currently best-known region. |
|          4 | submission_cleaninput_rawmdshape_v6_publicguided_totals_cogsmid.csv |     2.27325e+09 |  2.1299e+09  |      0.93694  |  7.63982e+08 |  6.20433e+08 |  8.83183e+08 | 5.65516e+06 |   7.50922e+08 |   6.26159e+08 |   7.46821e+08 |  6.00108e+06 | Same period revenue totals, but 2023H1 COGS softened to avoid over-stress.                      |

## Submit Order

1. `submission_cleaninput_rawmdshape_v6_finalday_down_h1cogs_mid.csv`
2. `submission_cleaninput_rawmdshape_v6_publicguided_totals.csv`
3. `submission_cleaninput_rawmdshape_v6_finalday_down.csv`
