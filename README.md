# Coffee Shop Sales Warehouse

A small data warehouse for a fictional chain of coffee shops in Sydney, Australia. ☕

Sales data is modelled as a **star schema** in **PostgreSQL**, loaded with Python ETL scripts, transformed and tested with **dbt**, orchestrated every day by **Apache Airflow**, and a daily report is delivered to **AWS S3**. The goal of the project is to practise the full lifecycle of a data warehouse: designing the model first, then building, loading, transforming, testing, scheduling and querying it.

Because there is no real coffee shop behind this project, a year of realistic sales (2025) is **generated with Python** using a fixed random seed, so every run produces exactly the same data.

---

## Tools

- **PostgreSQL 15**, running in **Docker** (Docker Compose)
- **dbt Core 1.11** with the **dbt-postgres** adapter for transformations, tests, documentation and snapshots
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
[load_stores]    ──┤                                     ┌──→ [analysis]
                   ├──→ [load_facts] ──→ [dbt_build] ────┤
[load_customers] ──┤                                     └──→ [export_report] ──→ S3
[load_dates]     ──┘
```

- The four dimensions load **in parallel** (fan-in): they do not depend on each other.
- `load_facts` waits for **all four**, because every sale references them.
- `dbt_build` runs every dbt model, test and snapshot. It is a **quality gate**: if any data test fails, the analysis and the S3 report do not run, so no one receives numbers from broken data.
- `analysis` and `export_report` run **in parallel** after the gate (fan-out).
- Every task retries **2 times, 1 minute apart**, so short outages (for example a database restart) recover on their own.

### Loading (Python)

1. **`schema.sql`** — creates the four dimension tables first, then `fact_sales` (which references them).
2. **`load_dimensions.py <products|stores|customers|dates>`** — loads **one** dimension, chosen by a command-line argument, so Airflow can run the four loads as separate tasks. An unknown argument stops the script with a clear error before anything is committed.
3. **`load_facts.py`** — reads the real IDs and current prices from the dimensions, generates 2,000 orders (1–3 items each, ~4,000 rows), and loads them into `fact_sales`.

### Transforming and testing (dbt)

The dbt project lives in **`coffee_dbt/`** and follows a layered structure:

```
sources (raw, schema public)  →  staging (views)  →  marts (tables)
   fact_sales                      stg_sales          store_revenue
   dim_store                       stg_stores         revenue_by_loyalty_tier
   dim_product                     stg_products
   dim_customer                    stg_customers
   dim_date                        stg_dates
