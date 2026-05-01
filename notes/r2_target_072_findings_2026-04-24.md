# R2 Target 0.72 Findings

Run evaluated: `logs/20260424_165217_multimetric_publiclike_research`

## Goal

Raise public-like pooled R2 from the current clean public-best range around `0.659` to about `0.72`, while tracking MAE/RMSE risk.

## Baseline

Current clean public MAE best:

- `submission_cleanv2_h1fine_b044_r0876.csv`
- Known public MAE: `673757.34993`
- Weighted public-like normalized MAE: `0.244554`
- Weighted public-like normalized RMSE: `0.324467`
- Weighted public-like pooled R2: `0.659252`
- Worst fold pooled R2: `0.544281`

Near-equivalent public MAE but slightly better RMSE/R2:

- `submission_cleanv3_funnel_c110_h1r0876.csv`
- Known public MAE: `673759.96838`
- Weighted public-like normalized MAE: `0.244347`
- Weighted public-like normalized RMSE: `0.324219`
- Weighted public-like pooled R2: `0.659794`

## Candidates That Reach R2 Around 0.72

Best clean train-derived scenario:

- `submission_clean_regime_recovery_v2_yoy100.csv`
- Weighted public-like normalized MAE: `0.211002`
- Weighted public-like normalized RMSE: `0.286863`
- Weighted public-like pooled R2: `0.731576`
- Worst fold pooled R2: `0.635189`
- Boundary: clean-input scenario, no sample/submission/test target input.
- Risk: public score is unknown; period totals are much lower than the current public-MAE winner.

Strong balanced R2 target from v5 sweep:

- `submission_cleanv5_r2_level_to_txnmonth_a400.csv`
- Weighted public-like normalized MAE: `0.222847`
- Weighted public-like normalized RMSE: `0.292554`
- Weighted public-like pooled R2: `0.722992`
- Worst fold pooled R2: `0.644209`
- Boundary: research clean-input-ish blend toward transaction-month donor; do not present as strict clean without explaining the transaction-month calibration source.

More aggressive R2 target from v5 sweep:

- `submission_cleanv5_r2_level_to_txnmonth_a500.csv`
- Weighted public-like normalized MAE: `0.219491`
- Weighted public-like normalized RMSE: `0.287843`
- Weighted public-like pooled R2: `0.731861`
- Worst fold pooled R2: `0.660674`
- Boundary: same as a400, more level movement toward transaction-month donor.

## Key Insight

Shape-only changes cannot raise R2 to 0.72. The v5 `txnshape_preserve` candidates preserve the public-best period totals, but top out below `0.69` pooled R2. To reach `0.72`, the model must reduce squared errors by moving period level and COGS ratio closer to train-derived recovery/transaction-month regimes.

This means the R2 target is not a small post-processing tweak. It requires a different level hypothesis:

- Current public-MAE clean best: high period totals, especially COGS, good MAE public.
- R2-target candidates: lower period totals and lower COGS/Revenue ratio, better public-like RMSE/R2.

## Suggested Submit Order If Testing Public

1. `dataset/submission_cleanv5_r2_level_to_txnmonth_a400.csv`
2. `dataset/submission_cleanv5_r2_level_to_txnmonth_a500.csv`
3. `dataset/submission_clean_regime_recovery_v2_yoy100.csv`

Readout:

- If `a400` public MAE stays near the clean best, switch final candidate toward R2/RMSE optimization.
- If `a400` public MAE collapses, public target period totals prefer the current high-level clean branch, and R2 improvement should be handled only in report/local validation rather than leaderboard candidates.
- If `yoy100` performs well, it is the cleanest story for final explanation because it is train-history regime recovery rather than submission blending.

## Public Readout

`submission_cleanv5_r2_level_to_txnmonth_a400.csv` returned public MAE `708303.49686`.

Interpretation:

- The candidate successfully raised public-like pooled R2 to `0.722992`.
- Public MAE rejected the level movement from the current clean-best regime toward the lower transaction-month regime.
- Do not submit `a500` as a MAE candidate; it has even stronger movement in the same rejected direction.
- For a final multi-metric story, `a400` is useful evidence that R2/RMSE improve when squared-error tails are reduced, but it should not replace the current clean MAE candidate unless final scoring heavily rewards R2/RMSE.

Next clean direction:

- Keep public-best period totals.
- Improve R2 only through daily-shape/tail-risk changes.
- Accept that this is unlikely to reach `0.72`; current evidence says `0.72` requires a level hypothesis that public MAE does not like.
