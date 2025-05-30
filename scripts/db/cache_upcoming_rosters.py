import sqlite3
import requests
from datetime import datetime

def get_upcoming_team_ids():
    conn = sqlite3.connect("data/mlb.db")
    result = conn.execute("""
        SELECT DISTINCT home_team FROM upcoming_games
        UNION
        SELECT DISTINCT away_team FROM upcoming_games
    """).fetchall()
    conn.close()

    team_names = [row[0] for row in result if row[0]]
    return team_names

def get_team_id_map():
    url = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
    response = requests.get(url)
    teams = response.json()["teams"]
    return {team["name"]: team["id"] for team in teams}

def fetch_team_roster(team_id):
    url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster"
    response = requests.get(url)
    return response.json().get("roster", [])

def cache_players(player_list):
    conn = sqlite3.connect("data/mlb.db")
    c = conn.cursor()

    for player in player_list:
        player_id = player["person"]["id"]
        full_name = player["person"]["fullName"].lower()

        c.execute("""
            INSERT OR REPLACE INTO cached_player_names (player_id, player_name, last_updated)
            VALUES (?, ?, ?)
        """, (
            player_id,
            full_name,
            datetime.now().isoformat(timespec='seconds')
        ))

    conn.commit()
    conn.close()

def cache_upcoming_players():
    print("Caching rosters from upcoming teams...")
    team_names = get_upcoming_team_ids()
    team_id_map = get_team_id_map()

    all_players = []
    for name in team_names:
        team_id = team_id_map.get(name)
        if not team_id:
            print(f"Unknown team: {name}")
            continue

        roster = fetch_team_roster(team_id)
        all_players.extend(roster)
        print(f"Pulled {len(roster)} players from {name}")

    cache_players(all_players)
    print(f"Cached {len(all_players)} total players.")

if __name__ == "__main__":
    cache_upcoming_players()
