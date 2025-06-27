from flask import Blueprint, jsonify, request, render_template, current_app
from app import db
from app.models import Player, Prop, Game, Team, Stat, PlayerIDMap, Standing, GameOdds, StatLeader, TeamStatLeader
from app.utils import log_api_call, handle_database_error, validate_integer_input, validate_string_input
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, Dict, Any
from datetime import date, timedelta

bp = Blueprint('main', __name__)

@bp.route("/")
def index():
    """Render the dashboard page."""
    return render_template("dashboard.html")

def get_player_stats(player_id: int, season: Optional[str] = None, stat_type: Optional[str] = None) -> Dict[str, Any]:
    """Return a dict of stat_name: stat_value for a player, with intelligent fallback logic. Optionally filter by stat_type ('hitting' or 'pitching')."""
    try:
        query = Stat.query.filter_by(player_id=player_id)
        if season:
            query = query.filter_by(season=season)
        if stat_type:
            query = query.filter_by(stat_type=stat_type)
        stats = query.all()
        if stats:
            stats_dict = {s.stat_name: s.stat_value for s in stats}
            return stats_dict
        # No stats for requested season/type, try career fallback if not already
        if season and season != "career":
            query = Stat.query.filter_by(player_id=player_id, season="career")
            if stat_type:
                query = query.filter_by(stat_type=stat_type)
            career_stats = query.all()
            if career_stats:
                stats_dict = {s.stat_name: s.stat_value for s in career_stats}
                current_app.logger.info(f"Player {player_id}: Using career stats fallback for season {season}")
                return stats_dict
        current_app.logger.warning(f"Player {player_id}: No stats found for season {season} and type {stat_type}")
        return {}
    except SQLAlchemyError as e:
        current_app.logger.error(f"Error fetching player stats: {e}")
        return {}

def get_team(team_id: int) -> Dict[str, Any]:
    """Return team info dict for a given team_id."""
    try:
        team = Team.query.filter_by(id=team_id).first()
        return {
            "id": team.id,
            "abbr": team.abbr,
            "logo": f"/static/team_logos/{team.id}.svg"
        } if team else {}
    except SQLAlchemyError as e:
        current_app.logger.error(f"Error fetching team: {e}")
        return {}

def get_espn_id_from_map(mlb_id: int) -> Optional[int]:
    """Returns ESPN ID from the PlayerIDMap for the given MLB ID, or None."""
    try:
        mapping = PlayerIDMap.query.filter_by(mlb_id=mlb_id).first()
        return mapping.espn_id if mapping and mapping.espn_id else None
    except SQLAlchemyError as e:
        current_app.logger.error(f"Error fetching ESPN ID: {e}")
        return None

def get_headshot(mlb_id: int) -> str:
    """Return the headshot URL for a player, or a placeholder if not found."""
    espn_id = get_espn_id_from_map(mlb_id)
    if espn_id and str(espn_id) != "None":
        return f"/static/headshots/{espn_id}.png"
    return "/static/headshots/placeholder.png"

