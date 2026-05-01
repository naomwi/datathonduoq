# Long-Horizon Retail Forecasting Gaps for Datathon Repo

## Phần 1 — Executive summary (actionable only)

- Long-horizon daily forecasting nên **siết chặt "forecast_core"** vào các feature chắc chắn known-in-future (calendar, campaign plan đã chốt, static metadata) và một lớp nhỏ các biến business được forecast phụ (ví dụ traffic hoặc promo volume nếu và chỉ nếu có pipeline dự báo riêng); tất cả các biến như inventory, returns, reviews nên được đẩy sang nhóm **analysis_rich / report-only** trừ khi có model phụ tương ứng.[^1][^2][^3]
- Trong bối cảnh aggregate revenue, có bằng chứng rằng **hybrid tree + seasonal/classical correction chỉ đáng đầu tư khi seasonal pattern không được explain tốt bởi covariates** hoặc khi model tabular gặp khó ở very-long horizon; decomposition (trend/seasonality) rồi model residual bằng ML có kết quả tích cực, nhưng gains moderate và không luôn vượt qua tree-only với FE tốt.[^4][^5][^6]
- Với regime drift, thực tế từ retail và long-horizon forecasting ủng hộ **recent-weighted / horizon-aware model selection**, ưu tiên performance trên các folds gần cuối và theo horizon hơn là chỉ tối ưu mean trên toàn backtests; ensembles có thể dùng trọng số nặng hơn cho model thắng ở recent windows để giảm risk mismatch với hidden period.[^2][^7][^8]
- Với aggregate revenue, evidence cho thấy **direct aggregate forecasting là baseline mạnh, component modeling có ích chủ yếu cho explainability và scenario planning**; component models (traffic × conversion × AOV, revenue by segment) chỉ thực sự giúp khi có covariates rõ ràng và pipeline ổn định cho từng component, nếu không dễ tăng noise và leakage risk.[^9][^10][^11]
- CatBoost có xu hướng **perform tốt với feature set gọn, tập trung vào lags/rolling/calendar/promos đã chuẩn hoá**, và dễ degrade khi thêm nhiều context feature nhiễu hoặc high-cardinality mà không có enough signal; thực hành mạnh là: giữ core compact, sử dụng categorical handling cho key IDs, và ưu tiên tuning depth, learning rate, l2_leaf_reg, grow_policy hơn là thêm thêm feature.[^12][^13][^3]
- Đối với repo hiện tại: nên **khóa một policy feature rõ cho forecast_core vs analysis_rich**, thử một nhánh hybrid đơn giản (tree + seasonal-naive correction hoặc TS decomposition + tree-on-residual) trên subset recent, áp dụng recent-fold-weighted model selection, giữ direct aggregate revenue model làm anchor, và mở một workstream hẹp cho CatBoost-specific tuning với feature diet có kiểm soát.[^14][^6][^12]

***

## Phần 2 — Decision table

| Research question | Strong evidence found? | Main conclusion | Actionable now? | Priority for repo |
|---|---|---|---|---|
| Q1. Long-horizon feature availability | **Medium-strong** (frameworks + M5 commentary + practice) | Phân loại feature thành: static/ calendar/ planned-dynamic = forecast_core; uncertain operational (traffic, inventory, returns, reviews, shipments) = forecast_submodel hoặc analysis_rich/report-only; chỉ đưa vào core nếu có pipeline dự báo hoặc được fix bởi business plan.[^1][^15][^3] | Có | **High** — cần formal hoá để tránh leakage / optimism ở horizon dài |
| Q2. Hybrid tree + seasonal/classical | **Medium** (papers + hybrid residual models + TS decomposition studies) | Hybrid hợp lý khi seasonality mạnh, horizon dài và covariates không explain hết; TS decomposition rồi model residual bằng ML có evidence cải thiện, nhưng lợi ích không luôn vượt tree-only trong retail khi FE tốt.[^4][^5][^6] | Thử nghiệm giới hạn | **Medium** — 1–2 experiment mục tiêu, không mở broad workstream |
| Q3. Validation/model selection with regime drift | **Medium-strong** (multi-horizon TS literature + weighted CV) | Ưu tiên recent/horizon-aware selection hơn mean toàn period; weighted CV và ensemble-weight tuning theo recent folds là chiến lược thực tế để align với hidden regime.[^2][^8][^7] | Có | **High** — trực tiếp ảnh hưởng chọn model production |
| Q4. Aggregate revenue vs component modeling | **Medium** (ecom practice + decomposition literature) | Direct aggregate revenue forecasting đủ tốt trong nhiều retail use cases; component modeling giúp interpretability và scenario planning, chỉ đáng đầu tư khi có component signals rõ (traffic, CR, AOV) và data đủ sạch cho từng component.[^9][^10][^11] | Một phần | **Medium** — test nhỏ, dùng nhiều cho explainability hơn là core LB |
| Q5. CatBoost-specific TS best practices | **Medium** (tooling guides + GBM TS examples) | CatBoost mạnh khi feature set gọn, categorical core được encode đúng, lags/rolling/calendar được thiết kế careful; thêm context features noisy dễ làm hại, nên enforce feature diet và tập trung tuning depth, learning rate, regularization, loss.[^13][^3][^12] | Có | **High** — anchor hiện là CatBoost, policy feature/tuning sẽ có impact trực tiếp |

