# Perplexity Research Brief: Retail Forecasting Feature Selection

## Goal

Produce a focused research memo on which feature families are consistently useful in winning or top-ranked solutions for **daily retail sales forecasting competitions**, and which families are often noisy, leakage-prone, or not worth the added complexity.

This research is meant to guide **feature pruning and governance** for the current repo, not to collect generic forecasting advice.

## Current Repo Context

We are working on a Kaggle-style retail forecasting problem with daily targets:

- `Revenue`
- `COGS`

Train period:

- `2012-07-04` to `2022-12-31`

Forecast period:

- `2023-01-01` to `2024-07-01`

Current raw tables:

- `products.csv`
- `customers.csv`
- `promotions.csv`
- `geography.csv`
- `orders.csv`
- `order_items.csv`
- `payments.csv`
- `shipments.csv`
- `returns.csv`
- `reviews.csv`
- `sales.csv`
- `inventory.csv`
- `web_traffic.csv`

Current feature families in the repo:

- `calendar`
- `revenue_history`
- `cogs_history`
- `promo`
- `geo_logistics`
- `traffic`
- `order_flow`
- `returns_reviews`
- `inventory`
- `mix`

Important current findings from local experiments:

- The strongest stable core so far is close to:
  - `calendar + revenue_history + cogs_history + promo`
- A current core experiment has:
  - `561` total features
  - of which `promo` alone contributes about `407`
- Recent local tests suggest these families are harmful or unstable in the current setup:
  - `traffic`
  - `inventory`
  - `returns_reviews`
  - `order_flow`
  - `mix`
- `geo_logistics/context` looks weak or unstable
- `payments.csv` is currently not used at all

The main uncertainty is whether this direction is aligned with what actually worked in strong retail forecasting competition solutions, or whether we are missing a high-value feature family.

## Target Research Question

For **daily retail demand / sales / revenue forecasting competitions** with tabular ML solutions, which feature families repeatedly appear in strong solutions, and under what assumptions about **future availability**?

## Competitions To Prioritize

Prioritize sources from or about these competitions:

1. Kaggle M5 Forecasting Accuracy
2. Corporacion Favorita Grocery Sales Forecasting
3. Rossmann Store Sales
4. Walmart Recruiting Store Sales Forecasting

You may include adjacent, highly similar retail forecasting competitions if they add real signal, but do not drift into generic time-series articles.

## Questions To Answer

### 1. Core feature families

Across strong solutions, how often do the following families appear?

- calendar / seasonality
- target lags
- rolling target statistics
- price / discount / promo features
- hierarchy or aggregation features
- item/store/category mix features
- inventory / stockout features
- traffic / site visit features
- returns / reviews / post-purchase signals
- payment / installment features
- logistics / shipping features

For each family, say whether it is:

- `must-have`
- `often useful`
- `conditional`
- `rarely useful`
- `usually noise / risk`

### 2. Future availability discipline

For each useful family, explain the assumption that makes it valid at forecast time:

- known in advance
- lagged only
- recursively forecasted first
- available only in some competitions
- not realistically available and therefore prone to leakage

This is a key part of the task.

### 3. Exogenous features that look attractive but often fail

Research whether winning solutions usually benefited from:

- traffic
- inventory
- returns
- reviews
- payment value / installments
- shipping latency / shipping fee

If these features were used, identify:

- at what granularity
- with what lagging / aggregation
- whether they required known future inputs
- whether they were central or only minor additions

### 4. Promo handling

This is especially important.

Investigate how top solutions handled promotions or analogous commercial interventions:

- contemporaneous promo flags if future promo schedule is known
- lagged promo history
- rolling promo intensity
- promo target encodings
- promo interactions with calendar or item/store keys
- future fill rules when exact future promo is not known

Also answer:

- do top solutions usually keep promo blocks simple and interpretable?
- or do they use very wide promo-derived feature expansions?

### 5. Payments and transaction-side financial features

Investigate whether features analogous to:

- payment value
- installments
- payment method mix

ever materially helped in strong retail forecasting solutions after target history and calendar were already present.

Be explicit about whether these are:

- redundant with sales target itself
- leakage-prone
- useful only for audit / reconciliation
- useful only in short-horizon or direct-known settings

### 6. Aggregate target vs panel target

Our repo forecasts one aggregate daily series for `Revenue` and one for `COGS`.

Research whether winners in similar competitions usually got their gains from:

- forecasting at item/store level and aggregating up
- forecasting aggregate target directly
- combining both

Also explain what feature families become more or less useful when moving from:

- item-store panel forecasting
to
- aggregate daily forecasting

### 7. Validation implications

Summarize best practices from strong solutions on:

- time-based folds
- recent-year weighting
- avoiding local overfit to exotic exogenous features
- handling recursive degradation
- deciding when a feature family is not robust enough to keep

## Deliverable Format

Please structure the answer like this:

