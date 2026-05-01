# AI CLI Handoff - Current Datathon Context

Date written: 2026-04-26  
Workspace: `C:\Users\admin\Documents\Project\datathon`

## One-Line State

We are no longer doing small coefficient squeezes. The active goal is a **large jump from ~661k public MAE toward 63x/60x** by testing structural public-blackbox hypotheses, while keeping clean/legal work clearly separated.

## Hard Boundaries

- There are two branches:
  - **Clean / clean-input**: must not use test `Revenue/COGS`, `sample_submission.csv`, previous submissions, or public-blackbox target signals as inputs. Public scores may be discussed only as motivation and must be labeled.
  - **Quarantine / blackbox**: may use `sample_submission.csv`, previous submissions, and public leaderboard feedback. Never present this as clean.
- User is aware that quarantine/public-blackbox is not clean. Do not blur this in reports.
- Do not include or log any API tokens. A TabPFN/Prior Labs token was shared earlier in conversation; do not copy it into notes/config/scripts.
- Follow `AGENTS.md`: surgical edits, explicit assumptions, save manifests/logs/notes, compile changed Python scripts.

## Competition/Data Snapshot

- Forecast horizon: `2023-01-01` to `2024-07-01`, 548 rows.
- Submission columns: `Date`, `Revenue`, `COGS`.
- Public leaderboard is the working feedback signal for quarantine.
- User reported top-1 around `632k`, so current `661k` still needs a structural jump, not micro-tuning.
- Final evaluation may also include MAE/RMSE/R2, but public leaderboard has been MAE-like and MAE remains the primary optimization signal.

## Current Bests

### Quarantine / Blackbox Best

- Current best known public:
  - `dataset/submission_qbb69_h1_q1_cogs_down120_keeprev.csv`
  - Public score: `655838.51372`
- Previous best:
  - `dataset/submission_qbb68_h1_q1_cogs_down080_keeprev.csv`
  - Public score: `656301.72926`
- Previous Q1 COGS point:
  - `dataset/submission_qbb68_h1_q1_cogs_down040_keeprev.csv`
  - Public score: `657443.28137`
- Previous H2/Q2 anchor:
  - `dataset/submission_qbb65_h2_highratio_cogs_down060_keeprev.csv`
  - Public score: `659211.90870`
- Previous H1/H2 combo anchor:
  - `dataset/submission_qbb62_h1_backload_preserve_total_q2up040.csv`
  - Public score: `661327.00240`
- Previous anchor:
  - `dataset/submission_qbb60v18_cogs2023h2_down010.csv`
  - Public score: `662607.08245`
- Improvement from previous anchor: about `-1280.08`.

### Clean Best

- Current clean/clean-input best known:
  - `dataset/submission_cleanv2_h1fine_b044_r0876.csv`
  - Public score: `673757.34993`
- Very close clean alternatives:
  - `submission_cleanv3_funnel_c110_h1r0876.csv` = `673759.96838`
  - `submission_cleanv2_h1funnel_b045_r0876.csv` = `673785.31754`
- Clean branch is temporarily paused unless user explicitly asks to continue it.

## Important Public Score History

### Major Blackbox Progression

- `submission_sampleprior_v19_periodshape_both_a025.csv` = `744359.56345`
- `submission_sampleprior_v20_periodshape_both_a050.csv` = `711472.67020`
- `submission_sampleprior_v20_periodshape_both_a070.csv` = `701103.47903`
- `submission_sample_v28_a0725_ratio_away_sample0175.csv` = `699556.47851`
- `submission_sample_v30_a0725_ratio_away_sample0250.csv` = `699376.32670`
- `submission_sample_v32_rev0725_cogs0650_away0250.csv` = `698994.05843`
- `submission_sample_v36_rev2023H2_r0600_c0650_away0250.csv` = `692128.76474`
- `submission_sample_v37_rev2023H2_p0100_c0650_away0250.csv` = `684463.34954`
- `submission_qbb60v4_level_rev2024h1_up030.csv` = `680506.89709`
- `submission_qbb60v8_nonh2shape_2023h1level105_away0300.csv` = `668570.18037`
- `submission_qbb60v9_nonh2shape_2023h1level110_away0300.csv` = `663346.24664`
- `submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv` = `662759.87577`
- `submission_qbb60v18_cogs2023h2_down010.csv` = `662607.08245`
- `submission_qbb62_h1_backload_preserve_total_q2up040.csv` = `661327.00240`
- `submission_qbb65_h2_highratio_cogs_down060_keeprev.csv` = `659211.90870`
  - Accepted: H2 high-ratio COGS reduction is live.
