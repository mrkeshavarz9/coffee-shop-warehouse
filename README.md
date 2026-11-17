# Coffee Shop Sales Warehouse

A small data warehouse for a fictional chain of coffee shops in Sydney, Australia. ☕

Sales data is modelled as a **star schema** in **PostgreSQL**, loaded with Python ETL scripts, orchestrated every day by **Apache Airflow**, and a daily report is delivered to **AWS S3**. The goal of the project is to practise dimensional modelling and pipeline orchestration end to end: designing the model first, then building, loading, scheduling and querying it.

Because there is no real coffee shop behind this project, a year of realistic sales (2025) is **generated with Python** using a fixed random seed, so every run produces exactly the same data.

---

## Tools

- **PostgreSQL 15**, running in **Docker** (Docker Compose)
- **Apache Airflow 3** (official Docker Compose setup) for scheduling and orchestration
- **AWS S3** (via `boto3`) for daily report files
- **Python**: `psycopg2` (loading), `SQLAlchemy` + `pandas` (analysis and export), `python-dotenv` (secrets and settings)
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

### The Airflow DAG

The pipeline runs daily as the Airflow DAG **`coffee_shop_daily`**:

```
[load_products]  ──┐
[load_stores]    ──┤                    ┌──→ [analysis]
                   ├──→ [load_facts] ───┤
[load_customers] ──┤                    └──→ [export_report] ──→ S3
[load_dates]     ──┘
```

- The four dimensions load **in parallel** (fan-in): they do not depend on each other.
- `load_facts` waits for **all four**, because every sale references them.
- `analysis` and `export_report` both read `fact_sales` only, so they run **in parallel** (fan-out). A failure in one does not block the other.
- Every task retries **2 times, 1 minute apart**, so short outages (for example a database restart) recover on their own.

Each task is a `BashOperator` that runs one of the project scripts inside the Airflow worker.

### The scripts

1. **`schema.sql`** — creates the four dimension tables first, then `fact_sales` (which references them).
2. **`load_dimensions.py <products|stores|customers|dates>`** — loads **one** dimension, chosen by a command-line argument, so Airflow can run the four loads as separate tasks. An unknown argument stops the script with a clear error before anything is committed.
3. **`load_facts.py`** — reads the real IDs and current prices from the dimensions, generates 2,000 orders (1–3 items each, ~4,000 rows), and loads them into `fact_sales`.
4. **`analysis.py`** — runs analytical queries with `pandas.read_sql` and prints the results (visible in the Airflow task logs).
5. **`export_report.py <YYYY-MM-DD>`** — writes the revenue-per-store report to CSV and uploads it to S3 as `store_revenue/<date>.csv`. Airflow passes the run date with `{{ ds }}`.

Shared code:
- **`db.py`** — `get_connection()` (psycopg2, for writing), `get_engine()` (SQLAlchemy, for reading with pandas) and `get_ids()` (reads the list of IDs from a dimension).
- **`queries.py`** — SQL used by more than one script (for example `STORE_REVENUE_QUERY`), written once so it cannot drift between files.

---

## Design decisions

### Data model and loading

- **Dimensions before facts.** Every foreign key in `fact_sales` uses `REFERENCES`, so a sale can never point to a product, store, customer or day that does not exist.
- **Surrogate keys vs natural keys.** Each dimension has a `SERIAL` surrogate key for joins, plus a `UNIQUE` constraint on its natural key so the same real-world thing can never be inserted twice.
- **Idempotent dimension loads.** `INSERT ... ON CONFLICT ... DO NOTHING` for stores, customers and dates; `DO UPDATE` (upsert) for products, so a price change in the menu is applied by simply re-running the script.
- **The receipt never changes.** `amount` is calculated and stored when the sale is loaded. Changing `list_price` later only affects future sales; past revenue stays correct.
- **Full refresh for facts.** Because the sales are regenerated from a fixed seed, `load_facts.py` runs `TRUNCATE ... RESTART IDENTITY` before loading, so running it twice still gives the same ~4,000 rows. (A real system with millions of rows would use an incremental load instead.)
- **IDs are read from the database, never hard-coded.** If an ID is deleted or skipped, the generator still only uses IDs that really exist.

### Orchestration

