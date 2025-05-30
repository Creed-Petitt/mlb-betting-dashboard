import sqlite3
import pandas as pd
import joblib
from datetime import datetime
import math

# Load the hits model
model = joblib.load("model/model_rf_game_hits_reg.joblib")

# Mappings
stand_map = {"L": 0, "R": 1}
p_throws_map = {"L": 0, "R": 1}
team_map = {
    'ARI': 0, 'ATL': 1, 'BAL': 2, 'BOS': 3, 'CHC': 4, 'CIN': 5, 'CLE': 6, 'COL': 7,
    'CWS': 8, 'DET': 9, 'HOU': 10, 'KC': 11, 'LAA': 12, 'LAD': 13, 'MIA': 14,
    'MIL': 15, 'MIN': 16, 'NYM': 17, 'NYY': 18, 'OAK': 19, 'PHI': 20, 'PIT': 21,
    'SD': 22, 'SEA': 23, 'SF': 24, 'STL': 25, 'TB': 26, 'TEX': 27, 'TOR': 28, 'WSH': 29
}

features = [
    'batter_hits_5g', 'pitcher_hits_allowed_5g', 'is_same_side',
    'stand', 'p_throws', 'batter_team', 'pitcher_team',
    'is_home_game', 'day_of_week', 'park_factor'
]

def run_hit_predictions():
    conn = sqlite3.connect("data/mlb.db")

    # Load FanDuel props
    props = pd.read_sql_query("SELECT * FROM hit_props", conn)

    for _, row in props.iterrows():
        name = row["player"].strip().lower()
        decimal_odds = row["decimal_odds"]

        # Lookup player ID
        result = conn.execute(
            "SELECT player_id FROM cached_player_names WHERE player_name = ?", (name,)
        ).fetchone()
        if not result:
            print(f"Skipping: {name} not found in cache")
            continue
        player_id = result[0]

        # Get most recent stats
        df = pd.read_sql_query(
            "SELECT * FROM game_level_stats WHERE batter = ? ORDER BY game_date DESC LIMIT 1",
            conn, params=[player_id]
        )
        if df.empty:
            print(f"No game stats for {name}")
            continue

        stat_row = df.iloc[0].copy()

        # Encode categoricals
        try:
            stat_row["stand"] = stand_map.get(stat_row["stand"], 0)
            stat_row["p_throws"] = p_throws_map.get(stat_row["p_throws"], 0)
            stat_row["batter_team"] = team_map.get(stat_row["batter_team"], 0)
            stat_row["pitcher_team"] = team_map.get(stat_row["pitcher_team"], 0)
        except Exception as e:
            print(f"Encoding error for {name}: {e}")
            continue

        input_df = pd.DataFrame([stat_row[features]])
        prediction = model.predict(input_df)[0]

        # Estimate P(hit ≥ 1) using Poisson
        p_hit = 1 - math.exp(-prediction)

        if decimal_odds:
            implied_prob = 1 / float(decimal_odds)
            edge = p_hit - implied_prob
            over_under = "OVER" if edge > 0 else "UNDER"
        else:
            implied_prob = None
            over_under = "N/A"

        # Log to predictions table
        conn.execute("""
            INSERT INTO predictions (timestamp, player_id, player_name, prop_type, line, prediction, over_under)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(timespec='seconds'),
            player_id,
            name,
            "hits",
            decimal_odds,
            round(p_hit, 4),  # now logging probability
            over_under
        ))

        if implied_prob:
            print(f"{name} --> Model P(hit): {p_hit:.2f}, Implied: {implied_prob:.2f} --> {over_under}")
        else:
            print(f"{name} --> Model P(hit): {p_hit:.2f} --> {over_under} (no odds)")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    run_hit_predictions()
