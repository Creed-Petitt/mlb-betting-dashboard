import sqlite3
import pandas as pd

# Connect
conn = sqlite3.connect("data/mlb.db")

# Read base matchups
df = pd.read_sql("""
    SELECT 
        game_date, batter, pitcher,
        MAX(events IN ('single', 'double', 'triple', 'home_run')) AS hit_in_game
    FROM cleaned_plate_appearances
    GROUP BY game_date, batter, pitcher
""", conn, parse_dates=["game_date"])
print("Initial matchups:", len(df))

# Load feature tables
batter_game = pd.read_sql("SELECT * FROM batter_game_stats", conn, parse_dates=["game_date"])
pitcher_game = pd.read_sql("SELECT * FROM pitcher_game_stats", conn, parse_dates=["game_date"])
batter_career = pd.read_sql("SELECT * FROM batter_career_stats", conn)
pitcher_career = pd.read_sql("SELECT * FROM pitcher_career_stats", conn)

# Rename to avoid collision
batter_game = batter_game.rename(columns={
    "plate_appearances": "batter_plate_appearances",
    "hits": "batter_hits"
})
pitcher_game = pitcher_game.rename(columns={
    "plate_appearances": "pitcher_plate_appearances",
    "hits_allowed": "pitcher_hits_allowed"
})

# Merge stats
df = pd.merge(df, batter_game, on=["batter", "game_date"], how="left")
df = pd.merge(df, pitcher_game, on=["pitcher", "game_date"], how="left")
df = pd.merge(df, batter_career, on="batter", how="left")
df = pd.merge(df, pitcher_career, on="pitcher", how="left")

# Final required columns
required = [
    "batter_plate_appearances", "batting_avg", "career_avg",
    "pitcher_plate_appearances", "baa", "career_baa",
    "avg_launch_speed", "avg_launch_angle", "stand", "p_throws",
    "batter_team", "pitcher_team"
]
missing = [col for col in required if col not in df.columns]
if missing:
    raise ValueError(f"Missing expected columns after merge: {missing}")

df = df.dropna(subset=required)

# Save final output
df.to_sql("game_level_features", conn, if_exists="replace", index=False)
conn.close()
print("game_level_features table saved successfully.")
