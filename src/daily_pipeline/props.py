import requests
import sqlite3

def get_fanduel_hit_props():
    url = "https://sbapi.nj.sportsbook.fanduel.com/api/content-managed-page?page=CUSTOM&customPageId=mlb&pbHorizontal=false&_ak=FhMFpcPWXMeyZxOx&timezone=America%2FNew_York"
    headers = {
        "User-Agent": "Mozilla/5.0",
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
                odds_info = runner.get("winRunnerOdds", {})

                # Pull both decimal and American odds
                decimal_odds = odds_info.get("decimalDisplayOdds", {}).get("value")
                american_odds = odds_info.get("americanDisplayOdds", {}).get("americanOdds")

                # Print for debugging
                #print(player_name, "=>", american_odds)

                hit_props.append({
                    "event_id": event_id,
                    "market_id": market_id,
                    "market_time": market_time,
                    "player": player_name,
                    "decimal_odds": decimal_odds,
                    "american_odds": str(american_odds) if american_odds is not None else None
                })

    return hit_props


def save_hit_props_to_db(props):
    conn = sqlite3.connect("data/mlb.db")
    c = conn.cursor()

    # Clear old props
    c.execute("DELETE FROM hit_props")

    for p in props:
        c.execute("""
            INSERT INTO hit_props (
                event_id, market_id, market_time, player, decimal_odds, american_odds
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            p["event_id"],
            p["market_id"],
            p["market_time"],
            p["player"],
            p["decimal_odds"],
            p["american_odds"]
        ))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    props = get_fanduel_hit_props()
    save_hit_props_to_db(props)
