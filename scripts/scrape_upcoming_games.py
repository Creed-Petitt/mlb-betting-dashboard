import requests
from datetime import datetime, timedelta

def get_upcoming_games(days_ahead=5):
    """
    Fetch upcoming MLB games and probable pitchers using MLB's Stats API.
    """
    today = datetime.now().date()
    end_date = today + timedelta(days=days_ahead)

    url = (
        f"https://statsapi.mlb.com/api/v1/schedule"
        f"?sportId=1"
        f"&startDate={today}"
        f"&endDate={end_date}"
        f"&hydrate=probablePitcher"
    )

    response = requests.get(url)
    data = response.json()

    games = []
    for date_block in data.get("dates", []):
        for game in date_block.get("games", []):
            home_team = game["teams"]["home"]["team"]["name"]
            away_team = game["teams"]["away"]["team"]["name"]
            game_date = game.get("gameDate")

            home_pitcher_info = game["teams"]["home"].get("probablePitcher", {})
            away_pitcher_info = game["teams"]["away"].get("probablePitcher", {})

            games.append({
                "game_date": game_date,
                "home_team": home_team,
                "away_team": away_team,
                "home_pitcher": home_pitcher_info.get("fullName"),
                "home_pitcher_id": home_pitcher_info.get("id"),
                "away_pitcher": away_pitcher_info.get("fullName"),
                "away_pitcher_id": away_pitcher_info.get("id"),
            })

    return games

import sqlite3

def save_upcoming_games_to_db(games):
    """
    Saves list of upcoming game dicts to the upcoming_games table.
    Wipes existing rows before inserting.
    """
    conn = sqlite3.connect("data/mlb.db")
    conn.execute("DELETE FROM upcoming_games")  # Clear old games

    for g in games:
        conn.execute("""
            INSERT INTO upcoming_games (
                game_date, home_team, away_team,
                home_pitcher, home_pitcher_id,
                away_pitcher, away_pitcher_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            g['game_date'], g['home_team'], g['away_team'],
            g['home_pitcher'], g['home_pitcher_id'],
            g['away_pitcher'], g['away_pitcher_id']
        ))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    upcoming = get_upcoming_games(days_ahead=5)
    save_upcoming_games_to_db(upcoming)
    print(f"Saved {len(upcoming)} upcoming games to DB.")
