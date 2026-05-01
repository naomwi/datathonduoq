# Agent Instructions

## Source
- Based on `forrestchang/andrej-karpathy-skills` CLAUDE.md plus datathon project rules.
- Prefer explicit assumptions, simple code, surgical edits, and verifiable goals.

## Runtime
- Use Python scripts from the repo root.
- Compile changed scripts with `python -m py_compile path\to\script.py`.
- Run focused scripts directly, e.g. `python run_cleaninput_rawmdshape_v6_followup.py`.

## Data Boundaries
- `strict clean`: use only provided train/raw data and known future calendar.
- `clean-input public-guided`: do not read test targets, `sample_submission.csv`, or previous submissions as inputs; public scores may guide constants and must be labeled.
- `quarantine blackbox`: may use public/submission/sample signals; keep separate from clean final story.
- Never present quarantine methods as clean.

## Datathon Workflow
- Every submission must test one clear hypothesis.
- Before submit, record expected read: what score improvement or regression would imply.
- Always sanity-check period totals, max daily values, COGS/Revenue ratios, and `2024-07-01`.
- Save manifests and notes under `logs/` and `notes/`.
- Keep final candidates in `dataset/`; raw donor/intermediate outputs belong in logs.

## Coding Rules
- Think before coding: surface assumptions and ambiguity.
- Simplicity first: avoid speculative abstractions and one-off frameworks.
- Surgical changes: touch only files needed for the task.
- Goal-driven execution: define verification, implement, then verify.
- Do not refactor unrelated code or delete pre-existing work without request.

## File-Scoped Commands
| Task | Command |
|------|---------|
| Compile script | `python -m py_compile path\to\script.py` |
| Run script | `python path\to\script.py` |
| Inspect CSV head | `Get-Content path\to\file.csv -TotalCount 20` |

## Commit Attribution
AI commits MUST include:
```
Co-Authored-By: Codex <noreply@openai.com>
```
