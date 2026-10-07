import os
import sys
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

# this script is run standalone (e.g. `python odds/scores_refresh.py`), which puts
# only this file's own directory on sys.path — add the repo root so the
# top-level `bingo` package (shared Firebase setup) is importable too.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bingo.config import BingoConfig
from bingo.extensions import get_db, init_firebase

from live_state import STATE_PATH, game_key, parse_espn_week, read_live_state, write_live_state

SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

# ESPN's ?dates= param buckets games by the US Eastern calendar day, not the UTC day —
# only used for the catch-up path below; the normal call has no date at all.
ESPN_SCHEDULE_TZ = ZoneInfo("America/New_York")

LIVE_INTERVAL = 20    # seconds between ESPN calls while any game is in progress
SOON_INTERVAL = 60    # within 30 minutes of a kickoff (or past it and not started yet)
IDLE_INTERVAL = 300
ERROR_INTERVAL = 30
SOON_WINDOW = timedelta(minutes=30)

CATCH_UP_AFTER = timedelta(hours=5)    # a game this long past kickoff should be final
CATCH_UP_EVERY = 30 * 60
RESEED_MIN_GAP = 15 * 60
SEED_LOOKBACK = timedelta(days=10)
SEED_LOOKAHEAD = timedelta(days=8)


def _aware(dt):
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def fetch_scoreboard(yyyymmdd=None):
    """Parsed games from ESPN. With no date this is the whole current NFL week in a single call."""
    params = {'dates': yyyymmdd} if yyyymmdd else None
    response = requests.get(SCOREBOARD_URL, params=params, timeout=15)
    response.raise_for_status()
    return parse_espn_week(response.json())


def seed_known(db):
    """{game_key: {ref, gameTime, finalized}} for games around now — one small range read."""
    now = datetime.now(timezone.utc)
    docs = (
        db.collection('odds_games')
        .where('gameTime', '>=', now - SEED_LOOKBACK)
        .where('gameTime', '<=', now + SEED_LOOKAHEAD)
        .stream()
    )
    known = {}
    for doc in docs:
        game = doc.to_dict()
        known[game_key(game.get('homeTeam'), game.get('awayTeam'))] = {
            'ref': doc.reference,
            'gameTime': _aware(game.get('gameTime')),
            'finalized': game.get('status') == 'final',
        }
    return known


def finalize_completed(games, known):
    """The only Firestore write this worker does: once per game, when it's actually over."""
    for key, game in games.items():
        entry = known.get(key)
        if game['state'] != 'post' or not entry or entry['finalized']:
            continue
        if game['homeScore'] is None or game['awayScore'] is None:
            continue
        # scores are stored as strings across the collection
        entry['ref'].update({
            'status': 'final',
            'homeScore': str(game['homeScore']),
            'awayScore': str(game['awayScore']),
        })
        entry['finalized'] = True
        print(f"Finalized {key}: {game['awayScore']}-{game['homeScore']}")


def catch_up(known, games, state):
    """A game can fall off ESPN's current-week view before we recorded its final (worker was down
    over a weekend). Look those up by date, at most once per CATCH_UP_EVERY. Games still visible in
    the current week are left to the normal path, so a postponed game doesn't trigger this."""
    cutoff = datetime.now(timezone.utc) - CATCH_UP_AFTER
    overdue = [
        key for key, entry in known.items()
        if not entry['finalized'] and entry['gameTime'] and entry['gameTime'] < cutoff and key not in games
    ]
    if not overdue or time.time() - state['last_catch_up'] < CATCH_UP_EVERY:
        return
    state['last_catch_up'] = time.time()
    dates = {known[key]['gameTime'].astimezone(ESPN_SCHEDULE_TZ).strftime('%Y%m%d') for key in overdue}
    for date in sorted(dates):
        finalize_completed(fetch_scoreboard(date), known)


def next_interval(games):
    if any(g['state'] == 'in' for g in games.values()):
        return LIVE_INTERVAL
    now = datetime.now(timezone.utc)
    for game in games.values():
        if game['state'] != 'pre' or not game['startTime'] or game['clock'] in ('Postponed', 'Canceled'):
            continue
        start = datetime.fromisoformat(game['startTime'].replace('Z', '+00:00'))
        if start - SOON_WINDOW <= now:
            return SOON_INTERVAL
    return IDLE_INTERVAL


def record_error(error):
    """Keep the last good games in the file, just flag the failure so the admin page can show it."""
    try:
        payload = dict(read_live_state(STATE_PATH) or {'games': {}})
        payload['error'] = str(error)
        payload['errorAtTs'] = time.time()
        write_live_state(payload)
    except Exception as e:
        print(f"Could not record error state: {e}")


def run():
    db = get_db()
    known = {}
    seeded_at = 0.0
    state = {'last_catch_up': 0.0}
    while True:
        interval = ERROR_INTERVAL
        try:
            games = fetch_scoreboard()
            now_ts = time.time()
            write_live_state({
                'updatedAt': datetime.now(timezone.utc).isoformat(),
                'updatedAtTs': now_ts,
                'games': games,
            })
            interval = next_interval(games)

            unmapped_final = any(g['state'] == 'post' and key not in known for key, g in games.items())
            if not known or (unmapped_final and now_ts - seeded_at > RESEED_MIN_GAP):
                known = seed_known(db)
                seeded_at = now_ts
            finalize_completed(games, known)
            catch_up(known, games, state)
        except Exception as e:
            print(f"Tick failed: {e}")
            record_error(e)
        time.sleep(interval)


if __name__ == '__main__':
    init_firebase(BingoConfig.FIREBASE_CREDENTIALS_PATH)
    run()
