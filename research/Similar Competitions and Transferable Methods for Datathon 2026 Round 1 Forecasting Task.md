# Similar Competitions and Transferable Methods for Datathon 2026 Round 1 Forecasting Task

## Phần 1 — Executive summary

- Các competition gần nhất về tinh thần và cấu trúc dữ liệu: **Rossmann Store Sales**, **Corporación Favorita Grocery Sales Forecasting**, **M5 Forecasting – Accuracy**, **Store Sales – Time Series Forecasting (Favorita v2)** và nhóm **Predict Future Sales / Store Item Demand Forecasting / Walmart Recruiting**.[^1][^2][^3][^4][^5][^6][^7]
- Nhóm phương pháp thắng giải tập trung vào **gradient-boosted tree trên tabular feature mart** (LightGBM / XGBoost / CatBoost) với feature engineering mạnh từ transactional data, promotion, calendar, hierarchical aggregation và nhiều rolling statistics.[^8][^9][^10][^11][^12]
- Deep learning time series (RNN/LSTM/seq2seq/TFT…) thường chỉ đóng vai trò **phụ / exploratory**, hiếm khi là model chính trong top solution các competition retail bán lẻ kiểu này, trừ khi đầu tư cực lớn vào kiến trúc và engineering.[^13][^14]
- Với cấu trúc **daily aggregated revenue** từ multi-table business data, baseline hợp lý và mạnh nhất thực tế là: **LightGBM/XGBoost/CatBoost + lag/rolling/calendar/promo/web-traffic/inventory features + multi-window CV**.[^9][^15][^8]
- Validation scheme gần private LB nhất trong các competition tương tự thường là **multiple rolling / expanding windows theo thời gian**, đôi khi kết hợp **horizon-aware models** (train model riêng cho từng horizon hoặc nhóm horizon).[^10][^16][^9]
- Feature families quan trọng nhất lặp đi lặp lại: **lags/rolling means**, **same DOW/DOM stats**, **promotion intensity**, **price/discount**, **calendar/holiday**, **store–item / category aggregation**, và với M5: **hierarchical grouping + stock-related constraints**.[^16][^12][^8][^10]
- Explainability ở các bài tabular forecasting thường dùng **gain-based feature importance** của tree model; khi cần nghiêm túc hơn thì dùng **SHAP global + grouped features + PDP/ICE** để kể câu chuyện business (promo, traffic, inventory, customer mix…).[^17][^18][^19]
- Kết luận cho Datathon: ưu tiên **tree-based tabular models làm xương sống**, tổ chức feature mart tốt, cross-validation cẩn thận, sau đó mới cân nhắc bổ sung **1–2 model deep learning** như secondary models để ensemble nếu còn thời gian.[^15][^14][^9]

***

## Phần 2 — Comparison table (top tương đồng)

