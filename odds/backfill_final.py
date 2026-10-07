"""One-time backfill: mark games that were already completed before the `status` field existed.

Grading now only counts games with status == 'final', so every old game that has a score
needs the flag or it would drop out of the leaderboard, stats and survivor history.

Dry run by default. Pass --apply to write. Safe to re-run (it skips games already marked).

    python odds/backfill_final.py            # list what would change
    python odds/backfill_final.py --apply    # write status='final'
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bingo.config import BingoConfig
from bingo.extensions import get_db, init_firebase

# a game this long past kickoff with a score is finished (the longest NFL games run ~4h)
FINISHED_AFTER = timedelta(hours=5)


def main(apply):
    init_firebase(BingoConfig.FIREBASE_CREDENTIALS_PATH)
    db = get_db()
    cutoff = datetime.now(timezone.utc) - FINISHED_AFTER

    to_mark = []
    skipped = []
    for doc in db.collection('odds_games').stream():
        game = doc.to_dict()
        if game.get('status') == 'final' or game.get('homeScore') is None or game.get('awayScore') is None:
            continue
        game_time = game.get('gameTime')
        if game_time.tzinfo is None:
            game_time = game_time.replace(tzinfo=timezone.utc)
        label = f"{game.get('awayTeam')} @ {game.get('homeTeam')} ({game_time:%Y-%m-%d}) {game['awayScore']}-{game['homeScore']}"
        (to_mark if game_time < cutoff else skipped).append((doc.reference, label))

    print(f"{len(to_mark)} completed game(s) to mark final:")
    for _, label in to_mark:
        print("  ", label)
    if skipped:
        print(f"{len(skipped)} scored game(s) too recent to treat as finished (left alone):")
        for _, label in skipped:
            print("  ", label)

    if not apply:
        print("\nDry run — nothing written. Re-run with --apply to write.")
        return
    for ref, _ in to_mark:
        ref.update({'status': 'final'})
    print(f"\nMarked {len(to_mark)} game(s) final.")


if __name__ == '__main__':
    main('--apply' in sys.argv)
