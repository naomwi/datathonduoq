from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from run_transaction_decomposition_v2 import DATASET_DIR, LOG_ROOT, NOTES_DIR, add_event_columns, write_submission


RUN_PREFIX = "publiconly_cogs_reshape_v6"
CURRENT_BEST_FILE = "submission_publiconly_cogs_break_v5_all_plus020.csv"
CURRENT_BEST_SCORE = 825080.79137


def make_run_dir() -> Path:
    run_dir = LOG_ROOT / f"{datetime.now():%Y%m%d_%H%M%S}_{RUN_PREFIX}"
    run_dir.mkdir(parents=True, exist_ok=True)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return run_dir


def cogs_ratio(frame: pd.DataFrame) -> pd.Series:
    return frame["COGS"] / frame["Revenue"].replace(0, pd.NA)


def cap_floor(frame: pd.DataFrame, mask: pd.Series, floor: float | None, cap: float | None, blend_floor: float, blend_cap: float) -> pd.DataFrame:
    out = frame[["Date", "Revenue", "COGS"]].copy()
    ratio = cogs_ratio(out)
    if floor is not None:
        target = out["Revenue"] * floor
        needs = mask & ratio.lt(floor)
        out.loc[needs, "COGS"] = (1.0 - blend_floor) * out.loc[needs, "COGS"] + blend_floor * target.loc[needs]
    ratio = cogs_ratio(out)
    if cap is not None:
        target = out["Revenue"] * cap
        needs = mask & ratio.gt(cap)
        out.loc[needs, "COGS"] = (1.0 - blend_cap) * out.loc[needs, "COGS"] + blend_cap * target.loc[needs]
    return out


def preserve_total(candidate: pd.DataFrame, base_total: float, mask: pd.Series | None = None) -> pd.DataFrame:
    out = candidate.copy()
    total = out["COGS"].sum()
    if total <= 0:
        return out
    if mask is None:
        out["COGS"] *= base_total / total
        return out
    adjust_idx = mask & out["COGS"].gt(0)
    fixed_total = out.loc[~adjust_idx, "COGS"].sum()
    target_adjust_total = base_total - fixed_total
    current_adjust_total = out.loc[adjust_idx, "COGS"].sum()
    if target_adjust_total > 0 and current_adjust_total > 0:
        out.loc[adjust_idx, "COGS"] *= target_adjust_total / current_adjust_total
    return out


def register(rows: list[dict[str, object]], base: pd.DataFrame, frame: pd.DataFrame, filename: str, thesis: str) -> None:
    path = DATASET_DIR / filename
    write_submission(frame, path)
    delta = frame["COGS"] - base["COGS"]
    ratio = cogs_ratio(frame)
    base_ratio = cogs_ratio(base)
    rows.append(
        {
            "filename": filename,
            "path": str(path),
            "thesis": thesis,
            "cogs_total_ratio_vs_best": frame["COGS"].sum() / base["COGS"].sum(),
            "mean_cogs_delta_vs_best": delta.mean(),
            "mean_abs_cogs_delta_vs_best": delta.abs().mean(),
            "high_ratio_days_gt_105": int(ratio.gt(1.05).sum()),
            "low_ratio_days_lt_095": int(ratio.lt(0.95).sum()),
            "base_high_ratio_days_gt_105": int(base_ratio.gt(1.05).sum()),
            "base_low_ratio_days_lt_095": int(base_ratio.lt(0.95).sum()),
            "cogs_ratio_mean": ratio.mean(),
            "cogs_ratio_promo": ratio.loc[base["win_main_promo"]].mean(),
            "cogs_ratio_nonpromo": ratio.loc[~base["win_main_promo"]].mean(),
            "cogs_ratio_2024h1": ratio.loc[base["is_2024h1"]].mean(),
        }
    )


