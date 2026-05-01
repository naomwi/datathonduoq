import os
import pandas as pd
import numpy as np
import sys

DATA_DIR = 'dataset'
OUT_FPATH = 'outputs/audit/audit_report.txt'
os.makedirs(os.path.dirname(OUT_FPATH), exist_ok=True)

files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]

with open(OUT_FPATH, 'w', encoding='utf-8') as f:
    f.write("=== DATA AUDIT REPORT ===\n")
    f.write(f"Found {len(files)} CSV files in {DATA_DIR}.\n\n")

    for file in sorted(files):
        filepath = os.path.join(DATA_DIR, file)
        try:
            df = pd.read_csv(filepath)
            f.write(f"--- {file} ---\n")
            f.write(f"Shape: {df.shape}\n")
            f.write("Columns & Missing Values & Uniqueness:\n")
            for col in df.columns:
                n_missing = df[col].isnull().sum()
                pct_missing = 100 * n_missing / len(df) if len(df) > 0 else 0
                n_unique = df[col].nunique()
                f.write(f"  - {col}: {df[col].dtype}, Missing: {n_missing} ({pct_missing:.2f}%), Unique: {n_unique}\n")
            f.write("\n")
        except Exception as e:
            f.write(f"Error reading {file}: {e}\n\n")

    # Specific checks from requirements:
    f.write("=== INTEGRITY CHECKS ===\n")
    # 1. products.csv: cogs < price
    try:
        products = pd.read_csv(os.path.join(DATA_DIR, 'products.csv'))
        n_violations = (products['cogs'] >= products['price']).sum()
        f.write(f"[CHECK] products.csv `cogs < price` violations: {n_violations}\n")
    except Exception as e: pass

    # 2. orders.csv and order_items.csv matching
    try:
        orders = pd.read_csv(os.path.join(DATA_DIR, 'orders.csv'))
        order_items = pd.read_csv(os.path.join(DATA_DIR, 'order_items.csv'))
        orphan_items = ~order_items['order_id'].isin(orders['order_id'])
        f.write(f"[CHECK] order_items.csv with missing orders in orders.csv: {orphan_items.sum()}\n")
        f.write(f"[CHECK] order_items.csv distinct orders: {order_items['order_id'].nunique()}, orders.csv target orders: {len(orders)}\n")
    except Exception as e: pass

    # 3. Target reconciliation (sales vs orders/order_items)
    try:
        sales = pd.read_csv(os.path.join(DATA_DIR, 'sales.csv'))
        f.write(f"[CHECK] sales.csv target shape: {sales.shape}, Date range: {sales['Date'].min()} to {sales['Date'].max()}\n")
    except Exception as e: pass
