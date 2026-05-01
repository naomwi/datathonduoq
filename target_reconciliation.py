import os
import pandas as pd

DATA_DIR = 'dataset'
OUT_FPATH = 'outputs/audit/reconciliation_report.txt'

with open(OUT_FPATH, 'w', encoding='utf-8') as f:
    f.write("=== TARGET RECONCILIATION REPORT ===\n")
    
    # Load required data
    sales = pd.read_csv(os.path.join(DATA_DIR, 'sales.csv'), parse_dates=['Date'])
    orders = pd.read_csv(os.path.join(DATA_DIR, 'orders.csv'), parse_dates=['order_date'])
    items = pd.read_csv(os.path.join(DATA_DIR, 'order_items.csv'))
    products = pd.read_csv(os.path.join(DATA_DIR, 'products.csv'))
    shipments = pd.read_csv(os.path.join(DATA_DIR, 'shipments.csv'))
    returns = pd.read_csv(os.path.join(DATA_DIR, 'returns.csv'), parse_dates=['return_date'])

    # Merge orders and items
    order_details = items.merge(orders[['order_id', 'order_date', 'order_status']], on='order_id', how='left')
    order_details = order_details.merge(products[['product_id', 'cogs']], on='product_id', how='left')

    # Formula 1: Gross Revenue = quantity * unit_price (ordered on the day)
    order_details['gross_rev'] = order_details['quantity'] * order_details['unit_price']
    order_details['gross_cogs'] = order_details['quantity'] * order_details['cogs']

    # Aggregate by order_date
    daily_gross = order_details.groupby('order_date')[['gross_rev', 'gross_cogs']].sum().reset_index()
    daily_gross.rename(columns={'order_date': 'Date'}, inplace=True)

    # Formula 2: Net Revenue = Gross Revenue - Refunds (but refunds happen on return_date, or order_date?)
    # First, let's just compare Gross Revenue to sales.csv Revenue
    compare = sales.merge(daily_gross, on='Date', how='left')
    compare['rev_diff_gross'] = compare['Revenue'] - compare['gross_rev']
    compare['cogs_diff_gross'] = compare['COGS'] - compare['gross_cogs']

    f.write(f"Compare Sales Revenue vs Gross Revenue:\n")
    f.write(f"Mean diff: {compare['rev_diff_gross'].mean():.2f}, Max diff: {compare['rev_diff_gross'].abs().max():.2f}\n")
    f.write(f"Exactly matched days: {(compare['rev_diff_gross'].abs() < 1e-4).sum()} / {len(compare)}\n\n")

    # Formula 3: Add shipping fees?
    # shipments has shipping_fee. Let's merge shipments to orders to attribute to order_date
    orders_ship = orders.merge(shipments[['order_id', 'shipping_fee']], on='order_id', how='left')
    orders_ship['shipping_fee'] = orders_ship['shipping_fee'].fillna(0)
    daily_shipping = orders_ship.groupby('order_date')['shipping_fee'].sum().reset_index()
    daily_shipping.rename(columns={'order_date': 'Date'}, inplace=True)
    
    compare = compare.merge(daily_shipping, on='Date', how='left')
    compare['gross_rev_plus_ship'] = compare['gross_rev'] + compare['shipping_fee']
    compare['rev_diff_ship'] = compare['Revenue'] - compare['gross_rev_plus_ship']

    f.write(f"Compare Sales Revenue vs (Gross Revenue + Shipping Fee):\n")
    f.write(f"Mean diff: {compare['rev_diff_ship'].mean():.2f}, Max diff: {compare['rev_diff_ship'].abs().max():.2f}\n")
    f.write(f"Exactly matched days: {(compare['rev_diff_ship'].abs() < 1e-4).sum()} / {len(compare)}\n\n")

    # Let's check order_status. Maybe excluded 'cancelled'?
    order_details_completed = order_details[order_details['order_status'] != 'cancelled']
    daily_completed = order_details_completed.groupby('order_date')[['gross_rev', 'gross_cogs']].sum().reset_index()
    daily_completed.rename(columns={'order_date': 'Date'}, inplace=True)
    
    compare = compare.merge(daily_completed, on='Date', how='left', suffixes=('', '_completed'))
    compare['rev_diff_completed'] = compare['Revenue'] - compare['gross_rev_completed']
    
    f.write(f"Compare Sales Revenue vs Gross Revenue (Excluding Cancelled):\n")
    f.write(f"Mean diff: {compare['rev_diff_completed'].mean():.2f}, Max diff: {compare['rev_diff_completed'].abs().max():.2f}\n")
    f.write(f"Exactly matched days: {(compare['rev_diff_completed'].abs() < 1e-4).sum()} / {len(compare)}\n\n")

    # Try applying refunds to the ordered date
    returns_agg = returns.groupby('order_id')[['refund_amount', 'return_quantity']].sum().reset_index()
    orders_returns = orders.merge(returns_agg, on='order_id', how='left')
    orders_returns['refund_amount'] = orders_returns['refund_amount'].fillna(0)
    daily_refunds = orders_returns.groupby('order_date')['refund_amount'].sum().reset_index()
    daily_refunds.rename(columns={'order_date': 'Date'}, inplace=True)

    compare = compare.merge(daily_refunds, on='Date', how='left')
    compare['net_rev_ordered_date'] = compare['gross_rev'] + compare['shipping_fee'] - compare['refund_amount']
    compare['rev_diff_net'] = compare['Revenue'] - compare['net_rev_ordered_date']

    f.write(f"Compare Sales Revenue vs (Gross Rev + Shipping - Refunds on Order Date):\n")
    f.write(f"Mean diff: {compare['rev_diff_net'].mean():.2f}, Max diff: {compare['rev_diff_net'].abs().max():.2f}\n")
    f.write(f"Exactly matched days: {(compare['rev_diff_net'].abs() < 1e-4).sum()} / {len(compare)}\n\n")

    # Apply refunds on return_date instead
    daily_return_date = returns.groupby('return_date')['refund_amount'].sum().reset_index()
    daily_return_date.rename(columns={'return_date': 'Date'}, inplace=True)
    compare = compare.merge(daily_return_date, on='Date', how='left', suffixes=('', '_realised'))
    compare['refund_amount_realised'] = compare['refund_amount_realised'].fillna(0)
    compare['net_rev_return_date'] = compare['gross_rev'] + compare['shipping_fee'] - compare['refund_amount_realised']
    compare['rev_diff_realised'] = compare['Revenue'] - compare['net_rev_return_date']

    f.write(f"Compare Sales Revenue vs (Gross Rev + Shipping - Refunds on Return Date):\n")
    f.write(f"Mean diff: {compare['rev_diff_realised'].mean():.2f}, Max diff: {compare['rev_diff_realised'].abs().max():.2f}\n")
    f.write(f"Exactly matched days: {(compare['rev_diff_realised'].abs() < 1e-4).sum()} / {len(compare)}\n\n")

    # Output a few examples to manually check
    f.write("Samples from compare dataframe:\n")
    f.write(compare[['Date', 'Revenue', 'gross_rev', 'gross_rev_plus_ship', 'net_rev_ordered_date', 'net_rev_return_date']].head(10).to_string())