| Competition | Platform / Year | Target | Horizon | Data structure | Metric | Similarity to Datathon | Winning/strong method family | Transferability notes |
|---|---|---|---|---|---|---|---|---|
| Rossmann Store Sales | Kaggle, 2015 | Daily store sales per store | Up to 6 weeks ahead | Single main fact table (store–date) + store metadata, promos, holidays, competitors | RMSPE | **High** (retail, daily, promo, store-level aggregation; thiếu multi-table rich như Datathon nhưng rất giống về tinh thần tabular TS) | Gradient boosted trees (XGBoost/LightGBM), RF; heavy FE on calendar/promo/store; stacking/ensembling | FE pattern (calendar, promo, store attrs), leakage-conscious CV, tree-based models có thể chuyển giao trực tiếp; cần mở rộng thêm multi-table aggregation cho Datathon.[^2][^20][^21]
| Corporación Favorita Grocery Sales Forecasting | Kaggle, 2017–2018 | Daily unit sales per store–item | ~16 ngày ahead | Multi-table: transactions, holidays, oil price, store/item metadata; long daily panel | NWRMSLE | **High** (retail, daily, promos, rich exogenous/transactional data; khác ở granularity store–item thay vì aggregated revenue) | LightGBM ensembles với rich rolling/lag features, promo/holiday modeling, multi-window CV | Toàn bộ FE và CV chiến lược có thể reuse; cần aggregation từ store–item lên daily revenue; bỏ bớt complexity item-level nếu không cần.[^1][^22][^8]
| M5 Forecasting – Accuracy | Kaggle (Makridakis/Walmart), 2020 | Daily unit sales cho 42k+ hierarchical series (item–store–state–all) | 28 ngày | Nhiều bảng: sales, prices, calendar; hierarchical structure, thousands TS | Weighted RMSSE | **Medium–High** (retail daily với promo/price; khác mạnh ở hierarchical item/store level và metric) | Global LightGBM/GBM-style models trên feature mart, hierarchical reconciliation/top-down alignment, complex multi-level CV | FE ideas (global lags, rolling stats, calendar, price/promo) và CV từ M5 rất hữu ích; hierarchical reconciliation ít liên quan vì Datathon target là aggregated revenue.[^3][^23][^9][^16]
| Store Sales – Time Series Forecasting (Favorita store families) | Kaggle, ongoing (getting started) | Daily sales per store–family | 15 ngày | train.csv + stores, oil, holidays, transactions; khá giống Favorita cổ điển nhưng đơn giản hơn | SMAPE | **Medium–High** (grocery retail, daily, promos, multiple side tables) | LightGBM/XGBoost, sometimes Prophet/ARIMA as baseline; FE từ Favorita được tái sử dụng | Thích hợp để lấy notebook template cho pipeline FE + modeling; mức độ phức tạp thấp hơn Datathon nhưng rất gần về kiểu feature mart.[^7][^24]
| Predict Future Sales | Kaggle, 2015+ | Monthly item_cnt per shop–item | 1 month | Daily sales aggregated lên monthly + item/shop metadata | RMSE | **Medium** (retail but at monthly granularity; still panel TS with strong lag FE) | Tree-based models (XGBoost/LightGBM), đôi khi thêm linear/NN; heavy use of monthly lag and mean encodings | Idea về lag/rolling trên panel và mean encodings theo shop/item/category hữu ích; khác về horizon và granularity nên cần điều chỉnh.[^25][^26][^6]
| Store Item Demand Forecasting Challenge | Kaggle, 2018 | Daily sales per store–item | 3 months | Single fact table (date, store, item, sales) | SMAPE | **Medium** (daily retail but đơn giản, ít exogenous variables) | XGBoost/LightGBM per item or global, FE chủ yếu từ dates (DOW, month, etc.) | Dùng như baseline sanity-check; ít multi-table nên chỉ giúp về khung modeling, không về data integration.[^11][^27][^12]
| Walmart Recruiting – Store Sales Forecasting | Kaggle, 2014 | Weekly department sales per store | Several weeks | Weekly panel với markdown (promotion) + store features | WMAE | **Medium** (retail + markdown promos, nhưng weekly và metric khác) | Tree-based models, linear models, some TS (ARIMA/ETS) as benchmarks | Ideas về treatment of markdown/promotion và holiday effect chuyển giao tốt; cần downscale lên daily và đổi metric.[^28][^29][^30]

***

## Phần 3 — Detailed analysis từng competition

### Rossmann Store Sales

Rossmann yêu cầu dự báo **daily sales** cho hơn 1000 cửa hàng tại Đức, dùng dữ liệu lịch sử sales kết hợp với thông tin về promotion, holiday, competitor và metadata của store. Target là cột "Sales" ở mức store–day, horizon khoảng 6 tuần, metric RMSPE nên phạt mạnh sai số tương đối. Không có multi-table transactional kiểu orders/order_items, nhưng có nhiều biến ngoại sinh liên quan business như promo duration, state holiday, school holiday và cạnh tranh.[^2][^31][^21]

Các solution top đề xuất pipeline: cleaning + feature engineering mạnh (calendar features, promo duration/intervals, state/store type, school vs public holidays) + gradient boosted tree (XGBoost/LightGBM) với cross-validation theo kiểu time-based splits. Một số team dùng ensembling nhiều model (RF, ExtraTrees, linear) nhưng backbone vẫn là boosted trees và mức cải thiện từ ensemble là nhỏ so với việc có feature engineering tốt. Việc chống leakage được thực hiện qua việc đảm bảo splits theo thời gian, không dùng thông tin của tương lai trong feature như "days since next promo".[^20][^21]

Về tương đồng, Rossmann **rất giống** Datathon ở tinh thần: retail demand forecasting, daily granularity, nhiều biến promo/holiday/store-level, và bài toán "tabular TS" hơn là modelling thẳng chuỗi đơn biến. Khác biệt lớn là Datathon có **multi-table transactional data** (orders, order_items, web_traffic, inventory, customers...) nên pipeline Rossmann chỉ cover phần "feature mart trên daily level" chứ chưa đụng phần data integration. Tuy vậy, toàn bộ thiết kế feature calendar/promo/store và cách setup time-based CV có thể chuyển giao gần như nguyên xi.[^2][^20]

### Corporación Favorita Grocery Sales Forecasting

Favorita là competition retail lớn với **daily item-level unit sales** cho hàng trăm nghìn combination store–item, kèm transactions, metadata store/item, holiday events, và oil price như một biến macro. Metric là NWRMSLE, horizon khoảng 16 ngày. Dataset có khoảng 125 triệu dòng train nên vấn đề scale và efficient feature engineering rất quan trọng.[^22][^1]

