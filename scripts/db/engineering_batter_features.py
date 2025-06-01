import sqlite3
import pandas as pd

def engineer_batter_stats(db_path="data/mlb.db"):
    conn = sqlite3.connect(db_path)

    # Load all batter game stats
    df = pd.read_sql_query("SELECT * FROM game_level_stats", conn)
    df["game_date"] = pd.to_datetime(df["game_date"])

    # Split 2025 stats and career stats
    df_2025 = df[df["game_date"].dt.year == 2025]

    def summarize(group):
        return pd.Series({
            "hits": group["game_hits"].sum(),
            "at_bats": group["ab"].sum(),
            "walks": group["bb"].sum(),
            "strikeouts": group["so"].sum(),
            "runs": group["game_runs_scored"].sum(),
            "total_bases": group["game_total_bases"].sum(),
            "games": group.shape[0],
            "avg": round(group["game_hits"].sum() / group["ab"].sum(), 3) if group["ab"].sum() else 0.0
        })

    # DO NOT reset_index() — manually assign group key instead
    career = df.groupby("batter").apply(summarize).copy()
    career["batter"] = career.index
    career = career.reset_index(drop=True)

    season = df_2025.groupby("batter").apply(summarize).copy()
    season["batter"] = season.index
    season = season.reset_index(drop=True)

    # Rename columns
    career.columns = ["career_" + col if col != "batter" else col for col in career.columns]
    season.columns = ["season_" + col if col != "batter" else col for col in season.columns]

    # Merge
    merged = pd.merge(career, season, on="batter", how="outer").fillna(0)

    # Save
    merged.to_sql("batter_summary_stats", conn, if_exists="replace", index=False)
    conn.close()
    print(f"Cached {len(merged)} batter summaries to batter_summary_stats table.")

if __name__ == "__main__":
    engineer_batter_stats()
