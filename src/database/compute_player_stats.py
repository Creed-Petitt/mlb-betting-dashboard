import sqlite3
import pandas as pd
from tqdm import tqdm

conn = sqlite3.connect("data/mlb.db")
df = pd.read_sql("SELECT * FROM cleaned_plate_appearances", conn, parse_dates=["game_date"])

# Ensure game_date is sorted
df = df.sort_values("game_date")

# Identify hits
df["is_hit"] = df["events"].isin(["single", "double", "triple", "home_run"]).astype(int)

# Game-level batter stats
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

# Game-level pitcher stats
pitcher_game = df.groupby(["pitcher", "game_date"]).agg(
    plate_appearances=("events", "count"),
    hits_allowed=("is_hit", "sum"),
    p_throws=("p_throws", "first"),
    pitcher_team=("fld_score", "last"),
).reset_index()
pitcher_game["baa"] = pitcher_game["hits_allowed"] / pitcher_game["plate_appearances"]

# Rolling 5-game stats for batters
rolling_batter = []
for pid, group in tqdm(batter_game.groupby("batter"), desc="Rolling batter stats"):
    group = group.sort_values("game_date")
    group["batter_hits_5g"] = group["hits"].rolling(window=5, min_periods=1).mean().shift(1)
    rolling_batter.append(group)
batter_game = pd.concat(rolling_batter)

# Rolling 5-game stats for pitchers
rolling_pitcher = []
for pid, group in tqdm(pitcher_game.groupby("pitcher"), desc="Rolling pitcher stats"):
    group = group.sort_values("game_date")
    group["pitcher_hits_allowed_5g"] = group["hits_allowed"].rolling(window=5, min_periods=1).mean().shift(1)
    rolling_pitcher.append(group)
pitcher_game = pd.concat(rolling_pitcher)

# Season stats for batters
df["game_year"] = df["game_date"].dt.year
season_batter_rows = []
for (batter, year), group in tqdm(df.groupby(["batter", "game_year"]), desc="Batter season stats"):
    group = group.sort_values("game_date")
    hits = group["is_hit"].cumsum().shift(1)
    pas = pd.Series(range(1, len(group) + 1))
    avg = hits / pas
    out = pd.DataFrame({
        "batter": batter,
        "game_date": group["game_date"],
        "batting_avg": avg
    })
    season_batter_rows.append(out)
batter_season = pd.concat(season_batter_rows)

# Season stats for pitchers
season_pitcher_rows = []
for (pitcher, year), group in tqdm(df.groupby(["pitcher", "game_year"]), desc="Pitcher season stats"):
    group = group.sort_values("game_date")
    hits = group["is_hit"].cumsum().shift(1)
    pas = pd.Series(range(1, len(group) + 1))
    avg = hits / pas
    out = pd.DataFrame({
        "pitcher": pitcher,
        "game_date": group["game_date"],
        "baa": avg
    })
    season_pitcher_rows.append(out)
pitcher_season = pd.concat(season_pitcher_rows)

# Career stats for batters
batter_career = df.groupby("batter").agg(
    total_hits=("is_hit", "sum"),
    total_pas=("events", "count")
).reset_index()
batter_career["career_avg"] = batter_career["total_hits"] / batter_career["total_pas"]

# Career stats for pitchers
pitcher_career = df.groupby("pitcher").agg(
    total_hits_allowed=("is_hit", "sum"),
    total_pas=("events", "count")
).reset_index()
pitcher_career["career_baa"] = pitcher_career["total_hits_allowed"] / pitcher_career["total_pas"]

# Save all to DB
batter_game.to_sql("batter_game_stats", conn, if_exists="replace", index=False)
pitcher_game.to_sql("pitcher_game_stats", conn, if_exists="replace", index=False)
batter_season.to_sql("batter_season_stats", conn, if_exists="replace", index=False)
pitcher_season.to_sql("pitcher_season_stats", conn, if_exists="replace", index=False)
batter_career.to_sql("batter_career_stats", conn, if_exists="replace", index=False)
pitcher_career.to_sql("pitcher_career_stats", conn, if_exists="replace", index=False)

conn.close()
print("All player stats saved successfully.")
 