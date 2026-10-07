from datetime import datetime, timedelta, timezone

from flask import Blueprint, g, jsonify, request

from bingo.extensions import get_db

from .auth import require_auth
from .live_state import game_is_final
from .schedule import get_nfl_week, load_weeks

odds_survivor_bp = Blueprint('odds_survivor', __name__)


def _current_week_number():
    week = get_nfl_week(datetime.now(timezone.utc))
    return int(week['value']) if week else None


def _week_bounds(week_number):
    weeks = load_weeks()
    week_info = next((w for w in weeks if w.get('value') == str(week_number)), None)
    if not week_info:
        return None
    start = datetime.fromisoformat(week_info['startDate'].replace('Z', '+00:00')) - timedelta(hours=1)
    end = datetime.fromisoformat(week_info['endDate'].replace('Z', '+00:00')) + timedelta(hours=1)
    return start, end


def _aware(dt):
    if dt and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _game_has_started(game):
    game_time = _aware(game.get('gameTime'))
    if not game_time:
        return False
    return game_time <= datetime.now(timezone.utc)


def _straight_up_winner(game):
    if not game_is_final(game):
        return None  # a score mid-game isn't a result
    try:
        home_score = float(game['homeScore'])
        away_score = float(game['awayScore'])
    except (KeyError, TypeError, ValueError):
        return None
    if home_score > away_score:
        return game['homeTeam']
    if away_score > home_score:
        return game['awayTeam']
    return 'tie'


def _season_start_week():
    weeks = load_weeks()
    return int(weeks[0]['value']) if weeks else 1


def _build_survivor_history(games_by_id, survivor, current_week):
    """Every week from the start of the season through the current week — this
    is a running record, not an elimination bracket: a loss or a missed week
    just gets logged and play continues (the only permanent rule is a team
    can never be picked again). Joining after week 1 counts the skipped weeks
    as missed too, same as anyone who joined on time and then sat one out —
    the pool doesn't grade you easier for starting late. Returns a list of
    {week, outcome, ...}.

    Takes a pre-fetched {gameId: game_dict} map rather than reading games one
    at a time — this gets called per-user from admin/still-undefeated loops
    over every participant, and re-querying the same (often shared, popular)
    game once per user was the read-cost bug that prompted this refactor."""
    picks = survivor.get('picks', {})
    if not picks:
        return []

    first_week = _season_start_week()
    history = []

    week = first_week
    while week <= current_week:
        pick = picks.get(str(week))
        if pick:
            outcome = 'pending'
            game = games_by_id.get(pick['gameId'])
            if game:
                winner = _straight_up_winner(game)
                if winner is not None:
                    outcome = 'win' if winner == pick['selectedTeam'] else 'loss'
            history.append({
                "week": week,
                "gameId": pick['gameId'],
                "homeTeam": pick.get('homeTeam'),
                "awayTeam": pick.get('awayTeam'),
                "selectedTeam": pick['selectedTeam'],
                "outcome": outcome,
            })
        elif week < current_week:
            # week is fully in the past (current_week already moved on) and no pick was made
            history.append({
                "week": week, "gameId": None, "homeTeam": None,
                "awayTeam": None, "selectedTeam": None, "outcome": "missed",
            })
        week += 1

    return history


def _games_by_id_for_survivors(db, survivors):
    """Batch-fetch (via get_all — one round trip, not one .get() per pick,
    and not the entire season-long odds_games collection either) just the
    specific games referenced across the given survivor dicts. odds_games
    holds the whole season (populated weeks ahead of time), so it's much
    larger than what any one survivor-state request actually needs — and
    picks cluster heavily on popular teams, so the unique-game set is far
    smaller than the raw pick count too."""
    unique_game_ids = {
        pick['gameId']
        for survivor in survivors
        for pick in (survivor.get('picks') or {}).values()
        if pick.get('gameId')
    }
    if not unique_game_ids:
        return {}
    refs = [db.collection('odds_games').document(gid) for gid in unique_game_ids]
    return {snap.id: snap.to_dict() for snap in db.get_all(refs) if snap.exists}


