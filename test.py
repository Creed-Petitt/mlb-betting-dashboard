from app import create_app
from app.models import db, Prop, Player

app = create_app()
with app.app_context():
    for prop in Prop.query.all():
        player = Player.query.get(prop.player_id)
        if not player:
            print(f"Prop {prop.id}: player missing from DB (player_id={prop.player_id})")
            continue
        print(f"Prop {prop.id}: {player.name} (MLB ID: {player.id}) | ESPN ID: {player.espn_id}")

