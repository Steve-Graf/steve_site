import os
import sys
from datetime import datetime, timezone

# this script is run standalone (e.g. `python odds/notify_week_reset.py`), which puts
# only this file's own directory on sys.path — add the repo root so the
# top-level `bingo` package (shared Firebase setup) is importable too.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bingo.config import BingoConfig
from bingo.extensions import get_db, init_firebase

from push_sender import send_push_to_all
from schedule import get_nfl_week

init_firebase(BingoConfig.FIREBASE_CREDENTIALS_PATH)


def main():
    db = get_db()
    week = get_nfl_week(datetime.now(timezone.utc))
    if week is None:
        print("No active NFL week right now, skipping")
        return

    meta_ref = db.collection('odds_meta').document('notifications')
    meta = meta_ref.get()
    last_notified = meta.to_dict().get('lastWeekNotified') if meta.exists else None

    if last_notified == week['value']:
        print(f"Already notified for week {week['value']}, skipping")
        return

    send_push_to_all(
        db,
        title="Dave's Odds",
        body=f"{week['label']} is up — new spreads are in!",
        url='/odds/',
    )
    meta_ref.set({'lastWeekNotified': week['value']}, merge=True)


if __name__ == '__main__':
    main()
