import sys
import os
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from app.models import db, Player, Team

def fetch_team_roster(team_id):
    url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster/Active"
    resp = requests.get(url)
    if not resp.ok:
        print(f"[ERROR] Failed to fetch roster for team {team_id}")
        return []
    data = resp.json()
    return data.get("roster", [])

def main():
    app = create_app()
    with app.app_context():
        teams = Team.query.all()
        print(f"[DEBUG] {len(teams)} teams found in DB")
        total_added = 0
        for team in teams:
            roster = fetch_team_roster(team.id)
            print(f"[DEBUG] Team {team.name} ({team.id}): {len(roster)} players on active roster")
            added = 0
            for player_obj in roster:
                pid = int(player_obj['person']['id'])
                name = player_obj['person']['fullName']
                position = player_obj.get('position', {}).get('abbreviation', None)
                player = Player.query.filter_by(id=pid).first()
                if player:
                    player.name = name
                    player.team_id = team.id
                    player.position = position
                else:
                    db.session.add(Player(
                        id=pid,
                        name=name,
                        team_id=team.id,
                        position=position
                    ))
                    added += 1
            print(f"[DEBUG] Added {added} new players for team {team.name}")
            total_added += added
        db.session.commit()
        print(f"[DEBUG] Roster sync done. Added {total_added} new players.")
        print(f"[DEBUG] Total players in table: {Player.query.count()}")

if __name__ == "__main__":
    main()
