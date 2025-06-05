import requests
import sqlite3
import pandas as pd

# Hardcoded abbreviation → full name map
TEAM_ABBR_TO_NAME = {
    "ARI": "Arizona Diamondbacks", "ATL": "Atlanta Braves", "BAL": "Baltimore Orioles",
    "BOS": "Boston Red Sox", "CHC": "Chicago Cubs", "CIN": "Cincinnati Reds",
    "CLE": "Cleveland Guardians", "COL": "Colorado Rockies", "CWS": "Chicago White Sox",
    "DET": "Detroit Tigers", "HOU": "Houston Astros", "KC": "Kansas City Royals",
    "LAA": "Los Angeles Angels", "LAD": "Los Angeles Dodgers", "MIA": "Miami Marlins",
    "MIL": "Milwaukee Brewers", "MIN": "Minnesota Twins", "NYM": "New York Mets",
    "NYY": "New York Yankees", "OAK": "Oakland Athletics", "PHI": "Philadelphia Phillies",
    "PIT": "Pittsburgh Pirates", "SD": "San Diego Padres", "SEA": "Seattle Mariners",
    "SF": "San Francisco Giants", "STL": "St. Louis Cardinals", "TB": "Tampa Bay Rays",
    "TEX": "Texas Rangers", "TOR": "Toronto Blue Jays", "WSH": "Washington Nationals"
}

def fetch_roster(team_abbr):
    team_name = TEAM_ABBR_TO_NAME.get(team_abbr)
    if not team_name:
        print(f"Unknown team abbreviation: {team_abbr}")
        return []

    # Get team ID by full name
    url = f"https://statsapi.mlb.com/api/v1/teams?sportId=1"
    teams = requests.get(url).json()["teams"]
    team_id = next((t["id"] for t in teams if t["name"] == team_name), None)
    if team_id is None:
        print(f"Could not find team ID for {team_name}")
        return []

    # Fetch roster
    roster_url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster"
    response = requests.get(roster_url)
    response.raise_for_status()
    data = response.json()

    roster = []
    for player in data.get("roster", []):
        player_id = player.get("person", {}).get("id")
        player_name = player.get("person", {}).get("fullName")
        if player_id and player_name:
            roster.append({
                "mlb_id": player_id,
                "player_name": player_name.lower(),  # Normalize
                "team": team_abbr
            })
    return roster

def save_roster_to_db(rosters):
    conn = sqlite3.connect("data/mlb.db")
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS cached_player_names")
    cursor.execute("""
        CREATE TABLE cached_player_names (
            mlb_id INTEGER PRIMARY KEY,
            player_name TEXT,
            team TEXT
        )
    """)

    for player in rosters:
        cursor.execute("""
            INSERT INTO cached_player_names (mlb_id, player_name, team)
            VALUES (?, ?, ?)
        """, (player["mlb_id"], player["player_name"], player["team"]))

    conn.commit()
    conn.close()
    print(f"Cached {len(rosters)} player names.")

def get_unique_teams():
    conn = sqlite3.connect("data/mlb.db")
    df = pd.read_sql("""
        SELECT DISTINCT home_team FROM upcoming_games
        UNION
        SELECT DISTINCT away_team FROM upcoming_games
    """, conn)
    conn.close()
    return df["home_team"].dropna().unique().tolist()

if __name__ == "__main__":
    teams = get_unique_teams()
    all_rosters = []
    for team in teams:
        print(f"Fetching roster for {team}...")
        roster = fetch_roster(team)
        all_rosters.extend(roster)

    save_roster_to_db(all_rosters)
