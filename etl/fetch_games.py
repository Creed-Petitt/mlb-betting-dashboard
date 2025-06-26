import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from datetime import datetime, timedelta
from dateutil import tz
from app import create_app
from app.models import db, Team, Player, Game, Prop

def fetch_upcoming_games(days_ahead=1):
    today = datetime.today().date()
    end_date = today + timedelta(days=days_ahead)
    url = (
        f"https://statsapi.mlb.com/api/v1/schedule"
        f"?sportId=1&startDate={today}&endDate={end_date}&hydrate=probablePitcher"
    )
    print(f"[fetch_games] Fetching games from {today} to {end_date}")
    r = requests.get(url)
    if not r.ok:
        print(f"[fetch_games] ERROR: Failed to fetch MLB schedule: {r.status_code}")
        return
    games_data = r.json().get("dates", [])
    print(f"[fetch_games] Got {len(games_data)} date(s) from MLB API")

    teams_added = set()
    game_count = 0
    pitcher_count = 0

    for date_info in games_data:
        game_list = date_info.get("games", [])
        print(f"[fetch_games] --- {date_info.get('date', 'UNKNOWN DATE')} | {len(game_list)} games ---")
        for game in game_list:
            gid = int(game["gamePk"])
            # Convert UTC to US/Eastern to match FanDuel and local schedules
            game_utc = datetime.fromisoformat(game["gameDate"].replace('Z', '+00:00'))
            game_et = game_utc.astimezone(tz.gettz("America/New_York"))
            gdate = game_et.date()
            # Teams
            home = game["teams"]["home"]["team"]
            away = game["teams"]["away"]["team"]
            home_team_id, home_team_name = int(home["id"]), home["name"]
            away_team_id, away_team_name = int(away["id"]), away["name"]

            # Insert teams if missing
            for tid, tname in [(home_team_id, home_team_name), (away_team_id, away_team_name)]:
                if tid not in teams_added:
                    if not db.session.get(Team, tid):
                        print(f"[fetch_games] Inserting team {tid} ({tname})")
                        db.session.add(Team(id=tid, name=tname, abbr=tname[:3].upper()))
                    teams_added.add(tid)

            # Probable pitchers
            home_pitcher = game["teams"]["home"].get("probablePitcher", {})
            away_pitcher = game["teams"]["away"].get("probablePitcher", {})
            home_pitcher_id = home_pitcher.get("id")
            home_pitcher_name = home_pitcher.get("fullName")
            away_pitcher_id = away_pitcher.get("id")
            away_pitcher_name = away_pitcher.get("fullName")
            if home_pitcher_id:
                if not db.session.get(Player, home_pitcher_id):
                    print(f"[fetch_games] Inserting home pitcher {home_pitcher_id} ({home_pitcher_name}) for team {home_team_id}")
                    db.session.add(Player(
                        id=home_pitcher_id,
                        name=home_pitcher_name,
                        team_id=home_team_id,
                        position="P",
                        is_pitcher=True
                    ))
                    pitcher_count += 1
            else:
                print(f"[fetch_games] WARNING: No probable home pitcher for team {home_team_id} ({home_team_name}) in game {gid}")
            if away_pitcher_id:
                if not db.session.get(Player, away_pitcher_id):
                    print(f"[fetch_games] Inserting away pitcher {away_pitcher_id} ({away_pitcher_name}) for team {away_team_id}")
                    db.session.add(Player(
                        id=away_pitcher_id,
                        name=away_pitcher_name,
                        team_id=away_team_id,
                        position="P",
                        is_pitcher=True
                    ))
                    pitcher_count += 1
            else:
                print(f"[fetch_games] WARNING: No probable away pitcher for team {away_team_id} ({away_team_name}) in game {gid}")

            # Insert or update game
            existing_game = db.session.get(Game, gid)
            if not existing_game:
                print(f"[fetch_games] Inserting game {gid} on {gdate}: {home_team_name} vs {away_team_name}")
                db.session.add(Game(
                    id=gid,
                    date=gdate,
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                    home_pitcher_id=home_pitcher_id,
                    away_pitcher_id=away_pitcher_id
                ))
                game_count += 1
            else:
                # Update pitcher information if it's now available
                updated = False
                if home_pitcher_id and existing_game.home_pitcher_id != home_pitcher_id:
                    print(f"[fetch_games] Updating home pitcher for game {gid}: {home_pitcher_id} ({home_pitcher_name})")
                    existing_game.home_pitcher_id = home_pitcher_id
                    updated = True
                if away_pitcher_id and existing_game.away_pitcher_id != away_pitcher_id:
                    print(f"[fetch_games] Updating away pitcher for game {gid}: {away_pitcher_id} ({away_pitcher_name})")
                    existing_game.away_pitcher_id = away_pitcher_id
                    updated = True
                if updated:
                    game_count += 1

    db.session.commit()
    print(f"[fetch_games] Inserted {game_count} new games, {len(teams_added)} teams, {pitcher_count} pitchers")

    # Check for missing games for all prop teams/dates
    print("\n[fetch_games] Checking for missing games for all prop teams/dates...")
    prop_dates_teams = db.session.query(Prop.date, Player.team_id).join(Player, Prop.player_id == Player.id).distinct()
    for prop_date, team_id in prop_dates_teams:
        game = Game.query.filter(
            Game.date == prop_date,
            ((Game.home_team_id == team_id) | (Game.away_team_id == team_id))
        ).first()
        if not game:
            print(f"[fetch_games]  MISSING: No game for team {team_id} on {prop_date}")

def main():
    app = create_app()
    with app.app_context():
        fetch_upcoming_games(days_ahead=1)  # today + tomorrow only

if __name__ == "__main__":
    main()