***

## Phần 3 — Detailed findings

### Q1 — Long-horizon feature availability

**Nguồn chính**

- Nixtla/MLForecast phân loại exogenous features thành **static**, **dynamic-known-advance**, và **calendar-derived**, nhấn mạnh rằng dynamic features chỉ hợp lệ nếu có future values known hoặc forecast từ nguồn khác; nếu không, chúng có thể gây optimistic bias khi backtest.[^1]
- Hướng dẫn gradient boosting cho time series cũng nhấn mạnh rằng exogenous variables phải **known at forecast time**; ví dụ, weather hoặc economic variables chỉ nên dùng nếu tương lai là forecast từ hệ thống khác, và nên đánh giá lại performance khi dùng forecast thay vì ground truth.[^3]
- Commentary M5 và kinh nghiệm thực tế từ Lokad chỉ ra rằng price/promotion data cho horizon forecast thường không có, và nhiều đội buộc phải **bỏ hoàn toàn giá/promo tương lai khỏi core** hoặc giả định scenario đơn giản, vì việc giả định "perfectly known future promotion" sẽ inflate accuracy trên backtest nhưng không transfer sang production.[^16][^15]

**Bằng chứng cụ thể / patterns**

- Trong M5, sell price series chỉ có observed values tới cuối train; future price trong horizon không được cung cấp, khiến các solution serious **không sử dụng price tương lai như exogenous input** mà chủ yếu rely vào past price patterns và calendar/promo proxies.[^15][^17][^16]
- Lokad phân tích rằng **không đội nào thực sự leverage được price** do lack of future values; họ kết luận rằng promotions là driver quan trọng nhưng cực khó forecast đúng, và dùng price/promo tương lai không thực tế nếu không có business planning data tương ứng.[^15]
- Các framework như MLForecast/TSF foundations đề xuất pipeline multi-horizon với input chia thành: (1) past-observed covariates, (2) future-known (calendar, planned promotions), (3) uncertain future signals, trong đó nhóm (3) cần được forecast riêng hoặc chỉ dùng cho offline analysis.[^2][^1]

**Decision framework đề xuất**

- **Static / gần như bất biến** (store/region, product category, channel type, customer segment, etc.):
  - Luôn **forecast_core**, cả short lẫn long horizon.
- **Calendar & deterministic events** (day-of-week, month, holiday/Tet dates, planned big campaigns đã chốt H-level):
  - **forecast_core** — luôn known in future, phù hợp cho long horizon.[^3][^1]
- **Operational & demand-driven signals**:
  - Web traffic, sessions, pageviews, click-throughs: thường **unknown in future**, trừ khi có pipeline marketing forecast (ad spend, planned campaigns, SEO/CRM scenarios).[^10][^9]
  - Inventory levels, stockouts, fill rate, inbound shipments: future states phụ thuộc vào demand (target forecast) và supply planning; treating them as known future là leakage. Nhiều guide inventory forecasting đề xuất dùng chúng như input cho supply-side but not as exogenous for demand long-horizon unless co-modeled trong joint system.[^9][^10]
  - Returns & reviews: heavily outcome-driven; future returns của order chưa phát sinh là unknown, nên phù hợp hơn cho **post-hoc analysis** hoặc short-horizon corrections, không cho long-horizon core.
  - Shipments/delivery metrics: similar — outcome/process metrics.

