import os
import sys

# this script is run standalone (e.g. `python odds/notify_sunday_reminder.py`), which puts
# only this file's own directory on sys.path — add the repo root so the
# top-level `bingo` package (shared Firebase setup) is importable too.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bingo.config import BingoConfig
from bingo.extensions import get_db, init_firebase

from push_sender import send_push_to_all

init_firebase(BingoConfig.FIREBASE_CREDENTIALS_PATH)


def main():
    db = get_db()
    send_push_to_all(
        db,
        title="Dave's Odds",
        body="This week's 1pm games kick off soon — get your picks in!",
        url='/odds/',
    )


if __name__ == '__main__':
    main()
