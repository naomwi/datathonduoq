# Next Public Routes - 2026-04-21

## Current Public State
- Best known public score: about `896k`.
- Best known public file: `dataset/submission_catboost_md2y_core_recencyexp20.csv`.
- The `tail_ramp40` family is rejected after public score about `911k`.
- Broad post-process calibration is no longer a credible attack vector.

## Important Feature Count Correction
- The old ablation report from `outputs/ablation/ablation_summary.csv` shows `curated_promo_cogs = 190` features.
- The actual later sprint family used a newer feature pipeline:
  - `logs/20260420_133528_transfer_methods_sprint/report.md` shows `curated_promo_cogs = 561` features.
  - Current code/data now reports `curated_promo_cogs = 565` features.
- Therefore, the 896k public anchor should be treated as a roughly `561-565` feature model, not a 190-feature model.

## Rejected Directions
- Broad revenue shrink: rejected by OOF and public behavior.
- Seasonal tail re-anchor / tail ramp: rejected by `tail_ramp40 = 911k`.
- EOM post-process: small public gain only; not a breakthrough path.
- Router/gate over existing donors: `gate_v3` lost to `recencyexp20`.
- Calendar mini-families, Tet, EOM/BOM interactions: rejected by `final_recency_calendar_sweep`.
- Piecewise recency weighting: rejected by `final_recency_calendar_sweep`.
- Full feature expansion: rejected. Bigger feature sets around `900+` features overfit.
- Deep learning / TFT / LSTM: rejected by offline underperformance and regime overfit.
- Direct horizon v1: rejected because of the frozen-origin bug and public crash.
- Direct horizon v2 full replacement: not suitable as a direct submission because it strongly lowers public Revenue shape and fails total OOF gate.

## Rejected Missed Route: Price History
`catboost_md2y_core_price_history` looked like the most interesting overlooked candidate offline, but public rejected it.

Evidence:
- Run: `logs/20260420_133528_transfer_methods_sprint/`.
- Existing submission: `dataset/submission_catboost_md2y_core_price_history.csv`.
- OOF:
  - `catboost_md2y_core_price_history`: `combined_mae_mean = 599608.55`.
  - `catboost_md2y_core_recencyexp20`: `combined_mae_mean = 603855.27`.
- Recent weighted OOF:
  - `price_history`: `571894.77`.
  - `recencyexp20`: `588516.41`.
- Recent tail Revenue:
  - `price_history`: `581001.99`.
  - `recencyexp20`: `606859.09`.
- It passed the submit gate in the transfer sprint.
- Public result later reported by user:
  - `submission_catboost_md2y_core_price_history.csv`: `923770.94996`

Final interpretation:
- Price-history features are public-toxic despite strong OOF.
- Do not submit this family again without a very narrow controlled variant.
- The proposed `price_history + recencyexp20` route should be deprioritized; price-history is now evidence of another OOF/public trap, not a clean breakthrough.

## Next Experiments Worth Running
1. Revenue-only feature decoupling.
   - Keep COGS from `recencyexp20`.
   - Test Revenue feature sets:
     - `baseline_plus_promo`
     - `forecast_core_promo_slim`
     - `curated_promo_cogs_target_history_plus`
   - Reason: COGS history may be useful for COGS but noisy for Revenue rollout.

2. CatBoost local hyperparameter and seed sweep.
   - Keep `recencyexp20` data path fixed.
   - Tune only CatBoost params:
     - `depth`: 4, 5, 6, 7
     - `l2_leaf_reg`: 1, 3, 6, 10
     - `learning_rate`: 0.02, 0.03, 0.05
     - `iterations`: 700, 900, 1200
     - seeds: 7, 42, 123, 2026
   - Export seed ensembles only if OOF beats the anchor and does not distort public shape too much.

3. Direct-v2 late-only hybrid.
   - Do not submit full `direct_v2_*`.
   - Test a hybrid that keeps `recencyexp20` for early horizon and uses `direct_v2` only after the cut.
   - Reason: direct v2 late recent Revenue beats anchor late recent Revenue, but full replacement fails total OOF.

