from flask import jsonify
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

client = MongoClient("mongodb://localhost:27017/")
db = client["mydb"]
games = db["games"]
games.create_index("gameId", unique=True)

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

if __name__ == '__main__':
    while True:
        sleep_time_hours = 12
        seconds_per_hour = 3600
        if(datetime.now().isoweekday() == 4 or datetime.now().isoweekday() == 1):
            sleep_time_hours = 8
        if(datetime.now().isoweekday() == 7):
            sleep_time_hours = 3
        sleep_time = sleep_time_hours * seconds_per_hour
        print(f"Pulling odds in {sleep_time_hours} hour(s)...")
        time.sleep(sleep_time)
        try:
            print("Pulling odds api now...")
            call_odds_api('NFL')
        except Exception as e:
            print("Could not call odds-api, likely out of credits or service is down")