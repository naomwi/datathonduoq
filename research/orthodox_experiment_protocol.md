# Orthodox Experiment Protocol

## Understanding Summary
- We are improving a retail revenue forecasting pipeline for a competition with hidden future targets.
- The current feature gate winner from orthodox ablation is `calendar + revenue_history + promo`.
- Recursive backtest is the closer proxy to the competition, but it is noisier and worse for clean attribution.
- New changes must be tested one at a time so we can tell what actually improved the model.
- Logs must be preserved under `logs/` so every experiment is auditable later.
- The next candidate change is `predicted_order_count` as a stage-1 forecasted driver for the revenue model.

## Assumptions
- `MAE` remains the primary ranking metric for both one-step and recursive checks.
- A change that fails the one-step gate should not advance to recursive A/B.
- Stage-1 generated features must be compared with a row-matched control to avoid unfair train-set differences.

## Decision Log
- Decision: adopt a two-gate workflow.
  Alternatives considered: `one-step only`, `recursive only`.
  Why chosen: it preserves clean attribution first, then validates usefulness in the competition-like regime.
- Decision: add exactly one change per experiment.
  Alternatives considered: grouped feature additions.
  Why chosen: grouped changes make attribution weak and break orthodox ablation discipline.
- Decision: store every run in `logs/<timestamp>_<experiment_name>`.
  Alternatives considered: overwrite latest outputs.
  Why chosen: timestamped logs make results reproducible and auditable.

## Official Workflow
1. Start from the current accepted control system.
2. Add one change only.
3. Run `one-step orthodox` A/B and log all artifacts.
4. Advance to `recursive A/B` only if the challenger beats control on the one-step gate.
5. Accept the change only after both gates pass.
