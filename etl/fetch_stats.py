import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import logging
from app import create_app
from app.models import db, Player, Game, Prop, Stat
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
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
    'k_9': 'strikeoutsPer9Inn',
    'avg': 'avg',
    'bb9': 'walksPer9Inn',
    'hr9': 'homeRunsPer9',
    'w': 'wins',
    'l': 'losses',
    'so': 'strikeOuts',
    'h': 'hits',
    'bb': 'baseOnBalls',
}

def get_relevant_player_ids():
    """Get only players we actually need stats for: players with props + starting pitchers in upcoming games."""
    from datetime import date, timedelta
    
    # Get players with props (only for today and tomorrow)
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    hitter_ids = set(pid for (pid,) in db.session.query(Prop.player_id).filter(
        (Prop.date == today) | (Prop.date == tomorrow)
    ).distinct())
    
    print(f"Found {len(hitter_ids)} players with props for today/tomorrow")
    
    # Get starting pitchers for upcoming games (today and tomorrow only)
    pitcher_ids = set()
    upcoming_games = db.session.query(Game).filter(
        (Game.date == today) | (Game.date == tomorrow)
    ).all()
    
    for game in upcoming_games:
        if game.home_pitcher_id:
            pitcher_ids.add(game.home_pitcher_id)
        if game.away_pitcher_id:
            pitcher_ids.add(game.away_pitcher_id)
    
    print(f"Found {len(pitcher_ids)} starting pitchers for today/tomorrow")
    
    all_relevant_ids = hitter_ids | pitcher_ids
    print(f"Total relevant players: {len(all_relevant_ids)}")
    
    return all_relevant_ids

def fetch_and_store_stats(player_id):
    """Fetch and store stats for a single player with error handling. Only store hitting stats for hitters and pitching stats for pitchers."""
    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=season,career&group=hitting,pitching"
        resp = requests.get(url, timeout=30)
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
            # Only store hitting stats for hitters, pitching stats for pitchers
            if stat_type == "hitting" and not player.is_pitcher:
                for split in splits:
                    season = split.get('season', 'career') if 'season' in split else 'career'
                    stat_dict = split.get('stat', {})
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
            elif stat_type == "pitching" and player.is_pitcher:
                for split in splits:
                    season = split.get('season', 'career') if 'season' in split else 'career'
                    stat_dict = split.get('stat', {})
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
    except requests.RequestException as e:
        print(f"Network error fetching stats for player {player_id}: {e}")
    except SQLAlchemyError as e:
        print(f"Database error storing stats for player {player_id}: {e}")
        db.session.rollback()
    except Exception as e:
        print(f"Unexpected error processing player {player_id}: {e}")

def main():
    """Main function with comprehensive error handling."""
    try:
        app = create_app()
        with app.app_context():
            player_ids = get_relevant_player_ids()
            print(f"Fetching stats for {len(player_ids)} players...")
            
            success_count = 0
            error_count = 0
            
            for idx, pid in enumerate(player_ids, 1):
                try:
                    print(f"[{idx}/{len(player_ids)}] Fetching stats for player {pid}...")
                    fetch_and_store_stats(pid)
                    success_count += 1
                except Exception as e:
                    print(f"Error processing player {pid}: {e}")
                    error_count += 1
                    continue
            
            try:
                db.session.commit()
                print(f"Stats ETL done. Success: {success_count}, Errors: {error_count}")
            except SQLAlchemyError as e:
                print(f"Error committing to database: {e}")
                db.session.rollback()
                raise
                
    except Exception as e:
        logging.error(f"Critical error in fetch_stats: {e}")
        print(f"Critical error: {e}")
        raise

if __name__ == "__main__":
    main()
