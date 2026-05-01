# Consultant Handoff - 2026-04-19

## 1. Executive Summary

This memo summarizes the current Datathon forecasting effort after the latest leaderboard sprint.

Current bottom line:

- The team now has a materially better public leaderboard anchor.
- The new best confirmed public result is approximately `921k MAE` from `dataset/submission_catboost_md2y_core.csv`.
- The previous best public anchor was approximately `983k MAE` from `dataset/submission_system_promo_plus_cogs_md2y.csv`.
- This confirms that the current winning direction is:
  - tree-based tabular forecasting
  - forecast-core features first
  - MAE-first model selection for public probing
  - narrow challenger generation around the best anchor

Current recommendation:

- Use `catboost_md2y_core` as the new anchor.
- Avoid broad sweeps.
- Test only a small number of near-anchor challengers.
- In parallel, begin formalizing `forecast_core` vs `analysis_rich` for the consultant-recommended long-horizon framing.
- That formalization has now started via a dedicated feature availability matrix.
- The first seasonal-enhanced challenger has now been built and is the strongest offline candidate under the recent-aware selector, but it is not yet public-confirmed.

## 2. Competition Facts and Constraints

### Organizer clarifications already available

The team currently has the following clarifications from the organizers:

1. The current Kaggle/public leaderboard is based on `MAE` only and is not the final official leaderboard.
2. Submit limit is now `4 submissions/day/team`.
3. Kaggle/public test is only the public round and only one part of the total competition score.

### What the requirement documents say

From local requirement extraction:

- The task wording says the problem is to forecast `Revenue`.
- Submission format still requires `Date, Revenue, COGS`.
- Evaluation section mentions `MAE`, `RMSE`, and `R2`.
- External data is forbidden.
- Using test `Revenue` or `COGS` as features is forbidden.

### Remaining ambiguity

One ambiguity is still unresolved:

- It is still not fully confirmed whether public `MAE` is computed on `Revenue` only or on both `Revenue + COGS`.

Working assumption used in the latest sprint:

- optimize public work as `MAE-first`
- treat the modeling target as `Revenue-first, COGS-stable`

This is an inference, not a fully organizer-confirmed fact.

## 3. Research and Consultant Synthesis

### What the research supports

The recent similar-competition research strongly supports:

- daily feature mart construction
- tree-based tabular models first
- lag, rolling, calendar, and promo features
- strict time-based validation
- ensemble/blending only after strong single-model baselines exist

### What the consultant added

The consultant critique materially changed the framing in four ways:

1. This is not only a forecasting competition.
2. The forecast horizon is unusually long.
3. Future feature availability matters more than in standard retail Kaggle setups.
4. Explainability, leakage control, reproducibility, and report readiness are part of the real objective.

### Current strategic framing

The current working framing is:

- short term: achieve a stronger public leaderboard anchor
- medium term: convert the pipeline into a consultant-acceptable long-horizon setup
- long term: align forecasting, analysis, SHAP/explainability, and report storytelling in one coherent pipeline

In practical terms:

- `leaderboard sprint` first
- but without ignoring long-horizon feature availability constraints

## 4. Code and Pipeline Work Completed

### 4.1 Feature engineering changes

The repository has already been extended with a narrow `geo/logistics/cohort` branch:

- customer signup counts and channel shares
- order region shares
- shipment timing features
- shipping fee aggregates
- fast/slow delivery ratios

Main code areas updated:

- `feature_pipeline.py`
- `run_ablation.py`
- `train_recursive_forecast.py`

### 4.2 Recursive forecasting engine upgrades

The recursive forecasting pipeline now supports:

- multiple model families:
  - XGBoost
  - LightGBM
  - CatBoost
- promo future policy controls
- context future policy controls
- context-history feature generation during recursive forecasting

### 4.3 New leaderboard sprint harness

A dedicated sprint script was created:

- `run_leaderboard_sprint.py`

This script was used to compare:

- classical/seasonal baselines
- XGBoost core
- XGBoost context
- LightGBM core/context
- CatBoost core/context
- CatBoost medium-window core
- CatBoost recent-window core
- CatBoost core + seasonal tail blend

### 4.4 Forecast-core governance artifact

A dedicated feature availability document now exists:

- `research/forecast_core_feature_availability_matrix_2026-04-19.md`

Its role is to lock the current rule that `forecast_core` should only include features that are:

- known in the future, or
- inferable in the future with a clear, reproducible rule

This governance has now also started to move into code:

- `feature_pipeline.py` now exposes feature-group policy metadata
- `run_ablation.py` now exposes a `forecast_core_strict` experiment
- `run_leaderboard_sprint.py` now includes a `catboost_core_strict` candidate

## 5. Offline Leaderboard Sprint Results

The latest offline sprint ranking on the annual rolling proxy is:

