import os
import sys

from firebase_admin import firestore

# this script is run standalone (e.g. `python odds/trend_update.py`), which puts
# only this file's own directory on sys.path — add the repo root so the
# top-level `bingo` package (shared Firebase setup) is importable too.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bingo.config import BingoConfig
from bingo.extensions import get_db, init_firebase

init_firebase(BingoConfig.FIREBASE_CREDENTIALS_PATH)
db = get_db()
users_ref = db.collection('odds_users')
games_ref = db.collection('odds_games')


if __name__ == '__main__':
    for game_doc in games_ref.stream():
        game_doc.reference.update({"homePickCount": 0, "awayPickCount": 0})

    for user_doc in users_ref.stream():
        user = user_doc.to_dict()
        picks = user.get('picks') or {}
        if not picks or user.get('displayName', 'Unnamed') == 'Unnamed':
            continue

        print(f"uid={user.get('uid')} | name={user.get('displayName')}")
        for pick_id, pick_data in picks.items():
            game_doc = games_ref.document(pick_id).get()
            if not game_doc.exists:
                continue
            game = game_doc.to_dict()
            try:
                print(f"{pick_id} -- {pick_data.get('selectedTeam')}")
                print(f"Home: {game['homeTeam']} {game['homeScore']}")
                print(f"Away: {game['awayTeam']} {game['awayScore']}")
                if pick_data["selectedTeam"] == pick_data["homeTeam"]:
                    print("Increase count for home team")
                    games_ref.document(pick_id).update({"homePickCount": firestore.Increment(1)})
                elif pick_data["selectedTeam"] == pick_data["awayTeam"]:
                    print("Increase count for away team")
                    games_ref.document(pick_id).update({"awayPickCount": firestore.Increment(1)})
            except Exception:
                pass
    exit()
