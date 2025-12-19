from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import requests
import keys
import time
from pymongo import MongoClient, collection
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timezone, timedelta
from datetime import time as time_datetime
import threading
import os
from dateutil.parser import isoparse
from bson import ObjectId
import json

app = Flask(__name__, static_folder='client/dist/assets', template_folder='client/dist')
CORS(app, origins=['http://localhost:5173', 'https://stevegraf.com'])

client = MongoClient("mongodb://localhost:27017/")
db = client["mydb"]
users = db["users"]
users.create_index("playerCode", unique=True)

games = db["games"]
games.create_index("gameId", unique=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/odds/')
def odds_template():
    return render_template('odds.html')

@app.route('/api/odds/scores', methods=['POST'])
def get_scores():
    data = request.json
    games = data.get("games", [])
    for game in games:
        game = update_game_score(game)
    return jsonify({"updatedGames":games})

def update_game_score(game):
    # Parse the string into a datetime object
    if not isinstance(game['gameTime'], datetime):
        dt = datetime.strptime(game['gameTime'], "%a, %d %b %Y %H:%M:%S %Z")
    else:
        dt = game['gameTime']
    # convert dt to est
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    yyyymmdd = dt.astimezone().strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={yyyymmdd}"

    try:
        response = requests.get(url)
        data = response.json()
        for event in data['events']:
            for team in event['competitions'][0]['competitors']:
                if(team['team']['displayName'] == game['homeTeam'] and team['homeAway'] == 'home'):
                    game['homeScore'] = team['score']
                elif(team['team']['displayName'] == game['awayTeam'] and team['homeAway'] == 'away'):
                    game['awayScore'] = team['score']
    except Exception as e:
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
    # load nfl_schedule.json
    with open("nfl_schedule.json") as f:
        weeks = json.load(f)

    def parse_iso_z(dt_str):
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

    current_day = datetime.today().weekday()
    matching_week = None

    for i, week in enumerate(weeks):
        start = parse_iso_z(week["startDate"])
        end = parse_iso_z(week["endDate"])
        
        if start <= target <= end:
            # if today is tuesday, go to next nfl week
            if(current_day == 1):
                matching_week = weeks[i + 1]
            else:
                matching_week = week
            break
    return matching_week

@app.route('/api/odds/sport/<sport>')
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
        # print(g["gameId"], g["homeTeam"], g["awayTeam"], g["gameTime"])
        current_games.append(serialize_mongo(g))
    games_sorted = sorted(
        current_games,
        key=lambda g: g["gameTime"]
    )
    # loop through each game and update the score
    for sorted_game in games_sorted:
        sorted_game = update_game_score(sorted_game)
    return jsonify(games_sorted)
    
def update_game(game_json, games_db=None):
    print(f'Updating game {game_json['id']}...')

    bookmaker_key = 'draftkings'
    spreads_key = 'spreads'
    ou_key = 'totals'

    try:
        game_id = game_json['id']
        game_time = isoparse(game_json['commence_time']).astimezone(timezone.utc)
        away_team = game_json['away_team']
        home_team = game_json['home_team']
        game_spread = 0
        ou_points = 0
        for bookmaker in game_json['bookmakers']:
            if(bookmaker['key'] == bookmaker_key):
                for market in bookmaker['markets']:
                    if(market['key'] == spreads_key):
                        # note -- the 0 index is for the home team
                        game_spread = market['outcomes'][0]['point']
                        game_spread_team = market['outcomes'][0]['name']
                    if(market['key'] == ou_key):
                        ou_points = market['outcomes'][0]['point']
    except Exception as e:
        # steve - change this later to handle missing fields better
        print(f'Could not parse game_json for game, skipping...')
        return

    # update OR insert — doesn't matter; $set handles both
    result = games_db.update_one(
        {"gameId": game_id},
        {
            "$set": {
                "awayTeam": away_team,
                "homeTeam": home_team,
                "gameSpread": game_spread,
                "gameSpreadTeam": game_spread_team,
                "ouPoints": ou_points,
                "gameTime": game_time,
            }
        },
        upsert=True
    )

    print("Game updated")

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
    
@app.route('/api/odds/update-username', methods=['POST'])
def update_username():
    data = request.json
    player_code = data["playerCode"]
    username = data["username"]

    result = users.update_one(
        {"playerCode": player_code},
        {"$set": {f"name": username}},
        upsert=False
    )

    if result.matched_count == 0:
        return jsonify({
            "status": "failed",
            "action": "no_user_found"
        })

    return jsonify({
        "status": "success",
        "action": "updated"
    })
    
def get_user(player_code):
    print(f"Looking up user {player_code}")
    user = users.find_one({"playerCode": player_code}, {"_id": 0})
    if user:
        return jsonify(user)
    else:
        create_user(player_code)
        user = users.find_one({"playerCode": player_code}, {"_id": 0})
        return jsonify(user)

@app.route('/api/odds/update-pick', methods=['POST'])
def update_pick():
    data = request.json
    player_code = data["playerCode"]
    game_id = data["gameId"]

    # new pick object
    new_pick = {
        "homeTeam": data.get("homeTeam"),
        "awayTeam": data.get("awayTeam"),
        "selectedTeam": data.get("selectedTeam"),
        "gameSpread": data.get("gameSpread")
    }

    # update OR insert — doesn't matter; $set handles both
    result = users.update_one(
        {"playerCode": player_code},
        {"$set": {f"picks.{game_id}": new_pick}}
    )

    return jsonify({
        "status": "success",
        "action": "updated" if result.matched_count else "created"
    })

@app.route('/api/odds/player/<player_code>')
def get_user_data(player_code):
    response_json = get_user(player_code)
    return response_json

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)