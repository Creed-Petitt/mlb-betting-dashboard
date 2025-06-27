import sys
import os
import unicodedata
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from app import create_app
from app.models import db, Player, Prop
from datetime import datetime, date, timedelta
import logging

url = "https://sbapi.nj.sportsbook.fanduel.com/api/content-managed-page?page=CUSTOM&customPageId=mlb&pbHorizontal=false&_ak=FhMFpcPWXMeyZxOx&timezone=America%2FNew_York"

headers = {
    "sec-ch-ua-platform": '"Windows"',
    "Referer": "https://sportsbook.fanduel.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 Edg/137.0.0.0",
    "Accept": "application/json",
    "sec-ch-ua": '"Microsoft Edge";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    "x-px-context": "_px3=7d4f6aa379bb34d253a0e334dea5a1c79d6ace594f9afd3cdaecff9aea435553:wfZjz89iVcAcdOlHjDMI6SHyPyItEKneBUcXEkQhMVgNT1qxrkL6JE3g2Xa1HYOHHm7BZ8VgctsnmueMoTiMTQ==:1000:wnu11CGQBis7hwMroq+ZFh1R+AARB6duyfdfc9PdzlAOphfVkrdxznl6+5+YWCMFkxyHWA0jkJiGgPumljyaXSbzN1fqzCSPXEl5jJ11Sytsq7A3+aRDGhRSViCq7fP5HUpOMe64/OIkRjuXBBHs15b+9aR2jSUaeNN48piOnF17tYoDJR8B8MMxCXXMidAbL2B/c8vLaVMFZf/MkcVKOZzdKC7p+3BstDkTbu8T3uA=;_pxvid=f68a7d3a-4bdd-11f0-9b34-bd50185eee2b;pxcts=f68a8c84-4bdd-11f0-9b34-4be61636ad41;",
    "sec-ch-ua-mobile": "?0"
}

def normalize_name(name):
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    name = name.lower().replace('.', '').replace('-', ' ').replace("'", "").strip()
    return name

def get_player_name_map():
    name_map = {}
    for player in Player.query.all():
        n = normalize_name(player.name)
        name_map[n] = player
    return name_map

