SELECT
    store_id,
    store_name,
    suburb,
    city
FROM {{source('coffee_shop', 'dim_store')}}