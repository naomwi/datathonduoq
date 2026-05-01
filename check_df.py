import pandas as pd
df = pd.read_csv('dataset/feature_store_main.csv', nrows=2)
dups = set([col for col in df.columns if list(df.columns).count(col) > 1])
if dups:
    print("Duplicate columns:", dups)
else:
    print("No duplicates")
