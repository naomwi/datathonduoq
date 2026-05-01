# Forecast Core Feature Availability Matrix - 2026-04-19

## Purpose

This file locks the current working distinction between:

- `forecast_core`: features acceptable for leaderboard-oriented forecasting
- `analysis_rich`: features acceptable for EDA, explainability, and report work

Working rule:

- Keep a feature in `forecast_core` only if it is:
  - known in the future, or
  - inferable in the future with a clear, reproducible rule

If a feature fails that test, it should move to `analysis_rich` unless a separate auxiliary forecast is built for it.

## Group-Level Classification

| Feature family | Current status | Why | Current repo stance |
| --- | --- | --- | --- |
| Calendar | known in future | deterministic by date | `forecast_core` |
| Revenue history | inferable with clear rule | recursive forecast uses lagged predicted history | `forecast_core` |
| COGS history | inferable with clear rule | recursive joint forecast + ratio postprocess | `forecast_core` |
| Promo priors | inferable with clear rule | current policy uses seasonal month-day priors from history | `forecast_core` |
| Geo/logistics/cohort context | inferable but lower-confidence | currently filled by seasonal priors, but transfer is model-dependent | experimental only |
| Order flow | not directly known | future orders are not known unless separately forecast | `analysis_rich` by default |
| Traffic | not directly known | future sessions/visitors/pageviews are not given | `analysis_rich` |
| Inventory | not directly known | future inventory states are not given | `analysis_rich` |
| Returns/reviews | not directly known | future returns/reviews are downstream business outcomes | `analysis_rich` |
| Mix features | not directly known | payment/device/source/category mix depends on future orders | `analysis_rich` |

## Current Practical Core

Current practical `forecast_core` for leaderboard work is:

1. calendar features
2. revenue target history
3. COGS target history
4. promo priors with explicit future fill rule

This corresponds most closely to:

- `curated_promo_cogs`

Current experimental extension:

- `curated_context_promo_cogs`

This extension is not yet considered part of the stable default core because:

- it helped XGBoost
- it barely helped LightGBM
- it hurt CatBoost relative to `catboost_md2y_core`

## Current Future-Fill Rules in Code

### Promo

Current supported future policies include:

- `zero`
- `seasonal_month_day_recent_1y`
- `seasonal_month_day_recent_2y`
- `seasonal_month_day_recent_3y`
- `seasonal_month_day_recent_2y_median`
- `seasonal_month_weekday_recent_2y`

Current default strong policy:

- `seasonal_month_day_recent_2y`

### Context

Current context future filling reuses the same policy framework as promo:

- either zero-fill
- or seasonal priors by month/day or month/weekday

This is acceptable for experimentation, but not yet fully trusted as default production core.

## Immediate Governance Rule

For the next leaderboard sprint:

- Default anchor path:
  - `catboost_md2y_core`
- Allowed challenger types:
  - window-aware variants of the same core
  - narrow seasonal blends with the same core
  - only one context family at a time, and only if it beats the anchor consistently

Avoid:

- adding traffic into the forecast core
- adding inventory into the forecast core
- adding returns/reviews into the forecast core
- adding mix or order-flow families into the forecast core without an explicit auxiliary-forecast design

## Next Upgrade Path

If the team wants to move a currently blocked family into `forecast_core`, require all three:

1. explicit future availability argument
2. concrete future fill or auxiliary-forecast rule
3. improvement on rolling windows, not just one mean proxy