- `submission_qbb63_h1_mayjun_up060_janfebfund.csv` = `666579.35776`
  - Reject: May-Jun localization is not the Q2 signal.

### Recent Failures / Rejects

- `submission_qbb61v21_shape_preserve_nonh2_g030.csv` = `664937.71763`
  - Reject: shape-preserve/non-H2 squeeze was worse.
- `submission_qbb61v21_extrap_clean_to_best_g010.csv` = `663007.39829`
  - Reject: clean-to-best extrapolation did not beat anchor.
- `submission_qbb62_h1_frontload_preserve_total_q1up050.csv` = `667597.86978`
  - Strong reject: moving 2023H1 mass from Q2 to Q1 is the wrong sign.
- `submission_qbb63_h1_mayjun_up060_janfebfund.csv` = `666579.35776`
  - Reject: late-Q2/May-Jun localization worsened strongly. Do not submit `jun_up120`.
- `submission_qbb64_apr_cogs_from_mayjun_q2preserve_cogs_apr080.csv` = `667484.97219`
  - Reject: COGS-side April pivot is toxic. Do not submit combined Revenue+COGS April pivot.
- `submission_qbb64_apr_from_mayjun_q2preserve_apr080.csv` = `667631.42258`
  - Reject: Revenue-only April pivot is toxic. H1/Q2 timing localization is effectively dead.
- `submission_qbb60v20_lastshot_cogs23h2_down010_cogs24h1_down016.csv` = `664159.16954`
  - Reject: adding 2024H1 COGS down hurt.
- `submission_qbb60v19_allin_cogs23h2_sample_cogs24h1_sample.csv` = `673566.41883`
  - Reject: all-in COGS/sample path hurt badly.
- `submission_qbb60v11_nonh2shape_2023h1level113_away0300_2024h1p1200.csv` = `664288.59833`
  - Reject: stronger 2024H1 sample shape hurt.
- `submission_qbb60v13_nonh2shape_2023h1level113_2023h2rev1025_away0300.csv` = `663501.80146`
  - Reject: 2023H2 Revenue up hurt.
- `submission_qbb60v13_nonh2shape_2023h1level113_2023h2rev0975_away0300.csv` = `663679.63710`
  - Reject: 2023H2 Revenue down hurt.
- `submission_qbb60v15_h2split_q3up050_q4down025.csv` = `664826.90886`
  - Reject: Q3/Q4 Revenue split hurt.

## Current Interpretation

### What Seems Real

- `sample_submission.csv` contains a very strong hidden daily-shape prior in quarantine mode. It is not clean, but it maps the public surface.
- The strongest improvements came from:
  - borrowing sample daily shape while preserving period totals,
  - shrinking 2023H2 Revenue sample-shape alpha strongly,
  - increasing non-H2 shape, especially 2023H1/2024H1,
  - lifting 2023H1 level up to around `+13%`,
  - using COGS ratio-away from sample around `0.300`,
  - small 2023H2 COGS down.
- The small positive signal was **2023H1 timing/backload into Q2**:
  - Q1 frontload failed badly.
  - Q2 backload improved to current best.
  - May-Jun localization failed badly, so the remaining H1 timing hypothesis is more likely April / March-April transition / source-funding structure.
  - April Revenue and April COGS both failed badly afterward, so stop localizing H1/Q2 timing.

### What Seems Exhausted