Top solutions ở Favorita sử dụng **LightGBM làm core model**, xây dựng một feature mart khổng lồ gồm: lags nhiều horizon (1, 3, 7, 14, 28, 56...), rolling means/medians, counts of zero-sales, promo intensity, holiday flags, oil price lags, transaction counts, v.v. Họ thường train global models hoặc theo nhóm (per category, per store type) với cross-validation kiểu rolling windows, dùng một khoảng validation 15 ngày gần cuối train để tune, đôi khi chọn model dựa trên sub-horizon giống cấu trúc public LB. Đáng chú ý là nhiều solution sử dụng multi-window strategy (train model riêng cho từng horizon hoặc nhóm horizon) để tránh drift giữa near-term và long-term.[^32][^8]

Điểm tương đồng lớn với Datathon là: retail/e-commerce, daily granularity, promo, holiday, multi-table transactional và metadata phong phú. Khác biệt là Datathon yêu cầu target là **daily aggregate revenue** thay vì unit sales per store–item; do đó cần design aggregation từ transactional để build target và features. Các kỹ thuật FE (lag/rolling by store/category, promo intensity, price/discount signals, transaction/traffic counts) và CV strategy từ Favorita **chuyển giao rất tốt** khi xây daily revenue feature mart.[^1][^22]

### M5 Forecasting – Accuracy

M5 là iteration mới nhất của Makridakis competition được tổ chức trên Kaggle, sử dụng **hierarchical daily sales** của Walmart ở nhiều mức: item–store, item–state, state, category, tổng toàn hệ thống. Horizon là 28 ngày; metric chính là weighted RMSSE, tính trên 42.840 chuỗi trong hierarchy với trọng số theo doanh số. Dữ liệu gồm sales history, calendar (events, SNAP benefits), sell price (weekly item-store prices) và hierarchical metadata.[^33][^3][^16]

Các paper tổng kết M5 cho thấy đa số top teams dùng **global machine learning models** (đặc biệt LightGBM) trên feature mart, đôi khi kết hợp với statistical TS models hoặc hierarchical reconciliation. Feature engineering tập trung vào lags nhiều horizon, rolling means, moving windows, price change indicators, promotion flags, calendar events và đôi khi stock-availability proxies. Cross-validation đa phần sử dụng multiple rolling windows (ví dụ nhiều block 28 ngày) để match private leaderboard behavior.[^23][^9][^10][^16]

So với Datathon, M5 cung cấp nhiều insight về modeling **global panel of time series** và hierarchical reconciliation, nhưng target Datathon là aggregated daily revenue nên không cần toàn bộ machinery của hierarchical forecasting. Tuy vậy, design feature mart (global lags/rolling, calendar, price/promo signals) và CV pattern trong M5 là **reference rất mạnh** cho bài toán này, đặc biệt nếu sau này muốn dự báo thêm revenue theo category/store.[^16]

### Store Sales – Time Series Forecasting (Favorita v2)

Competition "Store Sales – Time Series Forecasting" dùng lại data Favorita theo format "getting started", với target là daily sales theo store–family (product family) trong 15 ngày tương lai. Dataset cung cấp train.csv (store_nbr, family, onpromotion, sales), cùng stores.csv, oil.csv, holidays_events.csv, transactions.csv, tương tự Favorita gốc nhưng đơn giản hơn ở granularity.[^7][^24]

Các notebook điển hình sử dụng LightGBM/XGBoost làm backbone, với calendar features (DOW, DOM, DOY, holiday flags), promotion intensity, rolling means/medians theo window, và đôi khi Prophet/ARIMA như baseline TS một chiều. Do competition này hướng dẫn người mới, pipeline đơn giản nhưng rất gần với thứ sẽ cần cho Datathon: build feature mart daily với nhiều bảng phụ, train tree-based models, evaluate bằng SMAPE.[^24][^34][^7]

Transferability ở đây là **template code/pipeline**: cách join nhiều bảng (oil, stores, transactions, holidays), tạo feature lag/rolling, setup train/val split cuối cùng theo thời gian và submit predictions. Từ đó có thể thay target từ family-level sales sang aggregated revenue.[^7]

### Predict Future Sales

"Predict Future Sales" là final project playground của course "How to win a data science competition", dùng daily sales của một nhà bán lẻ Nga để dự báo **monthly total sales** per shop–item. Train data là daily item_cnt_day từ 2013-01 đến 2015-10; test yêu cầu dự báo tổng số lượng trong tháng 2015-11, metric RMSE.[^25][^6]

Pipeline phổ biến: aggregate lên monthly feature mart, build lag features của monthly sales (1, 2, 3, 6, 12 tháng), mean encodings theo shop, item, category, shop–category, plus price trends và holiday flags. Core model thường là XGBoost/LightGBM với cross-validation theo block time, đôi khi có thêm linear hoặc RF để ensemble. Deep learning chỉ xuất hiện trong một số kernel exploratory, không phải trong top solutions.[^26][^25]

