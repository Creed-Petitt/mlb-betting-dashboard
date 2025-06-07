import sqlite3
import requests
import pandas as pd
from tqdm import tqdm

DB_PATH = "data/mlb.db"
BATTER_TABLE = "external_batter_stats"
PITCHER_TABLE = "external_pitcher_stats"
TARGET_SEASON = "2025"

def fetch_batter_stats(mlb_id):
    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{mlb_id}/stats?stats=yearByYear,career&group=hitting&sportId=1"
        r = requests.get(url).json()
        stats = {"mlb_id": mlb_id}

        # === Find 2025 season split ===
        year_by_year = next((blk for blk in r["stats"] if blk["type"]["displayName"] == "yearByYear"), None)
        if year_by_year:
            season_split = next((s["stat"] for s in year_by_year["splits"] if s.get("season") == TARGET_SEASON), None)
            if season_split:
                stats.update({
                    "season_avg": season_split.get("avg"),
                    "season_obp": season_split.get("obp"),
                    "season_slg": season_split.get("slg"),
                    "season_ops": season_split.get("ops"),
                    "season_games": season_split.get("gamesPlayed"),
                    "season_hits": season_split.get("hits"),
                    "season_atBats": season_split.get("atBats"),
                    "season_homeRuns": season_split.get("homeRuns"),
                    "season_walks": season_split.get("baseOnBalls"),
                    "season_strikeOuts": season_split.get("strikeOuts")
                })

        # === Find career stats split ===
        career_block = next((blk for blk in r["stats"] if blk["type"]["displayName"] == "career"), None)
        if career_block and career_block["splits"]:
            c = career_block["splits"][0]["stat"]
            stats.update({
                "career_avg": c.get("avg"),
                "career_obp": c.get("obp"),
                "career_slg": c.get("slg"),
                "career_ops": c.get("ops"),
                "career_games": c.get("gamesPlayed"),
                "career_hits": c.get("hits"),
                "career_atBats": c.get("atBats"),
                "career_homeRuns": c.get("homeRuns"),
                "career_walks": c.get("baseOnBalls"),
                "career_strikeOuts": c.get("strikeOuts")
            })
        return stats
    except Exception as e:
        print(f"Failed batter {mlb_id}: {e}")
        return None

def fetch_pitcher_stats(mlb_id):
    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{mlb_id}/stats?stats=yearByYear,career&group=pitching&sportId=1"
        r = requests.get(url).json()
        stats = {"mlb_id": mlb_id}

        year_by_year = next((blk for blk in r["stats"] if blk["type"]["displayName"] == "yearByYear"), None)
        if year_by_year:
            season_split = next((s["stat"] for s in year_by_year["splits"] if s.get("season") == TARGET_SEASON), None)
            if season_split:
                stats.update({
                    "season_hits": season_split.get("hits"),
                    "season_atBats": season_split.get("atBats"),
                    "season_era": season_split.get("era"),
                    "season_whip": season_split.get("whip"),
                    "season_inningsPitched": season_split.get("inningsPitched"),
                    "season_strikeOuts": season_split.get("strikeOuts"),
                    "season_walks": season_split.get("baseOnBalls"),
                    "season_homeRuns": season_split.get("homeRuns")
                })
                if season_split.get("hits") and season_split.get("atBats"):
                    stats["season_baa"] = round(float(season_split["hits"]) / float(season_split["atBats"]), 3)

        career_block = next((blk for blk in r["stats"] if blk["type"]["displayName"] == "career"), None)
        if career_block and career_block["splits"]:
            c = career_block["splits"][0]["stat"]
            stats.update({
                "career_hits": c.get("hits"),
                "career_atBats": c.get("atBats"),
                "career_era": c.get("era"),
                "career_whip": c.get("whip"),
                "career_inningsPitched": c.get("inningsPitched"),
                "career_strikeOuts": c.get("strikeOuts"),
                "career_walks": c.get("baseOnBalls"),
                "career_homeRuns": c.get("homeRuns")
            })
            if c.get("hits") and c.get("atBats"):
                stats["career_baa"] = round(float(c["hits"]) / float(c["atBats"]), 3)
        return stats
    except Exception as e:
        print(f"Failed pitcher {mlb_id}: {e}")
        return None

# === Load player IDs from DB ===
conn = sqlite3.connect(DB_PATH)
batters = pd.read_sql("SELECT DISTINCT mlb_id FROM matched_hit_props", conn)
batters["mlb_id"] = pd.to_numeric(batters["mlb_id"], errors="coerce").dropna().astype(int)

pitcher_rows = pd.read_sql("SELECT DISTINCT home_pitcher_id, away_pitcher_id FROM upcoming_games", conn)
pitcher_ids = set()
for col in ["home_pitcher_id", "away_pitcher_id"]:
    ids = pd.to_numeric(pitcher_rows[col], errors="coerce").dropna().astype(int).tolist()
    pitcher_ids.update(ids)
conn.close()

# === Fetch batter stats ===
batter_stats = []
for pid in tqdm(batters["mlb_id"].tolist(), desc="Fetching batter stats"):
    data = fetch_batter_stats(pid)
    if data:
        batter_stats.append(data)

# === Fetch pitcher stats ===
pitcher_stats = []
for pid in tqdm(pitcher_ids, desc="Fetching pitcher stats"):
    data = fetch_pitcher_stats(pid)
    if data:
        pitcher_stats.append(data)

# === Save to DB ===
conn = sqlite3.connect(DB_PATH)
if batter_stats:
    pd.DataFrame(batter_stats).to_sql(BATTER_TABLE, conn, if_exists="replace", index=False)
if pitcher_stats:
    pd.DataFrame(pitcher_stats).to_sql(PITCHER_TABLE, conn, if_exists="replace", index=False)
conn.close()

print(f"Saved {len(batter_stats)} batters and {len(pitcher_stats)} pitchers to DB.")
