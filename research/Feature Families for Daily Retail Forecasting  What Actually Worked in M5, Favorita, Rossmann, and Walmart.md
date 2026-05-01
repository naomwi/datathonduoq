# Feature Families for Daily Retail Forecasting: What Actually Worked in M5, Favorita, Rossmann, and Walmart

## 1. Executive Summary

- Across M5, Favorita, Rossmann, and Walmart, the **only universal must‑have families** for daily retail forecasting are: calendar/seasonality, target lags, rolling target statistics, and price/discount/promo signals.[^1][^2][^3][^4]
- **Hierarchy / aggregation features** (item/store/category/state; cross‑level rollups) are very important in panel competitions like M5 and Favorita, but their value drops when the final target is a single global aggregate daily revenue/COGS series; they are best used to build intermediate aggregates, not necessarily as huge feature blocks in a single aggregate model.[^5][^4][^1]
- **Traffic, inventory, returns, reviews, payment, and shipping features rarely appear as core drivers** in documented winning solutions; when present, they are either highly aggregated (e.g., transaction counts) or treated as minor/experimental additions rather than core pillars.[^6][^7][^5]
- Most strong solutions are extremely strict about **future availability**: they use only lagged history for demand and most exogenous variables, calendar features known in advance, and promo/price information only when a realistic future schedule is available; there is no evidence of winners relying heavily on future web traffic, inventory, returns, or reviews as if they were known.[^8][^2][^4][^1]
- For promotions, winners typically use **a compact but well‑designed set of features**: contemporaneous promo flags (when future schedule known or reasonably approximated), lagged promo history, rolling promo intensity, and interactions with store/item and weekday; wide, highly combinatorial promo feature explosions are not a common pattern in top solutions.[^2][^3][^6]
- There is essentially **no competition‑grade evidence** that payment features (installments, payment method mix) materially improve long‑horizon retail forecasts once target history and calendar (plus basic promos) are in place; these are usually treated as accounting/audit dimensions rather than predictive drivers.[^9][^10]
- Your current core — `calendar + revenue_history + cogs_history + promo` — is strongly aligned with what winners actually use; freezing out `traffic`, `inventory`, `returns_reviews`, `order_flow`, and `mix` from the long‑horizon forecast core is consistent with public evidence, unless you can build robust, lag‑only or separately‑forecasted versions of these signals.[^6][^5][^2]
- `payments.csv` is unlikely to be a high‑value core feature family for long‑horizon daily aggregate Revenue/COGS; at best, it is a niche candidate for audit/reconciliation or very short‑horizon, campaign‑specific tasks.[^10][^9]
- The strongest underused family in your context is **hierarchical / aggregation features**, but not in the sense of wide mix features; rather, as **carefully designed aggregated histories** (e.g., category/brand/channel aggregates) that feed into the same kind of lag/rolling structure winners used on item/store panels.[^3][^4][^1]

***

## 2. Competition‑by‑Competition Evidence

### 2.1 M5 Forecasting Accuracy

The M5 Accuracy competition asked participants to forecast 28‑day ahead sales for 42,840 hierarchical series (item–store up to total) using 5 years of Walmart data, with additional explanatory variables like sell prices and calendar events. Top solutions and strong public reproductions emphasize:[^4][^11][^1]

- **Core used everywhere**:
  - Calendar/seasonality: week, day, month, day‑of‑week, special events, SNAP days, holidays.[^1][^4]
  - Target lags: multiple daily lags and multi‑scale lags per item/store (1, 7, 28, 56, 364 days, etc.).[^1]
  - Rolling statistics: rolling means/medians/std over several windows per series.[^4][^1]
  - Price/discount/promo: sell_price and derived price features (relative changes, price level vs history) used heavily; promotions mainly encoded via calendar/price proxies.[^4][^1]
  - Hierarchical keys and aggregations: item_id, store_id, category/department/state IDs, plus modelling at multiple aggregation levels.[^1][^4]

- **Exogenous features in practice**:
  - No strong evidence that inventory, web traffic, returns, reviews, payments, or shipping latency were present; the official dataset did not provide such variables.[^11][^4]
  - External explanatory variables were limited to sell_price and calendar; any additional context (e.g., weather) appeared only in some non‑winning explorations.

