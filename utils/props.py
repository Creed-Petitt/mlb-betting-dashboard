import requests
import sqlite3

def save_hit_props_to_db(props):
    conn = sqlite3.connect("data/mlb.db")
    c = conn.cursor()

    # Clear existing props
    c.execute("DELETE FROM hit_props")

    # Insert new ones
    for p in props:
        c.execute("""
            INSERT INTO hit_props (event_id, market_id, market_time, player, decimal_odds)
            VALUES (?, ?, ?, ?, ?)
        """, (p["event_id"], p["market_id"], p["market_time"], p["player"], p["decimal_odds"]))

    conn.commit()
    conn.close()


def get_fanduel_hit_props():
    url = "https://sbapi.nj.sportsbook.fanduel.com/api/content-managed-page?page=CUSTOM&customPageId=mlb&pbHorizontal=false&_ak=FhMFpcPWXMeyZxOx&timezone=America%2FNew_York"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    response = requests.get(url, headers=headers)

    data = response.json()

    hit_props = []

    for market in data.get("attachments", {}).get("markets", {}).values():
        if market.get("marketType") == "PLAYER_TO_RECORD_A_HIT":
            event_id = market.get("eventId")
            market_id = market.get("marketId")
            market_time = market.get("marketTime")

            for runner in market.get("runners", []):
                player_name = runner.get("runnerName")

                # Safely get decimal odds
                odds_info = runner.get("winRunnerOdds", {})
                decimal_odds = odds_info.get("decimalDisplayOdds", {}).get("value")

                # Fallback if display odds are missing
                if decimal_odds is None:
                    decimal_odds = odds_info.get("trueOdds", {}).get("decimalOdds", {}).get("decimalOdds", None)

                hit_props.append({
                    "event_id": event_id,
                    "market_id": market_id,
                    "market_time": market_time,
                    "player": player_name,
                    "decimal_odds": decimal_odds
                })

    return hit_props
