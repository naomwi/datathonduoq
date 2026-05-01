import pandas as pd
from pathlib import Path
feature_store = pd.read_csv("dataset/feature_store_main.csv", parse_dates=["Date"], nrows=1)
if "COGS" not in feature_store.columns:
    print("NO COGS in feature_store")
else:
    print("COGS is present.")