- **Future availability**:
  - Calendar and event flags are known in advance.[^4]
  - Sell prices for the forecast period were *not* provided, forcing top teams to either ignore future price or approximate with assumptions; commentary emphasizes that using price only as lagged history is safer and more realistic.[^12][^1]

### 2.2 Corporación Favorita Grocery Sales Forecasting

Favorita required daily item‑store unit sales forecasts for a large Ecuadorian grocery retailer, with data including store/item metadata, promotions, holidays/events, oil prices, and transactions (transaction counts per store–day).[^13][^14][^5]

From winner talk and strong public notebooks:

- **Core feature families**:
  - Calendar: day‑of‑week, month, year, holiday types, event indicators.[^13][^5]
  - Target lags & rolling stats: extensive use of lagged unit sales and rolling means/medians/max/zero counts at the store–item level over multiple windows.[^6][^13]
  - Promotions: contemporaneous promo flags, lagged promo history (days since last promo, days on promo), and rolling promo intensity per store–item and per store/family.[^13][^6]
  - Hierarchy/aggregation: item family, class, perishable flag; aggregated stats by family/store, etc.[^5]
  - Transactions: daily transaction counts per store, sometimes used as a demand proxy and aggregated into lag/rolling features.[^5][^13]

- **Secondary / conditional features**:
  - Oil price and its lags are sometimes used as macro covariates, but not reported as core drivers by winners; they are exploratory or small contributors.[^13][^5]
  - There is no evidence of raw web traffic, returns, reviews, payment method mix, or shipping features.

- **Future availability discipline**:
  - Promo: future promo flags only used when explicitly given (the dataset provided promo for train/test as a binary; winners commented on treating them as known at forecast time because the retailer plans promos ahead).[^13]
  - Transactions, oil, and other operational metrics are used with lags and rolling windows only, not as fully known future paths.

### 2.3 Rossmann Store Sales

Rossmann asked for 6‑week ahead daily sales for 1,115 stores, using store metadata, promotions (two promo schemes), competition information, holidays, weekdays, etc.[^15][^16][^2]

From the 1st‑place write‑up and summarized winning‑solution decks:[^15][^2][^3]

- **Core feature families**:
  - Calendar/time: day‑of‑week, day‑of‑month, month, week‑of‑year, number of holidays in current/previous/next week, and various “day counters” relative to events (promotion cycle, summer holidays, store refurbishment, etc.).[^2][^3]
  - Target history: recent aggregates of store sales by store×weekday×promo over last 3, 6, 12, 24 months, plus measures of spread (std, skewness, kurtosis) for stability.[^15][^2]
  - Promotions: multiple promo flags (Promo, Promo2), days since promo started/ended, ratios of sales during promotions/holidays/weekends, number of school holidays in this/last/next week.[^17][^3][^2]
  - Store metadata & hierarchy: store type, assortment, competition distance and open date, average sales per customer at store level.[^2][^15]

- **Additional context**:
  - Some solutions experimented with weather data at state level, but this is not clearly identified as core in the winning model.[^3]
  - Customer counts were available only in train and not in test; winning write‑ups explicitly note this as **leakage‑prone** and avoided using it as a feature because it is not available at prediction time.[^17]

- **Future availability**:
  - Promo schedule is assumed largely known (stores schedule promotions in advance), allowing future promo flags and day‑counters relative to promo events.[^3][^2]
  - Weather and other external context are used only with lagging or coarse aggregates when present.

### 2.4 Walmart Recruiting – Store Sales Forecasting

Walmart Recruiting asked for weekly department sales by store, with features like markdown (promotion) variables, CPI, unemployment, holiday types, and store‑level information.[^18][^19]

From public code and discussions:

- **Core features**:
  - Calendar: week index, week‑of‑year, holiday flags.[^18]
  - Target history: lagged weekly sales, rolling means, and holiday‑adjusted baselines.[^18]
  - Promotions: markdown variables summarizing depth and timing of discounts; often aggregated and lagged to avoid sparse raw markdown columns.[^18]
  - Store/department metadata and simple aggregates.[^18]

- **Exogenous features**:
  - CPI, unemployment, fuel price showed limited and inconsistent benefits; many strong kernels treat them as optional or minor.[^18]
  - No evidence that any solution used web traffic, returns, reviews, payments, or shipping latency.

