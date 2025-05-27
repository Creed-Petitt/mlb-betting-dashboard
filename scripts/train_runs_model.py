import sqlite3
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder
import joblib

# === Load game-level data ===
conn = sqlite3.connect("data/mlb.db")
df = pd.read_sql_query("SELECT * FROM game_level_stats", conn)
conn.close()

# === Create binary target: did player score at least 1 run?
df['over_0_5_runs'] = (df['game_runs_scored'] >= 1).astype(int)

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
    'over_0_5_runs'
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
y = df['over_0_5_runs']

# === Train/test split ===
df['game_date'] = pd.to_datetime(df['game_date'])
train_df = df[df['game_date'] < '2023-01-01']
test_df = df[df['game_date'] >= '2023-01-01']
X_train = train_df[features]
y_train = train_df['over_0_5_runs']
X_test = test_df[features]
y_test = test_df['over_0_5_runs']

# === Train model ===
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    random_state=42,
    n_jobs=-1,
    class_weight='balanced'
)
model.fit(X_train, y_train)

# === Evaluate ===
y_pred = model.predict(X_test)
print("\nRun Scored Classification Report (Over 0.5 runs):\n")
print(classification_report(y_test, y_pred, digits=3))

# === Save model ===
joblib.dump(model, "model/model_rf_game_runs_scored.joblib")
print("\nModel saved: model_rf_game_runs_scored.joblib")
