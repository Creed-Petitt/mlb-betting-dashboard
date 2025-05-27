import sqlite3
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder
import joblib

# === Load pitcher game-level data ===
conn = sqlite3.connect("data/mlb.db")
df = pd.read_sql_query("SELECT * FROM pitcher_game_stats", conn)
conn.close()

# === Drop missing rows ===
df.dropna(subset=[
    'pitcher_hits_allowed_5g',
    'p_throws',
    'pitcher_team',
    'batter_team',
    'is_home_game',
    'day_of_week',
    'park_factor',
    'game_innings_pitched'
], inplace=True)

# === Encode categoricals ===
for col in ['p_throws', 'pitcher_team', 'batter_team']:
    df[col] = LabelEncoder().fit_transform(df[col])

# === Features + target ===
features = [
    'pitcher_hits_allowed_5g',
    'p_throws',
    'pitcher_team',
    'batter_team',
    'is_home_game',
    'day_of_week',
    'park_factor'
]
X = df[features]
y = df['game_innings_pitched']

# === Time-based split ===
df['game_date'] = pd.to_datetime(df['game_date'])
train_df = df[df['game_date'] < '2023-01-01']
test_df = df[df['game_date'] >= '2023-01-01']
X_train = train_df[features]
y_train = train_df['game_innings_pitched']
X_test = test_df[features]
y_test = test_df['game_innings_pitched']

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

print("\nInnings Pitched (Regression):")
print(f"  MSE: {mse:.3f}")
print(f"  R² : {r2:.3f}")

# === Save model ===
joblib.dump(model, "model/model_rf_innings_pitched.joblib")
print("Saved: model_rf_innings_pitched.joblib")

