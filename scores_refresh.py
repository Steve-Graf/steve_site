import requests
from pymongo import MongoClient
import threading
import json
from datetime import datetime, timedelta, timezone
import time

client = MongoClient("mongodb://localhost:27017/")
db = client["mydb"]
games = db["games"]
games.create_index("gameId", unique=True)

def get_scores_from_week(week_number=None):
    # pull in the week info from nfl_schedule.json
    weeks = None
    nfl_week_days = []
    with open("nfl_schedule.json") as f:
        weeks = json.load(f)
    for nfl_week in weeks:
        if(nfl_week['label'] == f'Week {week_number}'):
            start_dt = datetime.strptime(nfl_week["startDate"], "%Y-%m-%dT%H:%MZ")
            end_dt = datetime.strptime(nfl_week["endDate"], "%Y-%m-%dT%H:%MZ")
            current = start_dt.date()
            end_date = end_dt.date()

            while current <= end_date:
                nfl_week_days.append(current.strftime("%Y%m%d"))
                current += timedelta(days=1)

    print(nfl_week_days)
    for nfl_week_day in nfl_week_days:
        update_games_on_day(nfl_week_day)

def update_games_on_day(yyyymmdd):
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={yyyymmdd}"
    try:
        response = requests.get(url)
        data = response.json()
        for event in data['events']:
            # each game is an event
            print(f"--- {yyyymmdd} matchup on {event['competitions'][0]['date']} ---")
            iso_str = event['competitions'][0]['date']
            dt_utc = datetime.strptime(iso_str, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
            dt_naive = dt_utc.replace(tzinfo=None)

            home_team = ''
            away_team = ''
            home_score = '---'
            away_score = '---'
            for team in event['competitions'][0]['competitors']:
                if(team['homeAway'] == 'home'):
                    home_team = team['team']['displayName']
                    home_score = team['score']
                elif(team['homeAway'] == 'away'):
                    away_team = team['team']['displayName']
                    away_score = team['score']
            print(f'Home: {home_team} {home_score}')
            print(f'Away: {away_team} {away_score}')
            matching_games = games.find({
                "homeTeam": home_team,
                "awayTeam": away_team
            })
            for db_game in matching_games:
                game_date = db_game["gameTime"].date()  # extract date only
                if game_date == dt_naive.date():
                    game_data = games.find_one({
                        "gameId": db_game["gameId"]
                    })
                    print(game_data)
                    result = games.update_one(
                        {"gameId": db_game["gameId"]},
                        {"$set": {
                            "homeScore": home_score,
                            "awayScore": away_score
                        }}
                    )
                    if result.matched_count:
                        print(f"Updated game {db_game['gameId']} successfully")
                    else:
                        print(f"Failed to update game {db_game['gameId']}")
                    break
    except Exception as e:
        print(f"Could not parse ESPN NFL date for day: {yyyymmdd} : {e}")
        return False
    return True

if __name__ == '__main__':
    while True:
        get_scores_from_week(16)
        time.sleep(60)