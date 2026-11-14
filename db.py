import os
from dotenv import load_dotenv
import psycopg2
from sqlalchemy import create_engine

def get_engine():
    load_dotenv()
    password = os.environ.get("POSTGRES_PASSWORD")
    if password is None:
        raise ValueError("POSTGRES_PASSWORD in .env file is missing!!!")
    
    host = os.environ.get("DB_HOST","127.0.0.1")
    port = os.environ.get("DB_PORT","5433")

    url = f"postgresql+psycopg2://coffee_admin:{password}@{host}:{port}/coffee_shop"
    engine = create_engine(url)
    return engine

def get_connection():
    load_dotenv()
    password = os.environ.get("POSTGRES_PASSWORD")
    if password is None:
        raise ValueError("POSTGRES_PASSWORD in .env file is missing!!!")

    host = os.environ.get("DB_HOST","127.0.0.1")
    port = os.environ.get("DB_PORT","5433")

    conn = psycopg2.connect(
    host=host,
    port=port,
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
    