Đối với Datathon, competition này hữu ích về tư duy **panel TS + lag FE mạnh** hơn là trực tiếp về domain (monthly vs daily, item-level vs aggregate revenue). Các kỹ thuật như generating lagged aggregates trên nhiều dimensions (shop/item/category) và "target encoding" có thể áp dụng cho các nhóm như customer segment, product category, channel mix.[^25]

### Store Item Demand Forecasting Challenge

Store Item Demand Forecasting là competition kernels-only, với 5 năm daily sales cho 50 items ở 10 stores; mục tiêu là dự báo 3 tháng tiếp theo. Data tương đối sạch, không có nhiều exogenous variables, nên competition này được dùng để demo nhiều phương pháp TS.[^4][^27]

Một số solution công khai dùng XGBoost/LightGBM với feature engineering từ date (day, month, weekday, etc.) và lag/rolling features; số khác thử ARIMA, Prophet hoặc LSTM để so sánh. Kết quả thường cho thấy tree-based models với FE tốt cho performance khá cạnh tranh trên metric SMAPE.[^11][^34][^12]

Transferability chủ yếu nằm ở **baseline sanity-check**: implement một LightGBM trên panel daily sales với lag/calendar features để kiểm tra pipeline và expectation về performance. Vì data cấu trúc đơn giản, competition này không giúp nhiều về multi-table integration hay promo/price modeling.[^11]

### Walmart Recruiting – Store Sales Forecasting

Walmart Recruiting yêu cầu dự báo **weekly department sales** per store, dùng historical weekly sales kết hợp với features như markdown (promotion), CPI, unemployment, holiday type và store category. Metric là WMAE với weight khác nhau cho tuần holiday.[^28][^5][^30]

Các solution top áp dụng tree-based models (RF, Gradient Boosting, XGBoost), linear models, và đôi khi ARIMA/ETS cho từng time series nhỏ. Feature engineering tập trung vào markdown/promotion intensity, holiday flags, seasonality theo week-of-year, và store–department interactions. External macro variables được sử dụng nhưng ít khi là driver chính.[^29][^35]

Với Datathon, competition này cung cấp insight về modelling **promotion markdowns và holiday effects** trên sales, đặc biệt là cách encode markdown over time và tránh leakage khi sử dụng thông tin đó. Tuy nhiên, granularity weekly và metric WMAE khá khác, nên chỉ nên lấy ý tưởng, không bê nguyên pipeline.[^28][^29]

***

## Phần 4 — Method transfer map

### Use directly (ưu tiên triển khai)

- **Gradient-boosted tree models (LightGBM / XGBoost / CatBoost) trên daily feature mart**: được sử dụng làm backbone trong Rossmann, Favorita, M5, Store Item Demand, Predict Future Sales và thường outperform classical TS và nhiều DL models khi có FE tốt.[^12][^8][^9][^10][^11]
- **Feature families cốt lõi**:
  - Lag features trên target (revenue) với nhiều horizon (1, 2, 3, 7, 14, 28, 56 ngày…), cả raw lags lẫn rolling stats (mean, median, std, min, max, count of zeros).[^8][^10][^12]
  - Calendar features: day-of-week, weekend, day-of-month, month, week-of-year, year, special flags cho Tet/holiday/sale events — pattern này xuất hiện nhất quán trong Rossmann, Favorita, M5, Store Sales.[^22][^2][^7]
  - Promotion/discount intensity: binary flags, promo duration (days since promo started, days to promo end), share of items on promotion, depth of discount (if available), markdown effects.[^29][^8][^28]
  - Aggregated sales metrics theo dimensions: product category mix, channel mix, customer segment mix, geography mix, payment mix; analog với store/item/category aggregations ở Favorita, M5, Predict Future Sales.[^9][^22][^25]
  - Web traffic / transaction counts / inventory stress (stockouts proxy): tương tự transaction count, oil price, and price signals in Favorita and M5 (thay oil price bằng web_traffic hoặc marketing intensity).[^22][^16]
- **Time-based cross-validation (rolling/expanding windows)**: đa số top teams dùng nhiều backtests theo thời gian để approximate private LB behavior, thay vì single last-block split.[^10][^8][^9][^16]
- **Global models across series**: thay vì model riêng cho từng product/store, nhiều solution M5/Favorita dùng global LightGBM với identifiers encoded, khai thác cross-learning giữa series.[^9][^16]
- **Regularization against leakage**: tất cả competition đều nhấn mạnh không sử dụng thông tin tương lai trong feature (e.g., future holidays, future promotions) ở thời điểm train; phải xây feature theo đúng time index.[^20][^8]

