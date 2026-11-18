{{ config(materialized='table') }}

SELECT
    store_name,
    SUM(amount) AS revenue
FROM {{ source('coffee_shop', 'fact_sales')}} AS f
JOIN {{ source('coffee_shop', 'dim_store')}} AS s ON f.store_id = s.store_id
GROUP BY store_name
ORDER BY revenue DESC