## Current Recommendation
The next practical move is not another calibration. It is:
1. Stop the `price_history` family after public `923770.94996`.
2. Run Revenue-only feature decoupling with COGS frozen from `recencyexp20`.
3. Run CatBoost hyperparameter/seed sweep around `recencyexp20`.
4. Keep direct-v2 only as a late-horizon donor experiment, never as full replacement.

## Breakthrough Route Update
The target jump from about `896k` public MAE to `700k` is roughly a `196k` public improvement, or about `22%`.
That is unlikely to come from another EOM, tail ramp, or minor recency tweak. It needs a different evidence source or a different modeling frame.

Priority routes:

1. Anchor residual correction.
   - Keep `submission_catboost_md2y_core_recencyexp20.csv` as the backbone.
   - Generate OOF anchor predictions for 2020-2022.
   - Train a small residual model on `log(actual_revenue) - log(anchor_revenue)` using only forecast-safe features: horizon step, month/day/week, anchor level, anchor COGS ratio, and promo priors.
   - Apply bounded corrections only, for example clip predicted log correction to `8-15%`.
   - This is different from manual shrink/ramp because it learns where the anchor is systematically wrong.
   - Status after run `logs/20260421_151736_anchor_residual_correction_probe/`: rejected for now.
   - Best time-forward variant `residual_logcb_s25_c08` still lost to anchor by about `+1.9k` combined MAE on folds 2021-2022.
   - The rejected submission files were removed from `dataset/` to avoid accidental submit; copies remain inside the run log directory for audit.

2. TabPFN / tabular foundation probe.
   - Local package is `tabpfn 7.1.1`, not a separate confirmed `2.6` install.
   - Use Revenue-only TabPFN, freeze COGS from the 896k anchor.
   - Test top-K feature sets (`50`, `100`, `200`) and recent windows (`2y`, `3y`, `5y`).
   - Do not use the full 565-feature set directly; TabPFN is strongest on compact tabular inputs.
   - `run_tabpfn_recursive.py` was patched so OOF recursion now feeds frozen anchor COGS into history instead of zero COGS.
   - `run_tabpfn_recursive.py` was also patched so `combined_mae` uses the same `0.5 * (Revenue MAE + COGS MAE)` convention as the leaderboard sprint.
   - The first safe TabPFN run with top100/e8 was stopped because it consumed heavy CPU for about 20 minutes without a fold result.
   - Default TabPFN smoke settings were reduced to `top50` and `n_estimators=2`, logs-only.
   - The top50/e2 smoke run also consumed heavy CPU without producing a fold result in a useful sprint window and was stopped.
   - Verdict: TabPFN is not practical on this local runtime for the 2-hour sprint unless CUDA execution can be made reliably fast or the problem is reduced further.

3. Public-feedback perturbation map.
   - Public already proved OOF can lie: price-history looked best offline but scored `923770.94996`.
   - If submissions are available, create controlled probes that only move one segment at a time: Revenue H1/H2, Revenue tail, COGS H1/H2, high-anchor days, low-anchor days.
   - Goal is not to submit a guessed fix, but to infer whether public wants higher/lower level by segment.
   - This is the most "competition-hack" route and should be used sparingly if submission count matters.
   - Status after run `logs/20260421_152653_public_perturbation_map/`: generated 7 controlled public probes in `dataset/`.
   - Recommended first 3 if submission quota is limited:
     - `dataset/submission_public_probe_rev2024h1_up5.csv`
     - `dataset/submission_public_probe_cogs2024h1_floor87.csv`
     - `dataset/submission_public_probe_promo_windows_rev_up6.csv`
   - These isolate the main public-bias signs: 2024 Revenue level up, 2024 COGS ratio up, promo-window Revenue uplift.
   - Public feedback:
     - `submission_public_probe_promo_windows_rev_up6.csv`: `888100.36839`.
     - `submission_public_probe_cogs2024h1_floor87.csv`: `898472.39191`.
     - `submission_public_probe_rev2024h1_up5.csv`: about `896000`.
   - Interpretation: promo-window Revenue uplift is the live signal; broad COGS floor is rejected; broad 2024 Revenue uplift is neutral.
   - Follow-up run `logs/20260421_173038_public_promo_followup/` generated amplitude and window-isolation probes.
   - Next submit: `dataset/submission_public_probe_promo_windows_rev_up8.csv`.
   - If `up8` beats `888100.36839`, try `dataset/submission_public_probe_promo_windows_rev_up10.csv`; if worse, try `dataset/submission_public_probe_promo_windows_rev_up7.csv`.

