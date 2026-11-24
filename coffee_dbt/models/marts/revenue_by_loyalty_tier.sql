SELECT
    loyalty_tier,
    COUNT(DISTINCT c.customer_id) AS customers,
    SUM(sales_amount) AS revenue,
    ROUND(SUM(sales_amount) / COUNT(DISTINCT c.customer_id), 2) AS revenue_per_customer,
    COUNT(DISTINCT order_id) AS orders
FROM {{ ref('stg_customers')}} AS c 
JOIN {{ ref('stg_sales')}} AS s ON c.customer_id = s.customer_id
GROUP BY loyalty_tier
ORDER BY orders DESC
