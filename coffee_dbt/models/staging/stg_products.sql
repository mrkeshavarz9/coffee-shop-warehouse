SELECT
    product_id,
    product_name,
    category,
    size,
    temperature,
    list_price
FROM {{source('coffee_shop', 'dim_product')}}