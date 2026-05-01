# Updated Requirement Diff - 2026-04-22

Files compared:

- `requirements/Đề thi Vòng 1.pdf`
- `requirements/Đề thi Vòng 1_updated.pdf`

Observed text differences:

1. `order_items.unit_price`
   - Old: `Đơn giá sau khi áp dụng khuyến mãi`
   - Updated: `Đơn giá`

2. Multiple-choice Q1 option C
   - Old: `180 ngày`
   - Updated: `144 ngày`

Modeling implications:

- The forecast target window is unchanged: `sales_test.csv` covers `01/01/2023` to `01/07/2024`.
- Scoring section is unchanged.
- The update does not reveal hidden public/private split details or new future covariates.
- Training data still confirms the target identity:
  - `Revenue = sum(quantity * unit_price)` exactly.
  - `COGS = sum(quantity * products.cogs)` up to rounding.
- Do not redefine Revenue as `quantity * unit_price - discount_amount`; that mismatches `sales.csv` by roughly `195,567` MAE per day on train.
- `discount_amount` remains useful as a promo-intensity feature, but it is not subtracted again from the Revenue target.

Leaderboard implications:

- `submission_h2rev_v15_current_h2_rev_up050.csv = 800572.16096`, worse than current best `797595.96410`; broad 2023H2 Revenue scale is near the optimum.
- `submission_h2shape_v16_cogs_oddmean_preserve.csv = 802116.33879`; odd-year COGS monthly shape is rejected.
- `submission_h2antishape_v17_cogs_antiodd025_preserve.csv = 800578.87166`; reverse COGS monthly shape is also rejected.
- Next high-leverage probe should move to 2023H2 Revenue monthly shape while preserving total 2023H2 Revenue.
