# Clean Lunar Calendar Audit

Run directory: `logs\20260501_144152_clean_lunar_calendar_audit`

## Boundary

This audit derives lunar-calendar features deterministically from the existing `Date` column. It does not merge a holiday table, query the internet, or read external event data.

## Read

- Strongest median Revenue window: `win_tet_0_3` with `rev_rel_median=1.0042` and `cogs_ratio_median=0.8090`.
- Historical Tet effects are measurable but should be treated as a small calendar family, not as a standalone breakthrough.
- Current broad `is_tet_month` is only a Jan/Feb approximation; exact lunar windows are cleaner and more explainable.

## Files

- `tet_dates.csv`
- `lunar_window_summary.csv`
- `lunar_feature_correlations.csv`

## Suggested Model Use

Use exact lunar features as derived calendar features:

- `lunar_month`, `lunar_day`, cyclic lunar encodings.
- `days_from_tet`, `days_to_tet`.
- Tet windows: pre-Tet, Tet core, post-Tet, and wide Tet window.

Do not use hard-coded Tet date tables in final clean code if the report claims the feature is derived only from `Date`.
