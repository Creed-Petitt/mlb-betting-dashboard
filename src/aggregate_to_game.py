import sqlite3
import pandas as pd
from tqdm import tqdm

# Connect to the updated path
conn = sqlite3.connect("data/mlb.db")

# Load cleaned data
df = pd.read_sql("SELECT * FROM cleaned_plate_appearances", conn)
print(f"Loaded {len(df)} rows from cleaned_plate_appearances")

# BATTER GAME STATS
print("Aggregating batter game-level stats...")

# Get home team by batter-game
home = df.groupby(["batter", "game_date"])["home_team"].first()
away = df.groupby(["batter", "game_date"])["away_team"].first()
batter_team = df.groupby(["batter", "game_date"])["stand"].first().copy()  # placeholder for shape match

# For each batter/game, count rows and hits
batter_game = df.groupby(["batter", "game_date"]).agg(
    plate_appearances=("events", "count"),
    hits=("is_hit", "sum"),
    avg_launch_speed=("launch_speed", "mean"),
    avg_launch_angle=("launch_angle", "mean"),
    stand=("stand", "first"),
    home_team=("home_team", "first"),
    away_team=("away_team", "first")
).reset_index()

# Determine if batter played for home or away team
batter_game["is_home_game"] = (
    batter_game["home_team"] == batter_game["home_team"]
).astype(int)

batter_game.to_sql("batter_game_stats", conn, if_exists="replace", index=False)
print(f"Saved {len(batter_game)} batter-game rows")

# PITCHER GAME STATS

print("Aggregating pitcher game-level stats...")

pitcher_game = df.groupby(["pitcher", "game_date"]).agg(
    batters_faced=("events", "count"),
    hits_allowed=("is_hit", "sum"),
    avg_pitch_speed=("release_speed", "mean"),
    avg_exit_velo_against=("launch_speed", "mean"),
    p_throws=("p_throws", "first"),
    home_team=("home_team", "first"),
    away_team=("away_team", "first")
).reset_index()

pitcher_game["is_home_game"] = (
    pitcher_game["home_team"] == pitcher_game["home_team"]
).astype(int)

pitcher_game.to_sql("pitcher_game_stats", conn, if_exists="replace", index=False)
print(f"Saved {len(pitcher_game)} pitcher-game rows")

conn.close()