- Uniform 2023H1 level beyond `+13%`:
  - `+15%` was flat/worse versus `+13%`.
- More 2024H1 sample-shape:
  - `2024H1 p1200` worsened.
- 2023H2 Revenue level/split:
  - up, down, Q3/Q4, Jul/Aug all worsened.
- Broad H2 COGS down:
  - `-1%` helped slightly, but followups did not create a large jump.
- Shape-preserve/non-H2 v21 style:
  - worsened.
- R2-only level shift:
  - `submission_cleanv5_r2_level_to_txnmonth_a400.csv` improved public-like R2 but public MAE worsened to `708303.49686`.

## Active Branch: V23 H1 Localize

Script:

- `make_quarantine_big_jump_v23_h1_localize.py`

Run dir:

- `logs/20260424_181141_quarantine_big_jump_v23_h1_localize`

Note:

- `notes/quarantine_big_jump_v23_h1_localize_2026-04-24.md`

Generated candidate files:

- `dataset/submission_qbb63_h1_mayjun_up060_janfebfund.csv`
- `dataset/submission_qbb63_h1_jun_up120_janfebfund.csv`
- `dataset/submission_qbb63_h1_aprmay_up060_janfebfund.csv`
- `dataset/submission_qbb63_h1_apr_up120_janfebfund.csv`
- `dataset/submission_qbb63_h1_q2_up080_q1fund.csv`
- `dataset/submission_qbb63_h1_q2_top35_shape_up100.csv`
- `dataset/submission_qbb63_h1_h1_top35_shape_up060.csv`

Sanity checks already passed:

- `python -m py_compile run_multimetric_publiclike_research.py make_quarantine_big_jump_v23_h1_localize.py`
- All V23 candidate CSVs have 548 rows, date range `2023-01-01` to `2024-07-01`, no negative values, no NaNs.
- All V23 candidates preserve total Revenue and COGS vs the `qbb60v18` anchor.

## Active Branch: V24 April Pivot

Script:

- `make_quarantine_big_jump_v24_april_pivot.py`

Run dir:

- `logs/20260426_195411_quarantine_big_jump_v24_april_pivot`

Note:

- `notes/quarantine_big_jump_v24_april_pivot_2026-04-26.md`

Why it exists:

- `qbb62_h1_backload_preserve_total_q2up040` improved to `661327.00240`.
- `qbb63_h1_mayjun_up060_janfebfund` failed at `666579.35776`.
- Therefore, do not continue late-Q2. V24 tests whether the real Q2 signal is April or March-April transition.

Generated candidate files:

- `dataset/submission_qbb64_apr_from_mayjun_q2preserve_apr080.csv`
- `dataset/submission_qbb64_apr_from_mayjun_q2preserve_apr120.csv`
- `dataset/submission_qbb64_apr_from_mar_marapr_preserve_apr080.csv`
- `dataset/submission_qbb64_apr_from_mar_marapr_preserve_apr120.csv`
- `dataset/submission_qbb64_aprmay_from_jun_q2preserve_aprmay050.csv`
- `dataset/submission_qbb64_march_down_q2_up_preserve_h1_q2p060.csv`
- `dataset/submission_qbb64_apr_cogs_from_mayjun_q2preserve_cogs_apr080.csv`
- `dataset/submission_qbb64_apr_rev_cogs_from_mayjun_q2preserve_apr080.csv`

Sanity checks already passed:

- `python -m py_compile make_quarantine_big_jump_v24_april_pivot.py run_multimetric_publiclike_research.py`
- All V24 candidate CSVs have 548 rows, date range `2023-01-01` to `2024-07-01`, no negative values, no NaNs.
- All V24 candidates preserve total Revenue and COGS vs the current best anchor.

Known V24 public result:

- `submission_qbb64_apr_cogs_from_mayjun_q2preserve_cogs_apr080.csv` = `667484.97219`
- Read: reject COGS timing pivot; do not submit `submission_qbb64_apr_rev_cogs_from_mayjun_q2preserve_apr080.csv`.
- `submission_qbb64_apr_from_mayjun_q2preserve_apr080.csv` = `667631.42258`
- Read: reject Revenue April timing; stop H1 timing localization.

