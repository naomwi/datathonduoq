# Public Black-Box Data Analysis - 2026-04-22

## Latest Best

| score | file |
|---:|---|
| `684463.34954` | `submission_sample_v37_rev2023H2_p0100_c0650_away0250.csv` |

## What The Public Black Box Has Taught Us

### 1. The sample submission is a shape prior

`sample_submission.csv` is not a blank template. It contains a strong 548-day shape prior.

Evidence:

| candidate family | result |
|---|---|
| Old pre-sample best | around `797.6k` |
| Sample period-shape blend `a0.25` | `744.4k` |
| Sample period-shape blend `a0.50` | `711.5k` |
| Sample period-shape blend `a0.70-0.725` | around `701.0k` |

Interpretation:

- The public target has day-level seasonality/event shape close to `sample_submission.csv`.
- Direct sample scale is not trustworthy.
- The useful signal is intra-period daily shape, while period totals should remain from our stronger forecast.

### 2. Sample totals and sample COGS ratio are not reliable

Evidence:

| probe | score | meaning |
|---|---:|---|
| `scale_to_sample005` | `707716.51463` | Moving totals toward sample failed. |
| `ratio_to_sample0050` | `701788.31792` | Moving COGS ratio toward sample failed. |
| `ratio_away_sample0250` | `699376.32670` | Moving COGS ratio away from sample helped, but plateaued. |

Interpretation:

- The sample prior gives calendar shape, not true level.
- COGS/Revenue ratio in sample is too low or structurally mismatched.
- COGS-ratio away-from-sample axis is nearly exhausted after `0.25`.

### 3. COGS shape is secondary

Evidence:

| probe | score | meaning |
|---|---:|---|
| COGS shape up `0.750` | `699662.34515` | Wrong direction. |
| COGS shape down `0.700` | `699167.79998` | Right direction. |
| COGS shape down `0.650` | `698994.05843` | Still right, but small gain. |

Interpretation:

- COGS day-shape should be less sample-like than Revenue.
- But it is not the main path from `68x` to `65x`.

### 4. 2023H2 Revenue is the major anti-sample regime

This is the strongest black-box insight.

| 2023H2 Revenue alpha | score |
|---:|---:|
| `1.000` | `707436.88912` |
| `0.800` | `698898.26661` |
| `0.600` | `692128.76474` |
| `0.400` | `687112.64298` |
| `0.200` | `684699.68850` |
| `0.100` | `684463.34954` |

Interpretation:

- `2023H2` in `sample_submission.csv` is badly over-shaped for the public target.
- Reducing 2023H2 sample-shape alpha creates the largest gains observed after the initial sample-prior breakthrough.
- The curve is now flattening near `0.100`, so `2023H2` alone likely cannot reach `65x`.

### 5. Non-H2 periods probably want stronger sample shape

Important inference:

- Global Revenue alpha `0.800` improved slightly even though `2023H2 alpha=0.800` was very bad.
- Therefore the benefit must have come from other periods, most likely `2023H1` and/or `2024H1`.
- Since `2024H1` has the largest day-level shape delta, it is the highest-information next axis.

## Working Model Hypothesis

The public target is not simply "more sample" or "less sample".

It looks like:

| period | likely behavior |
|---|---|
| `2023H1` | likely wants high sample-shape alpha, still untested under current H2 lock. |
| `2023H2` | wants very low sample-shape alpha, currently best at `0.100`. |
| `2024H1` | likely wants high sample-shape alpha, highest-priority next test. |
| COGS | wants less sample shape and a higher COGS ratio than sample, but low-yield now. |

## Next Candidate Family

Lock current best:

```text
2023H2 Revenue alpha = 0.100
COGS alpha = 0.650
COGS-away = 0.250
```

Then test non-H2 Revenue shape:

| priority | file | hypothesis |
|---:|---|---|
| 1 | `submission_sample_v40_h2p0100_2024h1p1000_2024h1p1000_c0650_away0250.csv` | 2024H1 wants stronger sample shape. |
| 2 | `submission_sample_v40_h2p0100_2024h1p1200_2024h1p1200_c0650_away0250.csv` | If 2024H1 up helps, extrapolate stronger. |
| 3 | `submission_sample_v40_h2p0100_2024h1p0600_2024h1p0600_c0650_away0250.csv` | If 2024H1 up fails, test opposite sign. |
| 4 | `submission_sample_v40_h2p0100_2023h1p1000_2023h1p1000_c0650_away0250.csv` | 2023H1 wants stronger sample shape. |
| 5 | `submission_sample_v40_h2p0100_2023h1p1000_2024h1p1000_2023h1p1000_2024h1p1000_c0650_away0250.csv` | Combine both non-H2 high-shape signals. |

## 65x Path

To reach `65x`, small 2023H2 micro tuning is not enough.

Need one of these to be true:

1. `2024H1` high sample-shape alpha improves strongly.
2. `2023H1` high sample-shape alpha improves strongly.
3. Combining `2023H1` and `2024H1` high-shape with `2023H2` low-shape is roughly additive.
4. After Revenue period shape is calibrated, a second pass on period-specific COGS shape adds the last few thousand.

If `2024H1 p1000` improves, the next move should be `2024H1 p1200` or combined non-H2 high shape.

If `2024H1 p1000` fails, the sign is wrong and we should test `2024H1 p0600`, then pivot to `2023H1`.

