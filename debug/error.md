# Breakthrough Strategy: 200k+ MAE Reduction

## Root Cause Diagnosis

The current best submission (`revenue_router_v1_clip`, public MAE ~902k) has a **massive systematic positive bias**:

| Metric | Value |
|--------|-------|
| Mean bias (pred − true) | **+682,518** |
| Median bias | **+614,684** |
| Days over-predicted | **500 / 548 (91%)** |
| Revenue MAE | 747,764 |
| COGS MAE | 640,183 |

**Why this happens:** The model is trained on 2012–2022 data. Revenue peaked during 2016–2018 (mean ~5.5M/day). The test period (2023–2024) resembles the declining 2021–2022 era (mean ~3.0M/day), but the model's learned mean is inflated by the high-revenue historical years. The recursive forecasting pipeline inherits this positive bias.

**Biggest error concentrations:**

| Dimension | Worst segment | MAE |
|-----------|--------------|-----|
| Month | March | 1,363,754 |
| Month | November | 1,062,335 |
| Days-to-EOM | 0 (last day) | 1,146,377 |
| Days-to-EOM | 2 (3rd from last) | 1,224,031 |

## Proposed Changes (3 Attack Vectors)

### Vector 1: Systematic Debias Post-Processing (Quick Win — est. 100–200k MAE reduction)

Since 91% of predictions are too high with mean bias ~682k, a calibrated post-processing step can recover most of this.

#### Approach
1. Compute the bias from OOF predictions on the 2022 fold (the most test-representative fold).
2. Apply a **multiplicative shrinkage** factor to Revenue predictions: `Revenue_adj = Revenue_pred × shrink_factor`, where `shrink_factor ≈ true_mean / pred_mean` computed from 2022 OOF.
3. Test multiple shrinkage levels: 0.80, 0.82, 0.85, 0.88, 0.90 on the existing submission.

#### [NEW] `debias_submission.py`
- Load existing best submission + sample_submission.
- Apply shrink factor to Revenue column.
- Keep COGS unchanged (or apply a separate COGS shrink).
- Generate submission variants.

> [!IMPORTANT]
> This is a zero-training-cost improvement. It can be tested within 1 minute and submitted immediately.

---

### Vector 2: Train-Window Restriction (Medium Effort — est. 50–150k MAE)

The current pipeline trains on 2012–2022. The high-Revenue years 2014-2018 dominate the learned function and inflate predictions.

#### Approach
1. Restrict training window to **2019-01-01 → 2022-12-31** (4 years) or even **2020-01-01 → 2022-12-31** (3 years).
2. This removes the high-Revenue historical period that causes the upward bias.
3. Retrain `catboost_md2y_core` with restricted window and compare offline + public.

#### [MODIFY] [train_recursive_forecast.py](file:///c:/Users/admin/Documents/Project/datathon/train_recursive_forecast.py)
- Add a `train_start_date` parameter.
- Filter training data before feature matrix assembly.

---

### Vector 3: Year-Aware Trend Feature (Medium Effort — est. 50–100k MAE)

The business has a strong downward Revenue trend since 2018. The model needs an explicit signal for this.

#### Approach
1. Add an **annual Revenue trend index**: ratio of recent 365-day rolling Revenue mean to the all-time peak.
2. Add a **year-over-year Revenue growth rate** feature.
3. These let the tree model explicitly learn the declining trend rather than averaging over all historical levels.

#### [MODIFY] [feature_pipeline.py](file:///c:/Users/admin/Documents/Project/datathon/feature_pipeline.py)
- Add `revenue_trend_index` feature in [build_daily_base()](file:///c:/Users/admin/Documents/Project/datathon/feature_pipeline.py#407-825).
- Add `revenue_yoy_growth` feature.

---

## Priority Order

| Priority | Vector | Est. Impact | Effort | Risk |
|----------|--------|-------------|--------|------|
| **1** | Debias post-processing | 100–200k | 10 min | Very low |
| **2** | Train-window restriction | 50–150k | 30 min | Low |
| **3** | Year-aware trend feature | 50–100k | 1 hour | Medium |

> [!CAUTION]
> Vector 1 alone could take public MAE from 902k → ~700–750k. Combined with Vector 2, the target of <700k is realistic.

## Verification Plan

### Automated Tests
1. **Debias script sanity check:**
   ```
   python debias_submission.py
   # Verify output files exist and Revenue values decreased
   ```
2. **Offline backtest comparison:**
   ```
   python run_leaderboard_sprint.py  # with modified train window
   # Compare fold 3 (2022) MAE: should be materially lower
   ```

### Manual Verification
1. Submit top debias variant to Kaggle public leaderboard.
2. User confirms public MAE score and reports back.
3. If debias alone achieves <750k, proceed to Vector 2 for further gains.
