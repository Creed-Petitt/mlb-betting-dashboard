from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    abbr = db.Column(db.String(8), nullable=False)
    espn_id = db.Column(db.Integer, nullable=True)
    logo_url = db.Column(db.String(256), nullable=True)
    league = db.Column(db.String(8), nullable=True)
    division = db.Column(db.String(16), nullable=True)

class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.Integer, primary_key=True)  # MLB ID
    name = db.Column(db.String(64), nullable=False)
    espn_id = db.Column(db.Integer, nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    position = db.Column(db.String(16), nullable=True)
    bats = db.Column(db.String(1), nullable=True)
    throws = db.Column(db.String(1), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    mlb_debut = db.Column(db.Date, nullable=True)
    is_pitcher = db.Column(db.Boolean, default=False)

class Game(db.Model):
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True)  # MLB gamePk
    date = db.Column(db.Date, nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    home_pitcher_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    away_pitcher_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    venue = db.Column(db.String(128), nullable=True)

class Roster(db.Model):
    __tablename__ = 'rosters'
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)

class Stat(db.Model):
    __tablename__ = 'stats'
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    season = db.Column(db.String(8), nullable=False)  # "2024", "2023", etc
    stat_type = db.Column(db.String(16), nullable=False)  # "hitting", "pitching"
    stat_name = db.Column(db.String(32), nullable=False)
    stat_value = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=True)  # For game-by-game stats, can be null for season/career

class Prop(db.Model):
    __tablename__ = 'props'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    event_id = db.Column(db.String(32), nullable=False)  # FanDuel event/game identifier
    prop_type = db.Column(db.String(32), nullable=False)
    line = db.Column(db.Float, nullable=True)
    odds = db.Column(db.String(16), nullable=True)

class Matchup(db.Model):
    __tablename__ = 'matchups'
    id = db.Column(db.Integer, primary_key=True)
    batter_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    pitcher_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    # Denormalized pitcher info for fast prop display
    pitcher_name = db.Column(db.String(64), nullable=False)
    pitcher_mlb_id = db.Column(db.Integer, nullable=True)
    pitcher_espn_id = db.Column(db.Integer, nullable=True)
    pitcher_team_id = db.Column(db.Integer, nullable=True)

class PlayerIDMap(db.Model):
    __tablename__ = 'player_id_map'
    id = db.Column(db.Integer, primary_key=True)
    mlb_id = db.Column(db.Integer, nullable=False, unique=True)
    espn_id = db.Column(db.Integer, nullable=True)
    # Might add more (baseball_ref_id, retrosheet_id, etc)

