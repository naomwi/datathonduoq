# Clean V2 EDA Takeaways - 2026-04-24

## Boundary

This note is source-clean. It summarizes only EDA computed from provided train/source tables. It does not use `sample_submission.csv`, previous submissions, public scores, or test targets as feature inputs.

Generated runs:

- `logs/20260424_110621_clean_v2_train_evidence`
- `logs/20260424_111124_clean_v2_missing_signals`

Scripts:

- `analyze_clean_v2_train_evidence.py`
- `analyze_clean_v2_missing_signals.py`

## What We Were Missing

### 1. Promo is not future-known

`promotions.csv` ends at `2022-12-31`. It cannot be used as a direct 2023-2024 promo schedule. The clean use is a train-derived recurring promo prior:

- month-day promo frequency
- recurring discount intensity
- recurring stackable-promo intensity

Strong recurring train patterns:

- December has promos all month in every observed year.
- September has promos all month in every observed year.
- July has around 23 promo days per year.
- August is unstable but has the strongest discount/Cogs-ratio effect.
- `08-31`, `09-01`, `09-02` appear in all years with high discount intensity.

### 2. The structural break is a funnel break

The 2019+ low regime is not caused by traffic disappearing. Sessions rise, but conversion collapses:

- H1 sessions recent/pre: `1.318x`
- H1 conversion recent/pre: `0.365x`
- H2 sessions recent/pre: `1.301x`
- H2 conversion recent/pre: `0.345x`

AOV increases:

- H1 AOV recent/pre: `1.235x`
- H2 AOV recent/pre: `1.248x`

Clean implication: model `sessions -> conversion -> orders -> AOV -> Revenue`, or at least encode train-derived conversion/AOV regime priors. Do not rely on raw calendar-only Revenue.

### 3. H1 is the cleaner recovery branch

H1 daily shape is more stable than H2:

- H1 pairwise daily-shape corr mean: `0.798`
- H2 pairwise daily-shape corr mean: `0.708`

H1 also has lower COGS-ratio dispersion:

- H1 COGS ratio std: `0.050`
- H2 COGS ratio std: `0.159`

Clean implication: H1 can support a wider regime-recovery prior. H2 should be shrunk/capped more strongly.

### 4. COGS must be a ratio model, not a Revenue follower

COGS ratio is mostly explained by promo/discount structure, not by raw Revenue:

- corr(`cogs_ratio`, `promo_discount_max`) = `0.921`
- corr(`cogs_ratio`, `active_promo_count`) = `0.646`
- corr(`cogs_ratio`, `promo_line_share`) = `0.594`
- corr(`cogs_ratio`, `aov`) = `-0.557`
- corr(`cogs_ratio`, `Revenue`) = `-0.167`

Every top high-COGS-ratio diagnostic day is in August with a 50% promo. This explains why generic COGS floors behaved badly and why the useful COGS moves were period/promo-specific.

Clean implication: predict `COGS / Revenue` using month, half, recurring promo priors, historical discount priors, and AOV/revenue-per-unit priors.

### 5. Product/segment and region mix matter more than source/device

Source and device shares are mostly stable; they explain little by themselves. The larger clean mix shifts are:

- Balanced segment share rises by about `+17pp`.
- Everyday segment share falls by about `-10pp`.
- Outdoor falls, Streetwear rises.
- Region shifts from West to Central, especially in H2.

Clean implication: use product/segment/region as train-derived slow-moving regime priors. Do not use future item mix or future orders directly.

### 6. August is special and dangerous

August has the highest H2 revenue-share instability:

- August revenue share CV: `0.237`
- H2 median monthly CV is much lower.

All top high COGS-ratio days are August 50% promo days.

Clean implication: H2/August should not get free Revenue shape movement, but COGS-ratio should explicitly know about August promo-risk priors.

## Recommended Clean Model Direction

1. Build a train-only funnel/regime layer:
   `calendar shape + H1/H2 regime prior + conversion/AOV recovery prior`.

2. Keep Revenue conservative:
   wider recovery in H1, stronger shrinkage in H2, special caution for August.

3. Replace post-hoc COGS multipliers with a ratio head:
   `ratio_pred = f(month, half, recurring promo prior, discount prior, AOV prior, segment/region prior)`.

4. Add product/segment and region priors:
   slow-moving regime features learned from train only.

5. Treat source/device/payment as weak diagnostics:
   useful for narrative and sanity checks, probably not a breakthrough feature.

6. Keep inventory/returns/reviews/shipments out of direct future features:
   use them for diagnostics or validation only unless future operational plans are explicitly provided.

## Next Experiments

1. `clean_v2_funnel_h1_recovery`: train-derived H1 recovery based on conversion/AOV gaps, H2 capped.
2. `clean_v2_ratio_head_augpromo`: COGS ratio head with recurring promo month-day priors, especially August/December/September.
3. `clean_v2_segment_region_prior`: product/segment + region regime priors blended into the funnel model.
4. `clean_v2_ablation`: compare calendar-only, funnel-only, ratio-only, and full model on long 548-day folds.
