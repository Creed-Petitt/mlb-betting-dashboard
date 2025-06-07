import requests
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "data/mlb.db"
today = datetime.today().strftime("%Y-%m-%d")
tomorrow = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")

url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={today}&endDate={tomorrow}&hydrate=probablePitcher"

r = requests.get(url)
games = r.json().get("dates", [])

rows = []

for date in games:
    for game in date["games"]:
        row = {
            "game_id": game["gamePk"],
            "game_date": game["gameDate"],
            "home_team_id": game["teams"]["home"]["team"]["id"],
            "home_team_name": game["teams"]["home"]["team"]["name"],
            "away_team_id": game["teams"]["away"]["team"]["id"],
            "away_team_name": game["teams"]["away"]["team"]["name"],
            "home_pitcher_id": game["teams"]["home"].get("probablePitcher", {}).get("id"),
            "home_pitcher_name": game["teams"]["home"].get("probablePitcher", {}).get("fullName"),
            "away_pitcher_id": game["teams"]["away"].get("probablePitcher", {}).get("id"),
            "away_pitcher_name": game["teams"]["away"].get("probablePitcher", {}).get("fullName"),
        }
        rows.append(row)

df = pd.DataFrame(rows)

# Save to DB
conn = sqlite3.connect(DB_PATH)
df.to_sql("upcoming_games", conn, if_exists="replace", index=False)
conn.close()

print(f"Saved {len(df)} games to upcoming_games (with pitchers)")
