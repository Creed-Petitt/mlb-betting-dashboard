from app import create_app, db
from app.models import Player

def list_pitchers_missing_espn_id():
    app = create_app()
    with app.app_context():
        pitchers = Player.query.filter(
            (Player.espn_id == None) | (Player.espn_id == ''),
            Player.is_pitcher == True
        ).all()
        if not pitchers:
            print("No pitchers missing ESPN ID.")
            return
        print(f"Pitchers missing ESPN IDs ({len(pitchers)}):")
        for p in pitchers:
            print(f"{p.id} - {p.name}")

if __name__ == "__main__":
    list_pitchers_missing_espn_id()
