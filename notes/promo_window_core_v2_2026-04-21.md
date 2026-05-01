# Promo Window Core v2 - 2026-04-21

## Runs
- Main run: `logs/20260421_205129_promo_window_core_v2/`
- Public-shift gate after new candidates: `logs/20260421_205146_public_shift_recovery/`

## Data Science Read
The forecast-safe promo-window features were tested seriously as a replacement/upgrade for the TabPFN windowmix shape.

Revenue residual modeling did **not** validate:

| model | target | mae | zero_mae | corr |
|---|---:|---:|---:|---:|
| prior_rev | promo_revenue_log_residual | 0.261434 | 0.225891 | -0.312658 |
| ridge_rev | promo_revenue_log_residual | 0.290842 | 0.225891 | -0.178917 |
| hgb_rev | promo_revenue_log_residual | 0.276780 | 0.225891 | -0.153235 |
| trees_rev | promo_revenue_log_residual | 0.273710 | 0.225891 | -0.140804 |

This means the engineered `promo_window_core_v2` Revenue features are not reliably learning historical promo residual shape. The public best `tabpfn_promo_windowmix_v1` should remain the production/default Revenue shape.

COGS ratio had real signal:

| model | target | mae | zero_mae | corr |
|---|---:|---:|---:|---:|
| prior_cogs_ratio_delta | promo_cogs_ratio_delta | 0.043823 | 0.059890 | 0.384210 |

This supports testing only very small promo-specific COGS ratio movement, ideally while keeping current best Revenue unchanged.

## Exported Candidates
- `dataset/submission_promo_core_v2_prior_cal8.csv`
- `dataset/submission_promo_core_v2_model_cal8.csv`
- `dataset/submission_promo_core_v2_hybrid_cal8.csv`
- `dataset/submission_promo_core_v2_hybrid_soft_cal8.csv`
- `dataset/submission_promo_core_v2_hybrid_sharp_cal8.csv`
- `dataset/submission_promo_core_v2_hybrid_cogsratio025.csv`
- `dataset/submission_promo_core_v2_bestrev_cogsratio010.csv`
- `dataset/submission_promo_core_v2_bestrev_cogsratio020.csv`

## Gate Result
All new candidates are `20_borderline_probe_only`; none beat the current best gate decisively.

Best-ranked new candidate in the public-like gate:
- `submission_promo_core_v2_prior_cal8.csv`
- projected weighted norm `0.223305`
- but OOF promo revenue shape is poor, so this is **not** a trusted submit.

Safer COGS-isolated probes:
- `submission_promo_core_v2_bestrev_cogsratio010.csv`
- `submission_promo_core_v2_bestrev_cogsratio020.csv`

These keep current best Revenue exactly and only move promo-window COGS slightly.

## Decision
Do not replace `submission_tabpfn_promo_windowmix_v1.csv`.

If spending one probe, prefer the COGS-isolated test over the new Revenue shapes:
`submission_promo_core_v2_bestrev_cogsratio010.csv`.

Rationale: Revenue core-v2 failed cross-fit; COGS ratio prior is the only part with positive evidence.
