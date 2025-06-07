import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pybaseball import statcast
from tqdm import tqdm

# === CONFIG ===
DB_PATH = "data/mlb.db"

# === STEP 1: Detect last date in plate_appearances ===
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT MAX(game_date) FROM plate_appearances;")
last_date = cursor.fetchone()[0]
conn.close()

if last_date is None:
    raise ValueError("plate_appearances table is empty or missing.")

start_date = (datetime.strptime(last_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
end_date = datetime.today().strftime("%Y-%m-%d")

if start_date > end_date:
    print("No new games to fetch.")
    exit()

print(f"Fetching new Statcast data: {start_date} to {end_date}")

# === STEP 2: Fetch and append new plate appearances ===
new_data = statcast(start_dt=start_date, end_dt=end_date)
new_data["game_date"] = pd.to_datetime(new_data["game_date"]).dt.strftime("%Y-%m-%d")

conn = sqlite3.connect(DB_PATH)
new_data.to_sql("plate_appearances", conn, if_exists="append", index=False)
print(f"Appended {len(new_data)} new rows to plate_appearances")

# === STEP 3: Clean and update cleaned_plate_appearances ===
hit_events = ["single", "double", "triple", "home_run"]

new_data = new_data.dropna(subset=["batter", "pitcher", "events"])
new_data["is_hit"] = new_data["events"].isin(hit_events).astype(int)
new_data["batter_game_id"] = new_data["batter"].astype(str) + "_" + new_data["game_date"]
new_data["pitcher_game_id"] = new_data["pitcher"].astype(str) + "_" + new_data["game_date"]
new_data.to_sql("cleaned_plate_appearances", conn, if_exists="append", index=False)
print(f"Appended to cleaned_plate_appearances")

# === STEP 4: Recompute all stats ===
df = pd.read_sql("SELECT * FROM cleaned_plate_appearances", conn, parse_dates=["game_date"])
df = df.sort_values("game_date")
df["is_hit"] = df["events"].isin(hit_events).astype(int)

# Game-level stats (batters)
batter_game = df.groupby(["batter", "game_date"]).agg(
    plate_appearances=("events", "count"),
    hits=("is_hit", "sum"),
    avg_launch_speed=("launch_speed", "mean"),
    avg_launch_angle=("launch_angle", "mean"),
    stand=("stand", "first"),
    batter_team=("bat_score", "last"),
    is_home_game=("home_team", "first")
).reset_index()
batter_game["batting_avg"] = batter_game["hits"] / batter_game["plate_appearances"]

# Game-level stats (pitchers)
pitcher_game = df.groupby(["pitcher", "game_date"]).agg(
    plate_appearances=("events", "count"),
    hits_allowed=("is_hit", "sum"),
    p_throws=("p_throws", "first"),
    pitcher_team=("fld_score", "last"),
).reset_index()
pitcher_game["baa"] = pitcher_game["hits_allowed"] / pitcher_game["plate_appearances"]

# Rolling 5G stats
rolling_batter = []
for pid, group in tqdm(batter_game.groupby("batter"), desc="Rolling batter stats"):
    group = group.sort_values("game_date")
    group["batter_hits_5g"] = group["hits"].rolling(window=5, min_periods=1).mean().shift(1)
    rolling_batter.append(group)
batter_game = pd.concat(rolling_batter)

rolling_pitcher = []
for pid, group in tqdm(pitcher_game.groupby("pitcher"), desc="Rolling pitcher stats"):
    group = group.sort_values("game_date")
    group["pitcher_hits_allowed_5g"] = group["hits_allowed"].rolling(window=5, min_periods=1).mean().shift(1)
    rolling_pitcher.append(group)
pitcher_game = pd.concat(rolling_pitcher)

# Season stats
df["game_year"] = df["game_date"].dt.year
batter_season = df.groupby(["batter", "game_year"]).apply(
    lambda g: pd.DataFrame({
        "batter": g["batter"],
        "game_date": g["game_date"],
        "batting_avg": g["is_hit"].cumsum().shift(1) / pd.Series(range(1, len(g)+1))
    })
).reset_index(drop=True)

pitcher_season = df.groupby(["pitcher", "game_year"]).apply(
    lambda g: pd.DataFrame({
        "pitcher": g["pitcher"],
        "game_date": g["game_date"],
        "baa": g["is_hit"].cumsum().shift(1) / pd.Series(range(1, len(g)+1))
    })
).reset_index(drop=True)

# Career stats
batter_career = df.groupby("batter").agg(
    total_hits=("is_hit", "sum"),
    total_pas=("events", "count")
).reset_index()
batter_career["career_avg"] = batter_career["total_hits"] / batter_career["total_pas"]

pitcher_career = df.groupby("pitcher").agg(
    total_hits_allowed=("is_hit", "sum"),
    total_pas=("events", "count")
).reset_index()
pitcher_career["career_baa"] = pitcher_career["total_hits_allowed"] / pitcher_career["total_pas"]

# === Save all to DB ===
batter_game.to_sql("batter_game_stats", conn, if_exists="replace", index=False)
pitcher_game.to_sql("pitcher_game_stats", conn, if_exists="replace", index=False)
batter_season.to_sql("batter_season_stats", conn, if_exists="replace", index=False)
pitcher_season.to_sql("pitcher_season_stats", conn, if_exists="replace", index=False)
batter_career.to_sql("batter_career_stats", conn, if_exists="replace", index=False)
pitcher_career.to_sql("pitcher_career_stats", conn, if_exists="replace", index=False)

conn.close()
print("Stats updated: rolling, season, career — done.")
