import sqlite3

def create_hit_props_table():
    conn = sqlite3.connect("data/mlb.db")  # or wherever your main .db file is
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS hit_props (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            market_id TEXT,
            market_time TEXT,
            player TEXT,
            decimal_odds REAL,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_hit_props_table()
    print("upcoming_games table created.")