- **Every task is safe to run more than once.** Airflow re-runs tasks on retries, on manual *Clear*, and on backfills, so all loads are idempotent and the S3 report overwrites the file for the same date instead of creating a duplicate.
- **Tasks only wait for what they really need.** The export does not wait for the analysis, so a problem in one cannot block the other.
- **Configuration lives in the environment, not in the code.** `db.py` reads `DB_HOST` and `DB_PORT` from environment variables with local defaults (`127.0.0.1`, `5433`). Inside the Airflow containers they are set to `host.docker.internal` and `5433`, because inside a container `127.0.0.1` means the container itself, not the Windows host. The same code runs in both places without changes.

### Security

- **Least privilege on AWS.** The pipeline uses a dedicated IAM user (`coffee-shop-etl`) with S3 access only, never the root account. Keys live only in `.env`, which is git-ignored.
- **A zero-spend budget alert** is set on the AWS account, so any unexpected cost is noticed immediately.
- While setting this up, the IAM dashboard showed that the root account still had an active access key that had been used recently. It was traced to old `aws configure` credentials that `boto3` falls back to when no environment keys are found. The root key was deactivated, and both the local run and the Airflow run were re-tested to confirm they use the IAM user.

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

Requirements: Docker Desktop, Python 3 with `psycopg2-binary`, `python-dotenv`, `pandas`, `sqlalchemy` and `boto3`, and an AWS account with an S3 bucket and an IAM user that can write to it.

### 1. Database

```bash
# Create your .env file
cp .env.example .env          # set POSTGRES_PASSWORD and the AWS_* values

# Start PostgreSQL (exposed on port 5433)
docker compose up -d

# Create the tables
docker compose exec -T postgres psql -U coffee_admin -d coffee_shop < schema.sql
#   (PowerShell: Get-Content schema.sql | docker compose exec -T postgres psql -U coffee_admin -d coffee_shop)
```

### 2. Run the scripts by hand (optional)

```bash
python load_dimensions.py products
python load_dimensions.py stores
python load_dimensions.py customers
python load_dimensions.py dates
python load_facts.py
python analysis.py
python export_report.py 2026-11-16
```

The S3 bucket name is set in `export_report.py`; change it to your own bucket.

### 3. Airflow

```bash
cd airflow

# airflow/.env (git-ignored) should contain:
#   AIRFLOW_UID=50000
#   _PIP_ADDITIONAL_REQUIREMENTS=python-dotenv

docker compose up airflow-init     # first time only
docker compose up -d
```

Open `http://localhost:8080` (login `airflow` / `airflow` in the quick-start setup), unpause **`coffee_shop_daily`**, and trigger it.

Changes made to the official Airflow `docker-compose.yaml`:
- the project folder is mounted into the containers at `/opt/airflow/project`
- `DB_HOST: host.docker.internal` and `DB_PORT: '5433'` are added to the shared environment
- example DAGs are switched off (`AIRFLOW__CORE__LOAD_EXAMPLES: 'false'`)

Notes:
- The scripts connect to `127.0.0.1` instead of `localhost` by default. On Windows, `localhost` can first try an IPv6 address and wait before falling back, which made each connection take about 20 seconds; using `127.0.0.1` reduced it to under a second.
- Airflow schedules in **UTC**, so the daily run starts at midnight UTC (3:30 am in Tehran, 11 am in Sydney).

---

## Project structure

```
coffee-shop-warehouse/
├── docker-compose.yaml        # PostgreSQL 15 on port 5433
├── schema.sql                 # star schema: 4 dimensions + fact_sales
├── db.py                      # get_connection, get_engine, get_ids
├── queries.py                 # shared SQL queries
├── load_dimensions.py         # loads one dimension per run (idempotent)
├── load_facts.py              # generates and loads fact_sales (full refresh)
├── analysis.py                # analytical queries with pandas
├── export_report.py           # daily revenue report → S3
├── .env.example               # template for database and AWS settings
├── .gitignore
└── airflow/
    ├── docker-compose.yaml    # official Airflow 3 setup, with the changes above
    └── dags/
        └── coffee_shop_daily.py
```

---

## Next steps

- Rebuild the transformations and tests with **dbt**
- Track product and customer changes over time with an **SCD Type 2** dimension
- Replace the full refresh with an **incremental** fact load that uses the Airflow run date
- Restrict the IAM policy to this one bucket instead of all of S3
- Send an alert (for example email) when a task fails after all retries