def _still_undefeated_users(games_by_id, users_by_id, current_week):
    """(Non-private) participants who have never taken a loss or missed a
    week — the closest honest equivalent to 'still alive' in a pool where
    losing never actually eliminates anyone. Returns the full user dicts."""
    result = []
    for user in users_by_id.values():
        if user.get('isPrivate'):
            continue
        survivor = user.get('survivor') or {}
        if not survivor.get('picks'):
            continue
        history = _build_survivor_history(games_by_id, survivor, current_week)
        if any(entry['outcome'] in ('loss', 'missed') for entry in history):
            continue
        result.append(user)
    return result


def _count_still_undefeated(games_by_id, users_by_id, current_week):
    """How many (non-private) participants have never taken a loss or missed
    week — the closest honest equivalent to 'still alive' in a pool where
    losing never actually eliminates anyone."""
    return len(_still_undefeated_users(games_by_id, users_by_id, current_week))


@odds_survivor_bp.route('/api/odds/survivor/state')
@require_auth
def get_survivor_state():
    db = get_db()
    current_week = _current_week_number()
    if current_week is None:
        return jsonify({"error": "No active NFL week"}), 400

    users_by_id = {doc.id: doc.to_dict() for doc in db.collection('odds_users').stream()}
    survivor = (users_by_id.get(g.uid) or {}).get('survivor', {})
    picks = survivor.get('picks', {})

    all_survivors = [u.get('survivor') or {} for u in users_by_id.values() if (u.get('survivor') or {}).get('picks')]
    games_by_id = _games_by_id_for_survivors(db, all_survivors)

    history = _build_survivor_history(games_by_id, survivor, current_week)
    used_teams = sorted({p['selectedTeam'] for w, p in picks.items() if int(w) < current_week})
    still_undefeated = _count_still_undefeated(games_by_id, users_by_id, current_week)

    return jsonify({
        "currentWeek": current_week,
        "currentPick": picks.get(str(current_week)),
        "usedTeams": used_teams,
        "history": history,
        "stillUndefeated": still_undefeated,
    })


@odds_survivor_bp.route('/api/odds/survivor/pick', methods=['POST'])
@require_auth
def submit_survivor_pick():
    data = request.json
    game_id = data.get('gameId')
    selected_team = data.get('selectedTeam')
    if not game_id or not selected_team:
        return jsonify({"error": "gameId and selectedTeam are required"}), 400

    db = get_db()
    current_week = _current_week_number()
    if current_week is None:
        return jsonify({"error": "No active NFL week"}), 400

    game_doc = db.collection('odds_games').document(game_id).get()
    if not game_doc.exists:
        return jsonify({"error": "Game not found"}), 404
    game = game_doc.to_dict()
    if selected_team not in (game.get('homeTeam'), game.get('awayTeam')):
        return jsonify({"error": "selectedTeam does not match either team in this game"}), 400

    bounds = _week_bounds(current_week)
    game_time = game.get('gameTime')
    if bounds and game_time and not (bounds[0] <= game_time <= bounds[1]):
        return jsonify({"error": "This game is not part of the current week"}), 400

    if _game_has_started(game):
        return jsonify({"error": "This game has already started"}), 400

    user_ref = db.collection('odds_users').document(g.uid)
    user_doc = user_ref.get()
    survivor = (user_doc.to_dict() or {}).get('survivor', {}) if user_doc.exists else {}
    picks = survivor.get('picks', {})

    current_pick = picks.get(str(current_week))
    if current_pick:
        current_pick_game_doc = db.collection('odds_games').document(current_pick['gameId']).get()
        if current_pick_game_doc.exists and _game_has_started(current_pick_game_doc.to_dict()):
            return jsonify({"error": "You can't change your pick — the game you selected has already started"}), 400

    used_teams = {p['selectedTeam'] for w, p in picks.items() if int(w) < current_week}
    if selected_team in used_teams:
        return jsonify({"error": f"You've already used {selected_team} in a previous week"}), 400

    user_ref.update({
        f"survivor.picks.{current_week}": {
            "gameId": game_id,
            "homeTeam": game.get('homeTeam'),
            "awayTeam": game.get('awayTeam'),
            "selectedTeam": selected_team,
        }
    })

    return jsonify({"status": "success"})