- **Future availability**:
  - Markdown schedule is assumed partially known (planned promotions), but some solutions still treat markdowns conservatively and primarily use historical patterns.[^18]

***

## 3. Feature Family Ranking

This section synthesizes competition evidence into a ranking with future‑availability discipline.

### 3.1 Must‑have families

**Calendar / seasonality**

- Used heavily in all four competitions: day‑of‑week, month, week‑of‑year, holiday flags, counters relative to events (promo cycles, holidays).[^2][^3][^1][^4]
- Always **known in advance**; safe for long‑horizon.[^4]

**Target lags & rolling target statistics**

- M5, Favorita, Rossmann, Walmart solutions all rely on rich lag structures and rolling stats over multiple windows at series or grouped level.[^1][^2][^13][^18]
- Must be **lagged only**; future target values are never used.

**Price / discount / promo features**

- Price/discount features are central in M5 and Favorita; promo flags and promo‑related statistics are central in Rossmann and Walmart.[^3][^2][^13][^1][^4]
- Future availability depends on business: winners treat promo schedule as **known in advance when retailer planning makes it realistic**, otherwise rely on lagged promo history and intensity.[^2][^13]

### 3.2 Often useful / conditional families

**Hierarchy / aggregation features (item/store/category/etc.)**

- Very important in panel settings (M5, Favorita): hierarchical IDs (item, store, category, dept, state) and aggregated statistics by group are core to expressing cross‑sectional differences.[^5][^1][^4]
- For a **single aggregate target** like your daily total Revenue/COGS, these features are more relevant as **intermediate aggregates** (e.g., building category/channel mix time series that then feed lags/rolling on aggregates), rather than as huge sets of per‑group dummy variables in one aggregate model.

**Item/store/category mix features**

- Winners often use mix ratios (e.g., share of sales from promo, weekends, school holidays, particular families) particularly in Rossmann (ratio of sales during promos/holidays/Saturdays) and Favorita (perishable vs non‑perishable, family‑level behaviour).[^5][^3][^2]
- However, these are **derived from target history and static metadata**, not from external future‑unknown signals; they are essentially **higher‑order lags/aggregates**.

### 3.3 Usually conditional or weak evidence

**Inventory / stockout features**

- M5/Favorita/Rossmann/Walmart public data do not include explicit stock levels or stockout flags; thus there is no strong competition evidence on inventory as a feature.[^14][^16][^19][^11]
- In external retail practice, inventory constraints matter, but modelling them usually requires joint demand–supply systems, not just a demand ML model.[^6]
- For your setting, inventory is at high risk of being **post‑outcome** or requiring nontrivial future modelling.

**Traffic / site visit features**

- Favorita includes **transaction counts** per store–day; some strong solutions use it as a demand proxy (number of tickets) with lags/rolling windows.[^13][^5]
- There is no evidence of web traffic in these competitions; transaction counts are still strongly tied to realised demand and thus fundamentally lagged.
- For long‑horizon aggregate revenue, traffic is only safe if it is either lagged or forecasted separately; winners do not rely on “known future web traffic”.

**Returns / reviews / post‑purchase signals**

- None of the four competitions exposes returns or review scores in a way that winners documented using as core features.[^16][^19][^14][^11]
- Conceptually, these are strongly outcome‑driven and often occur after the sale event; they are much more suitable for **diagnostic/quality** models than for forward‑looking demand.

**Payment / installments / payment mix**

- Not part of the main feature sets in these competitions. Financial modelling best practice treats payment method and instalments largely as accounting dimensions; gross margin forecasts are driven more by sales mix and cost structure than payment terms.[^9][^10]
- For aggregate daily Revenue/COGS, these are likely redundant with revenue itself or leakage‑prone (e.g., if using payment delays to infer future sales).

**Logistics / shipping features**

- Shipping latency, shipping fees, and logistics KPIs are not present in these competition datasets, and there is no evidence they were simulated or added by winners.[^6][^3]
- In practice, such features can matter at the operational level but are rarely central for long‑horizon aggregate demand forecasts unless using very detailed operational datasets.

### 3.4 Exogenous features that look attractive but often fail

