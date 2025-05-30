import sqlite3
import pandas as pd

# Connect and load plate appearance data 
conn = sqlite3.connect("data/mlb.db")
df = pd.read_sql_query("SELECT * FROM clean_plate_appearances", conn)

# Make sure dates are datetime 
df['game_date'] = pd.to_datetime(df['game_date'])

# Group to 1 row per batter per game 
agg = df.groupby(['game_date', 'batter']).agg({
    'is_hit': 'sum',
    'total_bases': 'sum',
    'is_batter_strikeout': 'sum',
    'is_run_scored': 'sum',
    'batter_hits_5g': 'last',
    'pitcher_hits_allowed_5g': 'last',
    'is_same_side': 'last',
    'stand': 'last',
    'p_throws': 'last',
    'batter_team': 'last',
    'pitcher_team': 'last',
    'is_home_game': 'last',
    'day_of_week': 'last',
    'park_factor': 'last'
}).reset_index()

# Rename target columns 
agg.rename(columns={
    'is_hit': 'game_hits',
    'total_bases': 'game_total_bases',
    'is_batter_strikeout': 'game_strikeouts',
    'is_run_scored': 'game_runs_scored'
}, inplace=True)

# Save to new SQL table 
agg.to_sql("game_level_stats", conn, if_exists="replace", index=False)
conn.close()

print(f"\nGame-level stats table created: {len(agg)} rows saved to 'game_level_stats'")
