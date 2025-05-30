from flask import Flask, request, render_template
import joblib
import sqlite3
import pandas as pd
from pybaseball import playerid_lookup, playerid_reverse_lookup
from datetime import datetime
from dotenv import load_dotenv
import os
import requests
from props import get_fanduel_hit_props, save_hit_props_to_db


app = Flask(__name__)

load_dotenv()
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

# Load models
models = {
    "hits": joblib.load("model/model_rf_game_hits_reg.joblib"),
    "tb": joblib.load("model/model_rf_game_total_bases.joblib"),
    "runs": joblib.load("model/model_rf_game_runs_scored.joblib"),
    "so": joblib.load("model/model_rf_pitcher_strikeouts.joblib"),
    "ip": joblib.load("model/model_rf_innings_pitched.joblib")
}

# Feature mappings
feature_map = {
    "hits": ['batter_hits_5g', 'pitcher_hits_allowed_5g', 'is_same_side', 'stand', 'p_throws',
             'batter_team', 'pitcher_team', 'is_home_game', 'day_of_week', 'park_factor'],
    "tb":   ['batter_hits_5g', 'pitcher_hits_allowed_5g', 'is_same_side', 'stand', 'p_throws',
             'batter_team', 'pitcher_team', 'is_home_game', 'day_of_week', 'park_factor'],
    "runs": ['batter_hits_5g', 'pitcher_hits_allowed_5g', 'is_same_side', 'stand', 'p_throws',
             'batter_team', 'pitcher_team', 'is_home_game', 'day_of_week', 'park_factor'],
    "so":   ['pitcher_hits_allowed_5g', 'p_throws', 'pitcher_team', 'batter_team',
             'is_home_game', 'day_of_week', 'park_factor'],
    "ip":   ['pitcher_hits_allowed_5g', 'p_throws', 'pitcher_team', 'batter_team',
             'is_home_game', 'day_of_week', 'park_factor']
}

# Label encoders
stand_map = {"L": 0, "R": 1}
p_throws_map = {"L": 0, "R": 1}
team_map = {
    'ARI': 0, 'ATL': 1, 'BAL': 2, 'BOS': 3, 'CHC': 4, 'CIN': 5, 'CLE': 6, 'COL': 7,
    'CWS': 8, 'DET': 9, 'HOU': 10, 'KC': 11, 'LAA': 12, 'LAD': 13, 'MIA': 14,
    'MIL': 15, 'MIN': 16, 'NYM': 17, 'NYY': 18, 'OAK': 19, 'PHI': 20, 'PIT': 21,
    'SD': 22, 'SEA': 23, 'SF': 24, 'STL': 25, 'TB': 26, 'TEX': 27, 'TOR': 28, 'WSH': 29
}

# Initialize DB with predictions table
def init_db():
    conn = sqlite3.connect("data/mlb.db")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        player_id INTEGER,
        player_name TEXT,
        prop_type TEXT,
        line REAL,
        prediction REAL,
        over_under TEXT
    )
    """)
    conn.close()

def get_today_hit_predictions():
    conn = sqlite3.connect("data/mlb.db")
    df = pd.read_sql_query("""
        SELECT player_name, line, prediction, over_under, timestamp
        FROM predictions
        WHERE prop_type = 'hits'
        ORDER BY timestamp DESC
    """, conn)
    conn.close()

    # Compute edge %
    df["implied_prob"] = 1 / df["line"]
    df["edge"] = (df["prediction"] - df["implied_prob"]) * 100
    df["edge"] = df["edge"].round(1)
    df.sort_values("edge", ascending=False, inplace=True)
    df = df.drop_duplicates(subset=["player_name"], keep="first")
    df["prediction"] = (df["prediction"] * 100).round(1)
    df["implied_prob"] = (df["implied_prob"] * 100).round(1)

    return df.to_dict(orient="records")

def init_player_cache():
    conn = sqlite3.connect("data/mlb.db")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS cached_player_names (
        player_id INTEGER PRIMARY KEY,
        player_name TEXT,
        last_updated TEXT
    )
    """)
    conn.close()


