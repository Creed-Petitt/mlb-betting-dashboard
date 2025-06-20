import sys
import os
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from app.models import db, Player

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app'))
HEADSHOTS_DIR = os.path.join(PROJECT_ROOT, 'static', 'headshots')
os.makedirs(HEADSHOTS_DIR, exist_ok=True)

def download_headshot(espn_id):
    url = f"https://a.espncdn.com/i/headshots/mlb/players/full/{espn_id}.png"
    out_path = os.path.join(HEADSHOTS_DIR, f"{espn_id}.png")
    try:
        resp = requests.get(url, timeout=10)
        if resp.ok and resp.headers.get('Content-Type', '').startswith('image'):
            with open(out_path, 'wb') as f:
                f.write(resp.content)
    except Exception:
        pass

def main():
    app = create_app()
    with app.app_context():
        espn_ids = [row.espn_id for row in Player.query.filter(Player.espn_id.isnot(None)).all()]
        for espn_id in espn_ids:
            if not espn_id:
                continue
            out_path = os.path.join(HEADSHOTS_DIR, f"{espn_id}.png")
            if not os.path.exists(out_path):
                download_headshot(espn_id)

if __name__ == "__main__":
    main()
