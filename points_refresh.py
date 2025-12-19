from pymongo import MongoClient
import time
import json

client = MongoClient("mongodb://localhost:27017/")
db = client["mydb"]
users = db["users"]
users.create_index("playerCode", unique=True)
games = db["games"]
games.create_index("gameId", unique=True)


if __name__ == '__main__':
    # cursor = games.find()
    # for game in cursor:
    #     print(game)

    cursor = users.find({
        "picks": {
            "$exists": True,
            "$type": "object",
            "$ne": {}
        },
        "name": {
            "$exists": True,
            "$type": "string",
            "$ne": "Unnamed"
        }
    })
    for user in cursor:
        print(
            f"playerCode={user.get('playerCode')} | "
            f"name={user.get('name')}"
        )
        user_points = 0
        total_picks = 0
        for pick_id, pick_data in user.get('picks', {}).items():
            # print(f"{pick_id} -- {pick_data.get('selectedTeam')}")
            game = games.find_one({
                "gameId": pick_id
            })
            try:
                away_points = float(game['awayScore'])
                home_points = float(game['homeScore'])
                # print(f'Home: {game['homeTeam']} {game['homeScore']}')
                # print(f'Away: {game['awayTeam']} {game['awayScore']}')
                points_spread = game['gameSpread']
                if(game['gameSpreadTeam'] == game['homeTeam']):
                    home_points += points_spread
                elif(game['gameSpreadTeam'] == game['awayTeam']):
                    away_points += points_spread
                spread_coverer = 'Push'
                if home_points > away_points:
                    spread_coverer = game['homeTeam']
                elif(away_points > home_points):
                    spread_coverer = game['awayTeam']
                # print(f'Spread team:{game['gameSpreadTeam']}, points:{game['gameSpread']}, bet winner:{spread_coverer}')
                if(pick_data.get('selectedTeam') == spread_coverer):
                    user_points += 1
                total_picks += 1
            except Exception as e:
                # print(f'Could not find data for game: {e}')
                pass
        print(f"User's points:{user_points}")
        print(f"Total picks:{total_picks}")
    exit()

    while True:
        # get a list of users that have data
        cursor = users.find({
            "picks": {
                "$exists": True,
                "$type": "object",
                "$ne": {}
            },
            "name": {
                "$exists": True,
                "$type": "string",
                "$ne": "Unnamed"
            }
        })
        for user in cursor:
            print(
                f"playerCode={user.get('playerCode')} | "
                f"name={user.get('name')}"
            )
        time.sleep(20)