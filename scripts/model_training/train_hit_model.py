import sqlite3
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV
import joblib

# Load game-level stats
conn = sqlite3.connect("data/mlb.db")
df_games = pd.read_sql_query("SELECT * FROM game_level_stats", conn)
df_batters = pd.read_sql_query("SELECT * FROM batter_summary_stats", conn)
df_pitchers = pd.read_sql_query("SELECT * FROM pitcher_summary_stats", conn)
conn.close()

# Merge batter stats
df = df_games.merge(df_batters, on="batter", how="left")

# Merge pitcher stats
df = df.merge(df_pitchers, on="pitcher", how="left")

# Fill missing season stats with 0 (start-of-season scenario)
for col in ['season_avg', 'season_ops']:
    if col not in df.columns:
        df[col] = 0
    else:
        df[col] = df[col].fillna(0)

# Fill missing pitcher stats with 0 (if no matching pitcher career data)
for col in ['h9_2025', 'h9_career']:
    if col not in df.columns:
        df[col] = 0
    else:
        df[col] = df[col].fillna(0)

# Create career hits per game
df["career_hits_per_game"] = df["career_hits"] / df["career_games"]
df["career_hits_per_game"] = df["career_hits_per_game"].fillna(0)

# Drop rows missing required columns or target
required = [
    'batter_hits_5g',
    'pitcher_hits_allowed_5g',
    'is_same_side',
    'stand',
    'p_throws',
    'batter_team',
    'pitcher_team',
    'is_home_game',
    'day_of_week',
    'park_factor',
    'career_avg',
    'career_ops',
    'career_hits_per_game',
    'season_avg',
    'season_ops',
    'h9_2025',
    'h9_career',
    'game_hits'
]
df.dropna(subset=required, inplace=True)

# Encode categorical variables
for col in ['stand', 'p_throws', 'batter_team', 'pitcher_team']:
    df[col] = LabelEncoder().fit_transform(df[col])

# Feature columns
features = [
    'batter_hits_5g',
    'pitcher_hits_allowed_5g',
    'is_same_side',
    'stand',
    'p_throws',
    'batter_team',
    'pitcher_team',
    'is_home_game',
    'day_of_week',
    'park_factor',
    'career_avg',
    'career_ops',
    'career_hits_per_game',
    'season_avg',
    'season_ops',
    'h9_2025',
    'h9_career'
]
X = df[features]
y = df['game_hits']

# Train/test split
df['game_date'] = pd.to_datetime(df['game_date'])
X_train = df[df['game_date'] < '2023-01-01'][features]
y_train = df[df['game_date'] < '2023-01-01']['game_hits']
X_test = df[df['game_date'] >= '2023-01-01'][features]
y_test = df[df['game_date'] >= '2023-01-01']['game_hits']

# Grid Search for best hyperparameters
param_grid = {
    'n_estimators': [100, 200],
    'max_depth': [10, 15, 20],
    'min_samples_leaf': [1, 3, 5]
}
grid = GridSearchCV(
    RandomForestRegressor(random_state=42, n_jobs=-1),
    param_grid,
    cv=3,
    scoring='neg_mean_squared_error',
    verbose=1
)
grid.fit(X_train, y_train)
model = grid.best_estimator_

# Evaluate
y_pred = model.predict(X_test)
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print("\nFinal Game-Level Hits Model:")
print(f"  Best Params: {grid.best_params_}")
print(f"  MSE: {mse:.3f}")
print(f"  R² : {r2:.3f}")

# Save final model
joblib.dump(model, "model/final_hit_model.joblib")
print("Final model saved to model/final_hit_model.joblib")