Từ đó, các nhóm:

- **forecast_core** (đưa vào model production):
  - Static metadata; calendar; holiday/sales events; high-level promo calendar đã chốt (e.g., "11.11 mega sale"), nếu available; some price/discount plans nếu thực sự locked-in bởi business.[^16][^1]
- **forecast_submodel** (chỉ đưa vào core nếu có model phụ forecast):
  - Web traffic scenario, marketing spend projections, channel mix projections.
  - Aggregate inventory pressure (e.g., predicted stock coverage) nếu có separate inventory planning model.
- **analysis_rich / report-only**:
  - Realized web traffic, realized inventory, realized returns/reviews, realized shipments, operational KPIs đo sau fact.
  - Dùng để giải thích forecast errors, provide narrative về drivers, nhưng không feed vào model long-horizon vì không available tại forecast time.[^3]

**Áp dụng ngay cho repo**

- Chuẩn hoá schema feature với flag `availability_type` ∈ {`static`, `calendar`, `planned_dynamic`, `uncertain_future`, `post_outcome`} và `usage_policy` ∈ {`forecast_core`, `forecast_submodel`, `analysis_rich`}.
- Siết lại feature set của CatBoost core chỉ gồm static/calendar/planned_dynamic; di chuyển traffic, inventory, returns, reviews, shipments hiện tại sang analysis_rich trừ khi có forecast pipeline tương ứng.
- Đảm bảo backtesting dùng cùng một set future-available features như at inference để tránh optimistic leakage, đặc biệt ở horizon xa.

**Không nên ưu tiên**

- Thiết kế complex joint models co-forecast traffic, inventory, returns trừ khi team có bandwidth lớn; evidence public hiếm thấy những hybrid này outperform simpler approach trong Kaggle-style competitions.

***

### Q2 — Hybrid tree-based + seasonal/classical correction

**Nguồn chính**

- Paper về hybrid residual modeling đề xuất hệ thống hai giai đoạn: dùng linear/statistical model (ARIMA/ETS) cho phần linear/seasonal, sau đó model residual bằng ensemble ML để capture nonlinear patterns; kết quả cho thấy hybrid thường outperform từng model riêng lẻ trên nhiều time series thực tế, nhưng gains phụ thuộc vào strength của mỗi component và quality của residuals.[^4]
- Một paper gần đây về trend-seasonality decomposition cho sales forecasting cho thấy **T-S decomposition + ML** (model phần residual) có thể cải thiện WRMSSE trên retail-like data, đặc biệt khi seasonality complex; tuy nhiên, lợi ích giảm khi feature set đã encode seasonality tốt (calendar, holiday features).[^6]
- Một số work thực nghiệm (e.g., gradient-boosted ARIMA, bagged ETS with residual AR/ML) cho thấy hybrid có thể cải thiện error, nhưng cũng cảnh báo về complexity và khó tuning; không phải lúc nào hybrid outperform naïve combination hoặc simple ML.[^18][^19][^20]

**Patterns thực tế liên quan aggregate revenue**

- Nhiều retailer-side practice (không chỉ Kaggle) sử dụng **seasonal naive hoặc ETS** làm baseline, sau đó sử dụng ML để điều chỉnh deviations (e.g., promo impact, anomalous events). Khi ML model đã ingest calendar & promo strongly, incremental gain từ explicit seasonal correction giảm.[^14][^12]
- Hybrid dạng: "tree model forecast + seasonal correction" thường xuất hiện dưới hai cấu trúc:
  - Additive: 
    - Forecast = Tree(y, X) + Seasonal_naive(y)
  - Residual: 
    - y = Seasonal_model(y) + Residual
    - Tree model forecast residual.
  Kết quả tốt hơn khi seasonality mạnh và relatively stable; kém hiệu quả nếu tree model đã encode seasonal pattern thông qua calendar features và lags.[^6][^4]

**Khi nào hybrid đáng làm**

- Long horizon với seasonal structure rõ (weekly, annual, campaign cycles) nhưng không được explain hết bởi covariates, hoặc khi muốn **stabilize long-horizon shape** (ensure weekly pattern preserved) còn tree model tập trung predict level.
- Khi backtests cho thấy tree-only model **good near-term nhưng drift shape** ở horizon xa, trong khi seasonal-naive giữ shape nhưng miss level.
- Khi có pipeline forecast seasonal components (e.g., from TS decomposition) rẻ và ổn định — decomposition không quá noisy.[^6]