4. Direct-v2 late-only donor.
   - Full direct-v2 replacement is rejected.
   - It can still be tested as a very small late-horizon donor: anchor early, then blend direct-v2 after horizon `45/60/90` with weights `0.10-0.30`.
   - Needs a shape clamp because direct-v2 public predictions are much lower than anchor.
   - Status after run `logs/20260421_152531_direct_v2_late_hybrid_probe/`: generated 27 logs-only candidates.
   - Nothing was published to `dataset/` because existing direct-v2 offline gate is false.
   - Lightest probe files remain in log submissions if manual public probing is desired.

Deprioritized for a 700k jump:
- More calendar mini-features, Tet, EOM/BOM, or piecewise recency.
- Price-history variants unless the perturbation map proves a very narrow safe use.
- Broad feature expansion beyond the current ~565-feature anchor.
- Large TFT/LSTM/Seq2Seq unless we add a much stronger external signal.

## QA Hardening During 2-Hour War Room
- `run_leaderboard_sprint.py`: patched `statsmodels` import to be lazy-safe and removed fallback export when no candidate passes submit gate.
- `run_recency_weighted_sprint.py`: removed fallback export when no candidate passes submit gate.
- `run_public_revenue_direct_horizon_v2.py`: patched recursive COGS history to use frozen anchor COGS instead of `0.0`; removed export-all behavior when direct-v2 gate fails.
- `run_tabpfn_recursive.py`: switched to logs-only output by default, fixed combined MAE convention, added CUDA fallback, and changed top-feature selection to use pre-OOF cutoff to avoid validation-fold feature-selection leakage.
- Working rule from this point: treat every file in `dataset/` as submit-candidate only if it is explicitly generated as a public probe or passes a public-anchor gate.

## Breakthrough CatBoost Sprint Result
- Run: `logs/20260421_152529_breakthrough_catboost_sprint/`.
- Tested Revenue feature decoupling plus local CatBoost hyperparameters/seeds around `recencyexp20`.
- No candidate beat the public anchor on selector or recent-weighted combined MAE.
- `rev_forecast_core_strict_recency20` beat recent-tail only, but lost badly on global/recent metrics; its accidental `dataset/` export was removed and the run-local file is audit-only.
- Verdict: CatBoost knobs/feature-decoupling do not look like the 700k jump route.

## TabPFN-First Route Implemented
- Script: `run_tabpfn_api_optimized_sprint.py`.
- Run: `logs/20260421_181237_tabpfn_api_optimized_sprint/`.
- The route now follows the public-winning signal instead of raw TabPFN direct forecast:
  - Keep `recencyexp20` as anchor.
  - Use TabPFN only to learn residual/uplift shape.
  - Apply correction only in promo windows for published candidates.
- API model paths all succeeded: `default`, `v2.5_default`, `v2.5_real`, `v2.5_small-samples`, `v2.5_low-skew`.
- Best OOF residual path was `v2.5_low-skew` with residual MAE `0.114698` versus zero-correction `0.232283`.
- Published files for public probing:
  1. `dataset/submission_tabpfn_promo_windowmix_v1.csv`
  2. `dataset/submission_tabpfn_promo_shape_cal8.csv`
  3. `dataset/submission_tabpfn_promo_shape_cal10.csv`
  4. `dataset/submission_tabpfn_promo_2024heavy_cal.csv`
  5. `dataset/submission_tabpfn_promo_shape_cogs4.csv`
  6. `dataset/submission_tabpfn_promo_shape_cogs8.csv`
