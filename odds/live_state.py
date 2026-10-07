"""Live game state shared by the ESPN worker (writes it) and the Flask API (reads it).

Stdlib-only on purpose: the worker runs standalone with this directory on
sys.path, while Flask imports it as part of the `odds` package.
"""
import json
import os
import tempfile
from datetime import timezone

STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'live_state.json')

# a live game's clock is dropped if the worker hasn't refreshed the file in this long
STALE_LIVE_SECONDS = 180


def game_key(home_team, away_team):
    return f"{home_team}|{away_team}"


def to_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def game_is_final(game):
    return game.get('status') == 'final'


def _aware(dt):
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _period_label(period):
    return f"Q{period}" if 1 <= period <= 4 else "OT"


def clock_text(status):
    """Short text for the LIVE chip, from ESPN's structured status. None when there's nothing to say."""
    stype = status.get('type') or {}
    name = stype.get('name', '')
    if name == 'STATUS_POSTPONED':
        return 'Postponed'
    if name == 'STATUS_CANCELED':
        return 'Canceled'
    if name in ('STATUS_DELAYED', 'STATUS_SUSPENDED', 'STATUS_RAIN_DELAY'):
        return 'Delayed'
    if stype.get('state') != 'in':
        return None
    period = status.get('period') or 0
    if name == 'STATUS_HALFTIME':
        return 'Halftime'
    if name == 'STATUS_END_PERIOD':
        return f"End of {_period_label(period)}"
    clock = status.get('displayClock')
    return f"{_period_label(period)} {clock}" if clock else _period_label(period)


def parse_espn_week(data):
    """{game_key: {homeTeam, awayTeam, state, clock, homeScore, awayScore, startTime}} from an
    ESPN scoreboard response. state is 'pre' | 'in' | 'post'; 'post' means actually completed, so a
    postponed or canceled game (which ESPN files under post without completed) stays 'pre'."""
    games = {}
    for event in data.get('events', []):
        competitions = event.get('competitions') or []
        if not competitions:
            continue
        comp = competitions[0]
        sides = {c.get('homeAway'): c for c in comp.get('competitors', [])}
        home, away = sides.get('home'), sides.get('away')
        if not home or not away:
            continue
        status = comp.get('status') or {}
        stype = status.get('type') or {}
        if stype.get('state') == 'post' and stype.get('completed'):
            state = 'post'
        elif stype.get('state') == 'in':
            state = 'in'
        else:
            state = 'pre'
        has_score = state in ('in', 'post')
        home_name = home['team']['displayName']
        away_name = away['team']['displayName']
        games[game_key(home_name, away_name)] = {
            'homeTeam': home_name,
            'awayTeam': away_name,
            'state': state,
            'clock': clock_text(status),
            'homeScore': to_int(home.get('score')) if has_score else None,
            'awayScore': to_int(away.get('score')) if has_score else None,
            'startTime': event.get('date'),
        }
    return games


def write_live_state(payload, path=STATE_PATH):
    """Atomic replace, so a reader never sees a half-written file."""
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix='.live_state.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(payload, f)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


_cache = {'sig': None, 'data': None}


def read_live_state(path=STATE_PATH):
    """The parsed file, or None if it doesn't exist. Re-parsed only when the file actually changed."""
    try:
        st = os.stat(path)
    except FileNotFoundError:
        return None
    sig = (path, st.st_ino, st.st_mtime_ns, st.st_size)
    if _cache['sig'] != sig:
        try:
            with open(path) as f:
                _cache['data'] = json.load(f)
            _cache['sig'] = sig
        except (OSError, ValueError):
            return _cache['data']
    return _cache['data']


def derive_view(game, entry, live_age, now):
    """What the board should show for one game.

    game: the Firestore doc (schedule, spread, durable final result)
    entry: this game's row from the live-state file, or None
    live_age: seconds since the worker last refreshed the file, or None
    Returns {'state': 'open'|'live'|'final'|'postponed', 'clock', 'homeScore', 'awayScore'}.
    """
    if entry and entry.get('state') == 'post':
        return {'state': 'final', 'clock': None, 'homeScore': entry.get('homeScore'), 'awayScore': entry.get('awayScore')}
    if game_is_final(game):
        return {'state': 'final', 'clock': None, 'homeScore': to_int(game.get('homeScore')), 'awayScore': to_int(game.get('awayScore'))}

    clock = entry.get('clock') if entry else None
    if clock in ('Postponed', 'Canceled'):
        return {'state': 'postponed', 'clock': clock, 'homeScore': None, 'awayScore': None}

    game_time = _aware(game.get('gameTime'))
    kicked_off = game_time is not None and game_time <= now
    if (entry and entry.get('state') == 'in') or kicked_off:
        if entry and entry.get('state') == 'in' and live_age is not None and live_age > STALE_LIVE_SECONDS:
            clock = None
        return {
            'state': 'live',
            'clock': clock,
            'homeScore': entry.get('homeScore') if entry else to_int(game.get('homeScore')),
            'awayScore': entry.get('awayScore') if entry else to_int(game.get('awayScore')),
        }
    return {'state': 'open', 'clock': None, 'homeScore': None, 'awayScore': None}