| Rank | Candidate | Revenue MAE mean | Notes |
| --- | --- | ---: | --- |
| 1 | `catboost_md2y_medium_core` | `632,130.28` | slightly better MAE mean, but mainly from the older fold |
| 2 | `catboost_md2y_core` | `632,835.25` | strongest all-around CatBoost anchor and best confirmed online result |
| 3 | `catboost_md2y_recent_core` | `678,546.18` | better than the LightGBM challengers, but below the CatBoost anchor |
| 4 | `lightgbm_md2y_context` | `682,622.91` | context helps slightly |
| 5 | `lightgbm_md2y_core` | `682,777.16` | nearly tied with context |
| 6 | `catboost_md2y_context` | `685,562.78` | worse than CatBoost core |
| 7 | `xgb_md2y_context` | `737,851.72` | beats XGB core |
| 8 | `xgb_md2y_core` | `751,512.44` | prior strong XGB anchor |
| 9 | `baseline_seasonal_md2y` | `891,269.98` | best classical sanity baseline |
| 10 | `catboost_core_strict` | `663,288.87` | first strict-core pass underperforms the current CatBoost anchor |

Interpretation:

- CatBoost clearly outperformed the rest on the current annual proxy.
- Context features help XGBoost.
- Context features help LightGBM only marginally.
- Context features currently hurt CatBoost relative to CatBoost core.
- Medium-window CatBoost slightly improves mean MAE, but loses to the long-history anchor on the more recent annual folds and on RMSE/R2.
- Recent-window CatBoost does not currently justify leaderboard probing.
- The first strict-core CatBoost pass does not beat the anchor; this means feature governance is still necessary, but the initial strict-core cut should not replace the current anchor.

### Seasonal-enhanced challenger result

After implementing a narrow seasonal repair challenger:

- `catboost_md2y_core_seasonal_tail_blend`

The current result on the recent-aware selector is:

- Revenue MAE mean: `627,825.36`
- Recent-weighted revenue MAE: `604,721.41`
- Recent-tail revenue MAE: `581,617.46`

Compared with `catboost_md2y_core`:

- It improves mean MAE.
- It improves recent-weighted MAE.
- It improves recent-tail MAE.
- It improves RMSE, R2, and COGS breadth overall.
- It passes the current submit gate.

Interpretation:

- This is the first structural challenger that clearly beats the current offline CatBoost anchor under the new selector.
- It should be treated as the next public probe candidate.

Key log artifacts:

- `logs/20260419_201155_leaderboard_sprint/summary.csv`
- `logs/20260419_201218_leaderboard_sprint/summary.csv`
- `logs/20260419_201810_leaderboard_sprint/summary.csv`
- `logs/20260419_202520_leaderboard_sprint/summary.csv`
- `logs/20260419_203131_leaderboard_sprint/summary.csv`
- `logs/20260419_204043_leaderboard_sprint/summary.csv`
- `logs/20260419_211140_leaderboard_sprint/summary.csv`
- `logs/20260419_215551_leaderboard_sprint/summary.csv`
- `logs/20260419_232106_leaderboard_sprint/summary.csv`

## 6. Public Leaderboard Results

### Earlier public anchors

Previously reported public scores:

- `dataset/submission_system_promo_plus_cogs_md2y.csv` -> approximately `983k`
- `dataset/submission_system_promo_plus_cogs_md2y_revenue_switch.csv` -> approximately `986k`
- `dataset/submission_blend_s2_5f22134209_s2_ebda31697a_50.csv` -> approximately `1.03M`

### New public result

The latest user-reported public result is:

- `dataset/submission_catboost_md2y_core.csv` -> approximately `921k`

Interpretation:

- The new CatBoost anchor improves public MAE by roughly `62k` versus the previous best known anchor.
- This is the first strong confirmation that the current offline sprint is also transferring online.
- The project should now treat `catboost_md2y_core` as the active production anchor.

### Subsequent public probes

Three narrow public probes were then tested:

- `dataset/submission_catboost_md2y_core_seasonal_tail_blend.csv` -> `940,344.88119`
- `dataset/submission_blend_catboost_core_lightgbm_context_70_30.csv` -> `918,247.11708`
- `dataset/submission_lightgbm_md2y_context.csv` -> `974,456.24438`

Interpretation:

- The seasonal tail blend was an offline false positive and should not become a main workstream.
- LightGBM context as a standalone challenger does not transfer and is too weak to serve as an anchor.
- The 70/30 CatBoost + LightGBM-context blend is now the best confirmed public result and should be treated as the public submission anchor.
- CatBoost core should still be retained as the structural modeling anchor, because the blend result implies that LightGBM context contributes useful diversity, not a stronger standalone signal.

## 7. Current Artifacts Worth Tracking

### Main anchor

- Public submission anchor:
  - `dataset/submission_blend_catboost_core_lightgbm_context_70_30.csv`

- Structural modeling anchor:
  - `dataset/submission_catboost_md2y_core.csv`

### Strong challengers

- `dataset/submission_catboost_md2y_core_seasonal_tail_blend.csv`
- `dataset/submission_lightgbm_md2y_context.csv`
- `dataset/submission_lightgbm_md2y_core.csv`
- `dataset/submission_catboost_md2y_context.csv`
- `dataset/submission_catboost_md2y_medium_core.csv`
- `dataset/submission_catboost_md2y_recent_core.csv`
- `dataset/submission_xgb_md2y_context.csv`

