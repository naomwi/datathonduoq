# Quarantine Blackbox 60x V18 2023H2 COGS Down

Run directory: `logs\20260424_013529_quarantine_blackbox60_v18_2023h2_cogs_down`

## Status

This branch is **not clean**. It builds directly on the current blackbox best and public-leaderboard feedback.

Current anchor:

- `submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv` = `662759.87577`

## Why This Batch Exists

- `2023H2 Revenue up` failed.
- `2023H2 Revenue down` also failed.
- `Q3/Q4` revenue reallocations also failed.
- The remaining plausible H2 axis is therefore `COGS`, not `Revenue`: current 2023H2 cost ratio is still high while revenue moves keep hurting.

## Candidate Manifest

|   priority | filename                                   | thesis                                                                                                                                  |   cogs_scale_2023H2 |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   movement |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_total |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |   ratio_q3 |   ratio_q4 |
|-----------:|:-------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------|--------------------:|--------------------------------:|---------------------------------:|-----------:|---------------------------------:|------------------------------:|--------------:|---------------:|---------------:|---------------:|-----------:|-----------:|
|          1 | submission_qbb60v18_cogs2023h2_down010.csv | Small H2 cost-ratio correction: current 2023H2 ratio is still high, but with 3 submissions left the first probe should be conservative. |                0.99 |                               0 |                          11467.6 |     5733.8 |                                1 |                      0.997062 |      0.898925 |        0.87628 |       1.00275  |       0.847066 |    1.06583 |   0.918763 |
|          2 | submission_qbb60v18_cogs2023h2_down020.csv | Medium H2 cost-ratio correction if the H2 error is materially in COGS rather than Revenue.                                              |                0.98 |                               0 |                          22935.2 |    11467.6 |                                1 |                      0.994124 |      0.896277 |        0.87628 |       0.992622 |       0.847066 |    1.05506 |   0.909482 |
|          3 | submission_qbb60v18_cogs2023h2_down030.csv | Stronger H2 COGS reduction if the hidden public regime wants a large step down in late-2023 costs.                                      |                0.97 |                               0 |                          34402.8 |    17201.4 |                                1 |                      0.991186 |      0.893628 |        0.87628 |       0.982493 |       0.847066 |    1.0443  |   0.900202 |
