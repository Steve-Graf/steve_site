from flask import Blueprint, jsonify, request
import requests
import os
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timezone, timedelta
from dateutil.parser import isoparse
from bson import ObjectId
import json
from collections import Counter
from functools import wraps

odds_bp = Blueprint('odds', __name__)

try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    db = client["mydb"]
    users = db["users"]
    users.create_index("playerCode", unique=True)
    games = db["games"]
    games.create_index("gameId", unique=True)
    mongo_available = True
except Exception:
    db = users = games = None
    mongo_available = False
    print("MongoDB unavailable — /api/odds/ routes disabled")

def require_mongo(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not mongo_available:
            return jsonify({"error": "odds service unavailable"}), 503
        return f(*args, **kwargs)
    return wrapper

@odds_bp.route('/api/odds/scores', methods=['POST'])
def get_scores():
    data = request.json
    game_list = data.get("games", [])
    for game in game_list:
        game = update_game_score(game)
    return jsonify({"updatedGames": game_list})

def update_game_score(game):
    if not isinstance(game['gameTime'], datetime):
        dt = datetime.strptime(game['gameTime'], "%a, %d %b %Y %H:%M:%S %Z")
    else:
        dt = game['gameTime']
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    yyyymmdd = dt.astimezone().strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={yyyymmdd}"

    try:
        response = requests.get(url)
        data = response.json()
        for event in data['events']:
            for team in event['competitions'][0]['competitors']:
                if team['team']['displayName'] == game['homeTeam'] and team['homeAway'] == 'home':
                    game['homeScore'] = team['score']
                elif team['team']['displayName'] == game['awayTeam'] and team['homeAway'] == 'away':
                    game['awayScore'] = team['score']
    except Exception:
        print("Could not find score for game")
        game['homeScore'] = '--'
        game['awayScore'] = '--'
    return game

def serialize_mongo(doc):
    doc = dict(doc)
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            doc[k] = str(v)
    return doc

def get_nfl_week(target):
    schedule_path = os.path.join(os.path.dirname(__file__), "nfl_schedule.json")
    with open(schedule_path) as f:
        weeks = json.load(f)

    def parse_iso_z(dt_str):
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

    current_day = datetime.today().weekday()
    matching_week = None

    for i, week in enumerate(weeks):
        start = parse_iso_z(week["startDate"])
        end = parse_iso_z(week["endDate"])

        if start <= target <= end:
            if current_day == 1:
                matching_week = weeks[i + 1]
            else:
                matching_week = week
            break
    return matching_week

@odds_bp.route('/api/odds/sport/<sport>')
@require_mongo
def odds(sport):
    current_nfl_week = get_nfl_week(target=datetime.now(timezone.utc))
    current_nfl_week_start = datetime.fromisoformat(current_nfl_week["startDate"].replace("Z", "+00:00")) - timedelta(hours=1)
    current_nfl_week_end = datetime.fromisoformat(current_nfl_week["endDate"].replace("Z", "+00:00")) + timedelta(hours=1)

    print("Querying from", current_nfl_week_start, "to", current_nfl_week_end)

    games_cursor = games.find({
        "gameTime": {"$gte": current_nfl_week_start, "$lte": current_nfl_week_end}
    })

    current_games = []
    for g in games_cursor:
        current_games.append(serialize_mongo(g))
    games_sorted = sorted(current_games, key=lambda g: g["gameTime"])
    for sorted_game in games_sorted:
        sorted_game = update_game_score(sorted_game)
    return jsonify(games_sorted)

@odds_bp.route('/api/odds/game-state', methods=['POST'])
@require_mongo
def game_state():
    data = request.json
    game_state_val = 'none'
    try:
        game_id = data["gameId"]
        player_code = data["playerCode"]
        game = games.find_one({"gameId": game_id})
        if game:
            pick_data = get_pick(game_id, player_code)
            print(pick_data)
            try:
                away_points = float(game['awayScore'])
                home_points = float(game['homeScore'])
                points_spread = game['gameSpread']
                if game['gameSpreadTeam'] == game['homeTeam']:
                    home_points += points_spread
                elif game['gameSpreadTeam'] == game['awayTeam']:
                    away_points += points_spread
                spread_coverer = 'Push'
                if home_points > away_points:
                    spread_coverer = game['homeTeam']
                elif away_points > home_points:
                    spread_coverer = game['awayTeam']
                if pick_data.get('selectedTeam') == spread_coverer:
                    game_state_val = 'win'
                else:
                    game_state_val = 'lose'
            except Exception as e:
                print(f'Could not find data for game: {e}')
    except Exception:
        print('Could not find game')
    return jsonify({"game_state": game_state_val})

def create_user(player_code, player_name="Unnamed"):
    try:
        result = users.insert_one({
            "playerCode": player_code,
            "name": player_name,
            "points": 0,
            "picks": {}
        })
        return jsonify({"ok": True, "inserted_id": str(result.inserted_id)})
    except DuplicateKeyError:
        return jsonify({"ok": False, "error": "User already exists"}), 400

@odds_bp.route('/api/odds/update-username', methods=['POST'])
@require_mongo
def update_username():
    data = request.json
    player_code = data["playerCode"]
    username = data["username"]

    result = users.update_one(
        {"playerCode": player_code},
        {"$set": {"name": username}},
        upsert=False
    )

    if result.matched_count == 0:
        return jsonify({"status": "failed", "action": "no_user_found"})

    return jsonify({"status": "success", "action": "updated"})

def get_user(player_code):
    print(f"Looking up user {player_code}")
    user = users.find_one({"playerCode": player_code}, {"_id": 0})
    if user:
        return jsonify(user)
    else:
        create_user(player_code)
        user = users.find_one({"playerCode": player_code}, {"_id": 0})
        return jsonify(user)

def get_pick(game_id, player_code):
    user = users.find_one({"playerCode": player_code})
    if user:
        for pick_id, pick_data in user.get('picks', {}).items():
            if pick_id == game_id:
                return pick_data

@odds_bp.route('/api/odds/update-pick', methods=['POST'])
@require_mongo
def update_pick():
    data = request.json
    player_code = data["playerCode"]
    game_id = data["gameId"]

    new_pick = {
        "homeTeam": data.get("homeTeam"),
        "awayTeam": data.get("awayTeam"),
        "selectedTeam": data.get("selectedTeam"),
        "gameSpread": data.get("gameSpread")
    }

    previous_entry = users.find_one(
        {"playerCode": player_code},
        {f"picks.{game_id}": 1}
    )

    old_pick = None
    if previous_entry and "picks" in previous_entry and game_id in previous_entry["picks"]:
        old_pick = previous_entry["picks"][game_id]
    print(old_pick)
    game_result = games.find_one({"gameId": game_id})
    print(game_result)
    if old_pick:
        old_team = old_pick.get("selectedTeam")
        new_team = new_pick.get("selectedTeam")

        if old_team != new_team:
            if old_team == new_pick["homeTeam"]:
                games.update_one(
                    {"gameId": game_id, "homePickCount": {"$gt": 0}},
                    {"$inc": {"homePickCount": -1}}
                )
            elif old_team == new_pick["awayTeam"]:
                games.update_one(
                    {"gameId": game_id, "awayPickCount": {"$gt": 0}},
                    {"$inc": {"awayPickCount": -1}}
                )

            if new_team == new_pick["homeTeam"]:
                games.update_one({"gameId": game_id}, {"$inc": {"homePickCount": 1}})
            elif new_team == new_pick["awayTeam"]:
                games.update_one({"gameId": game_id}, {"$inc": {"awayPickCount": 1}})
    else:
        if new_pick["selectedTeam"] == new_pick["homeTeam"]:
            games.update_one({"gameId": game_id}, {"$inc": {"homePickCount": 1}})
        elif new_pick["selectedTeam"] == new_pick["awayTeam"]:
            games.update_one({"gameId": game_id}, {"$inc": {"awayPickCount": 1}})

    result = users.update_one(
        {"playerCode": player_code},
        {"$set": {f"picks.{game_id}": new_pick}}
    )

    return jsonify({
        "status": "success",
        "action": "updated" if result.matched_count else "created"
    })

@odds_bp.route('/api/odds/player/<player_code>')
@require_mongo
def get_user_data(player_code):
    return get_user(player_code)

@odds_bp.route('/api/odds/stats/<player_code>')
@require_mongo
def get_user_stats(player_code):
    print(player_code)
    return get_stats(player_code)

def get_stats(player_code):
    user = users.find_one({"playerCode": player_code})
    user_points = 0
    total_picks = 0
    selected_teams = []
    underdog_teams = []
    underdog_winners = 0
    favored_teams = []
    favored_winners = 0
    favorite_team = ''
    favorite_team_times_picked = 0
    best_team = ''
    best_team_win_count = 0
    worst_team = ''
    worst_team_loss_count = 0
    for pick_id, pick_data in user.get('picks', {}).items():
        game = games.find_one({"gameId": pick_id})
        try:
            game_time_utc = game['gameTime'].replace(tzinfo=timezone.utc)
            now_utc = datetime.now(timezone.utc)
            if game_time_utc > now_utc:
                continue

            away_points = float(game['awayScore'])
            home_points = float(game['homeScore'])
            points_spread = game['gameSpread']
            if game['gameSpreadTeam'] == game['homeTeam']:
                home_points += points_spread
            elif game['gameSpreadTeam'] == game['awayTeam']:
                away_points += points_spread
            spread_coverer = 'Push'
            if home_points > away_points:
                spread_coverer = game['homeTeam']
            elif away_points > home_points:
                spread_coverer = game['awayTeam']
            is_winner = False
            if pick_data.get('selectedTeam') == spread_coverer:
                user_points += 1
                is_winner = True

            is_favorite = True
            if '+' in str(pick_data.get('gameSpread')):
                is_favorite = False

            pick_info = {
                'is_winner': is_winner,
                'selected_team': pick_data.get('selectedTeam')
            }
            if is_favorite:
                favored_teams.append(pick_info)
            else:
                underdog_teams.append(pick_info)
            selected_teams.append(pick_info)

            total_picks += 1
        except Exception:
            pass
    print(f"User's points:{user_points}")
    print(f"Total picks:{total_picks}")
    if total_picks > 0:
        for underdog in underdog_teams:
            if underdog['is_winner']:
                underdog_winners += 1
        for favorite in favored_teams:
            if favorite['is_winner']:
                favored_winners += 1

        selected_team_names = []
        winning_team_names = []
        losing_team_names = []
        for team in selected_teams:
            selected_team_names.append(team['selected_team'])
            if team['is_winner']:
                winning_team_names.append(team['selected_team'])
            else:
                losing_team_names.append(team['selected_team'])
        favorite_team_counts = Counter(selected_team_names)
        most_frequent_selected_team_tuple = favorite_team_counts.most_common(1)
        favorite_team = most_frequent_selected_team_tuple[0][0]
        favorite_team_times_picked = most_frequent_selected_team_tuple[0][1]
        best_team_counts = Counter(winning_team_names)
        best_team_tuple = best_team_counts.most_common(1)
        best_team = best_team_tuple[0][0]
        best_team_win_count = best_team_tuple[0][1]
        worst_team_counts = Counter(losing_team_names)
        worst_team_tuple = worst_team_counts.most_common(1)
        worst_team = worst_team_tuple[0][0]
        worst_team_loss_count = worst_team_tuple[0][1]

        return jsonify({
            "status": "success",
            "total": total_picks,
            "wins": user_points,
            "underdog_count": len(underdog_teams),
            "underdog_wins_count": underdog_winners,
            "favored_count": len(favored_teams),
            "favored_wins_count": favored_winners,
            "favorite_team": favorite_team,
            "favorite_team_count": favorite_team_times_picked,
            "best_team": best_team,
            "best_team_win_count": best_team_win_count,
            "best_team_pick_count": selected_team_names.count(best_team),
            "worst_team": worst_team,
            "worst_team_loss_count": worst_team_loss_count,
            "worst_team_pick_count": selected_team_names.count(worst_team)
        })

    return jsonify({"status": "failed"})
