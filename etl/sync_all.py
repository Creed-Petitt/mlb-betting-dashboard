import sys
import os
import subprocess

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from app.models import db, Player, PlayerIDMap

def sync_players_from_mapping():
    with create_app().app_context():
        count = 0
        total_players = Player.query.count()
        total_mapped = 0
        for player in Player.query.all():
            mapping = PlayerIDMap.query.filter_by(mlb_id=player.id).first()
            if mapping and mapping.espn_id and player.espn_id != mapping.espn_id:
                print(f"[DEBUG] Syncing Player {player.name} (MLBID {player.id}): ESPNID {player.espn_id} -> {mapping.espn_id}")
                player.espn_id = mapping.espn_id
                count += 1
            if mapping and mapping.espn_id:
                total_mapped += 1
        db.session.commit()
        print(f"[DEBUG] Synced {count} players from mapping.")
        print(f"[DEBUG] Players with ESPN ID: {total_mapped}/{total_players}")

def download_headshots():
    import requests
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app'))
    HEADSHOTS_DIR = os.path.join(PROJECT_ROOT, 'static', 'headshots')
    os.makedirs(HEADSHOTS_DIR, exist_ok=True)
    with create_app().app_context():
        espn_ids = set()
        espn_ids.update([row.espn_id for row in Player.query.filter(Player.espn_id.isnot(None)).all()])
        espn_ids.update([row.espn_id for row in PlayerIDMap.query.filter(PlayerIDMap.espn_id.isnot(None)).all()])
        for espn_id in espn_ids:
            if not espn_id:
                continue
            out_path = os.path.join(HEADSHOTS_DIR, f"{espn_id}.png")
            if not os.path.exists(out_path):
                url = f"https://a.espncdn.com/i/headshots/mlb/players/full/{espn_id}.png"
                try:
                    resp = requests.get(url, timeout=10)
                    if resp.ok and resp.headers.get('Content-Type', '').startswith('image'):
                        with open(out_path, 'wb') as f:
                            f.write(resp.content)
                        print(f"Downloaded: {espn_id}")
                except Exception:
                    print(f"[WARN] Failed to download headshot for {espn_id}")

def main():
    # Step 0: Create backup before sync
    print("[SYNC] Creating database backup...")
    subprocess.run([sys.executable, 'etl/backup_db.py'])
    
    # Step 1: import mapping
    subprocess.run([sys.executable, 'etl/import_player_id_map.py'])
    # Step 2: fetch games (creates teams)
    subprocess.run([sys.executable, 'etl/fetch_games.py'])
    # Step 3: fetch rosters (now teams exist)
    subprocess.run([sys.executable, 'etl/fetch_rosters.py'])
    # Step 4: sync mapping
    sync_players_from_mapping()
    # Step 5: download headshots
    download_headshots()
    # Step 6: fetch props
    subprocess.run([sys.executable, 'etl/fetch_props.py'])
    # Step 7: fetch stats
    subprocess.run([sys.executable, 'etl/fetch_stats.py'])
    # Step 8: fetch current standings
    subprocess.run([sys.executable, 'etl/fetch_standings.py'])

if __name__ == "__main__":
    main()
