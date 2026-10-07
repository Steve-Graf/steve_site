import os
import sys
import time
from datetime import datetime, timezone

import requests
from dateutil.parser import isoparse

import keys

# this script is run standalone (e.g. `python odds/odds_refresh.py`), which puts
# only this file's own directory on sys.path — add the repo root so the
# top-level `bingo` package (shared Firebase setup) is importable too.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bingo.config import BingoConfig
from bingo.extensions import get_db, init_firebase

from health import record_heartbeat

init_firebase(BingoConfig.FIREBASE_CREDENTIALS_PATH)
db = get_db()
games_ref = db.collection('odds_games')


def update_game(game_json, games_ref):
    print(f"Updating game {game_json['id']}...")

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
            if bookmaker['key'] == bookmaker_key:
                for market in bookmaker['markets']:
                    if market['key'] == spreads_key:
                        # note -- the 0 index is for the home team
                        game_spread = market['outcomes'][0]['point']
                        game_spread_team = market['outcomes'][0]['name']
                    if market['key'] == ou_key:
                        ou_points = market['outcomes'][0]['point']
    except Exception:
        print('Could not parse game_json for game, skipping...')
        return

    games_ref.document(game_id).set({
        "gameId": game_id,
        "awayTeam": away_team,
        "homeTeam": home_team,
        "gameSpread": game_spread,
        "gameSpreadTeam": game_spread_team,
        "ouPoints": ou_points,
        "gameTime": game_time,
    }, merge=True)

    print("Game updated")


last_odds_ping_unix = None


def call_odds_api(sport, backup_key=False):
    print(f"Pinging odds API for {sport}...")
    api_key = keys.odds_api
    if backup_key:
        api_key = keys.odds_api_backup
    if sport == 'NFL':
        sport_key = 'americanfootball_nfl'
    else:
        return {"error": "Unsupported sport"}
    api_url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds/'
    params = {"apiKey": api_key, "regions": "us", "markets": "h2h,spreads,totals", "oddsFormat": "american", "bookmakers": "draftkings"}
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        if response.status_code == 200:
            global last_odds_ping_unix
            last_odds_ping_unix = time.time()
            with open(os.path.join(os.path.dirname(__file__), "last_updated.txt"), "w") as f:
                f.write(str(int(time.time())))
            # update games that are not active or complete
            odds_json = response.json()
            for game in odds_json:
                game_time = datetime.fromisoformat(game['commence_time'].replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                if now < game_time:
                    update_game(game, games_ref)
            return odds_json
        else:
            return {"error": "Non 200 success status"}
    except requests.exceptions.Timeout:
        print("Request timed out")
        return {"error": "Request timed out"}
    except requests.exceptions.HTTPError as e:
        print("HTTP error:", e)
        if not backup_key:
            print("Retrying with backup API key...")
            return call_odds_api(sport, backup_key=True)
        return {"error": f"HTTP error: {e}"}
    except Exception as e:
        print("Other error:", e)
        if not backup_key:
            print("Retrying with backup API key...")
            return call_odds_api(sport, backup_key=True)
        return {"error": f"Other error: {e}"}


if __name__ == '__main__':
    while True:
        try:
            print("Pulling odds api now...")
            result = call_odds_api('NFL')
            if isinstance(result, dict) and result.get('error'):
                record_heartbeat(db, 'oddsRefresh', status='error', error=result['error'])
            else:
                record_heartbeat(db, 'oddsRefresh', status='ok')
        except Exception as e:
            print("Could not call odds-api, likely out of credits or service is down")
            record_heartbeat(db, 'oddsRefresh', status='error', error=e)

        sleep_time_hours = 12
        seconds_per_hour = 3600
        if datetime.now().isoweekday() == 4 or datetime.now().isoweekday() == 1:
            sleep_time_hours = 8
        if datetime.now().isoweekday() == 7:
            sleep_time_hours = 3
        sleep_time = sleep_time_hours * seconds_per_hour
        print(f"Pulling odds in {sleep_time_hours} hour(s)...")
        time.sleep(sleep_time)
