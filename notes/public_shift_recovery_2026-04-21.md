# Public Shift Recovery Implementation - 2026-04-21

Run directory: `logs\20260422_010501_public_shift_recovery`

Implemented fixed-anchor public-like validation, candidate manifest, segment metrics, and feature policy audit.

## Top Rows
| filename                                                  | family           |   public_score | gate                        |   public_like_weighted_norm |   worst_fold_norm |   delta_weighted_norm_vs_anchor |
|:----------------------------------------------------------|:-----------------|---------------:|:----------------------------|----------------------------:|------------------:|--------------------------------:|
| submission_txndecomp_v2_cogsratio_promotet_r40_up0075.csv | other_submission |         874819 | 00_keep_current_public_best |                    0.224802 |          0.260742 |                     0.00162926  |
| submission_catboost_md2y_core_recencyexp20.csv            | anchor           |         896000 | 01_anchor_baseline          |                    0.223173 |          0.253587 |                     0           |
| submission_promo_core_v2_prior_cal8.csv                   | other_submission |            nan | 20_borderline_probe_only    |                    0.223305 |          0.256615 |                     0.000132008 |
| submission_public_probe_promo_h1_rev_up8.csv              | other_submission |            nan | 20_borderline_probe_only    |                    0.223416 |          0.255634 |                     0.000243102 |
| submission_public_probe_promo_windows_rev_up4.csv         | flat_main_promo  |            nan | 20_borderline_probe_only    |                    0.223789 |          0.25616  |                     0.00061614  |
| submission_public_probe_promo_augoct_rev_up10.csv         | other_submission |            nan | 20_borderline_probe_only    |                    0.223964 |          0.255248 |                     0.000790713 |
| submission_promo_core_v2_hybrid_cogsratio025.csv          | other_submission |            nan | 20_borderline_probe_only    |                    0.224159 |          0.258805 |                     0.000986421 |
| submission_promo_core_v2_hybrid_sharp_cal8.csv            | other_submission |            nan | 20_borderline_probe_only    |                    0.224163 |          0.2573   |                     0.000990055 |
| submission_promo_core_v2_hybrid_cal8.csv                  | other_submission |            nan | 20_borderline_probe_only    |                    0.22446  |          0.257887 |                     0.00128688  |
| submission_promo_core_v2_model_cal8.csv                   | other_submission |            nan | 20_borderline_probe_only    |                    0.224518 |          0.257945 |                     0.0013452   |
| submission_public_probe_promo_novjan_rev_up10.csv         | other_submission |            nan | 20_borderline_probe_only    |                    0.224606 |          0.256355 |                     0.00143338  |
| submission_tabpfn26_windowmix_cogs2.csv                   | promo_windowmix  |            nan | 20_borderline_probe_only    |                    0.22463  |          0.258936 |                     0.00145719  |

Required outputs:
- `logs\20260422_010501_public_shift_recovery\summary.csv`
- `logs\20260422_010501_public_shift_recovery\segment_metrics.csv`
- `logs\20260422_010501_public_shift_recovery\candidate_manifest.csv`
- `logs\20260422_010501_public_shift_recovery\public_shift_report.md`
