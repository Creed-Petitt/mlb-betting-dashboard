from flask import Flask, request, jsonify, render_template
import joblib

app = Flask(__name__)

# Load model
models = {
    "hits": joblib.load("model/model_rf_game_hits_reg.joblib"),
    "tb": joblib.load("model/model_rf_game_total_bases.joblib"),
    "runs": joblib.load("model/model_rf_game_runs_scored.joblib"),
    "so": joblib.load("model/model_rf_pitcher_strikeouts.joblib"),
    "ip": joblib.load("model/model_rf_innings_pitched.joblib")
}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/predict_prop", methods=["POST"])
def predict_prop():
    prop_type = request.form["prop_type"]
    line = float(request.form["line"])
    
    # This part is mocked up since we don’t yet have real player input parsing
    # For now we’ll use dummy hardcoded input features per model
    dummy_input = {
        "hits": [0.6, 0.3, 1, 1, 0, 3, 12, 1, 3, 1.02],
        "tb":   [0.6, 0.3, 1, 1, 0, 3, 12, 1, 3, 1.02],
        "runs": [0.6, 0.3, 1, 1, 0, 3, 12, 1, 3, 1.02],
        "so":   [0.3, 1, 0, 15, 3, 12, 3, 1.00],
        "ip":   [0.3, 1, 0, 15, 3, 12, 3, 1.00]
    }

    model = models.get(prop_type)
    features = dummy_input[prop_type]
    prediction = model.predict([features])[0]
    over_under = "OVER" if prediction > line else "UNDER"

    return render_template("index.html", prediction=round(prediction, 2), over_under=over_under)


if __name__ == "__main__":
    app.run(debug=True)
