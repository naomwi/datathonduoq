# Top10 69x State After H1-Down Fail

## New Public Result

`submission_top10_v12_cogs2023h1_down100.csv` scored `825629.56220`.

Base before this probe:

`submission_publiconly_segment_v8_h2best_2024h1_down100.csv` scored `807504.66276`.

## Interpretation

The `2023H1 COGS down -10%` hypothesis is rejected. It worsened public by `18124.89944`.

This means current `2023H1` COGS is not obviously too high. The midpoint rule says actual `2023H1` COGS is probably above the midpoint between:

- current `2023H1` ratio: about `0.954`
- down100 candidate ratio: about `0.859`
- midpoint ratio: about `0.906`

So broad `2023H1` down is not the route to `69x`.

## Do Not Submit

- `submission_top10_v12_cogs2023h1_down150.csv`
- `submission_top10_v12_h1down100_2024highscale_down100.csv`
- `submission_top10_v12_h1down150_2024highscale_down100.csv`

These inherit the rejected H1-down move.

## Remaining 69x-Capable Hypothesis

The only remaining hypothesis with enough movement and a coherent story is `2024 Mar-Jun scale too high`.

Recommended next:

`submission_top10_v12_rev2024highscale_down100_cogs2024highscale_down100.csv`

Rationale:

- It does not depend on the rejected H1-down move.
- It tests whether high-scale `Mar-Jun 2024` is over-forecast.
- It moves both `Revenue` and `COGS`, which is necessary for a 69x-size jump.

Fallback if it improves but not enough:

`submission_top10_v12_rev2024q2_down100_cogs2024q2_down100.csv`

This localizes the effect to `2024Q2`.
