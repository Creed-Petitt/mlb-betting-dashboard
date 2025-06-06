# src/cache_rosters.py

import requests
import sqlite3
import pandas as pd

# Connect to DB and get unique team IDs
conn = sqlite3.connect("data/mlb.db")
teams = pd.read_sql("SELECT DISTINCT home_team_id AS team_id FROM upcoming_games UNION SELECT DISTINCT away_team_id FROM upcoming_games", conn)

all_players = []

# Fetch 40-man roster for each team
for team_id in teams["team_id"]:
    try:
        url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?rosterType=40Man"
        res = requests.get(url).json()
        for player in res.get("roster", []):
            all_players.append({
                "mlb_id": player["person"]["id"],
                "full_name": player["person"]["fullName"].strip().lower(),
                "team_id": team_id
            })
    except Exception as e:
        print(f"Error fetching roster for team {team_id}: {e}")

# Save all players to DB
df = pd.DataFrame(all_players)
df.to_sql("cached_rosters", conn, if_exists="replace", index=False)
conn.close()

print(f"Cached {len(df)} players to cached_rosters")
