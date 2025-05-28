import sqlite3
import os

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

def create_upcoming_games_table():
    conn = sqlite3.connect("data/mlb.db")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS upcoming_games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_date TEXT,
        home_team TEXT,
        away_team TEXT,
        home_pitcher TEXT,
        home_pitcher_id INTEGER,
        away_pitcher TEXT,
        away_pitcher_id INTEGER
    )
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_upcoming_games_table()
    print("upcoming_games table created.")
