# Revised Breakthrough Strategy — Post-Tail-Ramp

> [!CAUTION]
> The `tail_ramp40` post-process calibration scored **911k** on the public leaderboard, losing to the `recencyexp20` anchor (**896k**). The hypothesis that "re-anchoring tail Revenue to seasonal shapes" is sufficient for a breakthrough is **rejected**. Calibration and post-processing approaches are exhausted.

## The State of Play

- **Best Public Anchor:** `submission_catboost_md2y_core_recencyexp20.csv` (~896k).
- **Failed Paths:** Broad shrinkage (0.80-0.90), structural static routing, purely seasonal tail blends, and late-horizon post-process ramping. 
- **The Core Issue:** A ~180k MAE gap still exists. Because simple post-processing at the tail failed, the error originates from *how the recursive model learns to rollout Revenue across horizons*, not just a scaling issue.

## Sole Attack Vector: Horizon-Binned Revenue Model (v1)

We will stop making post-hoc adjustments to one monolithic model's output. Instead, we will train separate models specialized for different parts of the forecast horizon.

**Thesis:** The relationship between features (especially recursive lags) and the target changes as the forecast horizon extends. A single model cannot optimally capture both short-term (days 1-30) dynamics and long-term (days 31-500) equilibrium.

### Implementation Spec: `revenue_horizon_v1`

1. **Target Routing:** 
   - Keep the `COGS` path entirely unchanged (locked to the public-winning `recencyexp20` outputs).
   - Only modify the `Revenue` pipeline.

2. **Horizon Bins (Simplest Version First):**
   - **Early Model (A):** Trained / applied for `horizon <= 30` days.
   - **Late Model (B):** Trained / applied for `horizon > 30` days.
   - *(Alternative: 3 bins if 2 is too rigid, e.g., 1-15, 16-60, >60, but let's start with 2).*

3. **Routing Mechanism:**
   - The router is deterministic based on the `forecast_step` (horizon) feature. No complex ML blending or margin gates.
   - If `step <= 30` -> Predict with Model A.
   - If `step > 30` -> Predict with Model B.

4. **Feature Governance (Strict):**
   - Use exactly the `catboost_md2y_core` / `recencyexp20` feature schema (`strict_core + promo_detail`).
   - Do **NOT** reopen geo, logistics, mix, traffic, inventory, or returns. They are confirmed noise/unstable.

5. **Training Approach:**
   - Both models retain the sample recency weighting that proved successful in `recencyexp20`.
   - The recursive engine must use Model A for the first 30 days to generate lags, and then seamlessly hand off to Model B for the remaining days.

### Expected Deliverables

- `train_revenue_horizon_model.py`: Modification or wrapper around recursive training to split model fitting.
- `make_public_revenue_horizon_challengers.py`: Generator script holding `COGS` constant, using the early/late Revenue models.
- **Success Criteria:** The OOF combined MAE must beat `recencyexp20`'s `603855.27`, particularly measured on the **far horizon (tail)** of the recent folds (2021-2022).
