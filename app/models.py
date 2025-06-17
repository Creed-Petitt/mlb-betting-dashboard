from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)      # MLB team_id
    name = db.Column(db.String(64), nullable=False)
    abbr = db.Column(db.String(8), nullable=False)
    espn_id = db.Column(db.Integer, nullable=True)
    logo_url = db.Column(db.String(256), nullable=True)
    league = db.Column(db.String(8), nullable=True)   # AL/NL
    division = db.Column(db.String(16), nullable=True) # e.g. 'East', 'Central', 'West'

    players = db.relationship('Player', backref='team', lazy=True)
    games_home = db.relationship('Game', backref='home_team', foreign_keys='Game.home_team_id', lazy=True)
    games_away = db.relationship('Game', backref='away_team', foreign_keys='Game.away_team_id', lazy=True)

class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.Integer, primary_key=True)      # MLB player_id
    name = db.Column(db.String(64), nullable=False)
    espn_id = db.Column(db.Integer, nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    position = db.Column(db.String(16), nullable=True) # 'C', '1B', 'P', etc.
    bats = db.Column(db.String(1), nullable=True)      # 'L', 'R', 'S'
    throws = db.Column(db.String(1), nullable=True)    # 'L', 'R'
    date_of_birth = db.Column(db.Date, nullable=True)
    mlb_debut = db.Column(db.Date, nullable=True)
    is_pitcher = db.Column(db.Boolean, default=False)  # Helps filter pitcher vs batter

class Game(db.Model):
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    home_pitcher_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    away_pitcher_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    venue = db.Column(db.String(128), nullable=True)
    # Optionally: weather, attendance, etc.

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
    season = db.Column(db.String(8), nullable=False)      # '2025', 'career', 'rolling'
    stat_type = db.Column(db.String(16), nullable=False)  # 'season', 'career', 'rolling'
    stat_name = db.Column(db.String(32), nullable=False)  # 'AVG', 'HR', 'wOBA', 'K%', etc.
    stat_value = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=True)              # For rolling/game logs

class Prop(db.Model):
    __tablename__ = 'props'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    event_id = db.Column(db.String(32), nullable=False)
    prop_type = db.Column(db.String(32), nullable=False)  # 'hit', 'HR', etc.
    line = db.Column(db.Float, nullable=True)
    odds = db.Column(db.String(16), nullable=True)        # '+120', '-110', etc.

class Matchup(db.Model):
    __tablename__ = 'matchups'
    id = db.Column(db.Integer, primary_key=True)
    batter_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    pitcher_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    # You can add batter/pitcher handiness, historical stats, etc. here
