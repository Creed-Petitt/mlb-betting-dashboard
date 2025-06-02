import sqlite3
import pandas as pd

# Connect and drop any leftover table (shouldn’t exist now)
conn = sqlite3.connect("data/mlb.db")
conn.execute("DROP TABLE IF EXISTS clean_plate_appearances")
conn.commit()

# Constants
years = list(range(2015, 2025))
hit_events = ['single', 'double', 'triple', 'home_run']
PARK_FACTORS = {
    'ARI': 1.02, 'ATL': 0.99, 'BAL': 0.95, 'BOS': 1.03, 'CHC': 1.01,
    'CIN': 1.04, 'CLE': 1.00, 'COL': 1.15, 'CWS': 0.98, 'DET': 0.99,
    'HOU': 1.01, 'KC': 1.02, 'LAA': 1.00, 'LAD': 0.98, 'MIA': 0.95,
    'MIL': 1.00, 'MIN': 1.01, 'NYM': 0.97, 'NYY': 1.02, 'OAK': 0.94,
    'PHI': 1.01, 'PIT': 0.98, 'SD': 0.95, 'SEA': 0.97, 'SF': 0.96,
    'STL': 1.00, 'TB': 0.94, 'TEX': 1.04, 'TOR': 1.03, 'WSH': 0.99,
}
TB_MAP = {'single': 1, 'double': 2, 'triple': 3, 'home_run': 4}

def did_batter_score(event, description):
    if event == 'home_run':
        return 1
    if isinstance(description, str) and 'score' in description.lower():
        return 1
    return 0

def is_batter_strikeout(event):
    return 1 if event in ['strikeout', 'strikeout_double_play'] else 0

# Loop over each year’s PAs
for year in years:
    print(f"Processing year {year}...")
    query = f"""
        SELECT game_date, player_name, batter, pitcher, events,
               description, stand, p_throws, home_team, away_team, inning_topbot
        FROM plate_appearances
        WHERE game_date BETWEEN '{year}-01-01' AND '{year}-12-31'
    """
    df = pd.read_sql_query(query, conn)
    if df.empty:
        print(f"  No data for {year}.")
        continue

    df.rename(columns={"player_name": "pitcher_name"}, inplace=True)
    df['game_date'] = pd.to_datetime(df['game_date'].str.strip(), errors='coerce')
    df.dropna(subset=['game_date','batter','pitcher','stand','p_throws'], inplace=True)
    df['is_hit'] = df['events'].isin(hit_events).astype(int)

    # Batter-level fields
    df['total_bases'] = df['events'].map(TB_MAP).fillna(0).astype(int)
    df['is_run_scored'] = df.apply(lambda r: did_batter_score(r['events'], r.get('description','')), axis=1)
    df['is_batter_strikeout'] = df['events'].apply(is_batter_strikeout)

    # Pitcher run allowed
    df['is_pitcher_run_allowed'] = df.apply(lambda r: did_batter_score(r['events'], r.get('description','')), axis=1)

    # Assign teams from inning_topbot
    df['batter_team'] = df.apply(
        lambda r: r['home_team'] if r['inning_topbot']=='Bot' else r['away_team'], axis=1)
    df['pitcher_team'] = df.apply(
        lambda r: r['away_team'] if r['inning_topbot']=='Bot' else r['home_team'], axis=1)

    # Game context features
    df['is_home_game'] = (df['home_team'] == df['batter_team']).astype(int)
    df['day_of_week'] = df['game_date'].dt.dayofweek
    df['park_factor'] = df['home_team'].map(PARK_FACTORS).fillna(1.00)
    df['is_same_side'] = (df['stand'] == df['p_throws']).astype(int)

    # Rolling 5-game averages
    df = df.sort_values(['batter','game_date'])
    df['batter_hits_5g'] = (
        df.groupby('batter')['is_hit'].
        rolling(window=5, min_periods=1).mean().
        reset_index(level=0, drop=True)
    )

    df = df.sort_values(['pitcher','game_date'])
    df['pitcher_hits_allowed_5g'] = (
        df.groupby('pitcher')['is_hit'].
        rolling(window=5, min_periods=1).mean().
        reset_index(level=0, drop=True)
    )

    # Counting stats per PA (for batters)
    df['so'] = df['events'].isin(['strikeout','strikeout_double_play']).astype(int)
    df['bb'] = (df['events']=='walk').astype(int)
    df['ab'] = (~df['events'].isin(['walk','hit_by_pitch','sac_fly','sac_bunt','catcher_interference'])).astype(int)

    df.to_sql("clean_plate_appearances", conn, if_exists="append", index=False)
    print(f"  Saved {len(df)} rows for {year}.")

print("Completed clean_plate_appearances.")
conn.close()


