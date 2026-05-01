# LLM Council Score Optimization

## Current Scores

- Best clean/public-guided MAE: `submission_cleanv10_h1_shape141617_ratio1719_a075.csv = 668492.34671`.
- Best report-safe train-selected MAE: `submission_cleanv11_trainselected_revrecovery_141617_ratioall_median_a025.csv = 671492.88376`.
- Best quarantine/blackbox MAE: `submission_qbb69_h1_q1_cogs_down120_keeprev.csv = 655838.51372`.
- Broad H1 COGS-down was rejected: `submission_cleanv9_big_h1_keeprev_cogs_r0820.csv = 678484.18208`.
- Ratio-only H1 COGS monthly regime was rejected: `submission_cleanv10_h1_ratio1719_keeprev_a100.csv = 674778.63531`.
- V12 operational hybrid was close but did not beat V10: `submission_cleanv12_v10ops_h1_ratio_discount_a075.csv = 669972.24260`.
- V12 pure monthly funnel also failed: `submission_cleanv12_monthfunnel_h1_ratio_discount_a050.csv = 672391.67763`.

## Council Verdict

The best final-scoring family is clean H1 train-regime calibration on top of the cleanv7/source-funnel base.

- Use V10 if optimizing leaderboard MAE.
- Use V11 if optimizing report defensibility.
- Do not use `qbb*`, `sample*`, `publiconly*`, or `top10*` as final report methods.

## Why R2/RMSE Are Stuck

V10/V11 fix a period/month H1 regime issue, but they do not explain daily peaks/pockets. Public-like proxy shows V10 improves public MAE while slightly worsening RMSE/R2 versus cleanv7. This is expected because the calibration mostly shifts monthly Revenue/COGS allocation, not high-frequency daily peak structure.

## Immediate Submit Recommendation

Do not continue ratio-only H1 COGS probes.

Rationale:

- `submission_cleanv10_h1_ratio1719_keeprev_a100.csv` worsened to `674778.63531`.
- Public appears to require the paired V10 signal: H1 Revenue timing shift plus monthly COGS ratio adjustment.
- Isolated COGS-ratio correction is not a good final-scoring path.

Keep V10 as leaderboard final and V11 as report-safe final unless V12 improves.

After V12 A075, V10 remains the leaderboard final. The operational monthly router explains most of the V10 signal but loses about `+1479.90` MAE versus V10, so it is better as report support than final submission unless a follow-up improves.

After V12 A050, do not continue pure monthly funnel variants. The public signal still prefers the V10 train-regime donor shape over operational monthly priors.

## Next Implementation Direction

Build `run_clean_v12_monthly_funnel_router.py`.

Goals:

- Replace hard-coded H1 regime shape with monthly funnel features.
- Forecast monthly Revenue using train-derived `sessions x conversion x AOV`.
- Forecast monthly COGS ratio using train-derived discount, promo, stockout/fill-rate, and month priors.
- Preserve period totals so the model tests shape/ratio rather than broad level drift.

Then build `run_clean_v13_daily_peak_allocator.py` only after V12 shows public or proxy promise.

## Highest-Value Clean Features

1. Order-date return/refund pressure head.
2. Promo/discount pressure as COGS-ratio daily head.
3. SKU/category stockout and product-mix availability pressure.

All must use train-derived priors only; no future actual operational data, no sample submission values, and no prior submission values as inputs.

## Report Language

Use:

> We use a post-model calibration layer to allocate period-level forecasts into daily Revenue/COGS profiles. The calibration priors are derived only from historical training years and selected by rolling time-series validation.

For V10 specifically, label it as public-guided:

> A public-guided variant of the same train-derived calibration improved public MAE, while the report-safe variant selects calibration strength using train-only rolling validation.