**Khi nào hybrid dễ overkill**

- Khi calendar & lag features đã encode seasonality đủ; paper về simplified tree-based retail forecasting cho thấy tree models với explanatory variables (calendar, promos) có performance rất cạnh tranh mà không cần thêm tầng classical.[^12]
- Khi sample size không quá lớn và noise cao; hybrid có nguy cơ overfit residuals.

**Áp dụng cho repo (gợi ý pipeline)**

- Thiết kế một **"seasonal baseline"** cho daily aggregate revenue:
  - seasonal_naive_wk: ŷ(t) = y(t−7)
  - seasonal_naive_yr (nếu đủ data): ŷ(t) = y(t−365)
  - hoặc ETS/Prophet simple với trend + weekly + yearly + holiday.
- Hai nhánh experiment nhỏ:
  1. **Decomposition + CatBoost trên residual**:
     - Decompose y(t) = T(t) + S(t) + R(t) bằng STL hoặc một TS model phù hợp.
     - Train CatBoost core trên R(t) với feature mart (calendar, promo priors, etc.).
     - Forecast: ŷ = T̂ + Ŝ + R̂_catboost.
  2. **Tree-only vs Tree+Seasonal correction**:
     - Baseline: CatBoost core forecast ŷ_tree(t+h).
     - Hybrid: ŷ_hybrid(t+h) = ŷ_tree(t+h) + [y_seasonal_naive(t+h) − y_seasonal_naive(t+h_ref)], hoặc simpler là weighted blend giữa tree forecast và seasonal naive cho horizons xa.
- Evaluate trên **horizon bins** (e.g., 1–7, 8–30, 31+ days) để xem hybrid có gain thực sự ở long horizon hay không.

**Không nên ưu tiên**

- Complex hybrid như gradient-boosted ARIMA/ETS với tuning full ARIMA params trên aggregate revenue, trừ khi có strong evidence local; cost lớn, returns uncertain.[^5][^18]

***

### Q3 — Validation / model selection khi có regime drift

**Nguồn chính**

- Literature về **multi-horizon deep forecasting** (e.g., Temporal Fusion Transformers) formalize multi-horizon setting với static covariates, past-observed và known-future covariates; họ nhấn mạnh việc thiết kế loss và evaluation theo toàn horizon, đồng thời quan sát rằng **recent performance** là tốt hơn cho deployment trong presence of regime shift.[^2]
- Weighted CV và ensemble schemes cho time series cho thấy rằng weighting folds theo importance (e.g., recent periods) giúp align model selection với target regime và giảm risk khi distribution shift theo thời gian.[^7][^8]
- Các case study retail (M5, retail forecasting practice) cho thấy teams thường **ưu tiên backtests gần cuối** hoặc tạo dedicated validation block gần test period để chọn model, thay vì chỉ tối ưu mean trên nhiều năm lịch sử.[^21][^16]

**Patterns / insights**

- "Best average over entire history" ≠ "Best for next year": khi có structural changes (COVID, macro shifts, assortment changes), models fit tốt giai đoạn cũ có thể cho forecast tệ trong regime mới.[^14]
- Weighted CV frameworks đề xuất **fitness-weighted combination** hoặc selection, trong đó weights tăng dần theo time index của fold; điều này natural khi hidden period expected to resemble recent history.[^8]

**Decision logic đề xuất cho repo**

Giả sử có các folds time-based F1,…,Fk với Fk gần test nhất:

- Nếu model A thắng mean MAE trên tất cả folds nhưng **thua rõ rệt** ở Fk và Fk−1, còn model B thắng ở các folds gần cuối:
  - Ưu tiên model B hoặc **ensemble với weight ưu tiên** model B, vì hidden regime có khả năng gần các fold near-end hơn.
- Nếu model A có mean tốt hơn nhưng variance cao (performance khác biệt mạnh giữa folds), còn model B stability tốt hơn với chỉ slightly worse mean:
  - Với competition long horizon và unknown regime, chọn **model B** hoặc blend; stability quan trọng để tránh catastrophic failure trên hidden period.[^7]
- Khi metric chính của competition là MAE nhưng long-tail errors cũng quan trọng (RMSE/R2):
  - Sử dụng RMSE/R2 như **secondary filter**; nếu model B có RMSE/R2 tốt hơn đáng kể ở recent folds, tăng weight của B trong ensemble.[^2]

