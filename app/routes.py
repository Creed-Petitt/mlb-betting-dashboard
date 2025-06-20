from flask import Blueprint, jsonify
from app import db
from app.models import Player, Prop, Game, Team, Stat, PlayerIDMap
from flask import render_template

bp = Blueprint('main', __name__)

@bp.route("/")
def index():
    return render_template("dashboard.html")

def get_player_stats(player_id, season=None):
    stats = Stat.query.filter_by(player_id=player_id)
    if season:
        stats = stats.filter_by(season=season)
    stats_dict = {}
    for s in stats:
        stats_dict[s.stat_name] = s.stat_value
    return stats_dict

def get_team(team_id):
    team = Team.query.filter_by(id=team_id).first()
    return {
        "id": team.id,
        "abbr": team.abbr,
        "logo": f"/static/team_logos/{team.id}.svg"
    } if team else {}

def get_espn_id_from_map(mlb_id):
    # Returns ESPN ID from the PlayerIDMap for the given MLB ID, or None
    mapping = PlayerIDMap.query.filter_by(mlb_id=mlb_id).first()
    return mapping.espn_id if mapping and mapping.espn_id else None

def get_headshot(mlb_id):
    espn_id = get_espn_id_from_map(mlb_id)
    if espn_id and str(espn_id) != "None":
        return f"/static/headshots/{espn_id}.png"
    return "/static/headshots/placeholder.png"

@bp.route('/api/props')
def get_props():
    props = Prop.query.all()
    results = []
    for prop in props:
        player = Player.query.filter_by(id=prop.player_id).first()
        player_team = Team.query.filter_by(id=player.team_id).first() if player else None
        espn_id = get_espn_id_from_map(player.id) if player else None
        results.append({
            "prop_id": prop.id,
            "player_id": prop.player_id,
            "player_name": player.name if player else None,
            "player_team_id": player_team.id if player_team else None,
            "player_team_abbr": player_team.abbr if player_team else "",
            "player_espn_id": espn_id,
            "prop_type": prop.prop_type,
            "odds": prop.odds,
            "line": prop.line,
            "event_id": prop.event_id,
            "date": prop.date.isoformat()
        })
    return jsonify(results)

@bp.route('/api/prop/<int:prop_id>/matchup')
def get_prop_matchup(prop_id):
    prop = Prop.query.filter_by(id=prop_id).first()
    if not prop:
        return jsonify({"error": "Prop not found"}), 404

    batter = Player.query.filter_by(id=prop.player_id).first()
    if not batter:
        return jsonify({"error": "Batter not found"}), 404

    game = Game.query.filter(
        Game.date == prop.date,
        ((Game.home_team_id == batter.team_id) | (Game.away_team_id == batter.team_id))
    ).first()

    pitcher_id = None
    pitcher_team_id = None
    if game:
        if game.home_team_id == batter.team_id:
            pitcher_id = game.away_pitcher_id or game.home_pitcher_id
            pitcher_team_id = game.away_team_id
        else:
            pitcher_id = game.home_pitcher_id or game.away_pitcher_id
            pitcher_team_id = game.home_team_id
        if not pitcher_id:
            pitcher_id = game.home_pitcher_id or game.away_pitcher_id

    pitcher = Player.query.filter_by(id=pitcher_id).first() if pitcher_id else None

    result = {
        "batter": {
            "name": batter.name if batter else "N/A",
            "headshot": get_headshot(batter.id),
            "team": get_team(batter.team_id) if batter and batter.team_id else {},
            "season_stats": get_player_stats(batter.id, season=str(prop.date.year)) if batter else {},
            "career_stats": get_player_stats(batter.id, season="career") if batter else {},
        },
        "pitcher": {
            "name": pitcher.name if pitcher else "N/A",
            "headshot": get_headshot(pitcher.id) if pitcher else "/static/headshots/placeholder.png",
            "team": get_team(pitcher_team_id) if pitcher_team_id else {},
            "season_stats": get_player_stats(pitcher.id, season=str(prop.date.year)) if pitcher else {},
            "career_stats": get_player_stats(pitcher.id, season="career") if pitcher else {},
        },
        "prop": {
            "type": prop.prop_type or "",
            "odds": prop.odds or "",
            "line": prop.line or ""
        }
    }
    return jsonify(result)

