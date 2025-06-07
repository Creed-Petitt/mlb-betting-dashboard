import sqlite3
import pandas as pd
from flask import Flask, render_template, request

app = Flask(__name__, template_folder="templates")
DB_PATH = "data/mlb.db"

@app.route("/")
def home():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT player, american_odds, mlb_id, team_id, market_time FROM matched_hit_props", conn)
    conn.close()
    df = df.drop_duplicates(subset=["player"]).sort_values("player")
    return render_template("index.html", props=df.to_dict(orient="records"))

@app.route("/player/<int:mlb_id>")
def player_detail(mlb_id):
    team_id = request.args.get("team_id", type=int)
    game_date = request.args.get("date")

    conn = sqlite3.connect(DB_PATH)

    season = pd.read_sql("SELECT * FROM external_batter_stats WHERE mlb_id = ?", conn, params=(mlb_id,))
    career = pd.read_sql("SELECT * FROM external_batter_stats WHERE mlb_id = ?", conn, params=(mlb_id,))
    recent = pd.read_sql("""
        SELECT game_date, hits FROM batter_game_stats
        WHERE batter = ?
        ORDER BY game_date DESC LIMIT 5
    """, conn, params=(mlb_id,))

    games = pd.read_sql("SELECT * FROM upcoming_games", conn)
    games["game_date"] = games["game_date"].str[:10]

    pitcher_id = None
    pitcher_name = None
    pitcher_team_id = None
    match = games[
        (games["game_date"] == game_date) &
        ((games["home_team_id"] == team_id) | (games["away_team_id"] == team_id))
    ]
    if not match.empty:
        row = match.iloc[0]
        if row["home_team_id"] == team_id:
            pitcher_id = row["away_pitcher_id"]
            pitcher_name = row["away_pitcher_name"]
            pitcher_team_id = row["away_team_id"]
        else:
            pitcher_id = row["home_pitcher_id"]
            pitcher_name = row["home_pitcher_name"]
            pitcher_team_id = row["home_team_id"]

    # FIX: correctly extract batter team_id from season DataFrame
    batter_team_id = team_id

    pitcher = None
    if pitcher_id is not None:
        pitcher_id = int(float(pitcher_id))
        season_pit = pd.read_sql("SELECT * FROM external_pitcher_stats WHERE mlb_id = ?", conn, params=(pitcher_id,))
        career_pit = pd.read_sql("SELECT * FROM pitcher_career_stats WHERE pitcher = ?", conn, params=(pitcher_id,))
        pitcher = {
            "name": pitcher_name,
            "season_baa": season_pit.get("season_baa", [None])[0] if not season_pit.empty else None,
            "season_era": season_pit.get("season_era", [None])[0] if not season_pit.empty else None,
            "season_whip": season_pit.get("season_whip", [None])[0] if not season_pit.empty else None,
            "career_baa": career_pit.get("career_baa", [None])[0] if not career_pit.empty else None,
        }

    conn.close()

    return render_template(
        "player.html",
        mlb_id=mlb_id,
        season=season.iloc[0].to_dict() if not season.empty else {},
        career=career.iloc[0].to_dict() if not career.empty else {},
        recent=recent.sort_values("game_date").to_dict(orient="records"),
        pitcher=pitcher,
        team_id=batter_team_id,
        pitcher_id=pitcher_id,
        pitcher_team_id=pitcher_team_id
    )

if __name__ == "__main__":
    app.run(debug=True)
