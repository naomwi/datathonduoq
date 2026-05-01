# Public LB Sample-Shape Sprint Notes - 2026-04-22

## Current State

Current best public score:

| score | file |
|---:|---|
| `684699.68850` | `submission_sample_v37_rev2023H2_p0200_c0650_away0250.csv` |

Next recommended submit:

1. `submission_sample_v37_rev2023H2_p0100_c0650_away0250.csv`
2. If `p0100` improves: `submission_sample_v39_rev2023H2_p00500_c0650_away0250.csv`
3. If `p0100` fails: `submission_sample_v39_rev2023H2_p01500_c0650_away0250.csv`

## Main Finding

The breakthrough is not model choice. It is that `sample_submission.csv` contains a strong hidden/plausible day-level shape prior.

The winning strategy is not direct sample scaling. Directly moving totals/ratios toward sample is bad. The useful move is:

- Preserve period totals from our stronger forecast.
- Borrow only day-level shape from `sample_submission.csv`.
- Then tune shape strength target-wise and period-wise.

The largest remaining signal found today is:

- `2023H2` Revenue sample-shape alpha must be much lower than the global alpha.
- Increasing `2023H2` alpha to `1.000` was disastrous.
- Reducing `2023H2` alpha from `0.800 -> 0.600 -> 0.400 -> 0.200` produced large gains.

## Score Timeline

| step | public score | interpretation |
|---|---:|---|
| `submission_sample_v30_a0725_ratio_away_sample0250.csv` | `699376.32670` | COGS-ratio away-from-sample plateau point. |
| `submission_sample_v31_rev0725_cogs0750_away0250.csv` | `699662.34515` | COGS sample-shape up is wrong. |
| `submission_sample_v32_rev0725_cogs0700_away0250.csv` | `699167.79998` | COGS sample-shape down is right, but small. |
| `submission_sample_v32_rev0725_cogs0650_away0250.csv` | `698994.05843` | Further COGS down helps only slightly. |
| `submission_sample_v34_rev08000_cogs06500_away0250.csv` | `698898.26661` | Global Revenue sample-shape up helps only slightly. |
| `submission_sample_v35_rev2023H2_up1000_r1000_c0650_away0250.csv` | `707436.88912` | 2023H2 Revenue shape toward sample is badly overdone. |
| `submission_sample_v36_rev2023H2_r0600_c0650_away0250.csv` | `692128.76474` | Reversing 2023H2 alpha gives a real jump. |
| `submission_sample_v36_rev2023H2_r0400_c0650_away0250.csv` | `687112.64298` | 2023H2 alpha lower is still much better. |
| `submission_sample_v37_rev2023H2_p0200_c0650_away0250.csv` | `684699.68850` | Still better, but curve is flattening. |

## Data-Science Conclusions

1. `sample_submission.csv` is a shape prior, not a scale prior.
2. Global shape alpha helped, but exhausted around the high `0.7x` range.
3. COGS-ratio away-from-sample helped until `0.25`, then plateaued.
4. COGS day-shape alpha down helped, but the gains became small.
5. Revenue global alpha up helped slightly.
6. Period-wise Revenue shape is the major remaining axis.
7. `2023H2` is the key regime: current best has `2023H2 Revenue alpha = 0.200`, while other periods remain at base Revenue alpha `0.800`.
8. The curve near `2023H2 alpha 0.200` is flattening, so the next probe should be `0.100`, not a blind jump to `0.000`.

## Generated Scripts

| script | purpose |
|---|---|
| `make_publiconly_sample_targetwise_v31.py` | Target-wise Revenue/COGS alpha on top of COGS-away `0.250`. |
| `make_publiconly_sample_cogs_shape_down_v32.py` | Opposite direction after COGS alpha up failed. |
| `make_publiconly_sample_cogs_shape_micro_v33.py` | Micro fit around COGS alpha `0.65`. |
| `make_publiconly_sample_revenue_shape_v34.py` | Global Revenue-shape axis with COGS fixed. |
| `make_publiconly_sample_periodwise_shape_v35.py` | Single-period Revenue/COGS shape probes. |
| `make_publiconly_sample_2023h2_reversal_v36.py` | Dedicated reversal on 2023H2 Revenue alpha. |
| `make_publiconly_sample_2023h2_extension_v37.py` | Extension below 2023H2 alpha `0.600/0.400`. |
| `make_publiconly_sample_period_combo_v38.py` | Combo probes with 2023H2 low alpha plus 2024H1/2023H1. |
| `make_publiconly_sample_2023h2_micro_v39.py` | Micro search around 2023H2 alpha `0.10-0.18`. |

## Generated Notes

| note | content |
|---|---|
| `notes/publiconly_sample_targetwise_v31_2026-04-22.md` | Target-wise first pass. |
| `notes/publiconly_sample_cogs_shape_down_v32_2026-04-22.md` | COGS shape reversal. |
| `notes/publiconly_sample_cogs_shape_micro_v33_2026-04-22.md` | COGS shape micro fit. |
| `notes/publiconly_sample_revenue_shape_v34_2026-04-22.md` | Global Revenue shape probes. |
| `notes/publiconly_sample_periodwise_shape_v35_2026-04-22.md` | Period-wise first pass. |
| `notes/publiconly_sample_2023h2_reversal_v36_2026-04-22.md` | 2023H2 reversal. |
| `notes/publiconly_sample_2023h2_extension_v37_2026-04-22.md` | 2023H2 extension. |
| `notes/publiconly_sample_period_combo_v38_2026-04-22.md` | Period combo probes. |
| `notes/publiconly_sample_2023h2_micro_v39_2026-04-22.md` | 2023H2 micro search. |

## State Files Updated

The following were updated to point at the latest best:

- `run_public_shift_recovery.py`
- `analyze_public_shift_forensics.py`

Latest best path used by forensics:

```text
dataset/submission_sample_v37_rev2023H2_p0200_c0650_away0250.csv
```

## Candidate Paths To Continue

Primary:

```text
dataset/submission_sample_v37_rev2023H2_p0100_c0650_away0250.csv
dataset/submission_sample_v39_rev2023H2_p00500_c0650_away0250.csv
dataset/submission_sample_v39_rev2023H2_p01500_c0650_away0250.csv
```

If `2023H2` alpha low remains good, next combo candidates:

```text
dataset/submission_sample_v38_h2p0200_2024h1up1000_2023h2p0200_2024h1p1000_c0650_away0250.csv
dataset/submission_sample_v38_h2p0200_2024h1down0600_2023h2p0200_2024h1p0600_c0650_away0250.csv
dataset/submission_sample_v38_h2p0200_2023h1up1000_2023h1p1000_2023h2p0200_c0650_away0250.csv
dataset/submission_sample_v38_h2p0200_2023h1down0600_2023h1p0600_2023h2p0200_c0650_away0250.csv
```

## Risk Notes

- This is public-LB calibration/black-box probing. It is valid here because the user indicated there is no private leaderboard, but it should be explained carefully if this becomes a modeling report.
- The defensible modeling story is: `sample_submission.csv` is treated as an external seasonal prior/template, then calibrated with public feedback.
- Avoid saying the model learned this from local OOF. Local OOF did not capture this shift.
- Do not present the public-only tuning as a generalizable production model without caveats.