**Practical selector cho repo**

- Define **score_recent** = average MAE (hoặc competition metric) trên last m folds (e.g., 2–3 folds gần nhất).
- Define **score_global** = average trên tất cả folds.
- Define **stability** = variance của fold scores.
- Ranking policy:
  - Filter models với stability quá tệ (variance > threshold).
  - Trong các model ổn, optimize lexicographically: minimize score_recent, sau đó score_global.
- Ensemble policy:
  - Với top 2–3 models, set weights proportional to exp(−α · score_recent) để nhấn mạnh recent performance; α chọn nhỏ để tránh over-concentration.

**Áp dụng ngay**

- Implement một module **recent-weighted model selector** thay thế logic "best global mean" hiện tại.
- Log rõ ràng metrics per fold (MAE, RMSE, R2) và compute stability để tránh chọn model với high variance chỉ vì một vài folds tốt.

***

### Q4 — Forecast aggregate revenue trực tiếp hay via components

**Nguồn chính**

- Guides eCommerce forecasting nhấn mạnh decomposition của revenue thành components như **traffic × conversion rate × AOV**, hoặc inventory-adjusted demand vs realized sales; nhưng thường dùng decomposition để **diagnostics và scenario planning**, hơn là model long-horizon point forecast duy nhất.[^22][^9]
- Các bài viết về traffic/conversion/AOV cho thấy relationship phức tạp, với trade-off và inverse correlation tự nhiên giữa traffic và conversion, và giữa AOV và conversion; metric nên tập trung vào revenue per session hơn là từng thành phần riêng lẻ.[^11][^23]
- Research về sales forecasting với T-S decomposition cho thấy decomposition và modelling components có thể cải thiện accuracy trong setting multi-series và khi mỗi component có dynamics riêng; tuy nhiên, không phải luôn outperform direct ML trên aggregate nếu falta strong exogenous control.[^6]

**Pros/cons của component modeling**

- Pros:
  - Tăng **interpretability**: có thể nói "revenue miss do traffic vs CR vs AOV".
  - Cho phép gắn với marketing/planning pipelines: traffic dự báo từ marketing, CR/AOV từ UX/pricing assumptions.
  - Có thể improve stability nếu mỗi component được forecast từ covariates riêng (ad spend, UX changes, pricing plan) và noise khác nhau.[^10][^9]
- Cons:
  - Phức tạp hoá pipeline: cần **3 model** (traffic, CR, AOV) thay vì một, mỗi model có error riêng; error propagation có thể lớn hơn direct model error.
  - Leakage risk: nếu dùng realized traffic/CR/AOV trong training như exogenous cho revenue, nhưng không có forecast tương ứng cho inference, sẽ tạo optimistic bias similar to using future features (như cảnh báo trong exogenous-variable guidance).[^3]
  - Data quality: CR/AOV có thể noisy do small denominators, skewed distributions và campaign effects.

**When direct aggregate is đủ tốt**

- Khi aggregate revenue strongly driven by **stable seasonality + mixed effect của nhiều drivers** và không có single component dominating.
- Khi không có high-quality forecasts for individual components (e.g., traffic forecast uncertain, marketing plan hay đổi).
- Khi goal chính là **leaderboard accuracy**, ít yêu cầu scenario what-if.

**When component modeling đáng test**

- Khi business đã có pipeline riêng dự báo component (traffic, conversion, AOV) từ marketing/supply-side, và mục tiêu là align revenue forecast với những plans đó.
- Khi repo cần **explainability sâu** cho report và stakeholder: decomposition có thể dùng cho reporting ngay cả nếu core LB vẫn dùng direct model.[^11][^9]

**Actionable cho repo**

- Keep **direct aggregate revenue CatBoost** làm anchor cho LB.
- Thiết kế một **small experiment**:
  - Build component variables (traffic, CR, AOV) từ historical data.
  - Train simple models forecast each component using only forecast_core features (calendar, planned campaigns, static metadata).
  - Combine forecasted components thành revenue_hybrid = traffiĉ × CR̂ × AOV̂ và compare với direct aggregate.
- Nếu component pipeline không outperform aggregate trên recent folds, dừng ở việc dùng decomposition purely cho **diagnostic & narrative** (e.g., SHAP on traffic, CR, AOV contributions) thay vì production forecast.

