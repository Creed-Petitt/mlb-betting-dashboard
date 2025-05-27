import sqlite3
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder
import joblib

# === Load game-level data ===
conn = sqlite3.connect("data/mlb.db")
df = pd.read_sql_query("SELECT * FROM game_level_stats", conn)
conn.close()

# === Drop missing rows ===
df.dropna(subset=[
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
    'game_total_bases'
], inplace=True)

# === Encode categoricals ===
for col in ['stand', 'p_throws', 'batter_team', 'pitcher_team']:
    df[col] = LabelEncoder().fit_transform(df[col])

# === Features + target ===
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
    'park_factor'
]
X = df[features]
y = df['game_total_bases']

# === Train/test split (2023+ test) ===
df['game_date'] = pd.to_datetime(df['game_date'])
train_df = df[df['game_date'] < '2023-01-01']
test_df = df[df['game_date'] >= '2023-01-01']
X_train = train_df[features]
y_train = train_df['game_total_bases']
X_test = test_df[features]
y_test = test_df['game_total_bases']

# === Train model ===
model = RandomForestRegressor(
    n_estimators=200,
    max_depth=15,
    random_state=42,
    n_jobs=-1
)
model.fit(X_train, y_train)

# === Evaluate ===
y_pred = model.predict(X_test)
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print("\nGame-Level Total Bases (Regression):")
print(f"  MSE: {mse:.3f}")
print(f"  R² : {r2:.3f}")

# === Save model ===
joblib.dump(model, "model/model_rf_game_total_bases.joblib")
print("Saved: model_rf_game_total_bases.joblib")

