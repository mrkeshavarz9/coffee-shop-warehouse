SELECT
    customer_id,
    customer_name,
    loyalty_tier,
    card_number
FROM {{source('coffee_shop', 'dim_customer')}}