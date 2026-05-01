# Clean-From-Blackbox Methodology - 2026-04-24

## Core Principle

Blackbox public probing can be used as a **hypothesis generator**, not as a **source of direct model parameters**.

That means:

- acceptable: public blackbox suggests **where** the model is wrong
- acceptable: public blackbox suggests **which hypothesis to test first**
- not acceptable for a clean story: copying public-discovered constants directly into the final model
- not acceptable for a clean story: matching test/sample targets by construction

The clean branch should therefore learn from blackbox by **distilling directional insight into train-only evidence**, then implementing only the part that survives train-only validation.

## Safe Translation Rule

### Bad translation

Blackbox says `2023H1 +13%` helps, so final clean model multiplies `2023H1 Revenue` by `1.13`.

This is not a clean explanation. It is a public-calibrated constant.

### Good translation

Blackbox suggests `2023H1` is undercalled.

Then we go back to train-only data and test:

- whether post-shock H1 recovery is systematically underpredicted by recent-year anchors
- whether H1 shape is more stable than H2
- whether blending a low-regime anchor with a pre-2019 regime reduces long-fold error

If that is true on train-only backtests, then the clean model can include a `regime recovery layer` for H1.

The final clean choice is justified by train-only evidence, not by the public constant itself.

## The Right Evidence Chain

For every blackbox insight, require this chain:

1. **Blackbox observation**
   - Example: raising `2023H1 Revenue` repeatedly improved public.

2. **Train-only hypothesis**
   - Example: the baseline anchor underestimates H1 recovery after a low-regime period.

3. **Train-only evidence**
   - long folds
   - segment errors
   - year/half-year descriptive statistics
   - ablations

4. **Clean modeling choice**
   - Example: add a train-only H1 recovery component or a regime-blend feature set.

5. **Falsification test**
   - Example: if the component does not improve worst-fold normalized error on train-only long folds, remove it.

If any step in that chain is missing, the assumption is not strong enough for the clean branch.

## Assumptions We Can Reasonably Defend

### A1. `2023H1 Revenue` is the main underprediction zone

#### What blackbox told us

The biggest consecutive public gains came from strengthening `2023H1 Revenue`.

#### What clean must prove on train-only data

- recent-year anchors underpredict recovery-like periods more in `H1` than in other segments
- `H1` seasonal shape is more stable than `H2`
- a regime blend using pre-2019 high years plus recent low years improves long-horizon folds

#### Clean translation

- add a `regime recovery` component for `H1`
- use train-only recovery features such as:
  - relative level vs recent-low years
  - relative level vs pre-2019 years
  - recent trend / recovery slope
  - H1 seasonal priors from train history

#### Not clean

- forcing `2023H1` up by a public-found fixed percent

### A2. `2023H2 Revenue` should be shrunk, not freely reshaped

#### What blackbox told us

Almost every direct `2023H2 Revenue` edit failed:

- broad up
- broad down
- mixed-sign `Q3/Q4`
- `August-only`

#### What clean must prove on train-only data

- `H2` has higher fold variance than `H1`
- `H2` month-share/shape stability is lower
- candidate H2 residual models overfit long folds more easily

#### Clean translation

- stronger regularization for `H2 Revenue`
- heavier reliance on anchor in `H2`
- smaller adjustment caps for H2 residuals

#### Not clean

- manually freezing or moving H2 because a public probe said so

### A3. `COGS` needs its own regime logic, especially in `2023H2`

#### What blackbox told us

After H2 Revenue edits failed, the only positive late orthogonal move was:

- small `2023H2 COGS down`

#### What clean must prove on train-only data

- `COGS / Revenue ratio` varies by period/regime and is not fully explained by Revenue level
- H2 ratio variance is structurally larger than H1 ratio variance
- a separate ratio model improves long-fold `COGS` error without harming Revenue

#### Clean translation

- forecast `Revenue`
- forecast `COGS_ratio` separately
- set `COGS = Revenue * ratio_pred`
- allow extra flexibility in `2023H2` ratio, but keep it train-validated

#### Not clean

- hard-coding `2023H2 COGS -1%`

### A4. `2024H1 COGS` should only move mildly

#### What blackbox told us

Aggressive `2024H1 COGS` down did not transfer well on the late anchor.

#### What clean must prove on train-only data

- H1 cost-ratio dispersion is lower than H2
- aggressive H1 ratio corrections worsen long-fold stability

#### Clean translation

- cap `2024H1` ratio adjustments
- prefer mild ratio priors or train-derived gap features

#### Not clean

- forcing `2024H1` to exact sample-like ratios

## What A Clean Report Can Honestly Say

This is a defensible phrasing:

> Exploratory diagnostics suggested that the baseline underpredicted early-2023 recovery and treated late-2023 cost behavior too similarly to revenue behavior. We therefore returned to train-only data and tested train-derived hypotheses on long-horizon backtests. The final clean model uses a regime-aware H1 recovery component, stronger H2 revenue shrinkage, and a separate COGS ratio model. Public probing was used only to prioritize hypotheses, not to set final constants or features.

This is **not** a defensible phrasing:

> We found that `2023H1` should be `+13%` and `2023H2 COGS` should be `-1%`, so we used those values in the model.

## Required Proof Package For Each Clean Choice

Every clean assumption should be backed by the following:

### 1. Descriptive proof

- yearly / half-year totals
- monthly share stability
- ratio dispersion
- regime break analysis

### 2. Backtest proof

- long-horizon folds
- worst-fold score
- normalized error, not just MAE
- segment metrics by `2023H1`, `2023H2`, `2024H1`

### 3. Ablation proof

Compare:

- baseline anchor
- baseline + H1 recovery component
- baseline + H2 shrinkage
- baseline + separate COGS ratio model
- full clean model

### 4. Falsification proof

If a component wins only on average but fails on worst-fold or explodes in one segment, it should not be claimed as a robust clean insight.

## Recommended Clean V2 Design

### Revenue side

- keep a strong train-only anchor
- add an `H1 regime recovery head`
- shrink `H2 Revenue` more aggressively than `H1`

### COGS side

- predict `COGS_ratio` separately
- give `H2` its own ratio features and priors
- cap `2024H1` ratio adjustment magnitude

### Validation side

- replace mean OOF with public-like long folds
- report `worst-fold`
- report segment metrics by half-year

## Final Rule

Blackbox is useful if it changes the question:

- from: "what fixed knob should we add?"
- to: "what train-only structural assumption should we test?"

If the clean branch follows that rule, then it can honestly learn from blackbox without turning into disguised public fitting.
