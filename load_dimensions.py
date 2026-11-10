from db import get_connection

products = [
    ("Espresso",        "Drink",  "Small", "Hot"),
    ("Cappuccino",      "Drink",  "Small", "Hot"),
    ("Cappuccino",      "Drink",  "Large", "Hot"),
    ("Flat White",      "Drink",  "Small", "Hot"),
    ("Latte",           "Drink",  "Large", "Hot"),
    ("Chai Latte",      "Drink",  "Large", "Hot"),
    ("Iced Latte",      "Drink",  "Large", "Cold"),
    ("Cold Brew",       "Drink",  "Large", "Cold"),
    ("Croissant",       "Pastry", "N/A",   "N/A"),
    ("Banana Bread",    "Pastry", "N/A",   "N/A"),
    ("Blueberry Muffin","Pastry", "N/A",   "N/A"),
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

conn = get_connection()
cur = conn.cursor()

cur.executemany("""
    INSERT INTO dim_product (product_name, category, size, temperature)
    VALUES(%s, %s, %s, %s)
    ON CONFLICT (product_name, size, temperature) DO NOTHING
""", products)

cur.executemany("""
    INSERT INTO dim_store (store_name, suburb, city)
    VALUES (%s, %s, %s)
    ON CONFLICT (store_name) DO NOTHING
""", stores)

cur.executemany("""
    INSERT INTO dim_customer (card_number, customer_name, loyalty_tier)
    VALUES (%s, %s, %s)
    ON CONFLICT (card_number) DO NOTHING
""", customers)

conn.commit()
cur.close()
conn.close()
print("dimensions  are loaded!")