### Use with adaptation

- **Hierarchical forecasting từ M5**: reconciliation methods (top-down, middle-out, MinT) hữu ích nếu Datathon mở rộng sang nhiều target level (revenue per category/store/region), nhưng với single aggregate revenue thì chỉ cần giữ consistency giữa các view, không cần full hierarchy machinery.[^23][^16]
- **Item-level demand modeling**: patterns từ Favorita/M5/Predict Future Sales có thể dùng để build intermediate models (e.g., forecast sales per category hoặc channel rồi aggregate) nhưng phải cân nhắc complexity và thời gian thi đấu.[^3][^1][^25]
- **Deep learning TS models (LSTM/seq2seq/TFT/N-BEATS)**: một số kernel cho thấy kết quả competitive trên dataset đơn giản hoặc khi horizon dài, nhưng yêu cầu nhiều tuning, infrastructure, và thường khó beat tree-based models trong setting Kaggle/datathon với feature-rich tabular data. Có thể dùng như secondary model để ensemble nếu pipeline chính đã ổn.[^14][^13]
- **Classical TS (ARIMA/Prophet/ETS)**: hữu ích làm baseline và sanity-check cho chuỗi revenue tổng, nhưng khó tận dụng hết rich covariates và multi-table data như Favorita/M5. Có thể dùng để mô hình hóa phần residual seasonality còn lại sau khi tree model xử lý covariates.[^36][^28]

### Probably not worth prioritizing (trong bối cảnh thời gian ngắn)

- **Pure hierarchical reconciliation optimization** (MinT, complex top-down mixtures) khi only target là tổng daily revenue: chi phí implementation và tuning không tương xứng lợi ích, nhất là khi không submit multi-level forecasts.[^23][^16]
- **Phức tạp hóa kiến trúc deep learning** (multi-horizon transformers, PatchTST, N-BEATS ensembles) nếu team chưa có sẵn codebase; evidence từ Kaggle cho thấy các mô hình này ít khi thắng những bài retail/e-commerce với tabular-rich khi thời gian có hạn.[^15][^14]
- **Over-engineered statistical TS per series** (ARIMA per SKU/store) trên dataset lớn: M5 và các competition retail chỉ ra rằng global ML models scale tốt hơn nhiều và thường cho accuracy cao hơn.[^16][^11]

***

## Phần 5 — Recommended modeling roadmap cho Datathon

### 1. Baseline nhanh

- Build **single-variable baselines**:
  - Naive last-value, seasonal naive (same day last week/last year) trên daily revenue để đo mức độ seasonality và difficulty.[^16]
  - Simple moving-average/Exponential smoothing để có benchmark MAE/RMSE/SMAPE thô.[^28]
- Run **Prophet hoặc ARIMA** trên chuỗi revenue tổng để hiểu seasonal patterns (weekly, monthly, yearly, Tet) và compare với naive.[^36]

### 2. Xây feature mart daily từ multi-table

- Define clear forecasting target: **daily Revenue** (và có thể COGS như auxiliary) per global business, có thể thêm view per channel hoặc region nếu cần.
- Từ các bảng raw (`orders`, `order_items`, `payments`, `shipments`, `returns`, `reviews`, `inventory`, `web_traffic`, `promotions`, `customers`, `products`, `geography`):
  - Aggregate lên daily-level metrics: order count, item count, revenue by category/brand/channel, average order value, return rate, review scores, inventory days of cover, traffic sessions, conversion rate, promotion count/intensity.[^7][^22]
  - Join calendar table với holiday/Tet, marketing events nội bộ.
  - Ensure strict time cut: chỉ dùng thông tin đến ngày t khi tạo feature cho ngày t (hoặc t+forecast horizon nếu làm direct multi-horizon models).

### 3. Strong tabular model (backbone)

- Train **LightGBM/ XGBoost/ CatBoost** trên daily feature mart:
  - Vấn đề target: có thể bắt đầu với **one-step-ahead daily revenue** sau đó extend sang direct multi-horizon (e.g., separate models cho 7, 14, 30 ngày ahead) nếu cần.[^10][^9]
  - Use appropriate loss (MAE / Huber / RMSE) phù hợp với competition metric.
- Cross-validation:
  - Implement **multiple rolling windows** (e.g., vài block 30–60 ngày cuối trong train) để đo variance và tránh overfit vào một block.[^10][^16]
  - Option: horizon-aware validation – đánh giá riêng cho short vs long horizon để hiểu model behavior.[^10]

### 4. Advanced feature engineering

