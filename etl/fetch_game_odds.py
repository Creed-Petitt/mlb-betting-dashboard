#!/usr/bin/env python3
"""
Fetch game odds from OddsAPI for MLB games (today and tomorrow only)
"""

import sys
import os
import requests
import logging
from datetime import datetime, date, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import db, GameOdds

# Configure logging
logging.basicConfig(level=logging.INFO)

# API Configuration
ODDS_API_KEY = os.environ.get("ODDS_API_KEY")
if not ODDS_API_KEY:
    raise ValueError("ODDS_API_KEY environment variable not set. Please set it in your environment.")
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/"

# Target bookmakers (in order of preference)
TARGET_BOOKMAKERS = ['fanduel', 'draftkings', 'betmgm']

def fetch_mlb_odds():
    """Fetch MLB game odds from OddsAPI."""
    
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'h2h',  # Head-to-head (moneyline) odds
        'oddsFormat': 'american',
        'dateFormat': 'iso'
    }
    
    try:
        print(f"[INFO] Fetching MLB odds from OddsAPI...")
        response = requests.get(ODDS_API_URL, params=params, timeout=30)
        response.raise_for_status()
        
        remaining_requests = response.headers.get('x-requests-remaining')
        print(f"[INFO] API call successful. Remaining requests: {remaining_requests}")
        
        return response.json()
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch odds: {e}")
        raise

def process_and_store_odds(games_data):
    """Process odds data and store in database."""
    
    # Get today and tomorrow's dates for filtering
    today = date.today()
    tomorrow = today + timedelta(days=1)
    target_dates = {today, tomorrow}
    
    new_odds = 0
    updated_odds = 0
    total_games = 0
    
    print(f"[INFO] Processing {len(games_data)} games...")
    
    for game in games_data:
        try:
            # Parse game time
            commence_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            game_date = commence_time.date()
            
            # Only process today and tomorrow's games
            if game_date not in target_dates:
                continue
                
            total_games += 1
            game_id = game['id']
            home_team = game['home_team']
            away_team = game['away_team']
            
            date_label = "TODAY" if game_date == today else "TOMORROW"
            print(f"[INFO] Processing {date_label}: {away_team} @ {home_team}")
            
            # Process bookmakers
            for bookmaker_data in game['bookmakers']:
                bookmaker_key = bookmaker_data['key']
                
                # Only store odds from our target bookmakers
                if bookmaker_key not in TARGET_BOOKMAKERS:
                    continue
                
                # Extract odds from the h2h market
                market = bookmaker_data['markets'][0]  # h2h market
                outcomes = market['outcomes']
                
                # Find home and away odds
                home_odds = None
                away_odds = None
                
                for outcome in outcomes:
                    if outcome['name'] == home_team:
                        home_odds = outcome['price']
                    elif outcome['name'] == away_team:
                        away_odds = outcome['price']
                
                if home_odds is None or away_odds is None:
                    print(f"[WARNING] Missing odds for {bookmaker_key}: {away_team} @ {home_team}")
                    continue
                
                # Check if odds already exist
                existing_odds = GameOdds.query.filter_by(
                    game_id=game_id,
                    bookmaker=bookmaker_key
                ).first()
                
                last_update = datetime.fromisoformat(
                    bookmaker_data['last_update'].replace('Z', '+00:00')
                )
                
                if existing_odds:
                    # Update existing odds if they've changed
                    if (existing_odds.home_odds != home_odds or 
                        existing_odds.away_odds != away_odds):
                        existing_odds.home_odds = int(home_odds)
                        existing_odds.away_odds = int(away_odds)
                        existing_odds.last_update = last_update
                        updated_odds += 1
                        print(f"[UPDATE] {bookmaker_key}: {home_team} {home_odds}, {away_team} {away_odds}")
                else:
                    # Create new odds entry
                    new_game_odds = GameOdds(
                        game_id=game_id,
                        date=game_date,
                        commence_time=commence_time,
                        home_team=home_team,
                        away_team=away_team,
                        bookmaker=bookmaker_key,
                        home_odds=int(home_odds),
                        away_odds=int(away_odds),
                        last_update=last_update
                    )
                    db.session.add(new_game_odds)
                    new_odds += 1
                    print(f"[NEW] {bookmaker_key}: {home_team} {home_odds}, {away_team} {away_odds}")
                    
        except Exception as e:
            print(f"[ERROR] Failed to process game {game.get('id', 'unknown')}: {e}")
            continue
    
    # Commit all changes
    try:
        db.session.commit()
        print(f"\n[SUCCESS] Game odds update complete!")
        print(f"  📈 Processed {total_games} games")
        print(f"  🆕 Added {new_odds} new odds")
        print(f"  🔄 Updated {updated_odds} existing odds")
        
        # Show current odds summary
        total_odds = GameOdds.query.filter(GameOdds.date.in_([today, tomorrow])).count()
        print(f"  📊 Total odds in database: {total_odds}")
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Failed to commit odds to database: {e}")
        raise

def main():
    """Main function."""
    try:
        app = create_app()
        with app.app_context():
            # Create tables if they don't exist
            db.create_all()
            
            # Fetch odds data
            games_data = fetch_mlb_odds()
            
            # Process and store odds
            process_and_store_odds(games_data)
            
    except Exception as e:
        logging.error(f"Critical error in fetch_game_odds: {e}")
        print(f"[ERROR] {e}")
        raise

if __name__ == "__main__":
    main()
