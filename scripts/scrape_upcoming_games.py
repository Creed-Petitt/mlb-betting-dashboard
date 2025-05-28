import requests
from datetime import datetime, timedelta


def get_upcoming_games(days_ahead=5):
    """
    Fetch upcoming MLB games and probable pitchers using MLB's Stats API.

    Args:
        days_ahead (int): How many future days to load (starting from today)

    Returns:
        List[Dict]: Each dict contains game_date, home/away teams, and probable pitchers (name and ID if available)
    """
    # Define date range: today to today + N days
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
    if response.status_code != 200:
        raise Exception(f"API failed: {response.status_code}")

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


# Test it live
if __name__ == "__main__":
    print("Fetching upcoming games...")
    upcoming = get_upcoming_games(days_ahead=5)
    for game in upcoming:
        print(game)