- **Traffic / transactions:** Favorita transaction counts appear in some strong solutions but as **lagged aggregate** features; they are helpful mainly as another view of demand (tickets vs units) rather than as an independent exogenous signal.[^5][^13]
- **Inventory:** lacks strong competition evidence; risk of leakage if future stock states depend on forecast itself.
- **Returns / reviews:** post‑purchase, backward‑looking; using them as forward features would be leakage unless modelling future returns explicitly.
- **Payments / installments / shipping:** rarely mentioned; financial modelling guides focus on margin %, not payment terms, for forecasting COGS and gross profit.[^10][^9]

***

## 4. Promo Handling Patterns

From Rossmann, Favorita, Walmart, and M5‑style articles:

- **Contemporaneous promo flags (when future known):**
  - Rossmann uses promo flags (Promo, Promo2) and their day‑relative counters (days since promo start/end, whether promo is active this week/next week).[^3][^2]
  - Favorita uses binary `onpromotion` flags, plus rolling promo counts by store–item/store–family.[^13][^5]

- **Lagged promo history & rolling intensity:**
  - Winners compute statistics like proportion of days on promo in recent windows, ratio of sales during promos vs normal, and counts of promo days.[^7][^2][^3]
  - These are essentially **promo history features**, independent of future knowledge.

- **Promo target encodings and interactions:**
  - Rossmann: average sales per store in promo vs non‑promo, promo×weekday interactions, number of school holidays, days store open.[^2][^3]
  - Favorita: promo interacting with item family, perishable flag, and calendar; group‑by store/item/family/holiday.

- **Future fill rules:**
  - Where future promo schedule is not fully known, solutions either:
    - Assume “no additional future promos” for base forecast and use scenario‑based adjustments outside the competition scope, or
    - Use only lagged promo history; there is no documented pattern of inventing detailed future promo paths.[^8][^1]

- **Width vs simplicity of promo blocks:**
  - Rossmann’s winner mentions “lots of feature engineering”, but the promo block is built around **a handful of well‑motivated aggregates and ratios** (e.g., ratio of sales during promos/holidays/Saturdays, counts of school holidays, day counters around events), not hundreds of raw promo columns.[^15][^3][^2]
  - Favorita winners similarly focus on binary flags and a moderate number of rolling promo stats; public notebooks do not show thousand‑feature promo explosions as decisive factors.[^6][^13]

Conclusion: **promo should be structurally rich but semantically compact** — a few dozen well‑chosen aggregated and interaction features, not hundreds of sparse, highly specific columns.

***

## 5. Panel vs Aggregate Target and Validation Implications

### 5.1 Panel vs aggregate

- In panel competitions (M5, Favorita), hierarchical IDs and group‑level stats are crucial; winners leverage **information sharing across series** with item/store/category/state keys and aggregated lag/rolling statistics.[^1][^4][^13]
- When forecasting a **single aggregate series** (total daily Revenue/COGS), the incremental value of huge families like `mix`, `traffic`, `returns_reviews`, `inventory` is much lower unless they encode genuinely independent forward‑looking signals.
- What transfers well to your aggregate setting:
  - Calendar/seasonality.
  - Target lags & rolling stats at aggregate level.
  - Price/promo and high‑level hierarchy aggregates (e.g., daily revenue by big category or channel, then aggregated into lag/rolling metrics).

### 5.2 Validation best practices

- Strong solutions rely on **time‑based folds**, often using the last block(s) of data as a hold‑out to drive feature selection and ensembling.[^8][^15][^2]
- In Rossmann, the winner “heavily exploited a holdout set consisting of the last six weeks” for feature selection, effectively using **recent‑year weighting** and discarding features that overfit earlier years.[^15][^2]
- M5‑style write‑ups highlight the risk of overfitting to exotic exogenous features; exogenous variables are kept simple and business‑plausible, with most signal coming from lags, rolling stats, price/promo, and calendar.[^8][^1]
- General pattern for deciding when to drop a feature family:
  - If a family improves average CV score but degrades recent‑fold performance or significantly increases variance, winners tend to remove it or constrain its usage.[^8][^15][^2]
  - Families lacking clear future availability or business interpretation are treated as **high‑risk**.

***