- Từ insights Favorita/M5/Predict Future Sales:
  - Lags/rolling trên revenue, orders, traffic, promotion counts, inventory stress.
  - Same-DOW và same-holiday stats: average revenue cho các lịch Tet/holiday tương tự năm trước.[^8][^16]
  - Promo features: binary flags, cumulated days in promo, days since last promo, promo share của SKUs high-margin.[^29][^8]
  - Mixes: category mix, channel mix, customer mix và payment mix; encoded dưới dạng ratios hoặc entropy.
  - Price/discount: nếu có, sử dụng discount depth, relative price vs history để capture elasticity (analog với sell_price dynamics của M5).[^9]

### 5. Blending / ensembling

- Sau khi có backbone ổn định:
  - Train variations of tree-based models (different seeds, feature subsets, horizons) và **average/weighted blend**; M5 và Favorita cho thấy ensemble nhiều LightGBM variants thường mang lại vài phần trăm cải thiện.[^8][^10]
  - Optionally add 1–2 **DL models** (LSTM/seq2seq global model trên revenue + key covariates) và blend prediction để capture non-linear temporal patterns khó cho tree model.[^14]
- Giữ số lượng models hợp lý để tránh overfitting vào LB public và đảm bảo reproducibility.

### 6. Explainability & reporting

- Trên model backbone (e.g., LightGBM):
  - Compute **gain-based feature importance** để có ranking sơ bộ.[^18][^19]
  - Compute **SHAP values** cho sample window (ví dụ vài tháng gần cuối train) để:
    - Xây **global SHAP summary plot** (top features, distribution impacts).[^17][^18]
    - Xây **grouped SHAP** theo family (promo, traffic, inventory, customer mix, product mix…).
    - Tạo vài **PDP/ICE** cho các feature business-critical (promo intensity, web traffic, inventory days-of-cover, discount depth) để kể câu chuyện causal-like.[^19][^17]
- Map kết quả explainability sang narrative business: "promo tăng X đơn vị thì revenue tăng/giảm như thế nào", "web traffic vs conversion", "inventory stress dẫn tới mất sales".

### 7. Ablation & iteration order

- Thứ tự thực dụng trong thời gian ngắn:
  1. **Baseline + simple LightGBM với calendar + basic lags** để có một submission ổn định.
  2. Thêm **promo/holiday features** và check CV/LB uplift.
  3. Thêm **traffic/inventory/customer features**, iterate feature selection bằng gain/SHAP để loại bớt noise.[^15]
  4. Experiment multi-window models (per horizon hoặc per regime) + blending.
  5. Nếu còn thời gian, thêm 1–2 DL models nhỏ (e.g., LSTM với vài covariates) để thử ensemble.

***

## Phần 6 — Đánh giá các giả thuyết ban đầu

1. **"Rossmann Store Sales là competition gần nhất về tinh thần feature-engineered retail forecasting"** — Hợp lý nhưng chưa phải gần nhất về cấu trúc dữ liệu. Rossmann rất giống về spirit (retail, daily, promo, tree+FE) nhưng thiếu multi-table transactional data như Favorita/Store Sales, vì vậy nên coi Rossmann là **benchmark concept về feature-engineered daily retail forecasting**, còn **Favorita/Store Sales** gần hơn về data richness.[^2][^22][^7]
2. **"Corporación Favorita gần nhất về retail + promotions + tabular feature engineering + model blending"** — Được xác nhận. Favorita có multi-table, promos, oil price, holiday, transactions, và top solutions dùng LightGBM với rolling/promo features và blending nhiều models.[^1][^22][^8]
3. **"M5 rất hữu ích về phương pháp và validation, nhưng target khác (hierarchical item-store)"** — Hoàn toàn chính xác. Literature về M5 nhấn mạnh global LightGBM, hierarchical structure và advanced CV; nhưng Datathon chỉ cần một phần (global FE & CV) chứ không cần full hierarchy reconciliation.[^23][^9][^16]
4. **"LightGBM/XGBoost/CatBoost + strong FE có khả năng là hướng mạnh nhất"** — Được hậu thuẫn bởi tất cả competition retail/e-commerce lớn (Rossmann, Favorita, M5, Store Item, Predict Future Sales), nơi tree-based models với rich FE liên tục xuất hiện trong top solutions.[^11][^8][^9][^10]
5. **"Deep learning thuần có thể không phải lựa chọn tối ưu đầu tiên nếu dữ liệu cuối cùng là daily aggregated feature mart"** — Evidence từ Kaggle cho thấy LSTM/seq2seq thường chỉ đạt top-mid hoặc cần rất nhiều công sức để ngang bằng tree-based models, đặc biệt khi có nhiều exogenous features và multi-table. Do đó, DL nên ở vai trò secondary/ensemble hơn là model đầu tiên.[^13][^14]
6. **"Multi-window models + blending có thể hiệu quả hơn single model"** — Được ủng hộ rõ trong Favorita và M5, nơi top teams huấn luyện nhiều models cho các horizon/segments khác nhau và blend chúng để đạt thêm vài phần trăm improvement.[^23][^8][^10]
7. **"Explainability bằng SHAP phù hợp hơn với yêu cầu report"** — Phù hợp với practice hiện tại: SHAP được dùng rộng rãi để giải thích tree models, có support tốt trong Python ecosystem, và dễ chuyển thành plots đẹp cho report; có nhiều hướng dẫn cụ thể về aggregate feature importance, PDP/ICE kết hợp SHAP.[^18][^19][^17]

