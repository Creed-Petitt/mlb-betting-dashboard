import sqlite3
import pandas as pd
import joblib
from props import get_fanduel_hit_props, save_hit_props_to_db

# Load model
model = joblib.load("models/hit_model.joblib")

# Load database tables
conn = sqlite3.connect("data/mlb.db")

cached = pd.read_sql("SELECT * FROM cached_player_names", conn)
cached["player_name"] = cached["player_name"].str.lower()

features = pd.read_sql("SELECT * FROM game_level_features", conn, parse_dates=["game_date"])
conn.close()

# Load FanDuel props
props = get_fanduel_hit_props()

results = []

for row in props:
    name = row["player"].lower()
    decimal_odds = row["decimal_odds"]
    
    match = cached[cached["player_name"] == name]
    if match.empty:
        print(f"No match for: {name}")
        continue

    mlb_id = match.iloc[0]["mlb_id"]

    player_stats = features[features["batter"] == mlb_id].sort_values("game_date", ascending=False)
    if player_stats.empty:
        print(f"No game stats for: {name}")
        continue

    # Use latest row only
    X = player_stats.iloc[0:1].copy()

    try:
        X_model = X[model.feature_names_in_].copy()
        prob = float(model.predict_proba(X_model)[0][1])
    except Exception as e:
        print(f"Error predicting for {name}: {e}")
        continue

    results.append({
        "player_name": name,
        "line": decimal_odds,
        "prob": round(prob, 4)
    })
    print(f"{name}: P(hit) = {prob:.3f}, Odds = {decimal_odds}")

# Save to DB
conn = sqlite3.connect("data/mlb.db")
df = pd.DataFrame(results)
df.to_sql("hit_prop_predictions", conn, if_exists="replace", index=False)
conn.close()

print(f"Saved {len(df)} predictions to hit_prop_predictions")