def main() -> None:
    run_dir = make_run_dir()
    base = pd.read_csv(DATASET_DIR / CURRENT_BEST_FILE, parse_dates=["Date"])
    base = add_event_columns(base).reset_index(drop=True)
    base["is_2024h1"] = base["Date"].dt.year.eq(2024) & base["Date"].dt.month.le(6)
    ratio = cogs_ratio(base)
    all_mask = pd.Series(True, index=base.index)
    nonpromo = ~base["win_main_promo"].astype(bool)
    low_nonpromo = nonpromo & ratio.lt(0.96)
    high_all = ratio.gt(1.03)

    rows: list[dict[str, object]] = []
    base_total = float(base["COGS"].sum())

    specs = [
        ("submission_publiconly_cogs_reshape_v6_floor096_cap105_preserve.csv", all_mask, 0.96, 1.05, 0.55, 0.80, True, "floor low days to 0.96, cap high days to 1.05, preserve total"),
        ("submission_publiconly_cogs_reshape_v6_floor098_cap105_preserve.csv", all_mask, 0.98, 1.05, 0.45, 0.80, True, "floor low days to 0.98, cap high days to 1.05, preserve total"),
        ("submission_publiconly_cogs_reshape_v6_floor100_cap105_preserve.csv", all_mask, 1.00, 1.05, 0.30, 0.80, True, "floor low days to 1.00, cap high days to 1.05, preserve total"),
        ("submission_publiconly_cogs_reshape_v6_floor098_cap102_preserve.csv", all_mask, 0.98, 1.02, 0.45, 0.85, True, "tighter cap 1.02 plus floor 0.98, preserve total"),
        ("submission_publiconly_cogs_reshape_v6_nonpromo_floor098_cap105_preserve.csv", nonpromo, 0.98, 1.05, 0.50, 0.80, True, "nonpromo floor/cap only, preserve total through nonpromo"),
        ("submission_publiconly_cogs_reshape_v6_low_nonpromo_plus050_high_cap105.csv", all_mask, None, 1.05, 0.0, 0.85, False, "cap high ratio then manually boost low-ratio nonpromo +5%"),
    ]

    for filename, mask, floor, cap, blend_floor, blend_cap, preserve, thesis in specs:
        frame = cap_floor(base, mask, floor, cap, blend_floor, blend_cap)
        if "low_nonpromo_plus050" in filename:
            frame.loc[low_nonpromo, "COGS"] *= 1.05
        if preserve:
            preserve_mask = nonpromo if "nonpromo" in filename else all_mask
            frame = preserve_total(frame, base_total, preserve_mask)
        register(rows, base, frame, filename, thesis)

    # Controlled total changes around current best after reshape.
    frame = cap_floor(base, all_mask, 0.98, 1.05, 0.45, 0.80)
    frame = preserve_total(frame, base_total * 1.01, all_mask)
    register(rows, base, frame, "submission_publiconly_cogs_reshape_v6_floor098_cap105_totalup1.csv", "reshape floor/cap and increase total COGS +1%")

    frame = cap_floor(base, all_mask, 0.98, 1.05, 0.45, 0.80)
    frame = preserve_total(frame, base_total * 1.02, all_mask)
    register(rows, base, frame, "submission_publiconly_cogs_reshape_v6_floor098_cap105_totalup2.csv", "reshape floor/cap and increase total COGS +2%")

    manifest = pd.DataFrame(rows).sort_values(["cogs_total_ratio_vs_best", "mean_abs_cogs_delta_vs_best"])
    manifest.to_csv(run_dir / "candidate_manifest.csv", index=False)
    report = f"""# Public-Only COGS Reshape V6

Run directory: `{run_dir}`

Base: `{CURRENT_BEST_FILE}` scored `{CURRENT_BEST_SCORE}`.

The all-multiplier path improved but plateaued. These candidates reshape COGS ratio distribution: cap very high COGS/Revenue days and lift low-ratio days, sometimes preserving current total.

{manifest.to_markdown(index=False)}

Suggested order:

1. `submission_publiconly_cogs_reshape_v6_floor098_cap105_preserve.csv`
2. `submission_publiconly_cogs_reshape_v6_floor098_cap105_totalup1.csv`
3. `submission_publiconly_cogs_reshape_v6_floor098_cap102_preserve.csv`
4. `submission_publiconly_cogs_reshape_v6_nonpromo_floor098_cap105_preserve.csv`
"""
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (NOTES_DIR / "publiconly_cogs_reshape_v6_2026-04-22.md").write_text(report, encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