1. `Executive Summary`
2. `Competition-by-Competition Evidence`
3. `Feature Family Ranking`
4. `What Transfers To Our Repo`
5. `What Probably Does Not Transfer`
6. `Recommended Keep / Cut / Research-Next Table`
7. `Source List`

## Required Output Table

Include one compact table with these columns:

- `Feature family`
- `Evidence from winners`
- `Future availability requirement`
- `Transferability to our repo`
- `Recommendation`

## Evidence Standard

- Prefer official Kaggle winner interviews, official discussion writeups, strong public GitHub reproductions, and competition postmortems that cite original solutions.
- If a secondary source is used, label it clearly as secondary.
- Distinguish between:
  - `documented in winners`
  - `common among strong non-winning solutions`
  - `your inference`
- Avoid generic SEO blogs or vague forecasting articles unless they point to an original winner source.

## Final Decision-Oriented Ask

At the end, answer these exact decision questions:

1. Should our default forecast core stay close to:
   - `calendar + revenue_history + cogs_history + promo`
2. Is it likely correct to freeze out:
   - `traffic`
   - `inventory`
   - `returns_reviews`
   - `order_flow`
   - `mix`
3. Is `payments.csv` likely worth bringing into the forecast core, or better kept out unless a narrow audit proves otherwise?
4. Should `promo` be made narrower and simpler rather than wider?
5. For our setup, is there any feature family we are probably underusing that strong competition evidence says we should revisit?

## Copy-Paste Prompt

```text
I need a decision-oriented research memo about feature selection for a retail forecasting repository.

Context:
- Daily targets: Revenue and COGS
- Train: 2012-07-04 to 2022-12-31
- Forecast: 2023-01-01 to 2024-07-01
- Raw tables: products, customers, promotions, geography, orders, order_items, payments, shipments, returns, reviews, sales, inventory, web_traffic
- Current feature families: calendar, revenue_history, cogs_history, promo, geo_logistics, traffic, order_flow, returns_reviews, inventory, mix
- Current local evidence suggests the strongest stable core is close to calendar + revenue_history + cogs_history + promo
- Current core has 561 features, of which promo alone is about 407
- traffic, inventory, returns_reviews, order_flow, and mix currently look harmful or unstable
- geo_logistics/context looks weak or unstable
- payments.csv is currently not used

Research goal:
Determine which feature families are consistently useful in strong retail forecasting competition solutions, which ones are conditional on future availability assumptions, and which ones are often noise or leakage-prone.

Prioritize evidence from:
1. Kaggle M5 Forecasting Accuracy
2. Corporacion Favorita Grocery Sales Forecasting
3. Rossmann Store Sales
4. Walmart Recruiting Store Sales Forecasting

Questions:
1. Across strong solutions, how common and useful are:
   - calendar / seasonality
   - target lags
   - rolling target statistics
   - price / discount / promo features
   - hierarchy / aggregation features
   - item/store/category mix features
   - inventory / stockout features
   - traffic / site visit features
   - returns / reviews / post-purchase signals
   - payment / installment features
   - logistics / shipping features
2. For each family, state the future-availability assumption that makes it valid:
   - known in advance
   - lagged only
   - recursively forecasted first
   - competition-specific only
   - leakage-prone / not realistic
3. Investigate especially how winners handled promotions:
   - contemporaneous promo flags if future promo is known
   - lagged promo history
   - rolling promo intensity
   - promo interactions
   - target encodings
   - future fill rules when future promo is not fully known
4. Investigate whether payment-like features (payment value, installments, payment mix) ever materially helped after target history and calendar were already present.
5. Explain what feature families transfer well to aggregate daily forecasting of Revenue/COGS, versus item-store panel forecasting.
6. Summarize validation guidance from strong solutions on deciding when a feature family is not robust enough to keep.

Output format:
1. Executive Summary
2. Competition-by-Competition Evidence
3. Feature Family Ranking
4. What Transfers To Our Repo
5. What Probably Does Not Transfer
6. Recommended Keep / Cut / Research-Next Table
7. Source List

Required table columns:
- Feature family
- Evidence from winners
- Future availability requirement
- Transferability to our repo
- Recommendation

Evidence standard:
- Prefer official Kaggle winner interviews, official discussion writeups, strong public GitHub reproductions, and competition postmortems that cite original solutions.
- If using a secondary source, label it clearly.
- Distinguish documented evidence from your inference.
- Avoid generic forecasting blogs unless they point to original winner sources.

At the end, answer these exact decision questions:
1. Should our default forecast core stay close to calendar + revenue_history + cogs_history + promo?
2. Is it likely correct to freeze out traffic, inventory, returns_reviews, order_flow, and mix?
3. Is payments.csv likely worth bringing into the forecast core, or better kept out unless a narrow audit proves otherwise?
4. Should promo be made narrower and simpler rather than wider?
5. Is there any feature family we are probably underusing that strong competition evidence says we should revisit?
```