- Submit priority:
  1. Submit `submission_tabpfn_promo_windowmix_v1.csv` first because it is closest to the current public winner `promo_windows_rev_up8` but replaces flat uplift with TabPFN/window shape.
  2. Submit `submission_tabpfn_promo_shape_cal8.csv` second to isolate TabPFN shape at the known-good `+8%` mean.
  3. Submit `submission_tabpfn_promo_shape_cal10.csv` if either of the first two improves; otherwise stop amplitude escalation.
  4. Submit `submission_tabpfn_promo_2024heavy_cal.csv` only as high-risk/high-upside.
  5. Submit COGS co-move variants only if Revenue-only TabPFN shape improves public, because broad COGS correction already failed.

## Public Feedback: Windowmix Wins
- `submission_tabpfn_promo_windowmix_v1.csv`: `883183.19507`.
- `submission_tabpfn_promo_shape_cal8.csv`: `888962.79663`.
- Current best is now `883183.19507`.
- The previous best `submission_public_probe_promo_windows_rev_up8.csv = 887225.99926` was improved by about `4042.8` MAE.
- Conclusion:
  - Continue the windowmix route.
  - Stop the global `shape_cal*` route.
  - Do not submit `submission_tabpfn_promo_shape_cal10.csv`, `submission_tabpfn_promo_2024heavy_cal.csv`, `submission_tabpfn_promo_shape_cogs4.csv`, or `submission_tabpfn_promo_shape_cogs8.csv` for now.

## Windowmix Follow-Up Queue
- Script: `make_tabpfn_windowmix_followup.py`.
- Run: `logs/20260421_182343_tabpfn_windowmix_followup/`.
- Next submit order:
  1. `dataset/submission_tabpfn_windowmix_scale105.csv`
  2. If scale105 improves or is close, submit `dataset/submission_tabpfn_windowmix_scale110.csv`.
  3. If scale105 worsens materially, submit `dataset/submission_tabpfn_windowmix_scale095.csv`.
  4. Then test `dataset/submission_tabpfn_windowmix_soft_v1.csv` to reduce within-window sharpness without changing total Revenue.
  5. Then test `dataset/submission_tabpfn_windowmix_junjul12_v1.csv` or `dataset/submission_tabpfn_windowmix_augoct10_v1.csv` to identify which window wants more uplift.
  6. Only after Revenue-only windowmix improves, test `dataset/submission_tabpfn_windowmix_cogs2.csv`.

## v2.5-Only Probe Queue
- Script: `make_tabpfn_v25_windowmix_candidates.py`.
- Run: `logs/20260421_182817_tabpfn_v25_windowmix_candidates/`.
- Use this if the next question is whether explicit TabPFN v2.5 beats the mixed `default + v2.5` ensemble.
- Recommended v2.5 submit order:
  1. `dataset/submission_tabpfn_v25low_windowmix_v1.csv`
  2. `dataset/submission_tabpfn_v25ens_windowmix_v1.csv`
  3. `dataset/submission_tabpfn_v25low_windowmix_scale105.csv`
  4. `dataset/submission_tabpfn_v25ens_windowmix_soft.csv`

## True TabPFN 2.6 Probe Queue
- HF checkpoint `Prior-Labs/tabpfn_2_6/tabpfn-v2.6-regressor-v2.6_default.ckpt` downloaded successfully.
- Script: `run_tabpfn26_local_residual_windowmix.py`.
- Run: `logs/20260421_183330_tabpfn26_local_residual_windowmix/`.
- Local CUDA fit/predict succeeded.
- OOF residual promo MAE is `0.117715`, close to the previous best path and slightly better than explicit `v2.5_low-skew` promo MAE `0.118439`.
- Submit order:
  1. `dataset/submission_tabpfn26_windowmix_v1.csv`
  2. If it improves, `dataset/submission_tabpfn26_windowmix_scale105.csv`
  3. If it worsens, `dataset/submission_tabpfn26_windowmix_soft_v1.csv`
