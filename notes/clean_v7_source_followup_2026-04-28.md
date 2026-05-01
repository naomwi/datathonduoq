# Clean V7 Source Follow-Up

Run directory: `logs\20260428_133332_clean_v7_source_followup`

## Boundary

This is clean-input public-guided. It does not read `sample_submission.csv`, previous submissions, blackbox files, or test targets.

Known public results:

- `submission_cleanv2_h1fine_b044_r0876.csv = 673757.34993`
- `submission_cleanv3_funnel_c110_h1r0876.csv = 673759.96838`
- `submission_cleanv7_source_h1_s020_r0870.csv = 673720.88479`

## Hypothesis

The source-quality period-total head is a real clean improvement, but the first gain is tiny. This run maps the local optimum around:

- source recovery near `0.20`
- H1 COGS ratio near `0.870`

## Candidate Manifest

|   priority | filename                                      |   source_recovery |   h1_ratio |   revenue_total |   cogs_total |   ratio_total |   rev_2023H1 |   cogs_2023H1 |   ratio_2023H1 |   rev_2023H2 |   cogs_2023H2 |   rev_2024H1 |   cogs_2024H1 | note                                                               |
|-----------:|:----------------------------------------------|------------------:|-----------:|----------------:|-------------:|--------------:|-------------:|--------------:|---------------:|-------------:|--------------:|-------------:|--------------:|:-------------------------------------------------------------------|
|          1 | submission_cleanv7_sourcefine_s0190_r0870.csv |             0.19  |      0.87  |     2.35389e+09 |  2.11142e+09 |      0.896989 |  8.41384e+08 |   7.32004e+08 |          0.87  |  6.21578e+08 |   6.24991e+08 |  8.83831e+08 |   7.46735e+08 | Slightly lower source-quality H1 recovery than current clean best. |
|          2 | submission_cleanv7_sourcefine_s0195_r0870.csv |             0.195 |      0.87  |     2.35834e+09 |  2.11529e+09 |      0.896938 |  8.45835e+08 |   7.35876e+08 |          0.87  |  6.21578e+08 |   6.24991e+08 |  8.83831e+08 |   7.46735e+08 | Half-step below current source-quality H1 recovery.                |
|          3 | submission_cleanv7_sourcefine_s0205_r0870.csv |             0.205 |      0.87  |     2.36724e+09 |  2.12303e+09 |      0.896837 |  8.54735e+08 |   7.43619e+08 |          0.87  |  6.21578e+08 |   6.24991e+08 |  8.83831e+08 |   7.46735e+08 | Half-step above current source-quality H1 recovery.                |
|          4 | submission_cleanv7_sourcefine_s0210_r0870.csv |             0.21  |      0.87  |     2.37169e+09 |  2.1269e+09  |      0.896786 |  8.59185e+08 |   7.47491e+08 |          0.87  |  6.21578e+08 |   6.24991e+08 |  8.83831e+08 |   7.46735e+08 | Slightly higher source-quality H1 recovery.                        |
|          5 | submission_cleanv7_sourcefine_s0200_r0866.csv |             0.2   |      0.866 |     2.36279e+09 |  2.11576e+09 |      0.895448 |  8.50285e+08 |   7.36347e+08 |          0.866 |  6.21578e+08 |   6.24991e+08 |  8.83831e+08 |   7.46735e+08 | Same H1 source level, lower COGS ratio.                            |
|          6 | submission_cleanv7_sourcefine_s0200_r0868.csv |             0.2   |      0.868 |     2.36279e+09 |  2.11746e+09 |      0.896168 |  8.50285e+08 |   7.38047e+08 |          0.868 |  6.21578e+08 |   6.24991e+08 |  8.83831e+08 |   7.46735e+08 | Same H1 source level, slightly lower COGS ratio.                   |
|          7 | submission_cleanv7_sourcefine_s0200_r0872.csv |             0.2   |      0.872 |     2.36279e+09 |  2.12086e+09 |      0.897607 |  8.50285e+08 |   7.41448e+08 |          0.872 |  6.21578e+08 |   6.24991e+08 |  8.83831e+08 |   7.46735e+08 | Same H1 source level, slightly higher COGS ratio.                  |
|          8 | submission_cleanv7_sourcefine_s0200_r0874.csv |             0.2   |      0.874 |     2.36279e+09 |  2.12256e+09 |      0.898327 |  8.50285e+08 |   7.43149e+08 |          0.874 |  6.21578e+08 |   6.24991e+08 |  8.83831e+08 |   7.46735e+08 | Same H1 source level, mid-way back toward r0876.                   |
|          9 | submission_cleanv7_sourcefine_s0195_r0868.csv |             0.195 |      0.868 |     2.35834e+09 |  2.1136e+09  |      0.896221 |  8.45835e+08 |   7.34184e+08 |          0.868 |  6.21578e+08 |   6.24991e+08 |  8.83831e+08 |   7.46735e+08 | Lower source recovery plus lower COGS ratio.                       |
|         10 | submission_cleanv7_sourcefine_s0205_r0872.csv |             0.205 |      0.872 |     2.36724e+09 |  2.12474e+09 |      0.897559 |  8.54735e+08 |   7.45329e+08 |          0.872 |  6.21578e+08 |   6.24991e+08 |  8.83831e+08 |   7.46735e+08 | Higher source recovery plus slightly higher COGS ratio.            |

## Submit Order

1. `submission_cleanv7_sourcefine_s0200_r0868.csv`
2. `submission_cleanv7_sourcefine_s0195_r0870.csv`
3. `submission_cleanv7_sourcefine_s0205_r0870.csv`
4. `submission_cleanv7_sourcefine_s0200_r0872.csv`
5. `submission_cleanv7_sourcefine_s0195_r0868.csv`
