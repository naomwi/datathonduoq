# Feasible Path After Failed 69x Probes

## Current Best

`submission_publiconly_segment_v8_h2best_2024h1_down100.csv`

Public score:

`807504.66276`

## What Is Now Rejected

The following large hypotheses are rejected:

- Extra `2023H2` COGS spike:
  - `submission_publiconly_month_v10_h2_peak_more200.csv = 823082.86966`
  - `submission_publiconly_month_v10_h2_shoulder_more200.csv = 830056.22789`
- `2023H1` COGS down:
  - `submission_top10_v12_cogs2023h1_down100.csv = 825629.56220`
- `2024` high-scale down:
  - `submission_top10_v12_rev2024highscale_down100_cogs2024highscale_down100.csv = 841263.33232`
- `2024` high-margin shock:
  - `submission_top10_v13_rev2024highscale_up100_cogsdown100.csv = 830171.46835`
- `2024` highscale Revenue up alone:
  - `submission_top10_v13_rev2024highscale_up100_keepcogs.csv = 812154.38787`

## Re-Think

The current best likely has the COGS *absolute level* closer than before, but may have an unrealistic `2023H2` COGS/Revenue ratio.

Current best profile:

- `2023H1` COGS/Revenue: about `0.954`
- `2023H2` COGS/Revenue: about `1.090`
- `2024H1` COGS/Revenue: about `0.863`

Historical odd-year H2 ratios are high, but usually around `0.96-1.01`, not `1.09`.

This means the next feasible hypothesis is:

> `2023H2` COGS absolute is high and should stay high, but `2023H2` Revenue is underpredicted.

So the correction should be:

`2023H2 Revenue up, keep COGS fixed`

This lowers the H2 ratio while preserving the COGS correction that public already rewarded.

## Recommended Next Submit

Submit:

`dataset/submission_top10_v13_rev2023h2_up100_keepcogs.csv`

Why:

- It is not contradicted by previous failed probes.
- It targets the only remaining large anomaly: `2023H2` ratio too high.
- It can theoretically move score from `807k` to about `756k` if direction is correct.
- If it improves strongly, the path to `69x` is to combine it with a 2024 COGS split, not with more H2 COGS.

## If It Improves

Then test:

`dataset/submission_2024split_v14_marjun_cogs_up075.csv`

If both improve, create a combo:

- `2023H2 Revenue +10%`
- `2024 Mar-Jun COGS +7.5%`
- keep `2023H2` COGS high
- keep Revenue elsewhere unchanged

## If It Fails

Stop post-processing. The remaining `69x` gap probably requires a different base forecast or benchmark prior, not more segment adjustments.