***

### Q5 — CatBoost-specific best practices cho tabular TS forecasting

**Nguồn chính**

- Practitioner guides cho CatBoost time series nhấn mạnh strengths của CatBoost trên categorical features và robust default regularization; đồng thời lưu ý rằng CatBoost có thể overfit nếu feature space quá rộng và chứa nhiều noisy context variables.[^13]
- Tutorials về gradient boosting for TS (kể cả ví dụ với CatBoost) nhấn mạnh workflow: build supervised dataset bằng lagged target + exogenous known-in-future, sau đó dùng tree-based model; exogenous variables phải được chọn cẩn thận để tránh leakage, với calendar và static features là safe core.[^3]
- Retail forecasting research chỉ ra rằng simplified tree-based frameworks với explanatory variables đã đủ strong, và complexity hơn không luôn mang lại gain tương xứng; điều này gợi ý practice "feature diet" với emphasis on core signals.[^12]

**Patterns liên quan behavior CatBoost**

- CatBoost xử lý categorical features bằng **target-based statistics** (ordered boosting), nên:
  - Nhiều high-cardinality context features (e.g., user_id-like tokens, fine-grained campaign IDs) có thể introduce noise nếu không có đủ signal.[^13]
  - Features weakly related hoặc chỉ mang thông tin hậu nghiệm (post-outcome) dễ làm CatBoost overfit subtle patterns không tồn tại trong future.
- CatBoost thường **benefit từ feature set gọn** với focus vào:
  - Lags/rolling của target và một số aggregated signals ổn định.
  - Calendar features.
  - Category/segment IDs có business meaning rõ.
  - Promo priors với fill-rule rõ ràng (on/off promotions, campaign types) khi known-in-future.[^13][^3]

**Practical best practices cho repo**

- **Feature policy**:
  - Giữ `catboost_md2y_core` gần với forecast_core: lags/rolling revenue & COGS, calendar, promo priors với fill rule hợp lý.
  - Tránh thêm context features mà không kiểm tra availability_type; inventory/returns/reviews/web_traffic thực tế thuộc analysis_rich hoặc forecast_submodel.
- **Tuning priorities**:
  - Depth: moderate depth (6–8) thường capture đủ nonlinearities mà không overfit cho TS tasks.[^13]
  - Learning rate: small (e.g., 0.03–0.05) với nhiều trees để stabilization, đặc biệt với long horizon.
  - Regularization: l2_leaf_reg and bagging_temperature (random strength) dùng để combat overfitting; nên tune trước khi thêm thêm features.
  - Loss: dùng loss align với competition metric (MAE-like hoặc tweedie nếu distribution skewed) khi feasible.[^6]
- **Forecasting strategy**:
  - CatBoost phù hợp với **direct multi-horizon** (one model per horizon or horizon bins) sử dụng same feature mart; recursive multi-step (feeding predicted y back làm lag) tăng risk error accumulation.
  - Khi horizon dài, prefer direct horizon-specific targets (e.g., y(t+7), y(t+30)) để model heterogeneity giữa near-term và far-term.

**Evidence về context features làm hại**

- Việc nội bộ quan sát rằng adding context features giúp XGBoost nhưng làm hại CatBoost phù hợp với pattern CatBoost sensitive to noisy/weak categorical signals; guides khuyến nghị **feature selection** hoặc grouping for SHAP-based pruning để giữ signal-to-noise ratio cao.[^12][^13]

**Actionable**

- Thiết lập rule: bất kỳ feature mới muốn đưa vào CatBoost phải được label `forecast_core` và pass qua một **simple single-model ablation** (core vs core+feature) trên recent folds; nếu không gain rõ, loại bỏ.
- Tạo một cấu hình `catboost_core_strict` với feature diet hơn `catboost_md2y_core` hiện tại, tune hyperparameters trước, sau đó mới nới feature set nếu cần.

***

## Phần 4 — Actionable recommendations for our repo

**Nên làm ngay**

- Định nghĩa và gắn nhãn **feature availability & usage policy**:
  - Implement các flags `availability_type` và `usage_policy` như ở Q1, refactor pipelines để CatBoost core chỉ dùng features `forecast_core`.
- Cập nhật **model selection logic**:
  - Implement recent-weighted, horizon-aware selector: optimize score_recent (last folds) + stability, không chỉ global mean.
