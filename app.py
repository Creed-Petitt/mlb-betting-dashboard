from flask import Flask, request, jsonify
import joblib

app = Flask(__name__)

# === Load Models ===
models = {
    "hits": joblib.load("model/model_rf_game_hits_reg.joblib"),
    "tb": joblib.load("model/model_rf_game_total_bases.joblib"),
    "runs": joblib.load("model/model_rf_game_runs_scored.joblib"),
    "pitcher_so": joblib.load("model/model_rf_pitcher_strikeouts.joblib"),
    "ip": joblib.load("model/model_rf_innings_pitched.joblib")
}

# === Define Features for Each Model ===
features = {
    "hits": [
        'batter_hits_5g', 'pitcher_hits_allowed_5g', 'is_same_side',
        'stand', 'p_throws', 'batter_team', 'pitcher_team',
        'is_home_game', 'day_of_week', 'park_factor'
    ],
    "tb": [
        'batter_hits_5g', 'pitcher_hits_allowed_5g', 'is_same_side',
        'stand', 'p_throws', 'batter_team', 'pitcher_team',
        'is_home_game', 'day_of_week', 'park_factor'
    ],
    "runs": [
        'batter_hits_5g', 'pitcher_hits_allowed_5g', 'is_same_side',
        'stand', 'p_throws', 'batter_team', 'pitcher_team',
        'is_home_game', 'day_of_week', 'park_factor'
    ],
    "pitcher_so": [
        'pitcher_hits_allowed_5g', 'p_throws', 'pitcher_team',
        'batter_team', 'is_home_game', 'day_of_week', 'park_factor'
    ],
    "ip": [
        'pitcher_hits_allowed_5g', 'p_throws', 'pitcher_team',
        'batter_team', 'is_home_game', 'day_of_week', 'park_factor'
    ]
}

# === Generalized Prediction Endpoint ===
def make_prediction(model_key):
    model = models[model_key]
    input_features = features[model_key]
    data = request.get_json()

    try:
        input_vector = [data[feat] for feat in input_features]
        prediction = model.predict([input_vector])[0]

        line = data.get("line")
        result = None
        if line is not None:
            result = "OVER" if prediction >= float(line) else "UNDER"

        return jsonify({
            "prediction": round(prediction, 3),
            "line": line,
            "over_under": result
        })

    except KeyError as e:
        return jsonify({"error": f"Missing input feature: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Define Routes ===
@app.route("/predict", methods=["POST"])
def predict_hits():
    return make_prediction("hits")

@app.route("/predict_tb", methods=["POST"])
def predict_tb():
    return make_prediction("tb")

@app.route("/predict_runs", methods=["POST"])
def predict_runs():
    return make_prediction("runs")

@app.route("/predict_pitcher_so", methods=["POST"])
def predict_pitcher_so():
    return make_prediction("pitcher_so")

@app.route("/predict_ip", methods=["POST"])
def predict_ip():
    return make_prediction("ip")

if __name__ == "__main__":
    app.run(debug=True)