CREATE TABLE IF NOT EXISTS dim_product (
    product_id SERIAL PRIMARY KEY,
   product_name VARCHAR(100) NOT NULL,
   category VARCHAR(30) NOT NULL,
   size VARCHAR(30) NOT NULL,
   temperature VARCHAR(30) NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_store(
    store_id SERIAL PRIMARY KEY,
    store_name VARCHAR(100) NOT NULL,
    suburb VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id SERIAL PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    loyalty_tier VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL,
    day_name VARCHAR(50) NOT NULL,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    is_holiday BOOLEAN NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_sales (
    sale_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    date_key INTEGER NOT NULL  REFERENCES dim_date (date_key),
    store_id INTEGER NOT NULL REFERENCES dim_store(store_id),
    product_id INTEGER NOT NULL REFERENCES  dim_product (product_id),
    customer_id INTEGER NOT NULL REFERENCES dim_customer (customer_id),
    quantity INTEGER NOT NULL,
    amount NUMERIC(10, 2) NOT NULL
);