- Siết **CatBoost feature diet**:
  - Clone `catboost_md2y_core` thành `catboost_core_strict` với chỉ forecast_core features; tune depth, learning rate, l2_leaf_reg, iterations.

**Nên test tiếp (targeted experiments)**

- Hybrid vertical:
  - Một experiment decomposition + CatBoost-on-residual trên daily aggregate revenue.
  - Một experiment blend CatBoost forecast với seasonal naive (weekly) for far horizons.
- Component modeling vertical (small):
  - Build simple traffic/CR/AOV forecast from calendar + planned campaigns; compare aggregate revenue from components với direct CatBoost trên recent folds.
- CatBoost feature policy:
  - Systematic ablations with SHAP/gain to identify context features that hurt performance; maintain whitelist of safe context features (if any).

**Nên dừng hoặc deprioritize**

- Thêm nhiều context/business features vào CatBoost mà không qua filter forecast_core và ablation; evidence và practice gợi ý dễ làm hại hơn giúp.[^12][^13]
- Đầu tư lớn vào complex hybrid ARIMA/ETS + GBM for aggregate revenue trước khi các hybrid đơn giản được test; paper và practice cho thấy lợi ích incremental, không guaranteed.[^18][^5]

**Chưa đủ bằng chứng để đầu tư lớn**

- Heavy-weight component modeling (full-blown system traffic/CR/AOV/inventory returns) cho mục tiêu leaderboard trước mắt; các nguồn thiên về strategy/ops hơn là competition-style accuracy và yêu cầu data/ops phức tạp.[^22][^9]
- Deep learning long-horizon foundations được nhắc trong literature gần đây nhưng chưa có case đủ gần repo (multi-table aggregate revenue với no external data) để justify pivot khỏi tree-based backbone.[^24][^25]

***

## Phần 5 — What is still uncertain

- **Best-practice granularity cho component modeling trong e-commerce competitions**: literature business rất ủng hộ decomposition traffic/CR/AOV, nhưng ít có benchmark công khai chứng minh outperform direct ML trên aggregate revenue trong Kaggle-style setting; cần experimentation nội bộ để kết luận.[^9][^11]
- **Mức độ gain thực tế từ hybrid seasonal/TS decomposition + CatBoost** trên dataset gần giống Datathon: papers cho thấy benefits trên một số datasets nhưng không có case gần domain/structure repo hiện tại.[^4][^6]
- **Exact advantage profile của CatBoost vs LightGBM/XGBoost** cho long-horizon aggregate forecasting với multi-table data: có guides và anecdotal experience, nhưng thiếu comparative benchmark chuyên sâu ở setting giống Datathon; hiện tại repo phải dựa vào evidence nội bộ + một số general findings.[^13][^12]
- **Tối ưu scheme recent-weighted selection** (chọn trọng số, số folds gần nhất, trade-off với global mean): literature đưa ra ideas về weighted CV nhưng không có công thức universal; tuning chi tiết cần dựa trên backtests của chính repo.[^8][^7]

---

## References

