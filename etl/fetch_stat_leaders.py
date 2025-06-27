#!/usr/bin/env python3
"""
Fetch stat leaders from MLB API for 2025 season
"""

import sys
import os
import requests
import logging
from datetime import date

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import db, StatLeader, Player

# Configure logging
logging.basicConfig(level=logging.INFO)

def clear_existing_data():
    """Clear existing stat leaders data."""
    try:
        StatLeader.query.delete()
        db.session.commit()
        print("[INFO] Cleared existing stat leaders data")
    except Exception as e:
        print(f"[ERROR] Failed to clear existing data: {e}")
        db.session.rollback()

def is_pitcher(player_id):
    """Check if a player is a pitcher using our player database."""
    player = Player.query.filter_by(id=player_id).first()
    if player:
        return player.is_pitcher or player.position == 'P'
    return False

def fetch_2025_stat_leaders():
    """Fetch 2025 season stat leaders."""
    
    # Batting categories for position players
    batting_categories = [
        'battingAverage', 'homeRuns', 'rbi', 'hits', 'onBasePlusSlugging',
        'sluggingPercentage', 'onBasePercentage', 'stolenBases', 'runs', 'doubles', 'triples'
    ]
    
    # Pitching categories for pitchers
    pitching_categories = [
        'era', 'wins', 'strikeouts', 'whip', 'saves', 'holds', 'qualityStarts'
    ]
    
    total_added = 0
    
    # Process batting stats (position players only)
    print("[INFO] Fetching 2025 batting stat leaders...")
    for category in batting_categories:
        try:
            url = "https://statsapi.mlb.com/api/v1/stats"
            params = {
                'stats': 'season',
                'group': 'hitting',
                'season': '2025',
                'gameType': 'R',
                'limit': 50,
                'sportId': 1,
                'sortStat': category,
                'order': 'desc'
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            stats_data = data.get('stats', [])
            
            if not stats_data:
                print(f"[SKIP] No data for {category}")
                continue
                
            splits = stats_data[0].get('splits', [])
            valid_count = 0
            
            for rank, split in enumerate(splits, 1):
                try:
                    player_data = split.get('player', {})
                    team_data = split.get('team', {})
                    stat_data = split.get('stat', {})
                    
                    player_id = player_data.get('id')
                    if not player_id:
                        continue
                        
                    # Skip pitchers for batting stats
                    if is_pitcher(player_id):
                        continue
                    
                    player_name = player_data.get('fullName', 'Unknown')
                    team_id = team_data.get('id')
                    team_name = team_data.get('name', 'Unknown')
                    
                    # Get the specific stat value
                    if category == 'battingAverage':
                        value = stat_data.get('avg', '0')
                    elif category == 'homeRuns':
                        value = stat_data.get('homeRuns', '0')
                    elif category == 'rbi':
                        value = stat_data.get('rbi', '0')
                    elif category == 'hits':
                        value = stat_data.get('hits', '0')
                    elif category == 'onBasePlusSlugging':
                        value = stat_data.get('ops', '0')
                    elif category == 'sluggingPercentage':
                        value = stat_data.get('slg', '0')
                    elif category == 'onBasePercentage':
                        value = stat_data.get('obp', '0')
                    elif category == 'stolenBases':
                        value = stat_data.get('stolenBases', '0')
                    elif category == 'runs':
                        value = stat_data.get('runs', '0')
                    elif category == 'doubles':
                        value = stat_data.get('doubles', '0')
                    elif category == 'triples':
                        value = stat_data.get('triples', '0')
                    else:
                        value = '0'
                    
                    # Basic validation
                    if not value or value == '0' or (category == 'battingAverage' and float(value.replace('.', '')) < 200):
                        continue
                    
                    stat_leader = StatLeader(
                        season='2025',
                        category=category,
                        player_id=player_id,
                        player_name=player_name,
                        team_id=team_id,
                        team_name=team_name,
                        value=str(value),
                        rank=rank,
                        last_updated=date.today()
                    )
                    
                    db.session.add(stat_leader)
                    valid_count += 1
                    
                    if valid_count >= 50:  # Limit to top 50
                        break
                        
                except Exception as e:
                    print(f"[ERROR] Error processing {category} leader: {e}")
                    continue
            
            db.session.commit()
            total_added += valid_count
            print(f"[SUCCESS] Added {valid_count} {category} leaders")
            
        except Exception as e:
            print(f"[ERROR] Failed to fetch {category}: {e}")
            db.session.rollback()
            continue
    
    # Process pitching stats
    print("[INFO] Fetching 2025 pitching stat leaders...")
    for category in pitching_categories:
        try:
            url = "https://statsapi.mlb.com/api/v1/stats"
            params = {
                'stats': 'season',
                'group': 'pitching',
                'season': '2025',
                'gameType': 'R',
                'limit': 50,
                'sportId': 1,
                'sortStat': category,
                'order': 'asc' if category in ['era', 'whip'] else 'desc'
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            stats_data = data.get('stats', [])
            
            if not stats_data:
                print(f"[SKIP] No data for {category}")
                continue
                
            splits = stats_data[0].get('splits', [])
            valid_count = 0
            
            for rank, split in enumerate(splits, 1):
                try:
                    player_data = split.get('player', {})
                    team_data = split.get('team', {})
                    stat_data = split.get('stat', {})
                    
                    player_id = player_data.get('id')
                    player_name = player_data.get('fullName', 'Unknown')
                    team_id = team_data.get('id')
                    team_name = team_data.get('name', 'Unknown')
                    
                    # Get the specific stat value
                    if category == 'era':
                        value = stat_data.get('era', '0')
                    elif category == 'wins':
                        value = stat_data.get('wins', '0')
                    elif category == 'strikeouts':
                        value = stat_data.get('strikeOuts', '0')
                    elif category == 'whip':
                        value = stat_data.get('whip', '0')
                    elif category == 'saves':
                        value = stat_data.get('saves', '0')
                    elif category == 'holds':
                        value = stat_data.get('holds', '0')
                    elif category == 'qualityStarts':
                        value = stat_data.get('qualityStarts', '0')
                    else:
                        value = '0'
                    
                    # Basic validation
                    if not value or value == '0':
                        continue
                    
                    stat_leader = StatLeader(
                        season='2025',
                        category=category,
                        player_id=player_id,
                        player_name=player_name,
                        team_id=team_id,
                        team_name=team_name,
                        value=str(value),
                        rank=rank,
                        last_updated=date.today()
                    )
                    
                    db.session.add(stat_leader)
                    valid_count += 1
                    
                    if valid_count >= 50:  # Limit to top 50
                        break
                        
                except Exception as e:
                    print(f"[ERROR] Error processing {category} leader: {e}")
                    continue
            
            db.session.commit()
            total_added += valid_count
            print(f"[SUCCESS] Added {valid_count} {category} leaders")
            
        except Exception as e:
            print(f"[ERROR] Failed to fetch {category}: {e}")
            db.session.rollback()
            continue
    
    return total_added

def main():
    """Main function to fetch all stat leaders."""
    app = create_app()
    
    with app.app_context():
        try:
            print("============================================================")
            print("🏆 FETCHING 2025 SEASON STAT LEADERS")
            print("============================================================")
            
            # Clear existing data
            clear_existing_data()
            
            # Fetch individual stat leaders
            individual_count = fetch_2025_stat_leaders()
            print(f"[SUCCESS] Added {individual_count} individual stat leaders")
            
            print("============================================================")
            print(f"✅ COMPLETED: {individual_count} total stat leaders")
            print("============================================================")
            
        except Exception as e:
            print(f"[ERROR] Critical error: {e}")
            db.session.rollback()

if __name__ == "__main__":
    main() 