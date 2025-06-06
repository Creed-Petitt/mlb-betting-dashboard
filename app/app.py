from flask import Flask, render_template
import sqlite3
import pandas as pd

app = Flask(__name__)

@app.route("/")
def home():
    conn = sqlite3.connect("data/mlb.db")
    df = pd.read_sql("SELECT player, american_odds FROM hit_props", conn)
    conn.close()

    # Drop duplicates and sort alphabetically
    df = df.drop_duplicates(subset=["player"]).sort_values("player")

    return render_template("index.html", props=df.to_dict(orient="records"))

if __name__ == "__main__":
    app.run(debug=True)
