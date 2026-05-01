from __future__ import annotations

from pathlib import Path

from feature_pipeline import (
    CALENDAR_COLUMNS,
    DATA_DIR,
    add_calendar_features,
    add_exogenous_history_features,
    add_target_seasonal_prior_features,
    add_target_history_features,
    build_daily_base,
    get_model_signal_columns,
)


OUT_PATH = DATA_DIR / "feature_store_main.csv"
BASE_OUT_PATH = DATA_DIR / "daily_feature_base.csv"


def build_feature_store() -> Path:
    print("1. Building aligned daily base table...")
    base = build_daily_base()
    base.to_csv(BASE_OUT_PATH, index=False)

    print("2. Adding calendar features...")
    df = add_calendar_features(base)

    print("3. Adding target history features...")
    df = add_target_history_features(df, column="Revenue", prefix="rev")
    df = add_target_history_features(df, column="COGS", prefix="cogs")
    df = add_target_seasonal_prior_features(df)

    print("4. Adding lagged / rolling exogenous features...")
    model_signal_columns = get_model_signal_columns(df)
    raw_signal_columns = [
        col
        for col in model_signal_columns
        if not (
            col.startswith(("rev_", "cogs_", "revplus_", "cogsplus_"))
            or col.startswith("target_seasonal_")
            or col in set(CALENDAR_COLUMNS)
        )
    ]
    df = add_exogenous_history_features(df, columns=raw_signal_columns)

    print("5. Saving feature store...")
    df.to_csv(OUT_PATH, index=False)
    print(f"Daily base saved to {BASE_OUT_PATH}")
    print(f"Feature store saved to {OUT_PATH}. Shape: {df.shape}")
    return OUT_PATH


def main() -> None:
    build_feature_store()


if __name__ == "__main__":
    main()
