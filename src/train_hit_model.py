import sqlite3
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import joblib

# Load game-level features
conn = sqlite3.connect("data/mlb.db")
df = pd.read_sql("SELECT * FROM game_level_features", conn, parse_dates=["game_date"])
conn.close()

# Drop rows with missing target
df = df.dropna(subset=["hit_in_game"])

# Define features and target
target = "hit_in_game"
features = [
    "batter_plate_appearances", "batter_hits", "avg_launch_speed", "avg_launch_angle",
    "stand", "is_home_game", "batting_avg", "batter_hits_5g",
    "pitcher_plate_appearances", "pitcher_hits_allowed", "p_throws", "baa", "pitcher_hits_allowed_5g",
    "career_avg", "career_baa",
    "batter_team", "pitcher_team"  # added as categorical features
]

X = df[features].copy()
y = df[target]

# Automatically split numeric and categorical
numeric_features = X.select_dtypes(include=["number", "bool"]).columns.tolist()
categorical_features = X.select_dtypes(include=["object", "category"]).columns.tolist()

# Define preprocessing
numeric_transformer = SimpleImputer(strategy="mean")
categorical_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("onehot", OneHotEncoder(handle_unknown="ignore"))
])

preprocessor = ColumnTransformer([
    ("num", numeric_transformer, numeric_features),
    ("cat", categorical_transformer, categorical_features)
])

# Full model pipeline
pipeline = Pipeline([
    ("preprocessor", preprocessor),
    ("classifier", RandomForestClassifier(n_estimators=100, random_state=42))
])

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
pipeline.fit(X_train, y_train)

# Evaluate
y_pred = pipeline.predict(X_test)
print("Accuracy:", accuracy_score(y_test, y_pred))
print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred))
print("Classification Report:\n", classification_report(y_test, y_pred))

# Save model
joblib.dump(pipeline, "models/hit_model.joblib")
print("Model saved to models/hit_model.joblib")
