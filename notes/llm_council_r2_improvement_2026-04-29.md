# LLM Council: R2 / RMSE Improvement

## Current Baseline

- Best clean public MAE: `submission_cleanv14_v10_all_mddow_both_a300.csv = 667774.94896`.
- `a350` worsened public MAE to `668661.10196` but improved proxy RMSE/R2.
- True test RMSE/R2 are not observable unless leaderboard reports them; all RMSE/R2 values below are public-like proxy.

## Why R2 Is Still Low

R2 is low because the current model is better at period/month level calibration than daily peak placement. MAE tolerates this better than RMSE/R2. The worst proxy weakness is COGS daily peak/ratio, especially in hard folds around month-boundary/event days.

Observed proxy pattern:

- V10 base: pooled R2 `0.6574`.
- V14 V10 `a300`: pooled R2 `0.6684`, public MAE `667774.94896`.
- V14 V10 `a350`: pooled R2 `0.6697`, public MAE `668661.10196`.
- V14 V10 `a700`: pooled R2 `0.6733`, but likely MAE-risky.

## Council Verdict

### Metric Judge

If final scoring is equal-weight MAE/RMSE/R2:

- Pick `a350` as the multi-metric hedge.
- Pick `a300` if public MAE is the main criterion.
- Do not use V12 `a300` as final despite high proxy R2 because public MAE cost is too high.

### Data Scientist

Main missing signal is COGS ratio/peak modeling:

- COGS R2 is much weaker than Revenue in hard folds.
- Top errors cluster around month-boundary days such as late March, late June/July, and late August.
- Calendar month-day/DOW helps but is near its ceiling; next gain needs COGS-specific ratio/head logic.

### ML Engineer

Recommended existing submit candidates:

1. `submission_cleanv14_v10_all_mddow_r250_c350.csv`
   - Safest target-specific candidate.
   - Keeps Revenue below a300 sharpness and increases COGS to a350 sharpness.

2. `submission_cleanv14_v10_all_mddow_r300_c400.csv`
   - Clean diagnostic for COGS-specific improvement.
   - Keeps Revenue at a300, sharpens only COGS.

3. `submission_cleanv14_v10_all_mddow_both_a400.csv`
   - More R2/RMSE push, higher public MAE risk.

4. `submission_cleanv14_v10_all_mddow_r500_c600.csv`
   - R2-push candidate.
   - Proxy pooled R2 `0.6730`; likely MAE riskier.

### Legality / Report

V13/V14 daily allocator is clean in mechanism:

- Uses only train-derived month-day/day-of-week history.
- Preserves each month total.
- Does not read sample submission, previous submissions, quarantine files, or test targets.

But the selected alpha/base is public-guided, so report wording should label it as clean-input public-guided, not strict clean.

Safe report wording:

> We forecast period/month totals from provided training/raw data, then apply a deterministic within-month allocator. The allocator redistributes each month's fixed total across days using historical train-only month-day/day-of-week profiles, so it changes peak placement but does not inject test-level Revenue/COGS.

If alpha is selected after public feedback:

> Calibration strength was selected as a public-guided sensitivity setting; all numeric priors remain train-derived and the full script/manifest is reproducible.

## Next Implementation Direction

The next real model upgrade should be `clean_v15_ratio_first_cogs_allocator`:

- Keep V10/V14 Revenue shape.
- Derive daily COGS/Revenue ratio prior from train month-day/DOW and boundary features.
- Apply ratio to predicted Revenue to create daily COGS shape.
- Rescale COGS within each month to preserve monthly COGS total.
- Sweep ratio alpha separately from Revenue alpha.

This is more likely to improve R2 than increasing both-target calendar alpha further.
