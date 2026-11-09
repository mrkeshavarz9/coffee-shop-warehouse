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

conn = get_connection()
cur = conn.cursor()

cur.executemany("""
    INSERT INTO dim_product (product_name, category, size, temperature)
    VALUES(%s, %s, %s, %s)
    ON CONFLICT (product_name, size, temperature) DO NOTHING
""", products
)

conn.commit()
cur.close()
conn.close()
print("products are loaded!")