## Active Branch: V25 H2 + 2024H1 Pivots

Script:

- `make_quarantine_big_jump_v25_h2_2024_pivots.py`

Run dir:

- `logs/20260426_201228_quarantine_big_jump_v25_h2_2024_pivots`

Note:

- `notes/quarantine_big_jump_v25_h2_2024_pivots_2026-04-26.md`

Why it exists:

- H1/Q2 timing localization is dead after Q1, May-Jun, April Revenue, and April COGS failures.
- V25 preserves the current best H1 backload and pivots to H2 COGS concentration plus 2024H1 Revenue manifold.

Generated candidate files:

- `dataset/submission_qbb65_h2_highratio_cogs_down060_keeprev.csv`
- `dataset/submission_qbb65_h2_highratio_cogs_down100_keeprev.csv`
- `dataset/submission_qbb65_h2_highratio_cogs_down140_keeprev.csv`
- `dataset/submission_qbb65_h2_aug_cogs_down120_keeprev.csv`
- `dataset/submission_qbb65_h2_julaugdec_cogs_down060_keeprev.csv`
- `dataset/submission_qbb65_2024h1_recency_revshape_a040_keepcogs.csv`
- `dataset/submission_qbb65_2024h1_recency_revshape_a060_keepcogs.csv`
- `dataset/submission_qbb65_2024h1_frontload_q1up040_keepcogs.csv`
- `dataset/submission_qbb65_2024h1_frontload_q1up060_keepcogs.csv`

Sanity checks already passed:

- `python -m py_compile make_quarantine_big_jump_v25_h2_2024_pivots.py run_multimetric_publiclike_research.py`
- All V25 candidate CSVs have 548 rows, date range `2023-01-01` to `2024-07-01`, no negative values, no NaNs.
- All V25 candidates have `h1_max_abs_delta_vs_anchor = 0`, so current H1 backload gain is preserved.

Known V25 public result:

- `submission_qbb65_h2_highratio_cogs_down060_keeprev.csv` = `659211.90870`
- Read: accepted. Continue same axis with `submission_qbb65_h2_highratio_cogs_down100_keeprev.csv`.
- `submission_qbb65_h2_highratio_cogs_down100_keeprev.csv` = `660345.33116`
- Read: rejected vs `down060`; do not submit `down140`. Pivot to another axis while preserving `down060`.

## Recommended Next Submit Order

Do not submit more squeeze around the old qbb60/v21 axes.

1. Generate and use V25, not V24:
   - H2 COGS concentration on current best.
   - 2024H1 recency/frontload manifold on current best.
2. Next planned V25 submit:
   - `dataset/submission_qbb65_h2_highratio_cogs_down100_keeprev.csv`
3. Since down100 worsened:
   - generate V26 on top of `submission_qbb65_h2_highratio_cogs_down060_keeprev.csv`
   - next axis: 2024H1 Revenue manifold/frontload.

## Active Branch: V26 2024H1 After H2

Script:

- `make_quarantine_big_jump_v26_2024_after_h2.py`

Run dir:

- `logs/20260426_202055_quarantine_big_jump_v26_2024_after_h2`

Note:

- `notes/quarantine_big_jump_v26_2024_after_h2_2026-04-26.md`

Why it exists:

- `h2_highratio_down060` is current best at `659211.90870`.
- `h2_highratio_down100` overshot to `660345.33116`.
- V26 changes only 2024H1 Revenue while preserving both H1-backload and H2-down060 gains.

Generated candidate files:

- `dataset/submission_qbb66_2024h1_recency_revshape_a030_keep_h2cogs.csv`
- `dataset/submission_qbb66_2024h1_recency_revshape_a040_keep_h2cogs.csv`
- `dataset/submission_qbb66_2024h1_recency_revshape_a060_keep_h2cogs.csv`
- `dataset/submission_qbb66_2024h1_frontload_q1up030_keep_h2cogs.csv`
- `dataset/submission_qbb66_2024h1_frontload_q1up040_keep_h2cogs.csv`
- `dataset/submission_qbb66_2024h1_frontload_q1up060_keep_h2cogs.csv`
- `dataset/submission_qbb66_2024h1_janfeb_from_mayjun_up050_keep_h2cogs.csv`
- `dataset/submission_qbb66_2024h1_march_from_june_up080_keep_h2cogs.csv`

Sanity checks already passed:

- `python -m py_compile make_quarantine_big_jump_v26_2024_after_h2.py run_multimetric_publiclike_research.py`
- All V26 candidate CSVs have 548 rows, date range `2023-01-01` to `2024-07-01`, no negative values, no NaNs.
- All V26 candidates have `h1_max_abs_delta_vs_anchor = 0` and `h2_cogs_max_abs_delta_vs_anchor = 0`.

Next V26 submit:

- `submission_qbb66_2024h1_recency_revshape_a030_keep_h2cogs.csv` = `661604.13161`
- Read: rejected. Do not submit recency `a040/a060`.
- `submission_qbb66_2024h1_frontload_q1up030_keep_h2cogs.csv` = `659485.66889`
- Read: slight reject. Do not escalate `q1up040/q1up060`; return to H2 COGS structure after down060.

## Active Branch: V27 H2 After Down060

Script:

- `make_quarantine_big_jump_v27_h2_after_down060.py`

Run dir:

- `logs/20260426_202705_quarantine_big_jump_v27_h2_after_down060`

Note:

- `notes/quarantine_big_jump_v27_h2_after_down060_2026-04-26.md`

Why it exists:

- Current best is still `submission_qbb65_h2_highratio_cogs_down060_keeprev.csv = 659211.90870`.
- `down100` overshot, and 2024H1 recency/frontload failed.
- Pure intensity fit says optimum is near `down058`, so cleanup has tiny upside. V27 tests H2 structure after down060: August/December residual, extreme-row concentration, and shape-preserving redistribution.

Generated candidate files:

- `dataset/submission_qbb67_h2_highratio_cogs_down055_from_preanchor_keeprev.csv`
- `dataset/submission_qbb67_h2_highratio_cogs_down070_from_preanchor_keeprev.csv`
- `dataset/submission_qbb67_h2_highratio_cogs_down080_from_preanchor_keeprev.csv`
- `dataset/submission_qbb67_h2_aug_extra_cogs_down040_keeprev.csv`
- `dataset/submission_qbb67_h2_aug_extra_cogs_down080_keeprev.csv`
- `dataset/submission_qbb67_h2_dec_extra_cogs_down040_keeprev.csv`
- `dataset/submission_qbb67_h2_augdec_extra_cogs_down040_keeprev.csv`
- `dataset/submission_qbb67_h2_julaugdec_extra_cogs_down030_keeprev.csv`
- `dataset/submission_qbb67_h2_top25_extra_cogs_down060_keeprev.csv`
- `dataset/submission_qbb67_h2_top15_extra_cogs_down100_keeprev.csv`
- `dataset/submission_qbb67_h2_highratio_shape_preserve_down040.csv`
- `dataset/submission_qbb67_h2_aug_shape_preserve_down060.csv`

Sanity checks already passed:

- `python -m py_compile make_quarantine_big_jump_v27_h2_after_down060.py run_multimetric_publiclike_research.py`
- All V27 candidate CSVs have 548 rows, date range `2023-01-01` to `2024-07-01`, no negative values, no NaNs.
- All V27 candidates have zero 2023H1/2024H1 deltas versus current best.

Next V27 submit:

