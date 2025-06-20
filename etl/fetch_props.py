import sys
import os
import unicodedata
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from app import create_app
from app.models import db, Player, Prop
from datetime import datetime

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
    event_id_to_date = {}
    for eid, event in events.items():
        openDate = event.get("openDate")
        if openDate:
            try:
                game_date = datetime.fromisoformat(openDate.replace('Z', '+00:00')).date()
                event_id_to_date[str(eid)] = game_date
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

    for m in markets.values():
        market_type = m.get("marketType")
        prop_type = m.get("marketName")
        event_id = str(m.get("eventId", ""))
        competition_id = str(m.get("competitionId", ""))

        # Only use PLAYER_TO_RECORD_A_HIT for now
        if market_type != "PLAYER_TO_RECORD_A_HIT":
            continue

        # Prefer event date, fallback to competition date
        game_date = event_id_to_date.get(event_id)
        if not game_date:
            game_date = competition_id_to_date.get(competition_id)

        if not game_date:
            print(f"[DEBUG] No game_date found for market event_id {event_id}, competition_id {competition_id}")
            continue

        for runner in m.get("runners", []):
            fanduel_name = runner.get("runnerName", "")
            line = runner.get("handicap")
            odds = runner.get("winRunnerOdds", {}).get("americanDisplayOdds", {}).get("americanOdds")
            norm_name = normalize_name(fanduel_name)
            player = name_map.get(norm_name)
            if not player:
                # Fuzzy match fallback
                for db_name, db_player in name_map.items():
                    if norm_name in db_name or db_name in norm_name:
                        player = db_player
                        break
            if not player:
                print(f"[NO MATCH] {fanduel_name} (normalized: '{norm_name}')")
                continue

            exists = (
                db.session.query(Prop)
                .filter_by(date=game_date, player_id=player.id, event_id=event_id, prop_type=prop_type)
                .first()
            )
            if not exists:
                print(f"[DEBUG] Adding prop: {fanduel_name}, date={game_date}, event_id={event_id}, odds={odds}")
                db.session.add(Prop(
                    date=game_date,
                    player_id=player.id,
                    event_id=event_id,
                    prop_type=prop_type,
                    line=line,
                    odds=odds
                ))
                new_props += 1

    db.session.commit()
    print(f"\nAdded {new_props} props.")


    name_map = get_player_name_map()
    print(f"[DEBUG] Loaded {len(name_map)} player names from DB")

    new_props = 0
    seen_market_types = set()

    for m in markets.values():
        market_type = m.get("marketType")
        prop_type = m.get("marketName")
        event_id = str(m.get("eventId", ""))
        seen_market_types.add(market_type)
        if market_type != "PLAYER_TO_RECORD_A_HIT":
            continue
        game_date = event_id_to_date.get(event_id)
        if not game_date:
            print(f"[DEBUG] No game_date found for event_id {event_id}")
            continue

        for runner in m.get("runners", []):
            fanduel_name = runner.get("runnerName", "")
            line = runner.get("handicap")
            odds = runner.get("winRunnerOdds", {}).get("americanDisplayOdds", {}).get("americanOdds")
            norm_name = normalize_name(fanduel_name)
            player = name_map.get(norm_name)
            if not player:
                # Fuzzy match fallback
                for db_name, db_player in name_map.items():
                    if norm_name in db_name or db_name in norm_name:
                        player = db_player
                        break
            if not player:
                print(f"[NO MATCH] {fanduel_name} (normalized: '{norm_name}')")
                continue

            exists = (
                db.session.query(Prop)
                .filter_by(date=game_date, player_id=player.id, event_id=event_id, prop_type=prop_type)
                .first()
            )
            if not exists:
                print(f"[DEBUG] Adding prop: {fanduel_name}, date={game_date}, event_id={event_id}, odds={odds}")
                db.session.add(Prop(
                    date=game_date,
                    player_id=player.id,
                    event_id=event_id,
                    prop_type=prop_type,
                    line=line,
                    odds=odds
                ))
                new_props += 1

    db.session.commit()
    print(f"Added {new_props} props.")
    print(f"[DEBUG] Market types seen: {seen_market_types}")

    name_map = get_player_name_map()
    new_props = 0
    for m in markets.values():
        market_type = m.get("marketType")
        prop_type = m.get("marketName")
        event_id = str(m.get("eventId", ""))
        if market_type != "PLAYER_TO_RECORD_A_HIT":
            continue
        game_date = event_id_to_date.get(event_id)
        if not game_date:
            continue  # Skip if we can't determine the correct date

        for runner in m.get("runners", []):
            fanduel_name = runner.get("runnerName", "")
            line = runner.get("handicap")
            odds = runner.get("winRunnerOdds", {}).get("americanDisplayOdds", {}).get("americanOdds")
            norm_name = normalize_name(fanduel_name)
            player = name_map.get(norm_name)
            if not player:
                # Fuzzy match fallback
                for db_name, db_player in name_map.items():
                    if norm_name in db_name or db_name in norm_name:
                        player = db_player
                        break
            if not player:
                print(f"NO MATCH: {fanduel_name}")
                continue

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
    db.session.commit()
    print(f"Added {new_props} props.")

def main():
    app = create_app()
    with app.app_context():
        pull_fanduel_props()

if __name__ == "__main__":
    main()
