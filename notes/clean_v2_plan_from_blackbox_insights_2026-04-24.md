# Clean V2 Plan From Blackbox Insights - 2026-04-24

## Goal

Build a stronger clean-input branch that learns from blackbox **only as hypothesis direction**, then re-proves every choice with train-only evidence.

Target:

- beat current clean-input best `691281.03681`
- keep a defensible story that does not use test targets, previous submissions, or sample-derived target values as model inputs

Current references:

- clean-input best: `submission_cleaninput_rawmdshape_v5_v4main_cogs2024gap0545.csv`
- quarantine best: `submission_qbb60v18_cogs2023h2_down010.csv`

## Data Boundary

### Allowed for clean v2

- `dataset/sales.csv`
- provided raw/train tables
- future calendar dates
- train-derived regime summaries
- train-only validation results

### Not allowed for strict clean

- `sample_submission.csv` as target anchor
- previous `submission_*.csv` as input
- public score as a numeric calibration target
- constants copied from blackbox, such as `2023H1 +13%` or `2023H2 COGS -1%`

### Allowed only as research note, not input

- blackbox findings, used to prioritize hypotheses

## Hypotheses To Prove

### H1. H1 recovery is underpredicted by recent-low anchors

Blackbox signal:

- the biggest win came from strengthening `2023H1 Revenue`

Train-only proof needed:

- long folds show recent-low anchors underpredict H1 recovery periods
- H1 seasonal shape is more stable than H2
- pre-2019/recent-low blend improves worst-fold or segment WAPE

Clean model action:

- add `H1 regime recovery head`

### H2. H2 Revenue should be shrunk

Blackbox signal:

- broad H2 up/down and localized H2 Revenue edits failed

Train-only proof needed:

- H2 fold variance is higher than H1
- H2 residual models overfit more often
- stronger H2 shrinkage improves worst-fold stability

Clean model action:

- cap H2 Revenue residual adjustment
- blend H2 more heavily toward anchor

### H3. COGS needs a separate ratio model

Blackbox signal:

- late positive squeeze came from `2023H2 COGS`, not Revenue

Train-only proof needed:

- `COGS / Revenue` ratio has regime and half-year structure
- separate ratio model improves COGS error without breaking Revenue
- H2 ratio uncertainty is higher than H1

Clean model action:

- forecast `COGS_ratio`
- compute `COGS = Revenue_pred * ratio_pred`

### H4. 2024H1 COGS should have small caps

Blackbox signal:

- aggressive `2024H1 COGS` moves failed on the final anchor

Train-only proof needed:

- H1 ratio variance is lower than H2
- strong 2024H1-like ratio corrections fail in long folds

Clean model action:

- cap 2024H1 ratio movement

## Script Plan

### 1. `analyze_clean_v2_train_evidence.py`

Purpose:

- produce train-only evidence for all assumptions

Outputs:

- `logs/<run>/half_year_regime_stats.csv`
- `logs/<run>/month_shape_stability.csv`
- `logs/<run>/ratio_dispersion.csv`
- `notes/clean_v2_train_evidence_2026-04-24.md`

Checks:

- no sample/submission input
- no future target access

### 2. `run_clean_v2_publiclike_validation.py`

Purpose:

- evaluate clean candidates on long-horizon folds

Folds:

- `long_2020_548d`: train through `2019-12-31`, forecast `2020-01-01` to `2021-07-01`
- `long_2021_548d`: train through `2020-12-31`, forecast `2021-01-01` to `2022-07-02`
- `year_2022`: train through `2021-12-31`, forecast `2022`
- `year_2020`: COVID/regime stress fold

Outputs:

- `summary.csv`
- `segment_metrics.csv`
- `candidate_manifest.csv`
- `notes/clean_v2_validation_report_2026-04-24.md`

Metrics:

- combined MAE
- WAPE
- worst-fold score
- segment split by half-year, month, horizon bin
- Revenue bias
- COGS ratio bias

