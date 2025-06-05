import sqlite3
import pandas as pd
import os
from glob import glob

# Config
DB_PATH = "data/mlb.db"
TABLE_NAME = "plate_appearances"
CSV_DIR = "data/cache"

# Create output folder if missing
os.makedirs("data", exist_ok=True)

# Connect to DB and clear existing table
conn = sqlite3.connect(DB_PATH)
conn.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
conn.commit()

# Find matching CSV files
csv_files = sorted(glob(os.path.join(CSV_DIR, "statcast_*.csv")))

# Load and insert each
for file in csv_files:
    print(f"Loading {file}...")
    df = pd.read_csv(file)
    df.to_sql(TABLE_NAME, conn, if_exists="append", index=False)

print(f"Loaded {len(csv_files)} files into table '{TABLE_NAME}'")
conn.close()
