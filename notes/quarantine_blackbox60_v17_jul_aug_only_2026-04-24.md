# Quarantine Blackbox 60x V17 Jul-Aug Only

Run directory: `logs\20260424_012917_quarantine_blackbox60_v17_jul_aug_only`

## Status

This branch is **not clean**. It builds directly on the current blackbox best and public-leaderboard feedback.

Current anchor:

- `submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv` = `662759.87577`

## Why This Batch Exists

- Broad `Q3 up / Q4 down` failed.
- `Jul-Aug up / Q4 down` also failed harder, which makes the `Q4 down` leg suspect.
- The next branch drops `Q4 down` entirely and isolates `Jul`, `Aug`, and `Sep` inside `Q3`.

## Candidate Manifest

|   priority | filename                                    | thesis                                                                                                       |   jul_scale |   aug_scale |   sep_scale |   mean_abs_rev_delta_vs_current |   mean_abs_cogs_delta_vs_current |   movement |   revenue_total_ratio_vs_current |   cogs_total_ratio_vs_current |   ratio_total |   ratio_2023H1 |   ratio_2023H2 |   ratio_2024H1 |     rev_jul |   ratio_jul |     rev_aug |   ratio_aug |     rev_sep |   ratio_sep |      rev_q3 |   ratio_q3 |
|-----------:|:--------------------------------------------|:-------------------------------------------------------------------------------------------------------------|------------:|------------:|------------:|--------------------------------:|---------------------------------:|-----------:|---------------------------------:|------------------------------:|--------------:|---------------:|---------------:|---------------:|------------:|------------:|------------:|------------:|------------:|------------:|------------:|-----------:|
|          1 | submission_qbb60v17_augup050_only.csv       | August has the single highest ratio distortion in H2; test whether the missing signal is mostly August only. |        1    |       1.05  |       1     |                         10289.2 |                                0 |    5144.6  |                          1.00238 |                             1 |      0.899436 |        0.87628 |       1.00376  |       0.847066 | 1.28692e+08 |     1.05171 | 1.18408e+08 |     1.1586  | 1.12859e+08 |    0.965155 | 3.59959e+08 |    1.05973 |
|          2 | submission_qbb60v17_augup075_only.csv       | If August is the main miss, a stronger one-month correction should show a clearer public jump.               |        1    |       1.075 |       1     |                         15433.8 |                                0 |    7716.9  |                          1.00356 |                             1 |      0.898371 |        0.87628 |       0.999258 |       0.847066 | 1.28692e+08 |     1.05171 | 1.21227e+08 |     1.13165 | 1.12859e+08 |    0.965155 | 3.62778e+08 |    1.0515  |
|          3 | submission_qbb60v17_julup050_only.csv       | Check whether July is the more important undercalled month instead of August.                                |        1.05 |       1     |       1     |                         11742   |                                0 |    5870.98 |                          1.00271 |                             1 |      0.899135 |        0.87628 |       1.00248  |       0.847066 | 1.35126e+08 |     1.00163 | 1.1277e+08  |     1.21653 | 1.12859e+08 |    0.965155 | 3.60755e+08 |    1.05739 |
|          4 | submission_qbb60v17_augup050_sepdown025.csv | Reallocate within Q3: lift August but trim September, since broad Q3-up likely overmoved September.          |        1    |       1.05  |       0.975 |                         15437.9 |                                0 |    7718.94 |                          1.00119 |                             1 |      0.900505 |        0.87628 |       1.0083   |       0.847066 | 1.28692e+08 |     1.05171 | 1.18408e+08 |     1.1586  | 1.10037e+08 |    0.989903 | 3.57137e+08 |    1.0681  |