## 6. Recommended Keep / Cut / Research‑Next Table

| Feature family | Evidence from winners | Future availability requirement | Transferability to our repo | Recommendation |
|---|---|---|---|---|
| Calendar / seasonality | Documented as core in M5, Favorita, Rossmann, Walmart (DOW, month, holidays, event counters).[^1][^2][^3][^4] | Known in advance | Directly transferable; essential for long‑horizon aggregate Revenue/COGS. | **Keep (core)** |
| Revenue / COGS history (lags) | Heavy use of lagged sales in all competitions; often the single strongest signal.[^1][^2][^13][^18] | Lagged only | Directly transferable; critical backbone for your two targets. | **Keep (core)** |
| Rolling target statistics | Used extensively (rolling means/medians/std, zero counts) in M5, Rossmann, Favorita.[^1][^2][^13] | Lagged only | Directly transferable; improves stability and long‑horizon behavior. | **Keep (core)** |
| Price / discount / promo | Central in M5 (sell_price) and Rossmann/Favorita/Walmart (promo flags, promo ratios, days since promo).[^1][^4][^2][^3][^13] | Known future promo when realistic; otherwise lagged promo history and aggregated intensity | Highly transferable but should be **compact and well‑designed**, not 400+ sparse features. | **Keep but narrow & simplify** |
| Hierarchy / aggregation | Key to panel models (item/store/category/state) in M5/Favorita.[^1][^4][^5] | Static IDs; lagged/aggregated stats | For a global aggregate target, useful primarily as **intermediate aggregates** (category/channel level) feeding into lags/rolling, not giant one‑hot/mix blocks. | **Research‑next (focused)** |
| Item/store/category mix | Used as ratios of sales by condition (promo, weekend, family) in Rossmann and Favorita.[^2][^3][^5] | Derived from target history and static metadata | Transferable if implemented as **a small set of stable ratios**, not a wide `mix` block built from noisy context features. | **Keep only a narrow, curated subset; otherwise cut** |
| Traffic / site visits | Favorita uses transaction counts (tickets) as lagged aggregates in some strong notebooks; no web‑traffic winners.[^5][^13] | Lagged only or separately forecast; not known future | For long‑horizon aggregate Revenue, traffic is risky unless you have a robust forecast; current evidence suggests it is **not core** and easily becomes noise/leakage if treated as known future. | **Cut from core; maybe keep small lagged aggregates for analysis** |
| Inventory / stockout | Not present in prioritized competition datasets; no winner‑level evidence.[^11][^14][^16][^19] | Would require separate inventory model; future stock unknown | Likely leakage‑prone and noisy in long‑horizon demand forecast; better for supply or diagnostic modelling. | **Cut from core** |
| Returns / reviews | Absent from competition features; conceptually post‑purchase and outcome‑driven.[^14][^16][^11][^19] | Post‑outcome; future unknown | High leakage risk if used forward; more appropriate for quality/NPS models. | **Cut from core; use only for reporting** |
| Payment / installments | Not used in competitions; FP&A practice forecasts COGS via margin %, not payment terms.[^10][^9] | Often redundant with revenue; future mix uncertain | Little evidence for predictive value in long‑horizon aggregate demand; mainly accounting/audit. | **Keep out of core unless a narrow audit proves value** |
| Logistics / shipping | Not present in datasets; no documented use in winners.[^3][^6] | Would be lagged or separately forecast | Likely low value for aggregate daily Revenue/COGS long‑horizon; more relevant for operational SLAs. | **Cut from core** |
| Geo / store context | Store type, assortment, competition distance used in Rossmann; state/store IDs in M5.[^2][^15][^4] | Static | For a single global series, geographic context is less critical; can matter if you build intermediate aggregates by region/channel. | **Use minimally (static IDs for intermediate aggregates), not as a big context block** |

***

## 7. What Transfers to Your Repo vs What Does Not

### Transfers well

- **Default core**: `calendar + revenue_history + cogs_history + promo` is exactly aligned with the core of Rossmann/Favorita/M5/Walmart solutions: calendar + target history + promo/price.[^3][^4][^1][^2]
- **Promo handling**: a smaller, interpretable set of promo features — flags, days‑since/ until, rolling promo intensity, ratio of sales during promos — matches winning practice better than a 400+ feature block.[^2][^3][^13]
- **Panel → aggregate**: using category/channel aggregates as intermediate series, then building lags/rolling on those aggregated series, mirrors how panel competitions exploit hierarchy while still ultimately predicting aggregate behavior.[^4][^1][^5]

