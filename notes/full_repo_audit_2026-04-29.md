# Full Repo Audit - 2026-04-29

## Scope

This audit was run after the clean V17/V18 work to check for:

- syntax/compile errors across Python scripts;
- invalid clean submission files;
- accidental `sample_submission.csv`, previous `submission_*.csv`, or test-target input usage in the active clean path;
- implementation mistakes in the current clean lineage.

## Automated Checks

| Check | Result |
|---|---:|
| Python files scanned | `189` |
| Python compile errors | `0` |
| `submission_clean*.csv` files scanned | `315` |
| Bad clean submissions | `0` |
| `read_csv` calls scanned | `336` |
| Direct sample/submission read patterns | `5` |

Generated audit logs:

- `logs/full_repo_compile_audit.csv`
- `logs/full_repo_read_csv_audit.csv`
- `logs/full_repo_submission_constant_audit.csv`
- `logs/clean_submission_invariant_audit.csv`

`rg` was unavailable in this workspace due to Windows `Access is denied`, so the audit used `Get-ChildItem`, `Select-String`, and Python AST parsing.

## Active Clean Lineage

The current clean best is:

- `submission_cleanv17_v16_h2ratio_recent_weighted_c400.csv = 667263.90843`

The active generation path is:

`V10 -> V13/V14/V16 -> V17`, with V18 candidates rebuilding V17 as their base.

Files checked in the active clean path:

- `run_clean_v10_h1_regime_shape.py`
- `run_clean_v11_trainselected_regime_shape.py`
- `run_clean_v12_monthly_funnel_router.py`
- `run_clean_v13_daily_peak_allocator.py`
- `run_clean_v14_multimetric_frontier.py`
- `run_clean_v15_ratio_first_cogs_allocator.py`
- `run_clean_v16_foldlearned_daily_allocator.py`
- `run_clean_v17_period_ratio_head.py`
- `run_clean_v18_daily_ratio_tail_router.py`
- `run_cleaninput_rawmdshape_pubguided.py`
- `run_clean_v7_period_funnel_council.py`
- `run_clean_v2_eda_guided_candidates.py`
- `run_clean_regime_recovery_scenarios.py`
- `run_cleanroom_rawmd_pipeline.py`
- `train_recursive_forecast.py`
- `build_feature_store.py`
- `feature_pipeline.py`

No active clean-generation script directly reads:

- `sample_submission.csv`;
- previous `submission_*.csv` files as input anchors;
- `sales_test` target values.

The active clean anchor uses `curated_promo_cogs` features. Feature group audit showed it contains calendar, recursive Revenue/COGS history, and promo-derived features, but not the explicitly marked `unknown_future` groups such as raw order flow, traffic, returns/reviews, inventory, or mix.

## Direct Sample/Submission Reads Found

The repo contains five direct read patterns involving sample/submission files:

| File | Line | Classification |
|---|---:|---|
| `make_public_router_eom_challengers.py` | `222` | public/quarantine |
| `make_publiconly_top10_69x_v12.py` | `116` | public-only / blackbox |
| `run_public_revenue_direct_horizon_v1.py` | `305` | public/quarantine |
| `run_public_revenue_direct_horizon_v2.py` | `293` | public/quarantine |
| `run_tabpfn_recursive.py` | `248` | old experimental path |

These are not on the current clean generation path. They must remain quarantined and must not be presented as clean-source final code.

## Implementation Findings

No critical implementation error was found in the current clean lineage.

Rebuild checks from `notes/debug_v17_v18_audit_2026-04-29.md`:

| Check | Result |
|---|---:|
| V16 rebuild max target diff vs submitted V16 | `~1.86e-9` |
| V17 rebuild max target diff vs submitted V17 c400 | `~1.86e-9` |
| V18 internal base max target diff vs submitted V17 c400 | `~1.86e-9` |

V18 output scope checks passed:

- H1 candidates change only `2023H1`;
- H2 candidates change only `2023H2`;
- router candidates change only `2023H1` and `2023H2`;
- all checked outputs have 548 rows, correct date range, no NaN, and no negative values.

One validation-only bug was found and fixed earlier in `run_clean_v18_daily_ratio_tail_router.py`: the `all_median` validation regime was using the weighted lookup path instead of median lookup. This does not affect generated V18 candidates because none of the V18 submission specs uses `all_median`.

## Remaining Risks

The main risk is not a code bug; it is methodology labeling.

- Current best clean branch is `clean-input public-guided`, not strict clean.
- Public feedback is used to choose families and strength ranges; numeric daily/monthly shapes are train-derived.
- `run_multimetric_publiclike_research.py` intentionally reads candidate submissions and public scores for evaluation/research. It is not a clean generation script.
- Quarantine/public-only scripts are still present in the repo and should be excluded from final source package or clearly separated.
- Public-like metric proxy overvalued `submission_cleanv17_v16_h2ratio_recent_weighted_c550.csv`; public score showed c550 is worse than c400. Do not trust the proxy alone for stronger H2 COGS-down moves.

## Practical Conclusion

Current clean best `submission_cleanv17_v16_h2ratio_recent_weighted_c400.csv` is mechanically reproducible from the clean-input public-guided pipeline and does not appear to contain a direct test-target/sample/submission leak.

For final/report use:

- safe to present as `clean-input public-guided` if public calibration is allowed;
- not safe to present as fully `strict clean`;
- do not include or rely on public-only/quarantine scripts in the final clean story.
