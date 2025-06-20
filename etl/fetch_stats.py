import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from app import create_app
from app.models import db, Player, Game, Prop, Stat
from sqlalchemy import or_
from datetime import datetime

# Map our display fields to MLB API keys for hitters
HITTER_STATS_MAP = {
    'avg': 'avg',
    'obp': 'obp',
    'slg': 'slg',
    'ops': 'ops',
    'hr': 'homeRuns',
    'rbi': 'rbi',
    'h': 'hits',
    'ab': 'atBats',
    'pa': 'plateAppearances',
    'bb': 'baseOnBalls',
    'so': 'strikeOuts',
    'sb': 'stolenBases',
}

# Map our display fields to MLB API keys for pitchers
PITCHER_STATS_MAP = {
    'era': 'era',
    'whip': 'whip',
    'ip': 'inningsPitched',
    'k9': 'strikeoutsPer9Inn',
    'bb9': 'walksPer9Inn',
    'hr9': 'homeRunsPer9',
    'w': 'wins',
    'l': 'losses',
    'so': 'strikeOuts',
    'h': 'hits',
    'bb': 'baseOnBalls',
}

def get_relevant_player_ids():
    hitter_ids = set(pid for (pid,) in db.session.query(Prop.player_id).distinct())
    pitcher_ids = set()
    for game in db.session.query(Game).all():
        if game.home_pitcher_id:
            pitcher_ids.add(game.home_pitcher_id)
        if game.away_pitcher_id:
            pitcher_ids.add(game.away_pitcher_id)
    return hitter_ids | pitcher_ids

def fetch_and_store_stats(player_id):
    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=season,career&group=hitting,pitching"
    resp = requests.get(url)
    if not resp.ok:
        print(f"Failed to fetch stats for player {player_id}")
        return
    stats = resp.json().get('stats', [])
    player = db.session.get(Player, player_id)
    if not player:
        print(f"Player {player_id} not found in DB.")
        return

    for entry in stats:
        stat_type = entry.get('group', {}).get('displayName', '').lower()  # 'hitting' or 'pitching'
        splits = entry.get('splits', [])
        for split in splits:
            season = split.get('season', 'career') if 'season' in split else 'career'
            stat_dict = split.get('stat', {})
            if stat_type == "hitting":
                for our_name, mlb_key in HITTER_STATS_MAP.items():
                    if mlb_key in stat_dict:
                        stat_value = stat_dict[mlb_key]
                        exists = db.session.query(Stat).filter_by(
                            player_id=player_id,
                            season=season,
                            stat_type=stat_type,
                            stat_name=our_name
                        ).first()
                        if exists:
                            exists.stat_value = stat_value
                        else:
                            db.session.add(Stat(
                                player_id=player_id,
                                season=season,
                                stat_type=stat_type,
                                stat_name=our_name,
                                stat_value=stat_value,
                                date=None
                            ))
            elif stat_type == "pitching":
                for our_name, mlb_key in PITCHER_STATS_MAP.items():
                    if mlb_key in stat_dict:
                        stat_value = stat_dict[mlb_key]
                        exists = db.session.query(Stat).filter_by(
                            player_id=player_id,
                            season=season,
                            stat_type=stat_type,
                            stat_name=our_name
                        ).first()
                        if exists:
                            exists.stat_value = stat_value
                        else:
                            db.session.add(Stat(
                                player_id=player_id,
                                season=season,
                                stat_type=stat_type,
                                stat_name=our_name,
                                stat_value=stat_value,
                                date=None
                            ))

def main():
    app = create_app()
    with app.app_context():
        player_ids = get_relevant_player_ids()
        print(f"Fetching stats for {len(player_ids)} players...")
        for pid in player_ids:
            fetch_and_store_stats(pid)
        db.session.commit()
        print("Stats ETL done.")

if __name__ == "__main__":
    main()
