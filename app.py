from flask import Flask, request, render_template
import joblib
import sqlite3
import pandas as pd
from pybaseball import playerid_lookup, playerid_reverse_lookup
from datetime import datetime

app = Flask(__name__)

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

# Get dropdown list of players
def get_unique_players():
    conn = sqlite3.connect("data/mlb.db")
    batters = pd.read_sql("SELECT DISTINCT batter FROM game_level_stats", conn)['batter'].tolist()
    pitchers = pd.read_sql("SELECT DISTINCT pitcher FROM pitcher_game_stats", conn)['pitcher'].tolist()
    all_ids = sorted(set(batters + pitchers))

    name_df = playerid_reverse_lookup(all_ids, key_type='mlbam')
    name_map = dict(zip(name_df['key_mlbam'], name_df['name_first'] + ' ' + name_df['name_last']))
    conn.close()

    return [(pid, name_map.get(pid, f"Unknown {pid}")) for pid in all_ids]

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
    player_list = get_unique_players()
    return render_template("index.html", players=player_list)

@app.route("/predict_prop", methods=["POST"])
def predict_prop():
    name_input = request.form["player_name"]
    prop_type = request.form["prop_type"]
    line = float(request.form["line"])

    player_id = get_mlbam_id(name_input)
    if player_id is None:
        return render_template("index.html", prediction="N/A", over_under="Invalid name", players=get_unique_players())

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
        return render_template("index.html", prediction="N/A", over_under="No game data", players=get_unique_players())

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

        return render_template("index.html", prediction=round(prediction, 2), over_under=over_under, players=get_unique_players())
    except Exception as e:
        return render_template("index.html", prediction="Error", over_under=str(e), players=get_unique_players())


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
