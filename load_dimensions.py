from db import get_connection
from datetime import date, timedelta
import sys

products = [
    ("Espresso",        "Drink",  "Small", "Hot", 4.00),
    ("Cappuccino",      "Drink",  "Small", "Hot", 4.80),
    ("Cappuccino",      "Drink",  "Large", "Hot", 5.80),
    ("Flat White",      "Drink",  "Small", "Hot", 4.80),
    ("Latte",           "Drink",  "Large", "Hot", 5.80),
    ("Chai Latte",      "Drink",  "Large", "Hot", 5.50),
    ("Iced Latte",      "Drink",  "Large", "Cold", 6.50),
    ("Cold Brew",       "Drink",  "Large", "Cold", 6.00),
    ("Croissant",       "Pastry", "N/A",   "N/A", 5.00),
    ("Banana Bread",    "Pastry", "N/A",   "N/A", 5.50),
    ("Blueberry Muffin","Pastry", "N/A",   "N/A", 5.00),
]

stores = [
    ("Bondi Beach",   "Bondi",       "Sydney"),
    ("Manly Wharf",   "Manly",       "Sydney"),
    ("Surry Hills",   "Surry Hills", "Sydney"),
    ("Newtown",       "Newtown",     "Sydney"),
    ("Parramatta",    "Parramatta",  "Sydney"),
]

customers = [
    ("ANONYMOUS",  "Anonymous", "None"),
    ("CARD-10001", "Sarah",     "Gold"),
    ("CARD-10002", "James",     "Silver"),
    ("CARD-10003", "Olivia",    "Bronze"),
    ("CARD-10004", "Liam",      "Gold"),
    ("CARD-10005", "Sarah",     "Silver"),
    ("CARD-10006", "Noah",      "Bronze"),
    ("CARD-10007", "Mia",       "Silver"),
]

holidays = {
    date(2025, 1, 1),    # New Year's Day
    date(2025, 1, 27),   # Australia Day (observed)
    date(2025, 4, 18),   # Good Friday
    date(2025, 4, 19),   # Easter Saturday
    date(2025, 4, 20),   # Easter Sunday
    date(2025, 4, 21),   # Easter Monday
    date(2025, 4, 25),   # Anzac Day
    date(2025, 6, 9),    # King's Birthday
    date(2025, 10, 6),   # Labour Day
    date(2025, 12, 25),  # Christmas Day
    date(2025, 12, 26),  # Boxing Day
}

def build_date_row(d):
    date_key = int(d.strftime("%Y%m%d"))
    full_date = d
    day_name = d.strftime("%A")
    year = d.year
    quarter = (d.month - 1) // 3 + 1
    month = d.month
    is_holiday = d in holidays
    is_weekend = d.weekday() >= 5
    row = (date_key, full_date, day_name, year, quarter, month, is_holiday, is_weekend)
    return row


date_rows = []
start = date(2025, 1, 1)
end = date(2025, 12, 31)
d = start
while d <= end:
    row = build_date_row(d)
    date_rows.append(row)
    d = d + timedelta(days=1)


def load_products(cur):
    cur.executemany("""
        INSERT INTO dim_product (product_name, category, size, temperature, list_price)
        VALUES(%s, %s, %s, %s, %s)
        ON CONFLICT (product_name, size, temperature) DO UPDATE SET
            list_price = EXCLUDED.list_price
    """, products)

def load_stores(cur):
    cur.executemany("""
        INSERT INTO dim_store (store_name, suburb, city)
        VALUES (%s, %s, %s)
        ON CONFLICT (store_name) DO NOTHING
    """, stores)

def load_customers(cur):
    cur.executemany("""
        INSERT INTO dim_customer (card_number, customer_name, loyalty_tier)
        VALUES (%s, %s, %s)
        ON CONFLICT (card_number) DO NOTHING
    """, customers)

def load_dates(cur):
    cur.executemany("""
        INSERT INTO dim_date (date_key, full_date, day_name, year, quarter, month, is_holiday, is_weekend)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (date_key ) DO NOTHING
    """, date_rows)


if __name__ == "__main__":
    conn = get_connection()
    cur = conn.cursor()
    choice = sys.argv[1]
    if choice == "products":
     load_products(cur)
    elif choice == "stores":
     load_stores(cur)
    elif choice == "customers":
     load_customers(cur)
    elif choice == "dates":
     load_dates(cur)
    else:
        raise ValueError (f"Unknown dimension: {choice}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"{choice} loaded!")