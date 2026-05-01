# Public Black-Box To Legal Model Features

Run directory: `logs\20260422_151210_public_blackbox_to_legal_features`

Important constraint:

- This analysis treats `sample_submission.csv` numeric `Revenue/COGS` as forbidden.
- Public scores are used only as black-box behavioral signals.
- Proposed model changes below must be implemented from train/provided covariates only.

## Public Black-Box Signal

2023H2 Revenue-shape response:

|   x |   public_score |
|----:|---------------:|
| 1   |         707437 |
| 0.8 |         698898 |
| 0.6 |         692129 |
| 0.4 |         687113 |
| 0.2 |         684700 |
| 0.1 |         684463 |

Meaning:

- The public target strongly rejects a high `2023H2` daily-shape intensity.
- The response flattened near `0.100`, so 2023H2 alone is nearly exhausted.
- This is a regime/seasonality problem, not a base model capacity problem.

## Train-Only Evidence

Average adjacent-year normalized daily-shape correlation:

| half | mean corr(prev year) |
|---|---:|
| H1 | `0.854` |
| H2 | `0.672` |

Recent train promo-window effects:

| window   |   recent_uplift |   recent_cogs_ratio |
|:---------|----------------:|--------------------:|
| fall     |      -0.0650143 |            0.919448 |
| midyear  |       0.0809931 |            0.960896 |
| spring   |       0.536279  |            0.90485  |
| yearend  |      -0.475028  |            1.00367  |

Interpretation:

- H2 is less stable than H1, so single-template or strong annual lag shape is risky for H2.
- Spring is a real positive event; fall/yearend are not generic positive promo periods.
- COGS ratio is window/period sensitive, so COGS should follow a ratio regime, not a copied daily shape.

## Legal Feature Hypotheses

| hypothesis                                                           | blackbox_evidence                                                                | train_evidence                                                                               | legal_feature_or_model_change                                                                                            |   priority |
|:---------------------------------------------------------------------|:---------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------|-----------:|
| H2 seasonal shape reliability is low                                 | 2023H2 alpha reduction 0.800 -> 0.100 improved 698898 -> 684463.                 | H2 year-to-year shape correlations are lower than H1, especially 2021 -> 2022.               | Add period x horizon interactions and shrink annual/month-day seasonal priors more aggressively in H2.                   |          1 |
| 2023H2 should not use raw last-year or external template daily shape | Forcing 2023H2 shape high worsened to 707436.                                    | Train H2 contains unstable fall/yearend patterns and high year-specific COGS ratio variance. | Use train-only multi-year H2 template with variance shrinkage, not single-year shape; cap event spike amplitude.         |          1 |
| Local OOF underestimates public shift because horizon is 548 days    | Many low-OOF direct model changes did not move public; period-shape changes did. | H2 shape degrades over long horizons; short folds overvalue recursive lag features.          | Optimize on long horizon folds 2020/2021 and report worst-fold by period, not average OOF.                               |          1 |
| Promo/event effect must be signed by window, not globally positive   | Flat promo/window tuning gave small gains and could not explain 65x.             | Spring is strongly positive, midyear mild, fall often negative, yearend strongly negative.   | Create window-specific event priors: spring positive, midyear weak, fall/yearend negative, with target-specific effects. |          2 |
| COGS needs ratio-regime modeling, not sample-like daily shape        | COGS ratio away helped until 0.25, COGS shape down helped but plateaued.         | H2 COGS ratio alternates strongly and is high in several odd years.                          | Model COGS as Revenue x period/window COGS-ratio prior, with odd/even and window interactions.                           |          2 |
| Non-H2 periods may still need stronger deterministic calendar shape  | Global Revenue alpha 0.800 improved despite 2023H2 being harmful.                | H1 shape correlations are consistently high, so H1 calendar shape is more reliable.          | Use stronger train-only calendar/event template for H1/2024H1; tune separately from 2023H2.                              |          3 |

## Recommended Model Changes

1. Add `seasonal_reliability` features from train only:
   - `month_day_rev_share_mean_by_half`
   - `month_day_rev_share_std_by_half`
   - `month_day_rev_share_cv_by_half`
   - `horizon_step x half x seasonal_cv`

2. Replace raw annual-shape reliance with shrinkage:
   - H1: stronger month-day/event prior.
   - H2: shrink toward period/month mean, especially fall/yearend.

3. Make promo/event effects signed and window-specific:
   - `spring`: positive Revenue uplift.
   - `midyear`: weak/mixed.
   - `fall`: negative or damped.
   - `yearend`: negative/damped.

4. Use target-specific period routing:
   - Revenue: strong period-wise seasonal router.
   - COGS: Revenue x COGS-ratio model with period/window interactions.

5. Validate only with public-like folds:
   - Long 548-day folds from 2020 and 2021.
   - Segment metrics by H1/H2/window.
   - Penalize false positives that improve average OOF but fail H2.

## Candidate Legal Modeling Direction

Build a train-only `period_shape_router`:

```text
prediction = period_total_forecast * train_only_daily_share_template
daily_share_template = weighted_mean(month_day_or_event_shape from prior years)
weight = function(half, horizon_step, seasonal_cv, promo_window)
```

For public-like inference:

```text
2023H1 / 2024H1: use stronger train-only calendar/event template
2023H2: use heavily shrunk train-only H2 template
COGS: use Revenue forecast * train-only COGS-ratio prior
```

This transfers the black-box insight without using test `Revenue/COGS` values as features.