@bp.route('/api/props')
@log_api_call
@handle_database_error
def get_props():
    """Return a list of props with optional team filtering."""
    try:
        # Validate query parameters
        team_id = None
        if request.args.get('team_id'):
            team_id = validate_integer_input(request.args.get('team_id'), min_val=1, field_name="team_id")
        
        per_page = validate_integer_input(
            request.args.get('per_page', 300), 
            min_val=1, 
            max_val=current_app.config.get('MAX_PAGE_SIZE', 1000),
            field_name="per_page"
        )
        
        # Get date filter from request, default to today and tomorrow
        date_filter = request.args.get('date_filter', 'upcoming')  # 'today', 'tomorrow', 'upcoming', 'all'
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        # Apply date filter
        if date_filter == 'today':
            props_query = Prop.query.filter(Prop.date == today)
        elif date_filter == 'tomorrow':
            props_query = Prop.query.filter(Prop.date == tomorrow)
        elif date_filter == 'upcoming':
            # Show props for today and tomorrow (upcoming games)
            props_query = Prop.query.filter(
                (Prop.date == today) | (Prop.date == tomorrow)
            )
        else:  # 'all' or any other value
            # Show last 7 days of props
            week_ago = today - timedelta(days=7)
            props_query = Prop.query.filter(Prop.date >= week_ago)
        
        props_query = props_query.order_by(Prop.date.asc(), Prop.odds.desc())
        
        # Add team filter if specified
        if team_id:
            props_query = props_query.join(Player).filter(Player.team_id == team_id)
        
        props = props_query.limit(per_page).all()
        
        # Build results with date formatting
        results = []
        seen_players = set()  # Track players to avoid duplicates (simplified since no overlap)
        
        for prop in props:
            player = Player.query.filter_by(id=prop.player_id).first()
            if not player:
                continue
                
            # Simple duplicate check - since there's no overlap between dates, this should work fine
            player_prop_key = f"{player.id}-{prop.prop_type}"
            if player_prop_key in seen_players:
                continue
            seen_players.add(player_prop_key)
            
            player_team = Team.query.filter_by(id=player.team_id).first()
            espn_id = get_espn_id_from_map(player.id)
            
            # Get season hits if available
            season_hits = None
            season = str(prop.date.year)
            hits_stat = Stat.query.filter_by(player_id=player.id, season=season, stat_name='h').first()
            season_hits = int(hits_stat.stat_value) if hits_stat else None
            
            results.append({
                "prop_id": prop.id,
                "player_id": prop.player_id,
                "player_name": player.name,
                "player_team_id": player_team.id if player_team else None,
                "player_team_abbr": player_team.abbr if player_team else "",
                "player_espn_id": espn_id,
                "prop_type": prop.prop_type,
                "odds": prop.odds,
                "line": prop.line,
                "event_id": prop.event_id,
                "date": prop.date.isoformat(),
                "date_formatted": prop.date.strftime("%m/%d"),
                "is_today": prop.date == today,
                "is_tomorrow": prop.date == today + timedelta(days=1),
                "position": player.position,
                "bats": player.bats,
                "throws": player.throws,
                "season_hits": season_hits
            })
        
        return jsonify({
            "results": results,
            "total": len(results)
        })
    except ValueError as e:
        current_app.logger.warning(f"Input validation error in get_props: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except SQLAlchemyError as e:
        current_app.logger.error(f"Error fetching props: {e}")
        return jsonify({"error": "Database error"}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_props: {e}")
        return jsonify({"error": "Unexpected error"}), 500

@bp.route('/api/teams')
@log_api_call
@handle_database_error
def get_teams():
    """Return all teams for filtering."""
    try:
        teams = Team.query.order_by(Team.name).all()
        results = []
        for team in teams:
            results.append({
                "id": team.id,
                "name": team.name,
                "abbr": team.abbr,
                "logo": f"/static/team_logos/{team.id}.svg"
            })
        return jsonify(results)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Error fetching teams: {e}")
        return jsonify({"error": "Database error"}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_teams: {e}")
        return jsonify({"error": "Unexpected error"}), 500

@bp.route('/api/health')
@log_api_call
def health_check():
    """Application health check endpoint."""
    from .utils import health_check
    return jsonify(health_check())

@bp.route('/api/prop/<int:prop_id>/matchup')
@log_api_call
@handle_database_error
def get_prop_matchup(prop_id: int):
    """Return the batter vs pitcher matchup for a given prop."""
    try:
        # Validate prop_id
        prop_id = validate_integer_input(prop_id, min_val=1, field_name="prop_id")
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
        # Only return hitting stats for hitters, pitching stats for pitchers
        batter_stats_type = "hitting" if batter and not batter.is_pitcher else "pitching"
        pitcher_stats_type = "pitching" if pitcher and pitcher.is_pitcher else "hitting"
        result = {
            "batter": {
                "name": batter.name if batter else "N/A",
                "headshot": get_headshot(batter.id),
                "team": get_team(batter.team_id) if batter and batter.team_id else {},
                "season_stats": get_player_stats(batter.id, season=str(prop.date.year), stat_type=batter_stats_type) if batter else {},
                "career_stats": get_player_stats(batter.id, season="career", stat_type=batter_stats_type) if batter else {},
            },
            "pitcher": {
                "name": pitcher.name if pitcher else "N/A",
                "headshot": get_headshot(pitcher.id) if pitcher else "/static/headshots/placeholder.png",
                "team": get_team(pitcher_team_id) if pitcher_team_id else {},
                "season_stats": get_player_stats(pitcher.id, season=str(prop.date.year), stat_type=pitcher_stats_type) if pitcher else {},
                "career_stats": get_player_stats(pitcher.id, season="career", stat_type=pitcher_stats_type) if pitcher else {},
            },
            "prop": {
                "type": prop.prop_type or "",
                "odds": prop.odds or "",
                "line": prop.line or ""
            }
        }
        return jsonify(result)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Error fetching prop matchup: {e}")
        return jsonify({"error": "Database error"}), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_prop_matchup: {e}")
        return jsonify({"error": "Unexpected error"}), 500

@bp.route('/api/players')
def get_players():
    """Return all players with their basic info."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        team_id = request.args.get('team_id', type=int)
        
        query = Player.query
        if team_id:
            query = query.filter_by(team_id=team_id)
            
        players = query.order_by(Player.name).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        results = []
        for player in players.items:
            team = Team.query.filter_by(id=player.team_id).first()
            espn_id = get_espn_id_from_map(player.id)
            
            # Get some basic season stats
            season_stats = get_player_stats(player.id, season="2025")
            
            results.append({
                "id": player.id,
                "name": player.name,
                "position": player.position,
                "team": {
                    "id": team.id if team else None,
                    "name": team.name if team else None,
                    "abbr": team.abbr if team else None,
                    "logo": f"/static/team_logos/{team.id}.svg" if team else None
                },
                "headshot": get_headshot(player.id),
                "bats": player.bats,
                "throws": player.throws,
                "season_stats": season_stats
            })
        
        return jsonify({
            "results": results,
            "pagination": {
                "page": players.page,
                "per_page": players.per_page,
                "total": players.total,
                "pages": players.pages
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching players: {e}")
        return jsonify({"error": "Failed to fetch players"}), 500

@bp.route('/api/games')
def get_games():
    """Return recent and upcoming games."""
    try:
        from datetime import date, timedelta
        
        # Get games from 3 days ago to 7 days ahead
        start_date = date.today() - timedelta(days=3)
        end_date = date.today() + timedelta(days=7)
        
        games = Game.query.filter(
            Game.date >= start_date,
            Game.date <= end_date
        ).order_by(Game.date.desc()).limit(50).all()
        
        results = []
        for game in games:
            home_team = Team.query.filter_by(id=game.home_team_id).first()
            away_team = Team.query.filter_by(id=game.away_team_id).first()
            home_pitcher = Player.query.filter_by(id=game.home_pitcher_id).first() if game.home_pitcher_id else None
            away_pitcher = Player.query.filter_by(id=game.away_pitcher_id).first() if game.away_pitcher_id else None
            
            results.append({
                "id": game.id,
                "date": game.date.isoformat(),
                "date_formatted": game.date.strftime("%m/%d"),
                "venue": game.venue,
                "home_team": {
                    "id": home_team.id if home_team else None,
                    "name": home_team.name if home_team else None,
                    "abbr": home_team.abbr if home_team else None,
                    "logo": f"/static/team_logos/{home_team.id}.svg" if home_team else None
                },
                "away_team": {
                    "id": away_team.id if away_team else None,
                    "name": away_team.name if away_team else None,
                    "abbr": away_team.abbr if away_team else None,
                    "logo": f"/static/team_logos/{away_team.id}.svg" if away_team else None
                },
                "home_pitcher": {
                    "id": home_pitcher.id if home_pitcher else None,
                    "name": home_pitcher.name if home_pitcher else None,
                    "headshot": get_headshot(home_pitcher.id) if home_pitcher else None
                },
                "away_pitcher": {
                    "id": away_pitcher.id if away_pitcher else None,
                    "name": away_pitcher.name if away_pitcher else None,
                    "headshot": get_headshot(away_pitcher.id) if away_pitcher else None
                }
            })
        
        return jsonify({
            "results": results,
            "total": len(results)
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching games: {e}")
        return jsonify({"error": "Failed to fetch games"}), 500

@bp.route('/api/standings')
@log_api_call
@handle_database_error
def get_standings():
    """Return current MLB standings from database."""
    try:
        from sqlalchemy import text
        from datetime import date
        
        # Get the most recent standings data
        query = text("""
            SELECT team_id, team_name, team_abbr, division, league,
                   wins, losses, winning_pct, games_behind, streak,
                   division_rank, league_rank, wildcard_rank
            FROM standings 
            WHERE last_updated = (SELECT MAX(last_updated) FROM standings)
            ORDER BY league, division, division_rank
        """)
        
        result = db.session.execute(query)
        rows = result.fetchall()
        
        if not rows:
            return jsonify({"error": "No standings data available"}), 404
        
        # Organize data by division
        standings = {"divisions": {}}
        
        division_map = {
            "American League East": "AL East",
            "American League Central": "AL Central", 
            "American League West": "AL West",
            "National League East": "NL East",
            "National League Central": "NL Central",
            "National League West": "NL West"
        }
        
        for row in rows:
            division_key = division_map.get(row.division, row.division)
            
            if division_key not in standings["divisions"]:
                standings["divisions"][division_key] = []
            
            team_data = {
                "team": row.team_name,
                "abbr": row.team_abbr,
                "team_id": row.team_id,
                "wins": row.wins,
                "losses": row.losses,
                "pct": round(row.winning_pct, 3),
                "gb": row.games_behind if row.games_behind > 0 else 0.0,
                "streak": row.streak or "W1"
            }
            
            standings["divisions"][division_key].append(team_data)
        
        # Calculate playoff picture for league view
        al_teams = []
        nl_teams = []
        
        for division_name, teams in standings["divisions"].items():
            if division_name.startswith("AL"):
                al_teams.extend(teams)
            else:
                nl_teams.extend(teams)
        
        # Sort by winning percentage
        al_teams.sort(key=lambda x: x["pct"], reverse=True)
        nl_teams.sort(key=lambda x: x["pct"], reverse=True)
        
        # Get division leaders (already first in each division due to division_rank sorting)
        al_division_leaders = []
        nl_division_leaders = []
        
        for div in ["AL East", "AL Central", "AL West"]:
            if div in standings["divisions"] and standings["divisions"][div]:
                al_division_leaders.append(standings["divisions"][div][0])
        
        for div in ["NL East", "NL Central", "NL West"]:
            if div in standings["divisions"] and standings["divisions"][div]:
                nl_division_leaders.append(standings["divisions"][div][0])
        
        # Get wild card teams (non-division leaders sorted by record)
        al_wildcard_candidates = [team for team in al_teams if team not in al_division_leaders]
        nl_wildcard_candidates = [team for team in nl_teams if team not in nl_division_leaders]
        
        al_wildcards = al_wildcard_candidates[:3]
        nl_wildcards = nl_wildcard_candidates[:3]
        
        # Get "in the hunt" teams (next 3 best records)
        al_in_hunt = al_wildcard_candidates[3:6]
        nl_in_hunt = nl_wildcard_candidates[3:6]
        
        standings["playoffs"] = {
            "AL": {
                "division_leaders": al_division_leaders,
                "wild_cards": al_wildcards,
                "in_hunt": al_in_hunt
            },
            "NL": {
                "division_leaders": nl_division_leaders,
                "wild_cards": nl_wildcards,
                "in_hunt": nl_in_hunt
            }
        }
        
        return jsonify(standings)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching standings: {e}")
        return jsonify({"error": "Failed to fetch standings"}), 500

@bp.route('/api/stats/summary')
def get_stats_summary():
    """Return summary statistics about the data."""
    try:
        from datetime import date
        
        today = date.today()
        
        # Count various entities
        total_teams = Team.query.count()
        total_players = Player.query.count()
        total_props = Prop.query.count()
        total_games = Game.query.count()
        
        # Props today
        props_today = Prop.query.filter_by(date=today).count()
        
        # Recent props
        from datetime import timedelta
        week_ago = today - timedelta(days=7)
        props_this_week = Prop.query.filter(Prop.date >= week_ago).count()
        
        # Teams with most props - fix the JOIN query
        team_prop_counts = db.session.query(
            Team.name, Team.abbr, db.func.count(Prop.id).label('prop_count')
        ).select_from(Team).join(Player, Team.id == Player.team_id).join(Prop, Player.id == Prop.player_id).group_by(Team.id, Team.name, Team.abbr).order_by(db.func.count(Prop.id).desc()).limit(5).all()
        
        return jsonify({
            "totals": {
                "teams": total_teams,
                "players": total_players,
                "props": total_props,
                "games": total_games
            },
            "recent": {
                "props_today": props_today,
                "props_this_week": props_this_week
            },
            "top_teams_by_props": [
                {
                    "name": team.name,
                    "abbr": team.abbr,
                    "prop_count": team.prop_count
                } for team in team_prop_counts
            ]
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching stats summary: {e}")
        return jsonify({"error": "Failed to fetch stats summary"}), 500

@bp.route('/api/game-odds')
@log_api_call
def get_game_odds():
    """Get game odds for upcoming games from multiple bookmakers."""
    try:
        from datetime import date, timedelta
        
        # Get date filter from request
        date_filter = request.args.get('date_filter', 'upcoming')
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        # Build date filter
        if date_filter == 'today':
            date_conditions = [GameOdds.date == today]
        elif date_filter == 'tomorrow':
            date_conditions = [GameOdds.date == tomorrow] 
        else:  # 'upcoming' - default
            date_conditions = [GameOdds.date.in_([today, tomorrow])]
        
        # Query odds
        odds_query = GameOdds.query.filter(*date_conditions).order_by(
            GameOdds.date.asc(),
            GameOdds.commence_time.asc(),
            GameOdds.bookmaker.asc()
        )
        
        all_odds = odds_query.all()
        
        # Group odds by game
        games_dict = {}
        for odd in all_odds:
            game_key = f"{odd.game_id}"
            
            if game_key not in games_dict:
                games_dict[game_key] = {
                    'game_id': odd.game_id,
                    'date': odd.date.isoformat(),
                    'commence_time': odd.commence_time.isoformat(),
                    'home_team': odd.home_team,
                    'away_team': odd.away_team,
                    'bookmakers': {}
                }
            
            games_dict[game_key]['bookmakers'][odd.bookmaker] = {
                'home_odds': odd.home_odds,
                'away_odds': odd.away_odds,
                'last_update': odd.last_update.isoformat()
            }
        
        # Convert to list and ensure we have the target bookmakers
        games = []
        target_bookmakers = ['fanduel', 'draftkings', 'betmgm']
        
        for game_data in games_dict.values():
            # Only include games that have at least 2 of our target bookmakers
            available_books = [book for book in target_bookmakers 
                             if book in game_data['bookmakers']]
            
            if len(available_books) >= 2:
                games.append(game_data)
        
        return jsonify({
            "games": games,
            "total": len(games),
            "date_filter": date_filter
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in game-odds endpoint: {e}")
        return jsonify({"error": "Failed to fetch game odds"}), 500

@bp.route('/api/stat-leaders/individual')
@log_api_call
@handle_database_error
def get_individual_stat_leaders():
    """Return individual player stat leaders."""
    try:
        # Get query parameters
        category = request.args.get('category', 'homeRuns')
        limit = validate_integer_input(
            request.args.get('limit', 10), 
            min_val=1, 
            max_val=50,
            field_name="limit"
        )
        season = request.args.get('season', '2025')
        
        # Fetch stat leaders
        leaders = StatLeader.query.filter_by(
            season=season,
            category=category
        ).order_by(StatLeader.rank.asc()).limit(limit).all()
        
        results = []
        for leader in leaders:
            # Get ESPN ID for headshot
            espn_id = get_espn_id_from_map(leader.player_id)
            
            results.append({
                "rank": leader.rank,
                "player_id": leader.player_id,
                "player_name": leader.player_name,
                "team_id": leader.team_id,
                "team_name": leader.team_name,
                "value": leader.value,
                "category": leader.category,
                "season": leader.season,
                "headshot": get_headshot(leader.player_id),
                "team_logo": f"/static/team_logos/{leader.team_id}.svg" if leader.team_id else None
            })
        
        return jsonify({
            "results": results,
            "category": category,
            "season": season,
            "total": len(results)
        })
        
    except ValueError as e:
        current_app.logger.warning(f"Input validation error in get_individual_stat_leaders: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error fetching individual stat leaders: {e}")
        return jsonify({"error": "Failed to fetch stat leaders"}), 500

@bp.route('/api/stat-leaders/teams')
@log_api_call
@handle_database_error
def get_team_stat_leaders():
    """Return team stat leaders."""
    try:
        # Get query parameters
        category = request.args.get('category', 'teamBattingAverage')
        limit = validate_integer_input(
            request.args.get('limit', 10), 
            min_val=1, 
            max_val=30,
            field_name="limit"
        )
        season = request.args.get('season', '2025')
        
        # Fetch team stat leaders
        leaders = TeamStatLeader.query.filter_by(
            season=season,
            category=category
        ).order_by(TeamStatLeader.rank.asc()).limit(limit).all()
        
        results = []
        for leader in leaders:
            results.append({
                "rank": leader.rank,
                "team_id": leader.team_id,
                "team_name": leader.team_name,
                "value": leader.value,
                "category": leader.category,
                "stat_type": leader.stat_type,
                "season": leader.season,
                "team_logo": f"/static/team_logos/{leader.team_id}.svg"
            })
        
        return jsonify({
            "results": results,
            "category": category,
            "season": season,
            "total": len(results)
        })
        
    except ValueError as e:
        current_app.logger.warning(f"Input validation error in get_team_stat_leaders: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error fetching team stat leaders: {e}")
        return jsonify({"error": "Failed to fetch team stat leaders"}), 500

@bp.route('/api/stat-leaders/categories')
def get_stat_leader_categories():
    """Get available stat categories for both individual and team leaders."""
    
    # Batting categories (for position players)
    batting_categories = [
        {'category': 'homeRuns', 'display_name': 'Home Runs'},
        {'category': 'rbi', 'display_name': 'RBIs'},
        {'category': 'hits', 'display_name': 'Hits'},
        {'category': 'battingAverage', 'display_name': 'Batting Average'},
        {'category': 'onBasePlusSlugging', 'display_name': 'OPS'},
        {'category': 'sluggingPercentage', 'display_name': 'Slugging %'},
        {'category': 'onBasePercentage', 'display_name': 'On-Base %'},
        {'category': 'stolenBases', 'display_name': 'Stolen Bases'},
        {'category': 'runs', 'display_name': 'Runs'},
        {'category': 'doubles', 'display_name': 'Doubles'},
        {'category': 'triples', 'display_name': 'Triples'}
    ]
    
    # Pitching categories (for pitchers)
    pitching_categories = [
        {'category': 'era', 'display_name': 'ERA'},
        {'category': 'wins', 'display_name': 'Wins'},
        {'category': 'strikeouts', 'display_name': 'Strikeouts'},
        {'category': 'whip', 'display_name': 'WHIP'},
        {'category': 'saves', 'display_name': 'Saves'},
        {'category': 'holds', 'display_name': 'Holds'},
        {'category': 'qualityStarts', 'display_name': 'Quality Starts'}
    ]
    
    # Team categories
    team_categories = [
        {'category': 'teamBattingAverage', 'display_name': 'Team Batting Average'},
        {'category': 'teamHomeRuns', 'display_name': 'Team Home Runs'},
        {'category': 'teamRBI', 'display_name': 'Team RBIs'},
        {'category': 'teamRuns', 'display_name': 'Team Runs'},
        {'category': 'teamHits', 'display_name': 'Team Hits'},
        {'category': 'teamSluggingPercentage', 'display_name': 'Team Slugging %'},
        {'category': 'teamOnBasePercentage', 'display_name': 'Team On-Base %'},
        {'category': 'teamOPS', 'display_name': 'Team OPS'},
        {'category': 'teamERA', 'display_name': 'Team ERA'},
        {'category': 'teamWHIP', 'display_name': 'Team WHIP'},
        {'category': 'teamStrikeouts', 'display_name': 'Team Strikeouts'},
        {'category': 'teamSaves', 'display_name': 'Team Saves'},
        {'category': 'teamWins', 'display_name': 'Team Wins'}
    ]
    
    return jsonify({
        'batting': batting_categories,
        'pitching': pitching_categories,
        'team': team_categories
    })

# Global error handler for JSON errors
@bp.app_errorhandler(500)
def handle_500_error(error):
    current_app.logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

