# Coffee Shop Sales Warehouse

A small data warehouse for a fictional chain of coffee shops in Sydney, Australia. ☕

Sales data is modelled as a **star schema** in **PostgreSQL**, loaded with Python ETL scripts, and analysed with SQL. The goal of the project is to practise dimensional modelling end to end: designing the model first, then building, loading and querying it.

Because there is no real coffee shop behind this project, a year of realistic sales (2025) is **generated with Python** using a fixed random seed, so every run produces exactly the same data.

---

## Tools

- **PostgreSQL 15**, running in **Docker** (Docker Compose)
- **Python**: `psycopg2` (loading), `SQLAlchemy` + `pandas` (analysis), `python-dotenv` (secrets)
- **SQL**: joins across the star schema, aggregation, normalisation
- **Git / GitHub**

---

## Data model

The model was designed on paper before any code was written.

```
                 dim_product
                      |
 dim_customer --- fact_sales --- dim_store
                      |
                  dim_date
```

### Fact table

**`fact_sales`** — grain: **one product in one order** (one line of a receipt).
An order with a cappuccino and a croissant becomes two rows that share the same `order_id`.

| Column | Type | Notes |
|---|---|---|
| `sale_id` | SERIAL | Surrogate key |
| `order_id` | INTEGER | Groups the lines of one receipt (degenerate dimension) |
| `date_key` | INTEGER | → `dim_date` |
| `store_id` | INTEGER | → `dim_store` |
| `product_id` | INTEGER | → `dim_product` |
| `customer_id` | INTEGER | → `dim_customer` |
| `quantity` | INTEGER | Measure |
| `amount` | NUMERIC(10,2) | Measure: quantity × price **at the time of sale** |

### Dimension tables

| Table | Rows | Natural key | Main attributes |
|---|---|---|---|
| `dim_product` | 11 | `product_name` + `size` + `temperature` | category, size, temperature, `list_price` |
| `dim_store` | 5 | `store_name` | suburb, city |
| `dim_customer` | 8 | `card_number` | name, loyalty tier (includes an `ANONYMOUS` customer for buyers without a loyalty card) |
| `dim_date` | 365 | `date_key` (e.g. `20251225`) | day name, month, quarter, year, `is_weekend`, `is_holiday` (NSW public holidays 2025) |

---

## How it works

Scripts run in this order:

1. **`schema.sql`** — creates the four dimension tables first, then `fact_sales` (which references them).
2. **`load_dimensions.py`** — loads products, stores, customers, and generates one row per day of 2025 for `dim_date`.
3. **`load_facts.py`** — reads the real IDs and current prices from the dimensions, generates 2,000 orders (1–3 items each, ~4,000 rows), and loads them into `fact_sales`.
4. **`analysis.py`** — runs analytical queries with `pandas.read_sql`.

`db.py` holds shared helpers used by all scripts: `get_connection()` (psycopg2, for writing), `get_engine()` (SQLAlchemy, for reading with pandas) and `get_ids()` (reads the list of IDs from a dimension).

---

## Design decisions

- **Dimensions before facts.** Every foreign key in `fact_sales` uses `REFERENCES`, so a sale can never point to a product, store, customer or day that does not exist.
- **Surrogate keys vs natural keys.** Each dimension has a `SERIAL` surrogate key for joins, plus a `UNIQUE` constraint on its natural key so the same real-world thing can never be inserted twice.
- **Idempotent dimension loads.** `INSERT ... ON CONFLICT ... DO NOTHING` for stores, customers and dates; `DO UPDATE` (upsert) for products, so a price change in the menu is applied by simply re-running the script.
- **The receipt never changes.** `amount` is calculated and stored when the sale is loaded. Changing `list_price` later only affects future sales; past revenue stays correct.
- **Full refresh for facts.** Because the sales are regenerated from a fixed seed, `load_facts.py` runs `TRUNCATE ... RESTART IDENTITY` before loading, so running it twice still gives the same ~4,000 rows. (A real system with millions of rows would use an incremental load instead.)
- **IDs are read from the database, never hard-coded.** If an ID is deleted or skipped, the generator still only uses IDs that really exist.

---

## Sample analysis

**Revenue per store (2025)**

| store_name | revenue |
|---|---|
| Manly Wharf | 7,021.60 |
| Parramatta | 6,506.20 |
| Bondi Beach | 6,505.90 |
| Surry Hills | 6,300.80 |
| Newtown | 5,763.70 |

Total: **$32,098.20** — matches `SUM(amount)` over the whole fact table, which confirms the join neither lost nor duplicated rows.

**Weekdays vs weekends, per category**

Total weekday drink sales are about 3× weekend sales, but there are 261 weekdays and only 104 weekend days. After **normalising to sales per day**, the difference is only about 15% for drinks and about 6% for pastries.

A second lesson came out of this query: a fact table only records events that happened. Days with **no** pastry sales do not appear in it, so counting days from `fact_sales` gives a slightly optimistic average. Counting days from `dim_date` (which contains every day) gives the fairer "per calendar day" number.

---

## Setup

Requirements: Docker Desktop and Python 3 with `psycopg2-binary`, `python-dotenv`, `pandas` and `sqlalchemy`.

```bash
# 1. Clone the repo and create your .env file
cp .env.example .env          # then set POSTGRES_PASSWORD

# 2. Start PostgreSQL (exposed on port 5433)
docker compose up -d

# 3. Create the tables
docker compose exec -T postgres psql -U coffee_admin -d coffee_shop < schema.sql
#   (PowerShell: Get-Content schema.sql | docker compose exec -T postgres psql -U coffee_admin -d coffee_shop)

# 4. Load the data (dimensions first!)
python load_dimensions.py
python load_facts.py

# 5. Run the analysis
python analysis.py
```

Note: the scripts connect to `127.0.0.1` instead of `localhost`. On Windows, `localhost` can first try an IPv6 address and wait before falling back, which made each connection take about 20 seconds; using `127.0.0.1` reduced it to under a second.

---

## Project structure

```
coffee-shop-warehouse/
├── docker-compose.yaml   # PostgreSQL 15 on port 5433
├── schema.sql            # star schema: 4 dimensions + fact_sales
├── db.py                 # get_connection, get_engine, get_ids
├── load_dimensions.py    # loads the four dimensions (idempotent)
├── load_facts.py         # generates and loads fact_sales (full refresh)
├── analysis.py           # analytical queries with pandas
├── .env.example          # template for the database password
└── .gitignore
```

---

## Next steps

- Schedule the pipeline with **Airflow** (dimensions first, then facts)
- Rebuild the transformations and tests with **dbt**
- Track product and customer changes over time with an **SCD Type 2** dimension
- Replace the full refresh with an **incremental** fact load