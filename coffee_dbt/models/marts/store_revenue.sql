SELECT
    store_name,
    SUM(sales_amount) AS revenue
FROM {{ ref('stg_sales')}} AS f
JOIN {{ ref('stg_stores')}} AS s ON f.store_id = s.store_id
GROUP BY store_name
ORDER BY revenue DESC