### Blend challengers already created

- `dataset/submission_blend_catboost_core_lightgbm_context_70_30.csv`
- `dataset/submission_blend_catboost_core_lightgbm_context_50.csv`

## 8. Current Interpretation

What now appears to be true:

1. Tree-based tabular models are the correct backbone.
2. Public probing should remain `MAE-first`.
3. CatBoost is currently the best-performing model family on this setup.
4. The old broad-sweep strategy is no longer justified.
5. The team should not treat all context/business features as universally helpful.
6. The consultant was correct that feature-family validity and long-horizon discipline still matter, even while prioritizing leaderboard progress.
7. The first regime/window test suggests that medium-window training is interesting for offline analysis, but not yet strong enough to displace the online CatBoost anchor.
8. The first seasonal repair test is materially more promising than the medium-window or strict-core challengers and is currently the best candidate to test for a new public step-change.
9. Public evidence now overrides that seasonal optimism: the seasonal tail blend did not transfer online.
10. The best current public result comes from constrained model diversity around CatBoost, not from replacing CatBoost as the core model.
11. The first `core_plus` search shows that `promo_detail` is the only family worth reintroducing into CatBoost, and that the resulting `core_plus` collapses back to the current `catboost_md2y_core` schema.

## 9. Recommended Next Steps

### 9.1 Immediate leaderboard plan

Use only near-anchor challengers. Recommended submit order:

1. `dataset/submission_blend_catboost_core_lightgbm_context_70_30.csv`  
   Status: best confirmed public result at `918,247.11708`.
2. `dataset/submission_catboost_md2y_core.csv`  
   Status: best single-model public anchor around `921k`.
3. `dataset/submission_blend_catboost_core_lightgbm_context_50.csv`  
   Rationale: nearby diversity probe if additional quota is available.

Currently deprioritized for public probing:

- `dataset/submission_catboost_md2y_core_seasonal_tail_blend.csv`
- `dataset/submission_lightgbm_md2y_context.csv`

Current note on window challengers:

- `catboost_md2y_medium_core` is worth keeping as an offline challenger, but not yet the default next public submission because its gain comes mostly from the oldest fold rather than the near-end folds.
- `catboost_md2y_recent_core` is currently below threshold for public probing.

### 9.2 Next modeling workstream

After the current narrow public probing cycle, the next technical priorities should be:

1. Build a formal `feature availability matrix`.
2. Split the pipeline into:
   - `forecast_core`
   - `analysis_rich`
3. Standardize rolling backtests that report:
   - `MAE`
   - `RMSE`
   - `R2`
4. Prepare explainability assets earlier:
   - grouped feature importance
   - SHAP summaries
   - business-readable narratives

### 9.3 Core-plus search result

A dedicated `CatBoost core_plus` search was run with this policy:

- governance base: `forecast_core_strict`
- reintroduce families one at a time
- keep a family only if it improves recent metrics without failing breadth or stability

Families tested:

- `promo_detail`
- `geo_logistics`
- `mix_light`

Result:

- `promo_detail` passed
- `geo_logistics` failed
- `mix_light` failed

Most important implication:

- `forecast_core_strict + promo_detail` reproduces the current `catboost_md2y_core`
- therefore the current CatBoost anchor is already the practical `core_plus`
- no evidence currently supports reintroducing geo/logistics or light mix signals into CatBoost

### 9.3 Report and consultant-facing workstream

The project should start preparing a consultant/report-ready structure now, not after leaderboard work ends:

- leakage checklist
- reproducibility checklist
- model selection rationale
- business signal interpretation
- horizon and feature availability assumptions

## 10. Kill List

The following should remain de-prioritized for now:

- broad parameter sweeps
- deep learning as a primary workstream
- heavy hierarchical machinery
- large ensembles before single-model anchors stabilize
- using future-unavailable covariates directly in forecast-time modeling

## 11. Open Questions and Risks

1. Public metric ambiguity still exists around `Revenue` vs `Revenue + COGS`.
2. Final leaderboard will not be identical to the public one.
3. Long-horizon feature validity is still not fully formalized in code.
   Update: the formalization document now exists, but the repo is not yet fully split into separate `forecast_core` and `analysis_rich` pipelines.
4. The current annual offline proxy may still mismatch the final hidden regime.
5. CatBoost is currently the best anchor, but the team still needs a consultant-safe story for why that model is valid under long-horizon constraints.

## 12. Suggested Consultant Ask

If this memo is sent to a consultant for review, the most useful feedback would be:

1. Validate the current short-term submit order.
2. Review whether `catboost_md2y_core` is the right anchor despite the unresolved metric ambiguity.
3. Challenge the proposed `forecast_core` vs `analysis_rich` split.
4. Help rank the next feature families by expected ROI under long-horizon constraints.
5. Recommend the minimum explainability/report package that should be built in parallel with leaderboard work.
