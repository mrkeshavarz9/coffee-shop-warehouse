STORE_REVENUE_QUERY = ("""
SELECT
    store_name,
    SUM(amount) AS revenue
FROM fact_sales AS f
JOIN dim_store AS s ON f.store_id = s.store_id
GROUP BY store_name
ORDER BY revenue DESC
""")