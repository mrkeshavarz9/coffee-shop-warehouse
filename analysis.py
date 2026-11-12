import pandas as pd
from db import get_engine

engine = get_engine()

store_revenue_query = ("""
SELECT
    store_name,
    SUM(amount) AS revenue
FROM fact_sales AS f
JOIN dim_store AS s ON f.store_id = s.store_id
GROUP BY store_name
ORDER BY revenue DESC
""")

store_revenue = pd.read_sql(store_revenue_query, engine)
print(store_revenue)
print()

total_sell_query = ("""
SELECT
    category,
    SUM(amount) AS total_sell,
    ROUND(SUM(amount) / COUNT(DISTINCT d.date_key), 2) AS avg_per_day,
    is_weekend
FROM fact_sales AS f
JOIN dim_product AS p ON f.product_id = p.product_id
JOIN dim_date AS d ON f.date_key = d.date_key
GROUP BY category, is_weekend
ORDER BY category
""")

category_weekend = pd.read_sql(total_sell_query, engine)
print(category_weekend)
