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

global odds_json
odds_json = ''
global last_odds_ping_unix
last_odds_ping_unix = None
def call_odds_api(sport):
    print(f"Pinging odds API for {sport}...")
    api_key = keys.odds_api
    sport_key = ''
    if(sport == 'NFL'):
        sport_key = 'americanfootball_nfl'
    else:
        return jsonify({"error": f"Unsupported sport"})
    api_url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds/'
    params = {"apiKey":api_key, "regions":"us", "markets":"h2h,spreads,totals", "oddsFormat":"american", "bookmakers":"draftkings"}
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        if(response.status_code == 200):
            global last_odds_ping_unix
            last_odds_ping_unix = time.time()
            with open("last_updated.txt", "w") as f:
                f.write(str(int(time.time())))
            # update games that are not active or complete
            odds_json = response.json()
            for game in odds_json:
                game_time = datetime.fromisoformat(game['commence_time'].replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                if now < game_time:
                    update_game(game, games_db=games)
            return response.json()
        else:
            return jsonify([{"error", "Non 200 success status"}])
    except requests.exceptions.Timeout:
        print("Request timed out")
        return jsonify({"error": "Request timed out"})
    except requests.exceptions.HTTPError as e:
        print("HTTP error:", e)
        return jsonify({"error": f"HTTP error: {e}"})
    except Exception as e:
        print("Other error:", e)
        return jsonify({"error": f"Other error: {e}"})
    
def odds_refresh_thread():
    while True:
        # steve -- fix this
        sleep_time = 3600
        current_time = time.time()
        previous_time = 0
        try:
            if(os.path.exists('last_updated.txt')):
                with open("last_updated.txt", "r") as f:
                    previous_time = int(f.readline().strip())
        except:
            print("Value for last_updated.txt does not exist, skipping...")
        elapsed_time = int(current_time) - previous_time
        if(elapsed_time > 3600):
            call_odds_api('NFL')
        else:
            print('We pulled recently, skipping...')
        time.sleep(sleep_time)

def serialize_mongo(doc):
    doc = dict(doc)
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            doc[k] = str(v)
    return doc

@app.route('/api/odds/sport/<sport>')
def odds(sport):
    now = datetime.now(timezone.utc) - timedelta(days=2)
    week_ahead = now + timedelta(days=7)

    print("Querying from", now, "to", week_ahead)

    games_cursor = games.find({
        "gameTime": {"$gte": now, "$lte": week_ahead}
    })

    current_games = []
    for g in games_cursor:
        print(g["gameId"], g["homeTeam"], g["awayTeam"], g["gameTime"])
        current_games.append(serialize_mongo(g))
    return jsonify(current_games)
    
def get_game(game_id, game_json=None):
    print(f"Looking up game {game_id}")
    game = games.find_one({"gameId": game_id}, {"_id": 0})
    if game:
        return jsonify(game)
    else:
        update_game(game_json, games_db=games)
        game = games.find_one({"gameId": game_id}, {"_id": 0})
        return jsonify(game)
    
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

@app.route('/api/odds/game/<game_id>')
def get_game_data(game_id):
    response_json = get_game(game_id)
    return response_json

if __name__ == '__main__':
    odds_thread = threading.Thread(target=odds_refresh_thread, daemon=True)
    odds_thread.start()

    app.run(host='0.0.0.0', port=5000, debug=True)