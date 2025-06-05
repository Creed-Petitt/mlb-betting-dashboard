import requests
import sqlite3
from datetime import datetime, timedelta

# MLB Stats API endpoint for schedule
def fetch_schedule(start_date, end_date):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={start_date}&endDate={end_date}&hydrate=probablePitcher"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def extract_game_info(data):
    games = []
    for date_info in data.get("dates", []):
        for game in date_info.get("games", []):
            game_id = game.get("gamePk")
            game_date = game.get("gameDate")[:10]  # Truncate to YYYY-MM-DD

            teams = game.get("teams", {})
            home_team = teams.get("home", {}).get("team", {}).get("abbreviation")
            away_team = teams.get("away", {}).get("team", {}).get("abbreviation")

            home_pitcher = teams.get("home", {}).get("probablePitcher", {}).get("id")
            away_pitcher = teams.get("away", {}).get("probablePitcher", {}).get("id")

            games.append({
                "game_id": str(game_id),
                "game_date": game_date,
                "home_team": home_team,
                "away_team": away_team,
                "home_pitcher": home_pitcher,
                "away_pitcher": away_pitcher
            })
    return games

def save_to_db(games):
    conn = sqlite3.connect("data/mlb.db")
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS upcoming_games")
    cursor.execute("""
        CREATE TABLE upcoming_games (
            game_id TEXT PRIMARY KEY,
            game_date TEXT,
            home_team TEXT,
            away_team TEXT,
            home_pitcher INTEGER,
            away_pitcher INTEGER
        )
    """)

    for g in games:
        cursor.execute("""
            INSERT INTO upcoming_games (game_id, game_date, home_team, away_team, home_pitcher, away_pitcher)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            g["game_id"], g["game_date"], g["home_team"], g["away_team"], g["home_pitcher"], g["away_pitcher"]
        ))

    conn.commit()
    conn.close()
    print(f"Saved {len(games)} upcoming games to the database.")

if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    data = fetch_schedule(today, tomorrow)
    games = extract_game_info(data)
    save_to_db(games)
