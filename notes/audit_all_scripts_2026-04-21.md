# Audit: Toàn bộ Script (2026-04-21)

## Tổng kết nhanh

| Script | Verdict | Ghi chú |
|--------|---------|---------|
| `train_recursive_forecast.py` | ✅ OK | Engine chính. Logic recursive, weight, COGS postprocess đều đúng. |
| `feature_pipeline.py` | ✅ OK | Calendar, promo, context features xây dựng đúng. Mini-families isolated đúng. |
| `build_feature_store.py` | ✅ OK | Pipeline build store đúng thứ tự: calendar → target history → exogenous. |
| `run_recency_weighted_sprint.py` | ✅ OK | Sinh ra submission 896k. Gọi đúng `recursive_forecast` qua `evaluate_candidate`. |
| `run_leaderboard_sprint.py` | ✅ OK | Baseline + model candidates. Gating logic và export submission đúng. |
| `run_catboost_core_plus.py` | ✅ OK | Family ablation (promo_detail, geo, mix_light). Logic pass/fail gate đúng. |
| `run_five_hour_sweep.py` | ✅ OK | Stage 1/2 sweep + blend. Sử dụng đúng `recursive_forecast`. |
| `run_cogs_postprocess_ablation.py` | ✅ OK | COGS variant testing (blend, clip, ratio). Logic one-step và recursive đúng. |
| `run_seq2seq_sprint.py` | ⚠️ Minor | Encoder-Decoder LSTM. Chạy được nhưng không competitive do under-parameterized (hidden=256, 2 layers). Không có bug logic. |
| `run_final_recency_calendar_sweep.py` | ⚠️ Bug | COGS=0.0 dummy → 66 COGS features bị corrupt. **Ranking vẫn đúng** vì bug ảnh hưởng đều. |
| **`run_public_revenue_direct_horizon_v1.py`** | ❌ **BUG NGHIÊM TRỌNG** | **Frozen Origin Features** — xem chi tiết bên dưới. |

---

## Bug Nghiêm Trọng: `run_public_revenue_direct_horizon_v1.py`

### Nguyên nhân submission crash (1.11M / 1.19M Public MAE)

**Dòng 139:**
```python
origin_row = feature_store.set_index("Date").loc[train_end_date:train_end_date, origin_cols].copy()
```

**Dòng 144-145:**
```python
for c in origin_cols:
    infer_df[c] = origin_row[c].values[0]
```

### Vấn đề
Tất cả `origin_cols` (bao gồm `rev_lag_1`, `rev_rollmean_7`, `cogs_ewm_14`... — hàng trăm lag/rolling features) bị **đóng băng tại giá trị của ngày cutoff duy nhất** và dùng nguyên cho toàn bộ 365 ngày forecast.

Tức là ở ngày forecast thứ 300, mô hình vẫn "nhìn thấy" `rev_lag_1` = Revenue của ngày cutoff, chứ không phải Revenue ngày hôm trước.

### So sánh với recursive forecast (đúng)
Trong `train_recursive_forecast.py`, `build_feature_row()` được gọi **cho MỖI NGÀY** forecast, và `history` DataFrame được cập nhật bằng giá trị predicted → lags luôn tươi.

### Hậu quả
- Mô hình Direct nhận được features hoàn toàn sai cho mọi horizon > 1.
- `forecast_step` feature thậm chí không đủ mạnh để bù lại sai lệch hàng trăm cột origin bị freeze.
- Đây là lý do chính submission 1.11M và 1.19M thất bại nặng, **KHÔNG PHẢI** do kiến trúc Direct Horizon yếu bản chất.

### Fix (nếu muốn thử lại)
Cần build lại origin features cho từng ngày forecast, hoặc chuyển sang kiến trúc Factored Direct (origin features tại t, future features tại t+h, nhưng origin cập nhật bằng predicted values qua recursive loop).

---

## Các Script Không Audit (ít quan trọng)
Các script sau là các nhánh phụ hoặc EDA, không tạo public submission nên không audit sâu:
- `run_ablation.py`, `run_anchor_hierarchy_sprint.py`, `run_bottomup_*.py`
- `run_eda.py`, `run_feature_pruning_sprint.py`
- `run_long_horizon_selection.py`, `run_orthodox_ablation.py`
- `run_public_revenue_gate_v2.py`, `run_public_revenue_gate_v3.py`
- `run_public_revenue_horizon_v1/v2.py`, `run_public_revenue_router_v1.py`
- `run_revenue_family_screen.py`, `run_stage1_ordercount_ablation.py`
- `run_target_seasonal_prior_sprint.py`, `run_transfer_methods_sprint.py`
- `run_cogs_history_conflict_analysis.py`, `run_cogs_rate_protocol.py`
