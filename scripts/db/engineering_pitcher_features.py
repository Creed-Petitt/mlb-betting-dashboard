import sqlite3
import pandas as pd

def cache_pitcher_summary_stats():
    conn = sqlite3.connect("data/mlb.db")

    df = pd.read_sql_query("SELECT * FROM pitcher_game_stats", conn)
    df["game_date"] = pd.to_datetime(df["game_date"])
    df["season"] = df["game_date"].dt.year

    # Valid columns from upstream
    df["strikeouts"] = df["game_pitcher_strikeouts"]
    df["innings_pitched"] = df["game_innings_pitched"]
    df["runs_allowed"] = df["runs_allowed"]
    df["hits_allowed"] = df["pitcher_hits_allowed_5g"] * df["game_innings_pitched"]

    # 2025 season stats
    stats_2025 = df[df["season"] == 2025].groupby("pitcher").agg(
        g_2025=("game_date", "count"),
        h_2025=("hits_allowed", "sum"),
        so_2025=("strikeouts", "sum"),
        ip_2025=("innings_pitched", "sum"),
        r_2025=("runs_allowed", "sum")
    )

    # Career stats
    stats_career = df.groupby("pitcher").agg(
        g_career=("game_date", "count"),
        h_career=("hits_allowed", "sum"),
        so_career=("strikeouts", "sum"),
        ip_career=("innings_pitched", "sum"),
        r_career=("runs_allowed", "sum")
    )

    summary = stats_career.join(stats_2025, how="left").fillna(0).reset_index()
    summary["h9_2025"] = (summary["h_2025"] / summary["ip_2025"]).replace([float("inf"), -float("inf")], 0).fillna(0)
    summary["h9_career"] = (summary["h_career"] / summary["ip_career"]).replace([float("inf"), -float("inf")], 0).fillna(0)

    summary.to_sql("pitcher_summary_stats", conn, if_exists="replace", index=False)
    conn.close()
    print(f"Cached {len(summary)} pitchers to pitcher_summary_stats table.")

if __name__ == "__main__":
    cache_pitcher_summary_stats()