```

- **Sources** (`models/sources.yml`) declare the raw tables loaded by Python.
- **Staging** models are one per source: explicit column lists and clearer names (for example `amount` → `sales_amount`). **Only staging models read sources**; everything else reads staging through `ref()`, so a change in a raw table is fixed in one place.
- **Marts** are the business-facing reports.
- Materialization is set **per folder** in `dbt_project.yml`: staging as views, marts as tables.
- dbt builds everything in the `analytics` schema, separate from the raw tables in `public`.

**Data tests** (14 in total), all passing:

| Test | Example |
|---|---|
| `unique` / `not_null` | `sale_id`, every staging key, and `loyalty_tier` (the grain of its mart) |
| `relationships` | every `store_id` in `stg_sales` exists in `stg_stores` |
| `accepted_values` | `category` is only `Drink` or `Pastry` |

**Snapshot** (`snapshots/product_snapshot.yml`) keeps the history of menu prices as an **SCD Type 2** table in the `analytics_snapshots` schema. The Python load overwrites `list_price` (Type 1), so without the snapshot the old price would be lost. Each version gets `dbt_valid_from` and `dbt_valid_to`; the current price is the row where `dbt_valid_to` is null.

**Documentation** is generated with `dbt docs generate` and includes model and column descriptions, the tests on each column, and the full lineage graph.

### Analysis and export

- **`analysis.py`** — runs analytical queries with `pandas.read_sql` and prints the results (visible in the Airflow task logs).
- **`export_report.py <YYYY-MM-DD>`** — writes the revenue-per-store report to CSV and uploads it to S3 as `store_revenue/<date>.csv`. Airflow passes the run date with `{{ ds }}`.

Shared code:
- **`db.py`** — `get_connection()` (psycopg2, for writing), `get_engine()` (SQLAlchemy, for reading with pandas) and `get_ids()` (reads the list of IDs from a dimension).
- **`queries.py`** — SQL used by more than one script (for example `STORE_REVENUE_QUERY`), written once so it cannot drift between files.

---

## Design decisions

### Data model and loading

- **Dimensions before facts.** Every foreign key in `fact_sales` uses `REFERENCES`, so a sale can never point to a product, store, customer or day that does not exist.
- **Surrogate keys vs natural keys.** Each dimension has a `SERIAL` surrogate key for joins, plus a `UNIQUE` constraint on its natural key so the same real-world thing can never be inserted twice.
- **Idempotent dimension loads.** `INSERT ... ON CONFLICT ... DO NOTHING` for stores, customers and dates; `DO UPDATE` (upsert) for products, so a price change in the menu is applied by simply re-running the script.
- **The receipt never changes.** `amount` is calculated and stored when the sale is loaded. Changing `list_price` later only affects future sales; past revenue stays correct. (In this project the fact table is regenerated with a full refresh, which recalculates amounts with current prices; a real system would load facts incrementally so old receipts are never rewritten.)
- **Full refresh for facts.** Because the sales are regenerated from a fixed seed, `load_facts.py` runs `TRUNCATE ... RESTART IDENTITY` before loading, so running it twice still gives the same ~4,000 rows.
- **IDs are read from the database, never hard-coded.** If an ID is deleted or skipped, the generator still only uses IDs that really exist.

### dbt

- **Layers protect reports from raw-data changes.** Only staging touches sources, so renaming a raw column means changing one staging model, not every report.
- **Every mart documents its grain and protects it with a `unique` test.** If a join ever duplicates rows, the test fails before the report is published.
- **Caveats are documented, not hidden.** In `revenue_by_loyalty_tier`, the `None` tier is a single `ANONYMOUS` customer that stands for every buyer without a card, so its revenue per customer is not the spend of one real person. This is written in the column description.
- **Tests check assumptions as well as data.** A deliberate `unique` test on `store_id` in `stg_sales` failed, because many sales share a store; the lesson was that the test, not the data, was wrong for that grain.

### Orchestration

- **Every task is safe to run more than once.** Airflow re-runs tasks on retries, on manual *Clear*, and on backfills, so all loads are idempotent and the S3 report overwrites the file for the same date instead of creating a duplicate.
- **Tasks only wait for what they really need.** The four dimensions load in parallel, and `dbt_build` waits only for `load_facts`, which already waits for every dimension.
- **No duplicated work.** An earlier version had a separate `dbt snapshot` task, but the `dbt_build` log showed that `dbt build` already runs snapshots, so the separate task was removed.
- **Configuration lives in the environment, not in the code.** `db.py` and `coffee_dbt/profiles.yml` read the database host, port and password from environment variables (`DB_HOST`, `DB_PORT`, `POSTGRES_PASSWORD`), with local defaults for host (`127.0.0.1`) and port (`5433`) but no default for the password. Inside the Airflow containers the host is `host.docker.internal`, because inside a container `127.0.0.1` means the container itself, not the Windows host. The same code and the same `profiles.yml` run in both places, and `profiles.yml` contains no secrets, so it is safe to commit.

### Security

- **Least privilege on AWS.** The pipeline uses a dedicated IAM user (`coffee-shop-etl`) with S3 access only, never the root account. Keys live only in `.env`, which is git-ignored.
- **A zero-spend budget alert** is set on the AWS account, so any unexpected cost is noticed immediately.
- While setting this up, the IAM dashboard showed that the root account still had an active access key that had been used recently. It was traced to old `aws configure` credentials that `boto3` falls back to when no environment keys are found. The root key was deactivated, and both the local run and the Airflow run were re-tested to confirm they use the IAM user.
- **Secrets are checked without printing them.** To confirm a container received the database password, the check only tests whether the variable is set, so the value never appears in terminal output or logs.

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

**Revenue by loyalty tier** (dbt mart `revenue_by_loyalty_tier`)

| loyalty_tier | customers | revenue | revenue_per_customer | orders |
|---|---|---|---|---|
| Silver | 3 | 12,176.90 | 4,058.97 | 766 |
| Bronze | 2 | 8,177.50 | 4,088.75 | 502 |
| Gold | 2 | 8,070.70 | 4,035.35 | 494 |
| None | 1 | 3,673.10 | 3,673.10 | 238 |

Orders add up to **2,000** and revenue to **$32,098.20**, matching the totals of the fact table. Silver looks strongest only because it has the most customers; **per customer**, all tiers are almost the same (as expected, since customers were drawn uniformly at random). The `None` row is kept on purpose: comparing members with non-members is exactly what the business question asks.

**Weekdays vs weekends, per category**

Total weekday drink sales are about 3× weekend sales, but there are 261 weekdays and only 104 weekend days. After **normalising to sales per day**, the difference is only about 15% for drinks and about 6% for pastries.

A second lesson came out of this query: a fact table only records events that happened. Days with **no** pastry sales do not appear in it, so counting days from `fact_sales` gives a slightly optimistic average. Counting days from `dim_date` (which contains every day) gives the fairer "per calendar day" number.

---

## Setup

Requirements: Docker Desktop, Python 3 with `psycopg2-binary`, `python-dotenv`, `pandas`, `sqlalchemy` and `boto3`, a separate Python environment with `dbt-core` and `dbt-postgres` 1.11, and an AWS account with an S3 bucket and an IAM user that can write to it.

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

### 2. Run the pipeline by hand (optional)

```bash
python load_dimensions.py products
python load_dimensions.py stores
python load_dimensions.py customers
python load_dimensions.py dates
python load_facts.py
```

Then dbt, from a separate environment (dbt does not read `.env`, so the password must be set in the shell):

```powershell
conda create -n dbt python=3.11 -y
conda activate dbt
python -m pip install "dbt-core~=1.11.0" "dbt-postgres~=1.11.0"

