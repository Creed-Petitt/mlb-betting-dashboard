# ⚾️ MLB PropBet AI

An AI-powered web application that predicts whether a Major League Baseball (MLB) player will hit the **over or under** on key prop bets like hits, home runs, and strikeouts — based on matchup context, player history, and game location.

---

## 🚀 Features

- Predict **player stat outcomes** (e.g. Over 1.5 Hits)
- Interactive frontend with user input
- Flask API with trained ML models
- Data from `pybaseball` and Statcast
- Model explainability (e.g. SHAP values)
- Clean, modular code and structure

---

## 📁 Project Structure

mlb-bet-ai/
├── app/ # Flask app code (routes, model serving)
├── data/ # Game logs, datasets, and scraped data
├── models/ # Saved trained models (.joblib/.pkl)
├── notebooks/ # Jupyter exploration and training work
├── requirements.txt # Python dependencies
├── README.md # Project overview and instructions
└── .gitignore # Files/folders to exclude from Git

---

## 📦 Setup Instructions

```bash
# Clone the repo
git clone https://github.com/yourusername/mlb-bet-ai.git
cd mlb-bet-ai

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run Jupyter
jupyter notebook
