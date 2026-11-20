SELECT
    sale_id,
    order_id,
    date_key,
    store_id,
    product_id,
    customer_id,
    quantity,
    amount AS sales_amount
FROM {{source('coffee_shop', 'fact_sales')}}