cd coffee_dbt
$env:POSTGRES_PASSWORD = "<your password>"
dbt debug                            # should end with "All checks passed!"
dbt build                            # models, tests and snapshot
dbt docs generate
dbt docs serve --port 8081           # 8080 is used by Airflow
```

And the reports:

```bash
python analysis.py
python export_report.py 2026-11-16
```

The S3 bucket name is set in `export_report.py`; change it to your own bucket.

### 3. Airflow

```bash
cd airflow

# airflow/.env (git-ignored) should contain:
#   AIRFLOW_UID=50000
#   _PIP_ADDITIONAL_REQUIREMENTS=python-dotenv dbt-core~=1.11.0 dbt-postgres~=1.11.0

docker compose up airflow-init     # first time only
docker compose up -d
```

Open `http://localhost:8080` (login `airflow` / `airflow` in the quick-start setup), unpause **`coffee_shop_daily`**, and trigger it.

Changes made to the official Airflow `docker-compose.yaml`:
- the project folder is mounted into the containers at `/opt/airflow/project`
- the project `.env` is added to the shared `env_file` list, so the containers receive the database password and AWS keys
- `DB_HOST: host.docker.internal` and `DB_PORT: '5433'` are added to the shared environment
- example DAGs are switched off (`AIRFLOW__CORE__LOAD_EXAMPLES: 'false'`)

Notes:
- The scripts connect to `127.0.0.1` instead of `localhost` by default. On Windows, `localhost` can first try an IPv6 address and wait before falling back, which made each connection take about 20 seconds; using `127.0.0.1` reduced it to under a second.
- Airflow schedules in **UTC**, so the daily run starts at midnight UTC (3:30 am in Tehran, 11 am in Sydney).
- Installing dbt with `_PIP_ADDITIONAL_REQUIREMENTS` happens every time the containers start, which is fine for local practice; a production setup would build a custom Airflow image instead.
- dbt Core 1.11 is used on purpose: installing 1.12 repeatedly failed because one of its packages downloads a large file during installation over an unstable connection.

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
├── coffee_dbt/
│   ├── dbt_project.yml        # materialization per folder
│   ├── profiles.yml           # connection via environment variables (no secrets)
│   ├── models/
│   │   ├── sources.yml
│   │   ├── staging/           # 5 staging views + tests and descriptions
│   │   └── marts/             # store_revenue, revenue_by_loyalty_tier + tests
│   └── snapshots/
│       └── product_snapshot.yml
└── airflow/
    ├── docker-compose.yaml    # official Airflow 3 setup, with the changes above
    └── dags/
        └── coffee_shop_daily.py
```

---

## Next steps

- Replace the full refresh with an **incremental** fact load that uses the Airflow run date
- Run dbt on a **cloud data warehouse** (BigQuery or Snowflake)
- Add **pytest** tests for the Python scripts and run them in **GitHub Actions** (CI)
- Restrict the IAM policy to this one bucket instead of all of S3
- Set a proper `FERNET_KEY` for Airflow and build a custom Airflow image instead of installing packages at start-up
- Send an alert (for example email) when a task fails after all retries
