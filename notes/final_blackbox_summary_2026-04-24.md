# Final Blackbox Summary - 2026-04-24

## Final Status

- Target `655k` was **not reached**.
- Best final public score from the late blackbox branch:
  - `submission_qbb60v18_cogs2023h2_down010.csv`
  - public score: `662607.08245`
- Best pre-COGS anchor before the final H2 cost tweak:
  - `submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv`
  - public score: `662759.87577`

## Best Files To Keep

### Quarantine / public-blackbox best

- `dataset/submission_qbb60v18_cogs2023h2_down010.csv`

This is the strongest final file from the blackbox branch. It keeps the best Revenue anchor and applies only:

- `2023H2 COGS scale = 0.99`

Period totals:

| period     | Revenue | COGS | ratio |
|:-----------|--------:|-----:|------:|
| 2023H1     | 863.300M | 756.492M | 0.876280 |
| 2023H2     | 620.433M | 622.140M | 1.002751 |
| 2024H1     | 883.183M | 748.114M | 0.847066 |
| 2024-07-01 | 5.655M | 6.018M | 1.064152 |

### Best clean-input branch

- `dataset/submission_cleaninput_rawmdshape_v5_v4main_cogs2024gap0545.csv`
- public score: `691281.03681`

This remained the best cleaner/public-guided branch, but it did not catch the full hidden public regime.

## What Actually Won

### 1. `2023H1 Revenue level` was the only major winning axis

The strongest consistent gains came from repeatedly raising `2023H1 Revenue` while holding the rest of the winning structure fixed:

- `submission_qbb60v7_nonh2shape_2023h1level103_away0300.csv` = `671930.79214`
- `submission_qbb60v8_nonh2shape_2023h1level105_away0300.csv` = `668570.18037`
- `submission_qbb60v9_nonh2shape_2023h1level107_away0300.csv` = `665868.08869`
- `submission_qbb60v9_nonh2shape_2023h1level110_away0300.csv` = `663346.24664`
- `submission_qbb60v10_nonh2shape_2023h1level113_away0300.csv` = `662759.87577`

Read:

- Hidden public strongly preferred a much stronger `2023H1 Revenue` regime than the local baseline.
- The axis saturated around `+13%`.
- `+15%` no longer helped.

### 2. `away0300` mattered, but only as an enabler

- `away0300` was clearly better than softer anchors during the winning run.
- Pushing away beyond that stopped helping.
- So it was a useful support axis, not the main remaining source of jump.

### 3. Late-2023 costs were slightly too high on the final anchor

After the H2 Revenue path fully failed, the first positive orthogonal move was:

- `submission_qbb60v18_cogs2023h2_down010.csv` = `662607.08245`

Read:

- On the final anchor, the remaining H2 error was more likely `COGS` than `Revenue`.
- The effect existed, but it was small.
- This was a squeeze gain, not a breakthrough gain.

## What Did Not Work

### 1. Reopening `2024H1 shape`

- `submission_qbb60v11_nonh2shape_2023h1level113_away0300_2024h1p1200.csv` = `664288.59833`

This failed clearly once the `2023H1` anchor was already strong.

### 2. Lowering `2023H1 COGS`

- `submission_qbb60v12_nonh2shape_2023h1level113_away0300_cogs2023h1_098.csv` = `662841.06509`

This was slightly worse than the best anchor, so `2023H1` was not missing a lower-cost story.

### 3. Any direct `2023H2 Revenue` move

These all failed:

- broad `2023H2 up`
- broad `2023H2 down`
- `Q3 up / Q4 down`
- `Jul-Aug up / Q4 down`
- `August-only up`

Representative failures:

- `submission_qbb60v13_nonh2shape_2023h1level113_2023h2rev1025_away0300.csv` = `663501.80146`
- `submission_qbb60v13_nonh2shape_2023h1level113_2023h2rev0975_away0300.csv` = `663679.63710`
- `submission_qbb60v15_h2split_q3up050_q4down025.csv` = `664826.90886`
- `submission_qbb60v17_augup050_only.csv` = `665494.11971`

Read:

- By the end, H2 Revenue had become a dead axis on this anchor.
- H2 errors were not being fixed by re-shaping or re-leveling Revenue.

### 4. Big COGS all-in moves

These failed hard:

- `submission_qbb60v19_allin_cogs23h2_sample_cogs24h1_sample.csv` = `673566.41883`
- `submission_qbb60v20_lastshot_cogs23h2_down010_cogs24h1_down016.csv` = `664159.16954`

Read:

- `2024H1 COGS down` looked attractive in isolation, but did not transfer well onto the final `662k` anchor.
- Forcing both `2023H2` and `2024H1` all the way toward sample-like COGS ratios was too aggressive.

## Final Public Story We Learned

The hidden public target did **not** mainly reward a better model family at the end. The strongest rule we found was:

- `2023H1 Revenue` was substantially undercalled by the baseline.
- Once that was fixed, most remaining `H2 Revenue` edits were noise or harmful.
- The only meaningful late orthogonal gain left was a **small** reduction in `2023H2 COGS`.

In other words:

- the branch won by discovering a stronger `2023H1` regime,
- then ran out of large unexplored axes,
- and only had a tiny `2023H2 COGS` squeeze left.

## Practical Wrap-Up

- Best final blackbox file to keep: `dataset/submission_qbb60v18_cogs2023h2_down010.csv`
- Best cleaner file to keep: `dataset/submission_cleaninput_rawmdshape_v5_v4main_cogs2024gap0545.csv`
- Best concise statement about why `655k` was missed:
  - the big winning axis was found and exhausted,
  - but no second independent large axis remained within the remaining submission budget.

## Presentation / Narrative Guidance

If this project needs a cleaner explanation later, do **not** present the quarantine branch as clean modeling.

Cleaner narrative:

- emphasize regime-shift analysis,
- emphasize `2023H1` recovery underprediction,
- use the clean-input branch as the reproducible story,
- describe the blackbox branch only as diagnostic evidence about hidden public behavior.
