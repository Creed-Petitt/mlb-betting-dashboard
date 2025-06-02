import sqlite3
import pandas as pd

conn = sqlite3.connect("data/mlb.db")
df = pd.read_sql_query("SELECT * FROM game_level_stats", conn)
df["game_date"] = pd.to_datetime(df["game_date"])

# Subset for 2025 season (adjust year if needed)
df_2025 = df[df["game_date"].dt.year == 2025]

def summarize(group):
    hits = group["game_hits"].sum()
    at_bats = group["ab"].sum()
    walks = group["bb"].sum()
    total_bases = group["game_total_bases"].sum()

    obp = (hits + walks) / (at_bats + walks) if (at_bats + walks) else 0
    slg = total_bases / at_bats if at_bats else 0
    ops = obp + slg

    return pd.Series({
        "hits": hits,
        "at_bats": at_bats,
        "walks": walks,
        "strikeouts": group["so"].sum(),
        "runs": group["game_runs_scored"].sum(),
        "total_bases": total_bases,
        "games": group.shape[0],
        "avg": round(hits / at_bats, 3) if at_bats else 0.0,
        "obp": round(obp, 3),
        "slg": round(slg, 3),
        "ops": round(ops, 3)
    })

# Career aggregation
career = df.groupby("batter").apply(summarize).copy()
career["batter"] = career.index
career = career.reset_index(drop=True)
career.columns = ["career_" + col if col != "batter" else col for col in career.columns]

# Season aggregation (2025)
season = df_2025.groupby("batter").apply(summarize).copy()
season["batter"] = season.index
season = season.reset_index(drop=True)
season.columns = ["season_" + col if col != "batter" else col for col in season.columns]

merged = pd.merge(career, season, on="batter", how="outer").fillna(0)
merged.to_sql("batter_summary_stats", conn, if_exists="replace", index=False)
print(f"Cached {len(merged)} batters to batter_summary_stats table.")

conn.close()

