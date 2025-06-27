from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DisconnectionError, OperationalError
import logging
from typing import Optional

db = SQLAlchemy()

# Database connection event handlers for resilience
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite connection options for better performance and reliability."""
    if 'sqlite' in str(dbapi_connection):
        cursor = dbapi_connection.cursor()
        # Enable WAL mode for better concurrency
        cursor.execute("PRAGMA journal_mode=WAL")
        # Set timeout for busy database
        cursor.execute("PRAGMA busy_timeout=20000")
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

class Team(db.Model):
    """Represents an MLB team."""
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    abbr = db.Column(db.String(8), nullable=False)
    espn_id = db.Column(db.Integer, nullable=True)
    logo_url = db.Column(db.String(256), nullable=True)
    league = db.Column(db.String(8), nullable=True)
    division = db.Column(db.String(16), nullable=True)
    players = db.relationship('Player', backref='team', lazy=True)
    home_games = db.relationship('Game', backref='home_team', foreign_keys='Game.home_team_id', lazy=True)
    away_games = db.relationship('Game', backref='away_team', foreign_keys='Game.away_team_id', lazy=True)

class Player(db.Model):
    """Represents an MLB player."""
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
    stats = db.relationship('Stat', backref='player', lazy=True)
    props = db.relationship('Prop', backref='player', lazy=True)

class Game(db.Model):
    """Represents an MLB game."""
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True)  # MLB gamePk
    date = db.Column(db.Date, nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    home_pitcher_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    away_pitcher_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    venue = db.Column(db.String(128), nullable=True)

class Roster(db.Model):
    """Represents a roster entry for a player on a team at a given date."""
    __tablename__ = 'rosters'
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)

class Stat(db.Model):
    """Represents a player stat for a season or game."""
    __tablename__ = 'stats'
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    season = db.Column(db.String(8), nullable=False)  # "2024", "2023", etc
    stat_type = db.Column(db.String(16), nullable=False)  # "hitting", "pitching"
    stat_name = db.Column(db.String(32), nullable=False)
    stat_value = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=True)  # For game-by-game stats, can be null for season/career

class Prop(db.Model):
    """Represents a betting prop for a player in a game/event."""
    __tablename__ = 'props'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    event_id = db.Column(db.String(32), nullable=False)  # FanDuel event/game identifier
    prop_type = db.Column(db.String(32), nullable=False)
    line = db.Column(db.Float, nullable=True)
    odds = db.Column(db.String(16), nullable=True)

class Matchup(db.Model):
    """Represents a batter vs pitcher matchup for a given date."""
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
    """Maps MLB IDs to ESPN IDs and potentially other sources."""
    __tablename__ = 'player_id_map'
    id = db.Column(db.Integer, primary_key=True)
    mlb_id = db.Column(db.Integer, nullable=False, unique=True)
    espn_id = db.Column(db.Integer, nullable=True)
    # Might add more (baseball_ref_id, retrosheet_id, etc)

class Standing(db.Model):
    """Represents team standings for a given date."""
    __tablename__ = 'standings'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    team_name = db.Column(db.String(64), nullable=False)
    team_abbr = db.Column(db.String(8), nullable=False)
    division = db.Column(db.String(32), nullable=False)
    league = db.Column(db.String(8), nullable=False)
    wins = db.Column(db.Integer, nullable=False)
    losses = db.Column(db.Integer, nullable=False)
    winning_pct = db.Column(db.Float, nullable=False)
    games_behind = db.Column(db.Float, nullable=False)
    streak = db.Column(db.String(16), nullable=True)
    division_rank = db.Column(db.Integer, nullable=False)
    league_rank = db.Column(db.Integer, nullable=False)
    wildcard_rank = db.Column(db.Integer, nullable=True)
    last_updated = db.Column(db.Date, nullable=False)
    # Unique constraint on team and date
    __table_args__ = (db.UniqueConstraint('team_id', 'last_updated'),)

class GameOdds(db.Model):
    """Represents odds for MLB games from different bookmakers."""
    __tablename__ = 'game_odds'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.String(64), nullable=False)  # From OddsAPI
    date = db.Column(db.Date, nullable=False)
    commence_time = db.Column(db.DateTime, nullable=False)
    home_team = db.Column(db.String(100), nullable=False)
    away_team = db.Column(db.String(100), nullable=False)
    bookmaker = db.Column(db.String(50), nullable=False)  # 'fanduel', 'draftkings', 'betmgm'
    home_odds = db.Column(db.Integer, nullable=False)  # American odds format
    away_odds = db.Column(db.Integer, nullable=False)  # American odds format
    last_update = db.Column(db.DateTime, nullable=False)
    
    # Unique constraint to prevent duplicate odds for same game/bookmaker
    __table_args__ = (db.UniqueConstraint('game_id', 'bookmaker', name='unique_game_bookmaker'),)

class StatLeader(db.Model):
    """Represents individual player stat leaders."""
    __tablename__ = 'stat_leaders'
    id = db.Column(db.Integer, primary_key=True)
    season = db.Column(db.String(4), nullable=False)  # "2025"
    category = db.Column(db.String(50), nullable=False)  # "homeRuns", "battingAverage", "era"
    player_id = db.Column(db.Integer, nullable=False)  # MLB player ID
    player_name = db.Column(db.String(100), nullable=False)
    team_id = db.Column(db.Integer, nullable=True)
    team_name = db.Column(db.String(100), nullable=True)
    value = db.Column(db.String(20), nullable=False)  # Store as string to handle decimals
    rank = db.Column(db.Integer, nullable=False)
    last_updated = db.Column(db.Date, nullable=False)
    
    # Unique constraint for season/category/player
    __table_args__ = (db.UniqueConstraint('season', 'category', 'player_id', name='unique_stat_leader'),)

class TeamStatLeader(db.Model):
    """Represents team stat leaders."""
    __tablename__ = 'team_stat_leaders'
    id = db.Column(db.Integer, primary_key=True)
    season = db.Column(db.String(4), nullable=False)  # "2025"
    category = db.Column(db.String(50), nullable=False)  # "teamBattingAverage", "teamERA"
    stat_type = db.Column(db.String(20), nullable=False)  # "hitting" or "pitching"
    team_id = db.Column(db.Integer, nullable=False)
    team_name = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(20), nullable=False)  # Store as string to handle decimals
    rank = db.Column(db.Integer, nullable=False)
    last_updated = db.Column(db.Date, nullable=False)
    
    # Unique constraint for season/category/team
    __table_args__ = (db.UniqueConstraint('season', 'category', 'team_id', name='unique_team_stat_leader'),)

