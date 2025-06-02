import sqlite3
import pandas as pd

conn = sqlite3.connect("data/mlb.db")
df = pd.read_sql_query("SELECT * FROM clean_plate_appearances", conn)
df["game_date"] = pd.to_datetime(df["game_date"])

df['is_pitcher_strikeout'] = df['events'].isin(['strikeout','strikeout_double_play']).astype(int)
df['out_made'] = df['events'].isin([
    'strikeout','field_out','force_out',
    'grounded_into_double_play','double_play','triple_play'
]).astype(int)

agg = df.groupby(['game_date','pitcher']).agg({
    'is_pitcher_strikeout': 'sum',
    'out_made': 'sum',
    'is_pitcher_run_allowed': 'sum',
    'pitcher_hits_allowed_5g': 'last',
    'p_throws': 'last',
    'pitcher_team': 'last',
    'batter_team': 'last',
    'is_home_game': 'last',
    'day_of_week': 'last',
    'park_factor': 'last'
}).reset_index()

agg.rename(columns={
    'is_pitcher_strikeout': 'game_pitcher_strikeouts',
    'is_pitcher_run_allowed': 'runs_allowed'
}, inplace=True)

agg['game_innings_pitched'] = agg['out_made'] / 3.0

agg.to_sql("pitcher_game_stats", conn, if_exists="replace", index=False)
print(f"Saved pitcher_game_stats with {len(agg)} rows.")
conn.close()