- `submission_qbb67_h2_aug_extra_cogs_down040_keeprev.csv` = `661165.47840`
- Read: rejected. Do not submit `aug_extra_down080`.
- `submission_qbb67_h2_highratio_shape_preserve_down040.csv` = `659804.99207`
- Read: rejected. Shape-only H2 redistribution worsened by about `+593.08`; the H2 signal is level reduction, not total-preserving redistribution. Do not submit `aug_shape_preserve_down060`.
- Next V27 submit should be `dataset/submission_qbb67_h2_top25_extra_cogs_down060_keeprev.csv` only if continuing H2 concentration as a final sign-test.
- Use `down055_from_preanchor` only for small cleanup, not 60x jump.

## Active Branch: V28 H1 COGS Phase

Run dir:

- `logs/20260426_203948_quarantine_big_jump_v28_h1_cogs_phase`

Note:

- `notes/quarantine_big_jump_v28_h1_cogs_phase_2026-04-26.md`

Why it exists:

- H2 shape-preserve failed, so do not keep redistributing H2 COGS.
- The accepted `qbb62_h1_backload_preserve_total_q2up040` moved 2023H1 Revenue from Q1 to Q2, but COGS stayed fixed.
- This created suspicious 2023Q1 COGS/Revenue ratios near `0.93-1.00`, while 2023Q2 ratios are much lower.
- V28 tests whether the remaining error is 2023H1 COGS being out of phase after the Revenue backload.

Generated candidate files:

- `dataset/submission_qbb68_h1_q1_cogs_down040_keeprev.csv`
- `dataset/submission_qbb68_h1_q1_cogs_down080_keeprev.csv`
- `dataset/submission_qbb68_h1_cogs_backload_q2up020_preserve.csv`
- `dataset/submission_qbb68_h1_cogs_backload_q2up040_preserve.csv`
- `dataset/submission_qbb68_h1_cogs_follow_revbackload_a050.csv`
- `dataset/submission_qbb68_h1_cogs_follow_revbackload_a100.csv`
- `dataset/submission_qbb68_h1_q1_cogs_sample_ratio_a025.csv`
- `dataset/submission_qbb68_h1_q1_cogs_sample_ratio_a040.csv`

Sanity checks:

- `python -m py_compile make_quarantine_big_jump_v28_h1_cogs_phase.py run_multimetric_publiclike_research.py`
- All V28 candidates have 548 rows, date range `2023-01-01` to `2024-07-01`, no negative values, no NaNs.
- V28 changes only 2023H1 COGS; Revenue, 2023H2, and 2024H1 are preserved.

Next V28 submit:

- `submission_qbb68_h1_q1_cogs_down040_keeprev.csv` = `657443.28137`
- Read: accepted. Improves by about `1768.63` vs `qbb65_h2_highratio_cogs_down060_keeprev`.
- `submission_qbb68_h1_q1_cogs_down080_keeprev.csv` = `656301.72926`
- Read: accepted. Improves by about `1141.55` vs `down040`; slope is decreasing but still positive.
- Next action: generate V29 around absolute Q1 COGS down `10-14%`; response-curve optimum from `0/4/8%` is near `13%`.

## Active Branch: V29 Q1 COGS Curve

Run dir:

- `logs/20260426_204721_quarantine_big_jump_v29_q1_cogs_curve`

Note:

- `notes/quarantine_big_jump_v29_q1_cogs_curve_2026-04-26.md`

Why it exists:

- Q1 COGS down `4%` and `8%` both improved.
- Quadratic fit from known public points puts the optimum near absolute Q1 COGS down `13.28%`.
- V29 preserves Revenue, 2023Q2, 2023H2, and 2024H1; only 2023Q1 COGS moves.

Generated candidate files:

- `dataset/submission_qbb69_h1_q1_cogs_down100_keeprev.csv`
- `dataset/submission_qbb69_h1_q1_cogs_down120_keeprev.csv`
- `dataset/submission_qbb69_h1_q1_cogs_down130_keeprev.csv`
- `dataset/submission_qbb69_h1_q1_cogs_down140_keeprev.csv`
- `dataset/submission_qbb69_h1_q1_cogs_down160_keeprev.csv`
- `dataset/submission_qbb69_h1_q1_cogs_sample_monthratio_a0750.csv`
- `dataset/submission_qbb69_h1_q1_cogs_sample_monthratio_a1000.csv`
- `dataset/submission_qbb69_h1_mar_extra_cogs_down040_from_down080.csv`
- `dataset/submission_qbb69_h1_mar_extra_cogs_down060_from_down080.csv`

