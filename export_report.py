import pandas as pd
from db import get_engine
from queries import STORE_REVENUE_QUERY
import boto3
import sys

if len(sys.argv) < 2:
    raise ValueError("Usage: python export_report.py YYYY-MM-DD")

report_date = sys.argv[1]

engine = get_engine()


store_revenue = pd.read_sql(STORE_REVENUE_QUERY, engine)

store_revenue.to_csv("store_revenue.csv", index=False)

s3 = boto3.client("s3")
s3.upload_file(
    "store_revenue.csv",
    "coffee-shop-reports-mrkeshavarz9",
    f"store_revenue/{report_date}.csv",
)
print(f"Uploaded store_revenue/{report_date}.csv")