### Likely does not transfer (to long‑horizon aggregate Revenue/COGS)

- **Large `traffic` blocks** assuming future web traffic is known: no competition uses future traffic as a core exogenous; at best, transaction counts are lagged demand proxies.[^5][^13]
- **Inventory, returns, reviews** as exogenous drivers of long‑horizon demand: these are either unavailable in competitions or conceptually post‑outcome, and would require joint systems to avoid leakage.[^19][^14][^16][^11]
- **Broad `mix` and `order_flow` blocks** built from many context features: winners focus on a few robust ratios (sales during promo/weekend/holiday), not hundreds of fine‑grained mix features.
- **Payment features** as demand drivers: financial guides consistently treat payment mix as an accounting dimension, not a primary driver of COGS/gross margin forecasts.[^9][^10]

***

## 8. Decision Answers for Your Repo

1. **Should default forecast core stay close to `calendar + revenue_history + cogs_history + promo`?**  
   Yes. This is strongly supported by what actually works in M5, Favorita, Rossmann, and Walmart: every winning or top solution is built on calendar + target history + rolling stats + price/promo, with other families playing supporting roles at best.[^1][^3][^4][^2]

2. **Is it likely correct to freeze out `traffic`, `inventory`, `returns_reviews`, `order_flow`, and `mix` from the long‑horizon forecast core?**  
   Yes, as a **default**. There is no strong winner‑level evidence that these families (beyond very small, carefully derived ratios) are core drivers in long‑horizon retail panel competitions, and they are frequently at risk of being lagged demand proxies, post‑outcome signals, or future‑unknown covariates. They are better candidates for: (a) narrow experiments with strict future‑availability discipline, or (b) analysis/reporting layers.[^16][^11][^19][^5]

3. **Is `payments.csv` likely worth bringing into the forecast core, or better kept out unless a narrow audit proves otherwise?**  
   Better kept **out of core** by default. Payment value, instalments, and payment method mix are not present in the benchmark competitions and financial forecasting practice focuses on forecasting margin %, not payment terms, for COGS and gross profit. Unless a targeted experiment shows clear incremental value (e.g., specific payment types tightly linked to high‑margin categories), it should remain an audit/finance layer.[^10][^9]

4. **Should `promo` be made narrower and simpler rather than wider?**  
   Yes. Winners use promo intensively but with **structured, interpretable blocks**: a limited number of flags, duration counters, rolling intensities, and simple ratios, not hundreds of raw/one‑hot promo columns. Narrowing your 400+ promo features into a smaller, business‑meaningful set is more consistent with successful competition practice and should improve stability.[^3][^13][^2]

5. **Is there any feature family you are probably underusing that strong competition evidence says you should revisit?**  
   The main underused angle is **hierarchy/aggregation** in a controlled way: using product/category/channel/region aggregates to build additional lag/rolling features that reflect mix shifts, rather than broad, noisy `mix` blocks. For example, daily revenue by a few top‑level categories or channels, then adding their lag/rolling stats as a small, curated family, mirrors how M5 and Favorita exploit cross‑sectional structure while remaining robust.[^4][^1][^5]

Overall, public competition evidence suggests your current direction — compact, strict core centered on calendar + Revenue/COGS history + a cleaned‑up promo block, with most other families pruned or heavily constrained — is well aligned with what actually worked in the strongest retail forecasting solutions.

---

## References