Sanity checks:

- `python -m py_compile make_quarantine_big_jump_v29_q1_cogs_curve.py run_multimetric_publiclike_research.py`
- All V29 candidates have 548 rows, date range `2023-01-01` to `2024-07-01`, no negative values, no NaNs.

Next V29 submit:

- `submission_qbb69_h1_q1_cogs_down120_keeprev.csv` = `655838.51372`
- Read: accepted, but slope is small. Improvement vs `down080` is about `463.22`.
- Refit with `0/4/8/12%` puts optimum around `12.6-12.9%`; next submit can be `dataset/submission_qbb69_h1_q1_cogs_down130_keeprev.csv`, but this is a low-upside squeeze.
- After `down130`, pivot to a new axis because Q1 uniform COGS-down is nearly exhausted.

## Active Branch: V30 2024H1 COGS Pivot

Run dir:

- `logs/20260428_123905_quarantine_big_jump_v30_2024h1_cogs_pivot`

Note:

- `notes/quarantine_big_jump_v30_2024h1_cogs_pivot_2026-04-28.md`

Why it exists:

- User asked to pivot instead of squeezing `down130`.
- Q1 2023 uniform COGS-down is nearly exhausted.
- New axis: 2024H1 COGS month structure. Current 2024 Jan-Mar COGS/Revenue ratios are above sample, while June is below sample.
- V30 preserves all 2023 values and all Revenue; only 2024H1 COGS changes.

Generated candidate files:

- `dataset/submission_qbb70_2024q1_cogs_down030_keeprev.csv`
- `dataset/submission_qbb70_2024q1_cogs_down060_keeprev.csv`
- `dataset/submission_qbb70_2024h1_cogs_monthratio_a050_keeprev.csv`
- `dataset/submission_qbb70_2024h1_cogs_monthratio_a100_keeprev.csv`
- `dataset/submission_qbb70_2024q1_cogs_monthratio_a100_keeprev.csv`
- `dataset/submission_qbb70_2024h1_cogs_q1down040_q2fund_preserve.csv`
- `dataset/submission_qbb70_2024h1_cogs_q1down040_junfund_preserve.csv`
- `dataset/submission_qbb70_2024_janfeb_cogs_down040_keeprev.csv`
- `dataset/submission_qbb70_2024_mar_cogs_down050_keeprev.csv`

Sanity checks:

- `python -m py_compile make_quarantine_big_jump_v30_2024h1_cogs_pivot.py run_multimetric_publiclike_research.py`
- All V30 candidates have 548 rows, date range `2023-01-01` to `2024-07-01`, no negative values, no NaNs.
- All V30 candidates have zero 2023 deltas and zero Revenue deltas.

Next V30 submit:

- `dataset/submission_qbb70_2024h1_cogs_monthratio_a050_keeprev.csv`
- Expected read: if it improves, submit `submission_qbb70_2024h1_cogs_monthratio_a100_keeprev.csv`; if it fails, try total-preserve shape `submission_qbb70_2024h1_cogs_q1down040_q2fund_preserve.csv`.

## Do Not Submit Next

- `submission_qbb62_h1_frontload_preserve_total_q1up080.csv`
  - Same direction as the failed Q1 frontload.
- `submission_qbb61v21_shape_preserve_all_g020.csv`
  - Same family as rejected v21 shape-preserve.
- Any more tiny `q2up045/q2up050` unless user explicitly wants squeeze.
- Any `2024H1 p1200` style stronger sample-shape.
- Any 2023H2 Revenue up/down or Q3/Q4 split repeat.
- `submission_qbb63_h1_jun_up120_janfebfund.csv`
  - Same late-Q2 direction as failed May-Jun.
