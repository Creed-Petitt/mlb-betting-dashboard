import os
import time
import pandas as pd
from datetime import datetime
from pybaseball import statcast
from sqlalchemy import create_engine
import warnings

# -------------------------------
# Suppress Pybaseball Warnings
# -------------------------------
warnings.filterwarnings("ignore", category=FutureWarning)

# -------------------------------
# Configurable Parameters
# -------------------------------ce 
START_YEAR = 2015
END_YEAR = 2024
DATA_DIR = "data/cache"
DB_PATH = "data/mlb.db"

# -------------------------------
# Set up SQLAlchemy SQLite Engine
# -------------------------------
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}")

# -------------------------------
# Month Ranges to Pull (March to October)
# -------------------------------
MONTHS = ["03", "04", "05", "06", "07", "08", "09", "10"]

# -------------------------------
# Loop over each year/month and load into DB
# -------------------------------
for year in range(START_YEAR, END_YEAR + 1):
    for month in MONTHS:
        start_date = f"{year}-{month}-01"
        end_date = f"{year}-{month}-28"
        filename = f"{DATA_DIR}/statcast_{year}_{month}.csv"

        print(f"[{year}-{month}] Checking...", end=" ")

        # Skip if already cached
        if os.path.exists(filename):
            print("Cached. Skipping download.")
            try:
                df = pd.read_csv(filename)
            except Exception as e:
                print(f"Error reading cache: {e}")
                continue
        else:
            print("Downloading...", end=" ")
            try:
                df = statcast(start_dt=start_date, end_dt=end_date)
                if df.empty:
                    print("Empty. Skipped.")
                    continue
                df.to_csv(filename, index=False, encoding='utf-8')
                print(f"Saved {len(df)} rows.")
                time.sleep(2)
            except Exception as e:
                print(f"Failed to download: {e}")
                continue

        # Insert into DB
        try:
            df.to_sql("plate_appearances", engine, if_exists="append", index=False)
            print(f"Inserted {len(df)} rows into mlb.db.")
        except Exception as e:
            print(f"Failed to insert into DB: {e}")
