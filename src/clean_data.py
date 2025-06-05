import sqlite3
import pandas as pd
from tqdm import tqdm

# Connect to your Statcast database
conn = sqlite3.connect("data/mlb.db")
cursor = conn.cursor()

# Optional safety: delete existing cleaned table to avoid duplicate appends
cursor.execute("DROP TABLE IF EXISTS cleaned_plate_appearances")
conn.commit()

# Get all months available in the data
query_months = """
SELECT DISTINCT strftime('%Y-%m', game_date) AS month
FROM plate_appearances
ORDER BY month;
"""
months = pd.read_sql(query_months, conn)["month"].tolist()

# Define what counts as a hit
hit_events = ["single", "double", "triple", "home_run"]

for month in tqdm(months, desc="Cleaning month-by-month"):
    print(f"\nProcessing month: {month}")

    # Load one month of data
    query = f"""
    SELECT * FROM plate_appearances
    WHERE strftime('%Y-%m', game_date) = '{month}';
    """
    df = pd.read_sql(query, conn)

    # Drop rows where critical fields are missing
    df = df.dropna(subset=["batter", "pitcher", "events"])

    # Add binary hit indicator
    df["is_hit"] = df["events"].isin(hit_events).astype(int)

    # Create unique batter and pitcher game IDs
    df["batter_game_id"] = df["batter"].astype(str) + "_" + df["game_date"]
    df["pitcher_game_id"] = df["pitcher"].astype(str) + "_" + df["game_date"]

    # Append to the cleaned_plate_appearances table
    df.to_sql("cleaned_plate_appearances", conn, if_exists="append", index=False)

    print(f"{len(df)} rows saved for {month} — hits: {df['is_hit'].sum()}")

# Final row count
final_check = pd.read_sql("SELECT COUNT(*) AS total FROM cleaned_plate_appearances;", conn)
print(f"\nDone! Total cleaned rows: {final_check['total'][0]}")

conn.close()
