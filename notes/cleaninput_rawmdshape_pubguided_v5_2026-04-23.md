# Clean-Input RawMD Shape Public-Guided V5

Run directory: `logs\20260423_192533_cleaninput_rawmdshape_pubguided`

## Boundary

This branch does not read `sample_submission.csv`, previous submission files, or test target values as inputs.

It is **clean-input but public-guided**: period-level recovery assumptions were adjusted after public feedback, while daily shape is rebuilt from raw provided files and train `sales.csv` month-day priors.

## Why This Run Exists

The v4 period totals are close to the best-known region, but v4 uses a pure historical sales-profile daily shape. The earlier source-clean raw-md/anchor shape scored much better, so this run keeps v4-style totals and swaps in the cleaner raw-md/anchor daily allocation.

## Candidate Manifest

|   priority | filename                                                       | cogs_2024h1_mode   |   revenue_total |   cogs_total |   ratio_total |   rev_2023H1 |   rev_2023H2 |   rev_2024H1 |   cogs_2023H1 |   cogs_2023H2 |   cogs_2024H1 |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 | note                                                                                                 |
|-----------:|:---------------------------------------------------------------|:-------------------|----------------:|-------------:|--------------:|-------------:|-------------:|-------------:|--------------:|--------------:|--------------:|---------------:|---------------:|---------------:|:-----------------------------------------------------------------------------------------------------|
|          1 | submission_cleaninput_rawmdshape_v5_v4main.csv                 | scenario           |     2.27614e+09 |  2.13742e+09 |      0.939053 |  7.63629e+08 |  6.21578e+08 |  8.83831e+08 |   7.46787e+08 |   6.24991e+08 |   7.57951e+08 |       0.977944 |        1.00549 |       0.857575 | Use clean raw-md/anchor daily shape with v4 clean-input public-guided period totals.                 |
|          2 | submission_cleaninput_rawmdshape_v5_v4main_cogs2024gap0545.csv | gap_beta0545       |     2.27614e+09 |  2.1262e+09  |      0.934126 |  7.63629e+08 |  6.21578e+08 |  8.83831e+08 |   7.46787e+08 |   6.24991e+08 |   7.46735e+08 |       0.977944 |        1.00549 |       0.844885 | Same as v4main, but 2024H1 COGS is an independent train low/high gap total rather than max H1 ratio. |
|          3 | submission_cleaninput_rawmdshape_v5_h1p85.csv                  | gap_beta0545       |     2.27614e+09 |  2.11605e+09 |      0.929665 |  7.63629e+08 |  6.21578e+08 |  8.83831e+08 |   7.36635e+08 |   6.24991e+08 |   7.46735e+08 |       0.96465  |        1.00549 |       0.844885 | Softer 2023H1 COGS upper-tail plus independent 2024H1 COGS gap total.                                |
|          4 | submission_cleaninput_rawmdshape_v5_revlow.csv                 | gap_beta0545       |     2.25612e+09 |  2.10681e+09 |      0.933818 |  7.36918e+08 |  6.2827e+08  |  8.83831e+08 |   7.20665e+08 |   6.31719e+08 |   7.46735e+08 |       0.977944 |        1.00549 |       0.844885 | Lower 2023H1 revenue, stronger 2023H2 revenue, raw-md daily shape.                                   |
|          5 | submission_cleaninput_rawmdshape_v5_v4main_cogs2024gap0515.csv | gap_beta0515       |     2.27614e+09 |  2.11533e+09 |      0.929348 |  7.63629e+08 |  6.21578e+08 |  8.83831e+08 |   7.46787e+08 |   6.24991e+08 |   7.35862e+08 |       0.977944 |        1.00549 |       0.832582 | Slightly lower 2024H1 COGS independent gap total.                                                    |

## Submit Order

1. `submission_cleaninput_rawmdshape_v5_v4main_cogs2024gap0545.csv`
2. `submission_cleaninput_rawmdshape_v5_v4main.csv`
3. `submission_cleaninput_rawmdshape_v5_h1p85.csv`
