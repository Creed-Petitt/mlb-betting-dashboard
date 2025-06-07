import sqlite3
import pandas as pd
from props import get_fanduel_hit_props

# Load props and normalize names
props = pd.DataFrame(get_fanduel_hit_props())
props["player"] = props["player"].str.strip().str.lower()

# Load cached rosters and normalize names
conn = sqlite3.connect("data/mlb.db")
rosters = pd.read_sql("SELECT * FROM cached_rosters", conn)
rosters["player"] = rosters["full_name"].str.strip().str.lower()
conn.close()

# Merge on normalized player names
merged = props.merge(rosters, how="left", on="player")

# Show unmatched players
unmatched = merged[merged["mlb_id"].isna()]
if not unmatched.empty:
    print("No match for:")
    for name in unmatched["player"].unique():
        print(name)

# Drop unmatched for now
merged = merged.dropna(subset=["mlb_id"])

# Save matched props to database
conn = sqlite3.connect("data/mlb.db")
merged.to_sql("matched_hit_props", conn, if_exists="replace", index=False)
conn.close()

print(f"Saved {len(merged)} matched props to matched_hit_props")