1. [Exogenous Variables in MLForecast for Sales - Nixtla](https://www.nixtla.io/blog/mlforecast-exogenous-variables) - Learn how to incorporate external factors like prices, promotions, and calendar patterns into your t...

2. [Google Cloud AI, USA arXiv:1912.09363v3 [stat.ML] 27 Sep 2020](https://arxiv.org/pdf/1912.09363v3.pdf)

3. [Forecasting time series with gradient boosting - Cienciadedatos.net](https://cienciadedatos.net/documentos/py39-forecasting-time-series-with-skforecast-xgboost-lightgbm-catboost) - Missing: best lags rolling calendar promotions

4. [A hybrid system based on ensemble learning to model residuals for ...](https://www.sciencedirect.com/science/article/abs/pii/S0020025523011994) - This work proposes a hybrid system that combines a linear statistical model with an ensemble of ML m...

5. [[PDF] Two-stage hybrid models for enhancing forecasting accuracy ... - arXiv](https://arxiv.org/pdf/2502.08600.pdf) - The first option is to construct all local models on non-while noise residuals, we make use of auto....

6. [[PDF] Improved Sales Forecasting using Trend and Seasonality ... - arXiv](https://arxiv.org/pdf/2305.17201.pdf) - The application of both traditional time series models and modern machine learning and AI techniques...

7. [Conversational Time Series Foundation Models](https://arxiv.org/html/2512.16022v1) - ... current weight combinations will remain valid and to identify potential regime shifts. Second, t...

8. [Time series forecasting using a weighted cross-validation ...](https://www.sciencedirect.com/science/article/abs/pii/S0925231213000209) - In this paper, we focus on this second issue, by proposing the use of a fitness weighted n-fold cros...

9. [eCommerce Forecasting: A Comprehensive Guide (2026)](https://www.sarasanalytics.com/blog/ecommerce-forecasting) - eCommerce forecasting turns historical patterns and real-time signals into predictable inventory, re...

10. [Inventory Forecasting for E-Commerce: Predict Demand and ...](https://www.attnagency.com/blog/inventory-forecasting-ecommerce)

11. [How traffic, conversion rate, and AOV work together - Peasy.nu](https://www.peasy.nu/blog/how-traffic-conversion-rate-and-aov-work-together) - Revenue equals traffic times conversion rate times average order value. This simple equation—Revenue...

12. [Simplifying tree-based methods for retail sales forecasting with ...](https://www.sciencedirect.com/science/article/abs/pii/S0377221723008159) - For most retailers, the gains of more sophisticated tree-based methods may not be worth the increase...

13. [CatBoost For Accurate Time-Series Predictions: Here’s How](https://aicompetence.org/catboost-for-accurate-time-series-predictions/) - CatBoost improves time-series forecasting by enhancing accuracy and efficiency in prediction tasks. ...

14. [Retail forecasting: Research and practice - ScienceDirect.com](https://www.sciencedirect.com/science/article/abs/pii/S016920701930192X) - This paper reviews the research literature on forecasting retail demand. We begin by introducing the...

15. [No1 at the SKU-level in the M5 forecasting competition - Lecture 5.0](https://www.lokad.com/tv/2022/1/5/no1-at-the-sku-level-in-the-m5-forecasting-competition/) - In 2020, a team at Lokad achieved No5 over 909 competing teams at the M5, a worldwide forecasting co...

16. [Commentary on the M5 forecasting competition](https://eprints.lancs.ac.uk/id/eprint/214016/1/Kolassainpress.pdf)

17. [M5 Forecasting - Accuracy | Kaggle](https://www.kaggle.com/competitions/m5-forecasting-accuracy) - In this competition, the fifth iteration, you will use hierarchical sales data from Walmart, the wor...

18. [Gradient Boosted ARIMA for Time Series Forecasting](https://towardsdatascience.com/gradient-boosted-arima-for-time-series-forecasting-e093f80772f6/) - Adding gradient boosting to Arima adds complexity to the fitting procedure but can also drive accura...

19. [Kenneth-V-R/Gradient-Boosted-ARIMA-For-Time-Series-Forecasting](https://github.com/Kenneth-V-R/Gradient-Boosted-ARIMA-For-Time-Series-Forecasting) - By combining ARIMA models with XGBoost in a single model ensemble we manage to achieve better model ...

20. [[PDF] Bagging Exponential Smoothing Methods using STL Decomposition ...](https://robjhyndman.com/papers/BaggedETSForIJF_rev1.pdf)

21. [Option 3: Recursive Modeling](https://www.artefact.com/blog/sales-forecasting-in-retail-what-we-learned-from-the-m5-competition-published-in-medium-tech-blog/) - 5 February 2021 In this article, Data Scientist Maxime Lutel sums up his learnings from the M5 sales...

22. [ECommerce forecasting: A guide to profitable sales growth](https://www.cloudflight.io/en/blog/ecommerce-forecasting-sales-growth/) - ECommerce forecasting involves analyzing a range of historical and real-time data, such as past sale...

23. [AOV vs conversion rate: Balancing both - Peasy.nu](https://www.peasy.nu/blog/aov-vs-conversion-rate-balancing-both) - High conversion with low AOV can generate less revenue than moderate conversion with high AOV, and v...

24. [Time-Aware Prior Fitted Networks for Zero-Shot Forecasting ... - arXiv](https://arxiv.org/html/2603.15802v1) - In many time series forecasting settings, the target time series is accompanied by exogenous covaria...

25. [Recent advances in deep long-horizon forecasting - Google Research](https://research.google/blog/recent-advances-in-deep-long-horizon-forecasting/) - We present an all multilayer perceptron (MLP) encoder-decoder architecture for time-series forecasti...

