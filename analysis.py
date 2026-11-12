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
