import sqlite3
import pandas as pd

# Connect to the database and load clean plate appearances
conn = sqlite3.connect("data/mlb.db")
df = pd.read_sql_query("SELECT * FROM clean_plate_appearances", conn)
df["game_date"] = pd.to_datetime(df["game_date"])

# Group by batter per game and aggregate
agg = df.groupby(['game_date', 'batter']).agg({
    'events': 'count',
    'is_hit': 'sum',
    'total_bases': 'sum',
    'is_run_scored': 'sum',
    'is_batter_strikeout': 'sum',
    'ab': 'sum',
    'bb': 'sum',
    'so': 'sum',
    'is_home_game': 'last',
    'batter_team': 'last',
    'pitcher_team': 'last',
    'pitcher': 'last',  # ✅ this is the new column you need
    'stand': 'last',
    'p_throws': 'last',
    'day_of_week': 'last',
    'park_factor': 'last',
    'batter_hits_5g': 'last',
    'pitcher_hits_allowed_5g': 'last',
    'is_same_side': 'last'
}).reset_index()

# Rename for clarity
agg = agg.rename(columns={
    'is_hit': 'game_hits',
    'total_bases': 'game_total_bases',
    'is_batter_strikeout': 'game_strikeouts',
    'is_run_scored': 'game_runs_scored'
})

# Save result to SQL
agg.to_sql("game_level_stats", conn, if_exists="replace", index=False)
conn.close()

print(f"Saved game_level_stats with {len(agg)} rows (including pitcher ID).")


