from pymongo import MongoClient
import time
import json
from datetime import datetime, timezone

client = MongoClient("mongodb://localhost:27017/")
db = client["mydb"]
users = db["users"]
users.create_index("playerCode", unique=True)
games = db["games"]
games.create_index("gameId", unique=True)


if __name__ == '__main__':
    games.update_many(
        {},
        {
            "$set": {
                "homePickCount": 0,
                "awayPickCount": 0
            }
        }
    )

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
        for pick_id, pick_data in user.get('picks', {}).items():
            game = games.find_one({
                "gameId": pick_id
            })
            try:
                print(f"{pick_id} -- {pick_data.get('selectedTeam')}")
                print(f'Home: {game['homeTeam']} {game['homeScore']}')
                print(f'Away: {game['awayTeam']} {game['awayScore']}')
                if pick_data["selectedTeam"] == pick_data["homeTeam"]:
                    print(f"Increase count for home team")
                    games.update_one(
                        {"gameId": pick_id},
                        {"$inc": {"homePickCount": 1}}
                    )
                elif pick_data["selectedTeam"] == pick_data["awayTeam"]:
                    print(f"Increase count for away team")
                    games.update_one(
                        {"gameId": pick_id},
                        {"$inc": {"awayPickCount": 1}}
                    )
            except Exception as e:
                pass
    exit()