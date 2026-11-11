# ---- 1. Imports ----
import random
from db import get_connection, get_ids


# ---- 2. Connect ----
conn = get_connection()
cur = conn.cursor()

# ---- 3. IDs from dimensions ----
product_ids  = get_ids(cur, "SELECT product_id FROM dim_product")
store_ids    = get_ids(cur, "SELECT store_id FROM dim_store")
customer_ids = get_ids(cur, "SELECT customer_id FROM dim_customer")
date_keys    = get_ids(cur, "SELECT date_key FROM dim_date")

# ---- 4. Price list ----
cur.execute("SELECT product_id, list_price FROM dim_product")
rows = cur.fetchall()     # [(1, 4.00), (2, 4.80), (3, 5.80), ...]

prices = {}
for row in rows:
    prices[row[0]] = row[1]

# ---- 5. Generate receipts ----
random.seed(42)
sales_rows = []

for order_id in range(1, 2001):
    date_key    = random.choice(date_keys)
    store_id    = random.choice(store_ids)
    customer_id = random.choice(customer_ids)
    num_items   = random.randint(1, 3)

    for i in range(num_items):
        product_id = random.choice(product_ids)
        quantity = random.randint(1, 2)
        amount = prices[product_id] * quantity
        row = (order_id, date_key, store_id, product_id, customer_id, quantity, amount)
        sales_rows.append(row)

# ---- 6. Load into fact_sales ----
cur.execute("TRUNCATE TABLE fact_sales RESTART IDENTITY")
cur.executemany("""
    INSERT INTO fact_sales (order_id, date_key, store_id, product_id, customer_id, quantity, amount)
    VALUES(%s, %s, %s, %s, %s, %s, %s)
""",sales_rows)

# ---- 7. Commit and close ----
conn.commit()
cur.close()
conn.close()
print(len(sales_rows))