---

## References

1. [Corporación Favorita Grocery Sales Forecasting - Kaggle](https://www.kaggle.com/c/favorita-grocery-sales-forecasting) - Corporación Favorita Grocery Sales Forecasting. Can you accurately predict sales for a large grocery...

2. [Rossmann Store Sales | Kaggle](https://www.kaggle.com/c/rossmann-store-sales) - Prizes · 1st place - $15,000 · 2nd place - $10,000 · 3rd place - $5,000 · In addition, a single $5,0...

3. [M5 Forecasting - Accuracy | Kaggle](https://www.kaggle.com/competitions/m5-forecasting-accuracy) - In this competition, the fifth iteration, you will use hierarchical sales data from Walmart, the wor...

4. [Store Item Demand Forecasting Challenge | Kaggle](https://www.kaggle.com/competitions/demand-forecasting-kernels-only) - Predict 3 months of item sales at different stores.

5. [Walmart Recruiting - Store Sales Forecasting - Kaggle](https://www.kaggle.com/competitions/walmart-recruiting-store-sales-forecasting) - In this recruiting competition, job-seekers are provided with historical sales data for 45 Walmart s...

6. [Predict Future Sales | Kaggle](https://www.kaggle.com/competitions/competitive-data-science-predict-future-sales) - We are asking you to predict total sales for every product and store in the next month. By solving t...

7. [Store Sales - Time Series Forecasting - Kaggle](https://www.kaggle.com/competitions/store-sales-time-series-forecasting/data) - In this competition, you will predict sales for the thousands of product families sold at Favorita s...

8. [GitHub - btrotta/kaggle-favorita: Code for top 3% result in the Kaggle Corporacion Favorita Grocery Sales Forecasting competition.](https://github.com/btrotta/kaggle-favorita) - Code for top 3% result in the Kaggle Corporacion Favorita Grocery Sales Forecasting competition. - b...

9. [Silver medal solution for the "M5 Forecasting - Accuracy ...](https://github.com/stephenllh/m5-accuracy) - Silver medal solution for the "M5 Forecasting - Accuracy" Kaggle competition - stephenllh/m5-accurac...

10. [Top 3% solution for Kaggle M5 Accuracy competition - GitHub](https://github.com/btrotta/kaggle-m5) - Top 4% solution for the Kaggle M5 (Accuracy) competition. The competition requires predicting store ...

11. [jgonzalezab/Store-Item-Demand-Forecasting: Results of ... - GitHub](https://github.com/jgonzalezab/Store-Item-Demand-Forecasting) - This repository contains my own scripts, predictions and results on the Store Item Demand Forecastin...

12. [Store-Item-Demand-Forecasting/README.md at master - GitHub](https://github.com/jgonzalezab/Store-Item-Demand-Forecasting/blob/master/README.md) - This repository contains my own scripts, predictions and results on the Store Item Demand Forecastin...

13. [Corporación Favorita Grocery Sales Forecasting - #68 by EricPB](https://forums.fast.ai/t/corporacion-favorita-grocery-sales-forecasting/8359/68) - Corporación Favorita Grocery Sales Forecasting ... This kernel is based on senkin13's kernel: LSTM S...

14. [M5_Forecasting with LSTM and LightGBM - Kaggle](https://www.kaggle.com/code/surekharamireddy/m5-forecasting-with-lstm-and-lightgbm) - In this competition, the fifth iteration, you will use hierarchical sales data from Walmart, the wor...

15. [Chapter 8: Winningest Methods in Time Series Forecasting](https://phdinds-aim.github.io/time_series_handbook/08_WinningestMethods/lightgbm_m5_forecasting.html) - Specifically, we explore the machine learning model that majority of the competition's winners utili...

16. [the success of global forecasting models - Cienciadedatos.net](https://cienciadedatos.net/documentos/py61-m5-forecasting-competition)

17. [Get a feature importance from SHAP Values](https://stackoverflow.com/questions/65534163/get-a-feature-importance-from-shap-values) - iw ould like to get a dataframe of important features. With the code below i have got the shap_value...

18. [SHAP Feature Importance with Feature Engineering - Kaggle](https://www.kaggle.com/code/wrosinski/shap-feature-importance-with-feature-engineering) - We will begin analysis of importance with most important features for a model based on validation se...

19. [Model Interpretability - Feature Importance using SHAP & LIME](https://www.kaggle.com/getting-started/288193) - SHAP Values (an acronym from SHapley Additive exPlanations) break down a prediction to show the impa...

20. [[PDF] Rossmann Store Sales Prediction - CS229: Machine Learning](https://cs229.stanford.edu/proj2015/215_report.pdf) - We obtained Rossmann 1115. Germany stores' sales data from Kaggle.com. The goal of this project is t...

21. [Kaggle case study on predicting sales for Rossmann stores - GitHub](https://github.com/tiffanyhsu001/kaggle-rossmann) - In this Kaggle case study: I was provided with historical sales data for 1,115 Rossmann stores. The ...

22. [Corporación Favorita Grocery Sales Forecasting - Anant Agarwal](https://aagarwal4.github.io/grocery_forecasting.html) - The goal is to build a model that more accurately forecasts product sales. Source: Kaggle. Data. The...

23. [[PDF] The M5 Accuracy competition: Results, findings and conclusions](https://statmodeling.stat.columbia.edu/wp-content/uploads/2021/10/M5_accuracy_competition.pdf) - This paper describes the M5 Accuracy competition, the first of two parallel challenges of the latest...

24. [GitHub - Tech-i-s/techis-ds-kaggle-store_sales_time_series_forcasting: Use machine learning to predict grocery sales using time series forcasting](https://github.com/Tech-i-s/techis-ds-kaggle-store_sales_time_series_forcasting) - Use machine learning to predict grocery sales using time series forcasting - Tech-i-s/techis-ds-kagg...

25. [storieswithsiva/Kaggle-Predicting-Future-Sales - GitHub](https://github.com/storieswithsiva/Kaggle-Predicting-Future-Sales) - To predict total sales for every product and store in the next month. By solving this competition I ...

26. [Predict Future Sales | Kaggle](https://www.kaggle.com/competitions/competitive-data-science-predict-future-sales/code) - Final project for "How to win a data science competition" Coursera course

27. [Store Item Demand Forecasting Challenge - Kaggle](https://www.kaggle.com/c/demand-forecasting-kernels-only/data) - The objective of this competition is to predict 3 months of item-level sales data at different store...

28. [Walmart Store Sales Forecasting - GitHub](https://github.com/ezgigm/Project4_Store_Sales_Forecasting) - A time series model that predicts the future store sales of Walmart. Forecasting with ARIMA, Exponen...

29. [GitHub - ChenglongChen/Kaggle_Walmart-Recruiting-Store-Sales-Forecasting: R code for Kaggle's Walmart Recruiting - Store Sales Forecasting](https://github.com/ChenglongChen/Kaggle_Walmart-Recruiting-Store-Sales-Forecasting) - R code for Kaggle's Walmart Recruiting - Store Sales Forecasting - ChenglongChen/Kaggle_Walmart-Recr...

30. [Walmart Recruiting - Store Sales Forecasting - Kaggle](https://www.kaggle.com/c/walmart-recruiting-store-sales-forecasting) - Use historical markdown data to predict store sales.

31. [Rossmann Store Sales - Kaggle](https://www.kaggle.com/datasets/pratyushakar/rossmann-store-sales) - You are provided with historical sales data for 1,115 Rossmann stores. The task is to forecast the "...

32. [khatria/Corporacion-Favorita-Grocery-Sales-Forecasting-Kaggle](https://github.com/khatria/Corporacion-Favorita-Grocery-Sales-Forecasting-Kaggle/blob/master/Grocery_Sales_Forecasting_EDA.ipynb) - We are predicting future sales for a grocery store chain called 'Corporacion Favorita'. This is one ...

33. [KunalArora/kaggle-m5-forecasting - GitHub](https://github.com/KunalArora/kaggle-m5-forecasting) - M5 is the first M-competition to be held on Kaggle. Goal Teams have been challenged to predict sales...

34. [Forecasting Prediction Using LightGBM Model](https://www.kaggle.com/code/zhikchen/forecasting-prediction-using-lightgbm-model) - Explore and run machine learning code with Kaggle Notebooks | Using data from Store Item Demand Fore...

35. [ishritam/Walmart-Recruiting---Store-Sales-Forecasting - GitHub](https://github.com/ishritam/Walmart-Recruiting---Store-Sales-Forecasting) - My aim was to accurately forecast sales of Walmart as it is key for its ability to function. The dat...

36. [TeeNguyenDA/Store-Sales-Forecasting - GitHub](https://github.com/TeeNguyenDA/Store-Sales-Forecasting) - Use time series to predict daily sales for the Favorita grocery store in Ecuador. Data adapted from ...