1. [M5 Forecasting Accuracy Competition - Christophe Nicault](https://www.christophenicault.com/post/m5_forecasting_accuracy/) - The goal of the M5 competition is to forecast 28 days ahead for all items, and at different aggregat...

2. [Rossmann Store Sales | Kaggle](https://www.kaggle.com/c/rossmann-store-sales/discussion/17896) - Forecast sales using store, promotion, and competitor data. ... The last mean feature was constructe...

3. [Kaggle winning solutions: Retail Sales Forecasting](https://de.slideshare.net/slideshow/kaggle-winning-solutions-retail-sales-forecasting/249422466) - This document summarizes several winning solutions from Kaggle competitions related to retail sales ...

4. [rruss2/M5_competition: Time Series Forecasting Project - GitHub](https://github.com/rruss2/M5_competition) - The objective of the M5 forecasting competition is to advance the theory and practice of forecasting...

5. [Corporación Favorita Grocery Sales Forecasting - Anant Agarwal](https://aagarwal4.github.io/grocery_forecasting.html) - The goal is to build a model that more accurately forecasts product sales. Source: Kaggle. Data. The...

6. [Machine Learning for Retail Sales Forecasting — Feature Engineering](https://www.samirsaci.com/machine-learning-for-retail-sales-forecasting-features-engineering/) - In this article, we examine the impact of several features on the accuracy of a model using the M5 F...

7. [Kaggle Winning Solution : Retail Sales Forecasting - YouTube](https://www.youtube.com/watch?v=95l9qkPulFA) - Rossmann Store Sales (https://www.kaggle.com/c/rossmann-store-sales) - Corporación Favorita Grocery ...

8. [Option 3: Recursive Modeling](https://www.artefact.com/blog/sales-forecasting-in-retail-what-we-learned-from-the-m5-competition-published-in-medium-tech-blog/) - 5 February 2021 In this article, Data Scientist Maxime Lutel sums up his learnings from the M5 sales...

9. [CDD Skills - 3. Gross Margin Forecasting - Latitude Consulting](https://www.latitude.co.uk/cdd-skills-3-gross-margin-forecasting/) - Projecting flat gross margin for the complete product set is not unreasonable as long as as least on...

10. [Financial Forecasting Guide - Learn to Forecast Revenues, Expenses](https://corporatefinanceinstitute.com/resources/financial-modeling/financial-forecasting-guide/) - Financial forecasting is the process of estimating or predicting how a business will perform in the ...

11. [M5 Forecasting - Accuracy | Kaggle](https://www.kaggle.com/competitions/m5-forecasting-accuracy) - In this competition, the fifth iteration, you will use hierarchical sales data from Walmart, the wor...

12. [Commentary on the M5 forecasting competition](https://eprints.lancs.ac.uk/id/eprint/214016/1/Kolassainpress.pdf)

13. [Corporación Favorita Grocery Sales Forecasting - YouTube](https://www.youtube.com/watch?v=WDwlXqvc-vA) - Winning solution for Kaggle competition - Corporación Favorita Grocery Sales Forecasting: ...

14. [Corporación Favorita Grocery Sales Forecasting - Kaggle](https://www.kaggle.com/c/favorita-grocery-sales-forecasting) - Corporación Favorita Grocery Sales Forecasting. Can you accurately predict sales for a large grocery...

15. [Rossmann Store Sales Forecasting Model Documentation (KAG-DS1)](https://www.studocu.vn/vn/document/truong-dai-hoc-ngoai-thuong/financial-reporting/rossmann-nr1-doc/88283754) - Winning Model Documentation. describing my solution for the Kaggle competition. “Rossmann Store Sale...

16. [Rossmann Store Sales | Kaggle](https://www.kaggle.com/c/rossmann-store-sales) - Prizes · 1st place - $15,000 · 2nd place - $10,000 · 3rd place - $5,000 · In addition, a single $5,0...

17. [[PDF] Rossmann Store Sales Prediction - CS229: Machine Learning](https://cs229.stanford.edu/proj2015/215_report.pdf) - We obtained Rossmann 1115. Germany stores' sales data from Kaggle.com. The goal of this project is t...

18. [GitHub - ChenglongChen/Kaggle_Walmart-Recruiting-Store-Sales-Forecasting: R code for Kaggle's Walmart Recruiting - Store Sales Forecasting](https://github.com/ChenglongChen/Kaggle_Walmart-Recruiting-Store-Sales-Forecasting) - R code for Kaggle's Walmart Recruiting - Store Sales Forecasting - ChenglongChen/Kaggle_Walmart-Recr...

19. [Walmart Recruiting - Store Sales Forecasting - Kaggle](https://www.kaggle.com/c/walmart-recruiting-store-sales-forecasting) - Use historical markdown data to predict store sales.