### 3. `run_clean_v2_regime_ratio_candidates.py`

Purpose:

- build final clean candidates after validation

Candidate families:

- `clean_v2_h1_recovery_mild`
- `clean_v2_h1_recovery_strong`
- `clean_v2_h1_recovery_h2shrink`
- `clean_v2_ratio_head_h2flex`
- `clean_v2_full_regime_ratio`

Outputs:

- final selected candidates in `dataset/`
- diagnostics in `logs/`
- report in `notes/`

## Feature Design

### Revenue features

Known future:

- date
- month
- day of week
- day of year
- week of year
- half-year
- month start/end
- cyclic month/day features

Train-derived regime features:

- recent-low mean by month/day
- pre-2019 high-regime mean by month/day
- 2022 recovery slope
- recent-vs-pre2019 level gap
- H1/H2 stability score
- fold-derived recovery residual priors

Forecast-safe anchor features:

- anchor revenue level
- anchor log revenue
- anchor month share
- anchor half-year share

### COGS ratio features

- revenue prediction level
- period label
- month
- historical ratio median by month
- historical ratio p25/p75 by month
- recent ratio trend
- H2 ratio volatility flag
- train-derived ratio cap by period

## Target Design

### Revenue target

Use log residual around a train-only anchor:

```text
target_rev = log1p(actual_revenue) - log1p(anchor_revenue)
```

Apply period caps:

- H1: wider cap
- H2: narrower cap

### COGS target

Model ratio residual:

```text
ratio = COGS / Revenue
target_ratio = ratio - historical_ratio_anchor
```

Then:

```text
COGS_pred = Revenue_pred * ratio_pred
```

## Candidate Logic

### Candidate 1: `clean_v2_h1_recovery_mild`

Purpose:

- prove H1 regime recovery helps without aggressive movement

Expected clean story:

- H1 is historically more stable and recovery-sensitive

### Candidate 2: `clean_v2_h1_recovery_h2shrink`

Purpose:

- combine H1 recovery with H2 shrinkage

Expected clean story:

- H2 Revenue is noisier and should be less free

### Candidate 3: `clean_v2_ratio_head_h2flex`

Purpose:

- test separate COGS ratio head

Expected clean story:

- COGS has regime behavior not captured by Revenue

### Candidate 4: `clean_v2_full_regime_ratio`

Purpose:

- full clean architecture

Components:

- H1 recovery
- H2 shrink
- separate COGS ratio
- 2024H1 mild cap

### Candidate 5: `clean_v2_conservative_reportable`

Purpose:

- safest presentation candidate

Components:

- only components that win train-only worst-fold

## Required Ablations

Run these before trusting any final clean candidate:

- anchor only
- anchor + H1 recovery
- anchor + H2 shrink
- anchor + COGS ratio head
- anchor + H1 recovery + H2 shrink
- full clean v2

Required pass gates:

- does not worsen worst-fold combined WAPE
- does not worsen non-target segment badly
- no single month spike
- `2024-07-01` remains sane
- COGS/Revenue ratio stays within train-derived period bands

## Expected Outcome

This clean v2 may not reach the final blackbox `662k`, because it cannot use direct public calibration. The realistic goal is:

- improve over clean best `691k`
- build a defendable model story
- produce evidence that explains why the blackbox-winning direction was plausible

## Presentation Story

Clean v2 can be explained like this:

> Exploratory diagnostics indicated that the baseline undercalled early-2023 recovery and overtrusted late-2023 Revenue reshaping. We validated this using train-only long-horizon folds and found that H1 recovery behavior is more stable than H2, while COGS ratio has separate regime dynamics. The final clean model therefore uses a regime-aware H1 recovery head, stronger H2 Revenue shrinkage, and a separate COGS ratio head with period-specific caps.

This is the bridge from blackbox to clean: the public scores tell us **where to investigate**, but the clean model only keeps what train-only evidence can support.
