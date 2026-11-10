import os
from dotenv import load_dotenv
import psycopg2
from sqlalchemy import create_engine

def get_engine():
    load_dotenv()
    password = os.environ.get("POSTGRES_PASSWORD")
    if password is None:
        raise ValueError("POSTGRES_PASSWORD in .env file is missing!!!")

    url = f"postgresql+psycopg2://coffee_admin:{password}@localhost:5433/coffee_shop"
    engine = create_engine(url)
    return engine

def get_connection():
    load_dotenv()
    password = os.environ.get("POSTGRES_PASSWORD")
    if password is None:
        raise ValueError("POSTGRES_PASSWORD in .env file is missing!!!")

    conn = psycopg2.connect(
    host="localhost",
    port="5433",
    dbname="coffee_shop",
    user="coffee_admin",
    password=password
    )
    return conn

def get_ids(cur, query):
    cur.execute(query)
    rows = cur.fetchall()
    ids = []
    for row in rows:
        ids.append(row[0])
    return ids
    
