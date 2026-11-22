SELECT
    date_key,
    full_date,
    day_name,
    year,
    quarter,
    month,
    is_holiday,
    is_weekend
FROM {{source('coffee_shop', 'dim_date')}}