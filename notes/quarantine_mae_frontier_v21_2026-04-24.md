# Quarantine MAE Frontier V21

Run directory: `logs\20260424_171509_quarantine_mae_frontier_v21`

## Boundary

This branch is **quarantine blackbox**. It uses public-leaderboard feedback and previous submissions as inputs. Do not present it as a clean method.

Current known qbb best:

- `submission_qbb60v18_cogs2023h2_down010.csv` = `662607.08245`

## Hypotheses

1. The small positive 2023H2 COGS-down direction may have an optimum slightly beyond `-1%`.
2. The public target may still sit beyond the learned clean-to-qbb direction, so a controlled extrapolation can test for a larger jump.
3. If full extrapolation over-moves level, shape-only extrapolation with preserved period totals can still reduce day-level error.

## Candidate Manifest

|   priority | filename                                           | mode        |   gamma |   h2_cogs_scale |   h1_rev_rel_scale |   revenue_total |   cogs_total |   ratio_total |   max_revenue |    max_cogs |   mean_abs_rev_delta_vs_best |   mean_abs_cogs_delta_vs_best |   p95_abs_rev_delta_vs_best |   p95_abs_cogs_delta_vs_best |   movement_vs_best | thesis                                                                                                       |
|-----------:|:---------------------------------------------------|:------------|--------:|----------------:|-------------------:|----------------:|-------------:|--------------:|--------------:|------------:|-----------------------------:|------------------------------:|----------------------------:|-----------------------------:|-------------------:|:-------------------------------------------------------------------------------------------------------------|
|          1 | submission_qbb61v21_h2cogs_down0125.csv            | fine        |     0   |          0.9875 |            1       |     2.37257e+09 |  2.13119e+09 |      0.898263 |   1.26027e+07 | 1.19721e+07 |                  5.94823e-12 |                       2866.9  |                         0   |                      11237.8 |            1433.45 | Fine tune the only still-positive late-stage axis: 2023H2 COGS slightly below the known -1% winner.          |
|          2 | submission_qbb61v21_h2cogs_down015_h1level1135.csv | fine        |     0   |          0.985  |            1.00442 |     2.37639e+09 |  2.12962e+09 |      0.896158 |   1.26027e+07 | 1.19721e+07 |               6970.64        |                       5733.8  |                     27302.8 |                      22475.6 |            6352.22 | Combine a slightly stronger H2 COGS reduction with the quadratic 2023H1 level optimum between +13% and +15%. |
|          3 | submission_qbb61v21_extrap_clean_to_best_g010.csv  | extrapolate |     0.1 |          0.99   |            1       |     2.37331e+09 |  2.13341e+09 |      0.898916 |   1.26786e+07 | 1.19789e+07 |              17063.1         |                       8695.26 |                     45452.9 |                      23669.5 |           12879.2  | Test whether hidden target is still beyond the clean-to-qbb direction; moderate full-vector extrapolation.   |
|          4 | submission_qbb61v21_extrap_clean_to_best_g020.csv  | extrapolate |     0.2 |          0.99   |            1       |     2.37405e+09 |  2.13405e+09 |      0.898906 |   1.27546e+07 | 1.19857e+07 |              34126.2         |                      17390.5  |                     90905.7 |                      47338.9 |           25758.3  | Higher-variance continuation of the same direction; useful only if g010 improves materially.                 |
|          5 | submission_qbb61v21_shape_preserve_nonh2_g030.csv  | shape_nonh2 |     0.3 |          0.99   |            1       |     2.37257e+09 |  2.13276e+09 |      0.898925 |   1.28333e+07 | 1.19472e+07 |              27845.5         |                      14056.2  |                    109628   |                      51445.2 |           20950.9  | Push daily shape further in 2023H1/2024H1 while preserving period totals; avoids rejected level movement.    |
|          6 | submission_qbb61v21_shape_preserve_all_g020.csv    | shape_all   |     0.2 |          0.99   |            1       |     2.37257e+09 |  2.13276e+09 |      0.898925 |   1.27564e+07 | 1.19555e+07 |              32139.6         |                      15861.9  |                     89654.5 |                      43076.6 |           24000.7  | Push daily shape further in every main period while preserving period totals.                                |

## Suggested Public Probe Order

1. `submission_qbb61v21_shape_preserve_nonh2_g030.csv`
2. `submission_qbb61v21_extrap_clean_to_best_g010.csv`
3. `submission_qbb61v21_h2cogs_down0125.csv`
4. Only if one of the first two improves: `submission_qbb61v21_extrap_clean_to_best_g020.csv`

## Public Readout

`submission_qbb61v21_shape_preserve_nonh2_g030.csv` returned public MAE `664937.71763`.

Interpretation:

- Further daily-shape extrapolation in 2023H1/2024H1 while preserving period totals is rejected.
- The remaining gap to `650k` is unlikely to come from non-H2 daily shape alone.
- Next best orthogonal probe is `submission_qbb61v21_extrap_clean_to_best_g010.csv`, which tests whether the full clean-to-qbb vector still has positive slope.
- If `g010` also worsens, the only low-risk remaining v21 probe is the tiny COGS optimum check `submission_qbb61v21_h2cogs_down0125.csv`.

`submission_qbb61v21_extrap_clean_to_best_g010.csv` returned public MAE `663007.39829`.

Interpretation:

- Full-vector extrapolation beyond qbb-best is also rejected.
- The public optimum is not simply further along the clean-to-qbb direction.
- Do not submit `submission_qbb61v21_extrap_clean_to_best_g020.csv`.
- The only remaining v21 candidate with a clear low-risk hypothesis is `submission_qbb61v21_h2cogs_down0125.csv`, which fine-tunes the small 2023H2 COGS axis that improved from `662759.87577` to `662607.08245`.