def pull_fanduel_props():
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        print("[DEBUG] Successfully fetched FanDuel JSON")
    except Exception as e:
        print("[ERROR] Failed to fetch or parse FanDuel page:", e)
        return

    events = data.get("attachments", {}).get("events", {})
    competitions = data.get("attachments", {}).get("competitions", {})
    markets = data.get("attachments", {}).get("markets", {})

    print("\n=== EVENTS SAMPLE ===")
    for eid, event in list(events.items())[:10]:
        print(f"[DEBUG] Event ID: {eid} | Name: {event.get('name')} | openDate: {event.get('openDate')}")

    print("\n=== COMPETITIONS SAMPLE ===")
    for cid, comp in list(competitions.items())[:10]:
        print(f"[DEBUG] Competition ID: {cid} | Name: {comp.get('name')} | openDate: {comp.get('openDate')}")

    print("\n=== MARKETS SAMPLE ===")
    for i, m in enumerate(markets.values()):
        if i >= 10:
            break
        print(f"[DEBUG] Market eventId: {m.get('eventId')} | marketName: {m.get('marketName')} | competitionId: {m.get('competitionId')} | keys: {m.keys()}")

    print(f"\n[DEBUG] Loaded {len(events)} events, {len(competitions)} competitions, {len(markets)} markets")

    name_map = get_player_name_map()
    print(f"[DEBUG] Loaded {len(name_map)} player names from DB")

    # Try to build mapping from eventId to openDate
    # Focus on today and tomorrow's games only for cleaner data
    event_id_to_date = {}
    today = date.today()
    tomorrow = today + timedelta(days=1)
    target_dates = {today, tomorrow}
    
    for eid, event in events.items():
        openDate = event.get("openDate")
        if openDate:
            try:
                game_date = datetime.fromisoformat(openDate.replace('Z', '+00:00')).date()
                # Only include today and tomorrow's games
                if game_date in target_dates:
                    event_id_to_date[str(eid)] = game_date
                    if game_date == today:
                        print(f"[DEBUG] Found TODAY's game: {event.get('name')} on {game_date}")
                    elif game_date == tomorrow:
                        print(f"[DEBUG] Found TOMORROW's game: {event.get('name')} on {game_date}")
            except Exception as ex:
                print(f"[DEBUG] Could not parse openDate '{openDate}' for event {eid}: {ex}")

    print(f"[DEBUG] event_id_to_date sample: {list(event_id_to_date.items())[:5]}")

    # Try to build mapping from competitionId to openDate
    competition_id_to_date = {}
    for cid, comp in competitions.items():
        openDate = comp.get("openDate")
        if openDate:
            try:
                game_date = datetime.fromisoformat(openDate.replace('Z', '+00:00')).date()
                competition_id_to_date[str(cid)] = game_date
            except Exception as ex:
                print(f"[DEBUG] Could not parse openDate '{openDate}' for competition {cid}: {ex}")

    print(f"[DEBUG] competition_id_to_date sample: {list(competition_id_to_date.items())[:5]}")

    new_props = 0
    
    # Target prop market types
    target_markets = {
        "PLAYER_TO_RECORD_A_HIT": "Hits",
        "TO_RECORD_AN_RBI": "RBI", 
        "TO_RECORD_2+_RBIS": "RBI",
        "TO_HIT_A_HOME_RUN": "Home Runs"
    }
    
    print(f"🎯 Targeting {len(target_markets)} prop market types:")
    for market_type, category in target_markets.items():
        print(f"   📈 {market_type} → {category}")
    
    markets_found = {market_type: 0 for market_type in target_markets}
    
    for m in markets.values():
        market_type = m.get("marketType")
        prop_type = m.get("marketName")
        event_id = str(m.get("eventId", ""))
        competition_id = str(m.get("competitionId", ""))

        # Only process our target market types
        if market_type not in target_markets:
            continue
            
        markets_found[market_type] += 1
        category = target_markets[market_type]
        print(f"✅ Found {category} market: {market_type} #{markets_found[market_type]} → '{prop_type}'")

        # Get game date with improved logging
        game_date = event_id_to_date.get(event_id)
        if not game_date:
            game_date = competition_id_to_date.get(competition_id)
        if not game_date:
            game_date = date.today()  # fallback
            print(f"[DEBUG] ⚠️  No game_date found for eventId={event_id}, competitionId={competition_id}, using TODAY ({game_date}) as fallback")
        else:
            print(f"[DEBUG] ✅ Found game_date: {game_date} for eventId={event_id}")

        runners = m.get("runners", [])
        print(f"📝 Processing {len(runners)} runners for {market_type}")
        
        for runner in runners:
            fanduel_name = runner.get("runnerName", "")
            line = runner.get("handicap")
            odds = runner.get("winRunnerOdds", {}).get("americanDisplayOdds", {}).get("americanOdds")
            
            if not fanduel_name:
                continue
                
            norm_name = normalize_name(fanduel_name)
            player = name_map.get(norm_name)
            if not player:
                # Fuzzy match fallback
                for db_name, db_player in name_map.items():
                    if norm_name in db_name or db_name in norm_name:
                        player = db_player
                        break
            if not player:
                print(f"❌ [NO MATCH] {fanduel_name} (normalized: '{norm_name}')")
                continue

            # Check if prop already exists
            exists = (
                db.session.query(Prop)
                .filter_by(date=game_date, player_id=player.id, event_id=event_id, prop_type=prop_type)
                .first()
            )
            if not exists:
                db.session.add(Prop(
                    date=game_date,
                    player_id=player.id,
                    event_id=event_id,
                    prop_type=prop_type,
                    line=line,
                    odds=odds
                ))
                new_props += 1
    
    # Print summary
    print(f"\n📊 MARKET SUMMARY:")
    total_markets = 0
    for market_type, count in markets_found.items():
        category = target_markets[market_type]
        print(f"   {category}: {count} markets found ({market_type})")
        total_markets += count
    
    db.session.commit()
    
    # Show current date breakdown
    print(f"\n📅 CURRENT PROPS BY DATE:")
    from sqlalchemy import text
    result = db.session.execute(text("SELECT date, COUNT(*) as count FROM props GROUP BY date ORDER BY date DESC LIMIT 7"))
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    for row in result:
        prop_date, count = row
        date_label = ""
        if str(prop_date) == str(today):
            date_label = " (TODAY)"
        elif str(prop_date) == str(tomorrow):
            date_label = " (TOMORROW)"
        print(f"   {prop_date}{date_label}: {count} props")
    
    print(f"\n🎉 Added {new_props} NEW props from {total_markets} markets total!")

def main():
    """Main function with error handling to prevent crashes."""
    try:
        app = create_app()
        with app.app_context():
            pull_fanduel_props()
    except Exception as e:
        logging.error(f"Critical error in fetch_props: {e}")
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    main()
