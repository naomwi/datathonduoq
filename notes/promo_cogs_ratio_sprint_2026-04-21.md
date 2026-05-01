# Promo COGS Ratio Sprint - 2026-04-21

## Runs
- COGS sprint: `logs/20260421_225855_promo_cogs_ratio_sprint/`
- Public-shift gate: `logs/20260421_225906_public_shift_recovery/`

## Hypothesis
Keep the current best Revenue exactly and only adjust COGS inside promo windows using the promo-window COGS-ratio prior from `promo_window_core_v2`.

Current best Revenue source:
- `dataset/submission_tabpfn_promo_windowmix_v1.csv`

## Diagnostics
The COGS-ratio prior suggests higher COGS ratio in most promo windows:

| window | rows | mean ratio delta |
|---|---:|---:|
| marapr | 62 | +0.0411 |
| junjul | 39 | +0.0585 |
| augoct | 34 | -0.0112 |
| novjan | 48 | +0.0563 |

Because current best Revenue raises promo Revenue, even alpha/clip variants mostly become small positive COGS moves.

## Exported Candidates
- `dataset/submission_promo_cogsratio_bestrev_a005_clip005.csv`
- `dataset/submission_promo_cogsratio_bestrev_a010_clip005.csv`
- `dataset/submission_promo_cogsratio_bestrev_a015_clip010.csv`
- `dataset/submission_promo_cogsratio_bestrev_pos_a010_clip005.csv`
- `dataset/submission_promo_cogsratio_bestrev_pos_a020_clip010.csv`
- `dataset/submission_promo_cogsratio_bestrev_noaugoct_a010_clip005.csv`
- `dataset/submission_promo_cogsratio_bestrev_junjul_novjan_a015_clip010.csv`

Duplicate groups:
- `a005_clip005`, `a010_clip005`, and `pos_a010_clip005` are identical.
- `a015_clip010` and `pos_a020_clip010` are identical.

## Gate Read
All COGS-ratio candidates are `20_borderline_probe_only`.

Best COGS-only variants by public-like weighted norm:

| candidate | cogs total ratio | promo COGS delta mean | read |
|---|---:|---:|---|
| `promo_cogsratio_bestrev_a015_clip010` | 1.003437 | +34.6k | medium COGS probe, duplicate of `pos_a020_clip010` |
| `promo_cogsratio_bestrev_noaugoct_a010_clip005` | 1.001445 | +14.5k | safest non-Aug-Oct COGS probe |
| `promo_cogsratio_bestrev_a005_clip005` | 1.001719 | +17.3k | safest all-window COGS probe |

## Decision
This is not a breakthrough path yet. It is a clean hypothesis probe only.

If spending exactly one submission:
- Prefer `dataset/submission_promo_cogsratio_bestrev_noaugoct_a010_clip005.csv`

Reason:
- Keeps current best Revenue exactly.
- Moves only promo COGS.
- Avoids Aug-Oct where the COGS-ratio prior is negative/uncertain.
- Smaller COGS total movement than the older `bestrev_cogsratio010`.

Do not submit duplicate variants from the same MD5 group.