def get_upcoming_players():
    from pybaseball import playerid_reverse_lookup
    from datetime import datetime

    conn = sqlite3.connect("data/mlb.db")

    # Get all unique player ids from upcoming games
    result = conn.execute("""
        SELECT DISTINCT home_pitcher_id FROM upcoming_games WHERE home_pitcher_id IS NOT NULL
        UNION
        SELECT DISTINCT away_pitcher_id FROM upcoming_games WHERE away_pitcher_id IS NOT NULL
    """).fetchall()
    pitcher_ids = [int(row[0]) for row in result]

    # Get probable batter ids
    # For now: fetch all batter IDs from recent games (say last 7 days) — a simple heuristic
    batter_result = conn.execute("""
        SELECT DISTINCT batter FROM game_level_stats
        WHERE game_date >= DATE('now', '-7 day') AND batter IS NOT NULL
    """).fetchall()
    batter_ids = [int(row[0]) for row in batter_result]

    # Combine all IDs
    all_ids = sorted(set(pitcher_ids + batter_ids))

    # Fetch from cache
    cached = conn.execute(
        f"""SELECT player_id, player_name FROM cached_player_names
            WHERE player_id IN ({','.join(['?'] * len(all_ids))})
        """, all_ids
    ).fetchall()
    cached_dict = {pid: name for pid, name in cached}

    # Find missing ids
    missing_ids = [pid for pid in all_ids if pid not in cached_dict]

    # Fetch and cache missing games
    if missing_ids:
        new_df = playerid_reverse_lookup(missing_ids, key_type="mlbam")
        new_df["full_name"] = new_df["name_first"] + " " + new_df["name_last"]

        for _, row in new_df.iterrows():
            pid = int(row["key_mlbam"])
            name = row["full_name"]
            cached_dict[pid] = name
            conn.execute("""
                INSERT OR REPLACE INTO cached_player_names (player_id, player_name, last_updated)
                VALUES (?, ?, ?)
            """, (pid, name, datetime.now().isoformat(timespec='seconds')))
        conn.commit()

    conn.close()

    return [(pid, cached_dict.get(pid, f"Unknown {pid}")) for pid in pitcher_ids]

# Lookup player ID from name
def get_mlbam_id(name):
    try:
        first, last = name.strip().split(maxsplit=1)
        result = playerid_lookup(last, first)
        if not result.empty:
            return int(result.iloc[0]['key_mlbam'])
    except Exception:
        return None

@app.route("/")
def home():
    predictions = get_today_hit_predictions()
    return render_template("index.html", predictions=predictions)

@app.route("/predict_prop", methods=["POST"])
def predict_prop():
    name_input = request.form["player_name"]
    prop_type = request.form["prop_type"]
    line = float(request.form["line"])

    player_id = get_mlbam_id(name_input)
    if player_id is None:
        return render_template("index.html", prediction="N/A", over_under="Invalid name", players=get_upcoming_players())

    table = "pitcher_game_stats" if prop_type in ["so", "ip"] else "game_level_stats"
    features = feature_map[prop_type]

    conn = sqlite3.connect("data/mlb.db")
    if prop_type in ["so", "ip"]:
        query = "SELECT * FROM {} WHERE pitcher = ? ORDER BY game_date DESC LIMIT 1".format(table)
    else:
        query = "SELECT * FROM {} WHERE batter = ? ORDER BY game_date DESC LIMIT 1".format(table)
    df = pd.read_sql_query(query, conn, params=[player_id])
    conn.close()

    if df.empty:
        return render_template("index.html", prediction="N/A", over_under="No game data", players=get_upcoming_players())

    try:
        row = df.iloc[0]
        if 'stand' in features:
            row['stand'] = stand_map.get(row['stand'], 0)
        if 'p_throws' in features:
            row['p_throws'] = p_throws_map.get(row['p_throws'], 0)
        if 'batter_team' in features:
            row['batter_team'] = team_map.get(row['batter_team'], 0)
        if 'pitcher_team' in features:
            row['pitcher_team'] = team_map.get(row['pitcher_team'], 0)

        input_data = [row[f] for f in features]
        model = models[prop_type]
        prediction = float(model.predict([input_data])[0])
        over_under = "OVER" if prediction > line else "UNDER"

        # Log to DB
        conn = sqlite3.connect("data/mlb.db")
        conn.execute("""
        INSERT INTO predictions (timestamp, player_id, player_name, prop_type, line, prediction, over_under)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(timespec='seconds'),
            player_id,
            name_input,
            prop_type,
            line,
            round(prediction, 2),
            over_under
        ))
        conn.commit()
        conn.close()

        return render_template("index.html", prediction=round(prediction, 2), over_under=over_under, players=get_upcoming_players())
    except Exception as e:
        return render_template("index.html", prediction="Error", over_under=str(e), players=get_upcoming_players())

if __name__ == "__main__":
    # Optionally refresh props when server starts
    props = get_fanduel_hit_props()
    save_hit_props_to_db(props)

    # Start the Flask app
    app.run(debug=True)


