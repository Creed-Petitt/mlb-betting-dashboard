import sys
import os
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app
from app.models import db, PlayerIDMap

CSV_PATH = 'data/SFBB Player ID Map - PLAYERIDMAP copy.csv'


def main():
    app = create_app()
    with app.app_context():
        if not os.path.exists(CSV_PATH):
            print(f"[ERROR] Mapping file not found: {CSV_PATH}")
            return
        df = pd.read_csv(CSV_PATH)
        print(f"[DEBUG] Read mapping CSV with {len(df)} rows")
        added = 0
        for i, row in df.iterrows():
            mlb_id = int(row['MLBID']) if not pd.isna(row['MLBID']) else None
            espn_id = int(row['ESPNID']) if not pd.isna(row['ESPNID']) else None
            if not mlb_id:
                continue
            mapping = PlayerIDMap.query.filter_by(mlb_id=mlb_id).first()
            if not mapping:
                db.session.add(PlayerIDMap(mlb_id=mlb_id, espn_id=espn_id))
                added += 1
            else:
                if mapping.espn_id != espn_id:
                    print(f"[DEBUG] Updating mapping for MLBID {mlb_id}: {mapping.espn_id} -> {espn_id}")

                mapping.espn_id = espn_id
        db.session.commit()
        print(f"[DEBUG] Imported {added} new player mappings.")
        print(f"[DEBUG] Total mappings in table: {PlayerIDMap.query.count()}")

if __name__ == "__main__":
    main()
