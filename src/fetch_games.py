# src/fetch_games.py

import requests
import sqlite3
import pandas as pd
from datetime import datetime

today = datetime.today().strftime("%Y-%m-%d")
url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}"

response = requests.get(url)
data = response.json()

games = []
for date in data.get("dates", []):
    for game in date.get("games", []):
        games.append({
            "game_id": game["gamePk"],
            "game_date": game["gameDate"],
            "home_team_id": game["teams"]["home"]["team"]["id"],
            "home_team_name": game["teams"]["home"]["team"]["name"],
            "away_team_id": game["teams"]["away"]["team"]["id"],
            "away_team_name": game["teams"]["away"]["team"]["name"],
        })

# Save to SQLite
conn = sqlite3.connect("data/mlb.db")
df = pd.DataFrame(games)
df.to_sql("upcoming_games", conn, if_exists="replace", index=False)
conn.close()

print(f"Saved {len(games)} games to upcoming_games")