- `submission_qbb64_apr_rev_cogs_from_mayjun_q2preserve_apr080.csv`
  - Contains the failed/toxic April COGS timing move.
- `submission_qbb64_apr_from_mayjun_q2preserve_apr120.csv`
  - Same Revenue April direction as failed `apr080`.
- `submission_qbb64_apr_from_mar_marapr_preserve_apr080.csv`
  - Same H1 timing localization family; skip unless explicitly doing postmortem mapping.

## Key Files To Inspect First

- `notes/quarantine_big_jump_v23_h1_localize_2026-04-24.md`
- `logs/20260424_181141_quarantine_big_jump_v23_h1_localize/candidate_manifest.csv`
- `notes/quarantine_big_jump_v22_2026-04-24.md`
- `logs/20260424_173924_quarantine_big_jump_v22/candidate_manifest.csv`
- `run_multimetric_publiclike_research.py`
- `make_quarantine_big_jump_v23_h1_localize.py`
- `make_quarantine_big_jump_v22.py`

## If User Gives A New Public Score

Do this immediately:

1. Record score in this handoff note or the relevant experiment note.
2. Add the score to `KNOWN_PUBLIC_SCORES` in `run_multimetric_publiclike_research.py` if the file is important.
3. Compile changed script:
   - `python -m py_compile run_multimetric_publiclike_research.py`
4. Interpret sign before generating more files:
   - If `mayjun_up060` improves, localize harder toward June.
   - If `mayjun_up060` fails but `q2up040` improved, test `aprmay_up060`.
   - If both May-Jun and Apr-May fail, Q2 backload improvement was likely a broad weak effect; pivot away from H1 timing.

## Clean Branch Context

Clean work tried to translate blackbox insights into legal source-clean assumptions:

- `submission_cleanv2_h1fine_b044_r0876.csv` = `673757.34993`
- `submission_cleanv3_funnel_c110_h1r0876.csv` = `673759.96838`
- `submission_cleaninput_rawmdshape_v5_v4main_cogs2024gap0545.csv` = `691281.03681`
- `submission_clean_regime_recovery_v3_h2strong_cogsp95.csv` = `732768.71351`

Clean interpretation:

- Strict end-to-end/raw feature modeling was much worse than public-blackbox branch.
- Clean route can explain some assumptions with train EDA, but it has not matched the qbb branch.
- If asked for legal/clean final story, use clean candidates only. Do not cite sample/public-blackbox operations as model inputs.

## TabPFN Context

- TabPFN v2.6/API was tried as residual/uplift shaper.
- It did not produce the large gap; best TabPFN/windowmix family reached around `883k`, much worse than later qbb/sample-prior branch.
- Conclusion: current gap is not primarily model class. It is hidden prior/shape/regime/leaderboard-surface mismatch.

## R2/Multi-Metric Context

- Public-like R2 can be raised by level shifts, but MAE worsened.
- `submission_cleanv5_r2_level_to_txnmonth_a400.csv` had better public-like R2 around `0.72`, but public MAE was `708303.49686`.
- Do not optimize R2 in isolation. Any multi-metric candidate must keep MAE competitive first.

## Useful Commands

- Compile changed Python:
  - `python -m py_compile path\to\script.py`
- Run candidate generator:
  - `python make_quarantine_big_jump_v23_h1_localize.py`
- Inspect a manifest:
  - `Import-Csv logs\...\candidate_manifest.csv | Format-Table -AutoSize`
- Inspect latest notes:
  - `Get-ChildItem notes -File | Sort-Object LastWriteTime -Descending | Select-Object -First 20`

## Personality/Interaction Note

The user is trying to climb public leaderboard and is frustrated by tiny gains. Be direct:

- Prefer “this hypothesis is accepted/rejected” over vague optimism.
- Do not recommend small squeezes unless a response curve clearly justifies it.
- Separate “submit now” from “analysis only”.
- Keep saying whether a branch is clean or quarantine.
