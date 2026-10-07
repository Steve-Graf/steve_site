import time
from collections import Counter
from datetime import datetime, timezone, timedelta

from flask import Blueprint, g, jsonify, request, session
from google.cloud import firestore

from bingo.extensions import get_db

from .auth import require_auth
from .live_state import derive_view, game_is_final, game_key, read_live_state
from .schedule import get_nfl_week
from .survivor_routes import _current_week_number, _games_by_id_for_survivors, _still_undefeated_users, _week_bounds

odds_bp = Blueprint('odds', __name__)

# Schedule, spreads and pick counts barely change, and live scores no longer live in
# Firestore at all (the worker publishes them to a local file), so the board only needs
# to re-read the week's docs every few minutes. Pick counts are kept current by writing
# through to this cache on every pick. Assumes a single gunicorn worker (-w 1).
WEEK_CACHE_TTL_SECONDS = 300
_week_cache = {'key': None, 'fetched_at': 0.0, 'games': {}}


def _current_week_games(db):
    """{gameId: doc dict} for the current NFL week."""
    week = get_nfl_week(target=datetime.now(timezone.utc))
    if week is None:
        return {}
    start = datetime.fromisoformat(week["startDate"].replace("Z", "+00:00")) - timedelta(hours=1)
    end = datetime.fromisoformat(week["endDate"].replace("Z", "+00:00")) + timedelta(hours=1)
    key = (start, end)
    if _week_cache['key'] != key or time.monotonic() - _week_cache['fetched_at'] > WEEK_CACHE_TTL_SECONDS:
        docs = db.collection('odds_games').where('gameTime', '>=', start).where('gameTime', '<=', end).stream()
        _week_cache.update(key=key, fetched_at=time.monotonic(), games={doc.id: doc.to_dict() for doc in docs})
    return _week_cache['games']


def _live_context():
    """(per-game rows from the live-state file, seconds since the worker last refreshed it, now)."""
    live = read_live_state()
    entries = (live or {}).get('games', {})
    updated_at = (live or {}).get('updatedAtTs')
    live_age = time.time() - updated_at if updated_at else None
    return entries, live_age, datetime.now(timezone.utc)


def _game_view(game, context=None):
    entries, live_age, now = context or _live_context()
    entry = entries.get(game_key(game.get('homeTeam'), game.get('awayTeam')))
    return derive_view(game, entry, live_age, now)


@odds_bp.route('/api/odds/sport/<sport>')
def odds(sport):
    games = _current_week_games(get_db()).values()
    context = _live_context()
    board = [{**game, **_game_view(game, context)} for game in games]
    return jsonify(sorted(board, key=lambda game: game["gameTime"]))


def _spread_coverer(game):
    """Which team covered the spread for this game — game['homeTeam'],
    game['awayTeam'], or 'Push' — or None until the game is final (a score
    mid-game isn't a result)."""
    if not game_is_final(game):
        return None
    try:
        away_points = float(game['awayScore'])
        home_points = float(game['homeScore'])
    except (KeyError, TypeError, ValueError):
        return None

    points_spread = game.get('gameSpread', 0)
    if game.get('gameSpreadTeam') == game.get('homeTeam'):
        home_points += points_spread
    elif game.get('gameSpreadTeam') == game.get('awayTeam'):
        away_points += points_spread

    if home_points > away_points:
        return game['homeTeam']
    if away_points > home_points:
        return game['awayTeam']
    return 'Push'


def _grade_ats_pick(game, pick_data):
    """Did this pick cover the spread? True/False, or None until the game is
    final. A push counts as a win for whichever team was picked."""
    spread_coverer = _spread_coverer(game)
    if spread_coverer is None:
        return None
    return spread_coverer == 'Push' or pick_data.get('selectedTeam') == spread_coverer


@odds_bp.route('/api/odds/leaderboard')
def get_leaderboard():
    db = get_db()
    current_uid = session.get('odds_user_id')

    games_by_id = {doc.id: doc.to_dict() for doc in db.collection('odds_games').stream()}

    entries = []
    for user_doc in db.collection('odds_users').stream():
        user = user_doc.to_dict()
        if user.get('isPrivate'):
            continue

        wins = 0
        losses = 0
        for pick_id, pick_data in user.get('picks', {}).items():
            game = games_by_id.get(pick_id)
            if not game:
                continue
            result = _grade_ats_pick(game, pick_data)
            if result is None:
                continue
            if result:
                wins += 1
            else:
                losses += 1

        if wins + losses == 0:
            continue

        entries.append({
            "uid": user_doc.id,
            "displayName": user.get('displayName') or 'Unnamed',
            "wins": wins,
            "losses": losses,
        })

    # ranked purely on total correct picks — no win-percentage weighting
    entries.sort(key=lambda e: (-e['wins'], e['losses']))
    for i, entry in enumerate(entries):
        entry['rank'] = i + 1
        entry['isYou'] = entry['uid'] == current_uid
        del entry['uid']

    return jsonify({"entries": entries})


def _grade_week_record(user, games_by_id):
    """(wins, losses) for every graded pick this user made against the given
    week's games — shared by the recap's "your record" and "best record"
    sections so they can't drift out of sync with each other."""
    wins = 0
    losses = 0
    for pick_id, pick_data in (user.get('picks') or {}).items():
        game = games_by_id.get(pick_id)
        if not game:
            continue
        result = _grade_ats_pick(game, pick_data)
        if result is None:
            continue
        if result:
            wins += 1
        else:
            losses += 1
    return wins, losses


@odds_bp.route('/api/odds/recap')
def get_weekly_recap():
    """A look back at the week that just ended, shown once per user right
    after the weekly reset: who had the best record last week (not
    cumulative), the biggest ATS upset, and who's still undefeated in the
    survivor pool. {"available": False} if there's no previous week yet
    (week 1) or it has no graded games (nothing to recap)."""
    current_week = _current_week_number()
    if current_week is None:
        return jsonify({"available": False})

    last_week = current_week - 1
    bounds = _week_bounds(last_week) if last_week >= 1 else None
    if not bounds:
        return jsonify({"available": False})
    start, end = bounds

    db = get_db()
    last_week_games_by_id = {
        doc.id: doc.to_dict()
        for doc in db.collection('odds_games').where('gameTime', '>=', start).where('gameTime', '<=', end).stream()
    }
    if not last_week_games_by_id:
        return jsonify({"available": False})

    users_by_id = {doc.id: doc.to_dict() for doc in db.collection('odds_users').stream()}

    # the viewer's own record — independent of the isPrivate filter below,
    # since hiding from the leaderboard shouldn't hide your own stats from you
    your_record = None
    current_uid = session.get('odds_user_id')
    if current_uid and current_uid in users_by_id:
        viewer = users_by_id[current_uid]
        wins, losses = _grade_week_record(viewer, last_week_games_by_id)
        if wins + losses > 0:
            your_record = {"name": viewer.get('displayName') or 'Unnamed', "wins": wins, "losses": losses}

    # best record last week — ranked by wins only, same philosophy as the main
    # leaderboard (no percentage weighting); losses are carried along just for
    # display, since "record" reads oddly as a bare win count
    best_wins = -1
    best_entries = []
    for user in users_by_id.values():
        if user.get('isPrivate'):
            continue
        wins, losses = _grade_week_record(user, last_week_games_by_id)
        if wins + losses == 0:
            continue
        entry = {"name": user.get('displayName') or 'Unnamed', "wins": wins, "losses": losses}
        if wins > best_wins:
            best_wins = wins
            best_entries = [entry]
        elif wins == best_wins:
            best_entries.append(entry)

    # biggest upset — fewest people correct among games that were actually picked
    # and actually resolved to a side (a push means everyone "wins", so it can
    # never be the upset)
    upset = None
    upset_game_id = None
    for game in last_week_games_by_id.values():
        coverer = _spread_coverer(game)
        if coverer is None or coverer == 'Push':
            continue
        home_picks = game.get('homePickCount', 0)
        away_picks = game.get('awayPickCount', 0)
        total_picks = home_picks + away_picks
        if total_picks == 0:
            continue
        correct_count = home_picks if coverer == game['homeTeam'] else away_picks
        if upset is None or correct_count < upset['correctCount']:
            upset = {
                "awayTeam": game['awayTeam'],
                "homeTeam": game['homeTeam'],
                "correctTeam": coverer,
                "correctCount": correct_count,
                "totalCount": total_picks,
            }
            upset_game_id = game['gameId']

    if upset is not None:
        upset['correctNames'] = sorted(
            user.get('displayName') or 'Unnamed'
            for user in users_by_id.values()
            if not user.get('isPrivate')
            and (user.get('picks') or {}).get(upset_game_id, {}).get('selectedTeam') == upset['correctTeam']
        )

    # still undefeated in survivor, as of right now (not frozen to last week)
    all_survivors = [u.get('survivor') or {} for u in users_by_id.values() if (u.get('survivor') or {}).get('picks')]
    survivor_games_by_id = _games_by_id_for_survivors(db, all_survivors)
    still_alive = _still_undefeated_users(survivor_games_by_id, users_by_id, current_week)
    survivor_names = [u.get('displayName') or 'Unnamed' for u in still_alive]

    return jsonify({
        "available": True,
        "week": last_week,
        "yourRecord": your_record,
        "bestRecord": {"entries": best_entries} if best_entries else None,
        "upset": upset,
        "survivorAlive": {"names": survivor_names, "count": len(survivor_names)},
    })


@odds_bp.route('/api/odds/game-pickers/<game_id>')
def get_game_pickers(game_id):
    db = get_db()
    game_doc = db.collection('odds_games').document(game_id).get()
    if not game_doc.exists:
        return jsonify({"error": "Game not found"}), 404
    game = game_doc.to_dict()
    current_uid = session.get('odds_user_id')

    home_team = game.get('homeTeam')
    away_team = game.get('awayTeam')
    home_pickers = []
    away_pickers = []

    for user_doc in db.collection('odds_users').stream():
        user = user_doc.to_dict()
        if user.get('isPrivate'):
            continue
        pick = user.get('picks', {}).get(game_id)
        if not pick:
            continue
        entry = {
            "displayName": user.get('displayName') or 'Unnamed',
            "isYou": user_doc.id == current_uid,
        }
        if pick.get('selectedTeam') == home_team:
            home_pickers.append(entry)
        elif pick.get('selectedTeam') == away_team:
            away_pickers.append(entry)

    home_pickers.sort(key=lambda e: e['displayName'].lower())
    away_pickers.sort(key=lambda e: e['displayName'].lower())

    return jsonify({
        "homeTeam": home_team,
        "awayTeam": away_team,
        "homeCount": game.get('homePickCount', 0),
        "awayCount": game.get('awayPickCount', 0),
        "homePickers": home_pickers,
        "awayPickers": away_pickers,
    })


@odds_bp.route('/api/odds/player/me')
@require_auth
def get_user_data():
    doc = get_db().collection('odds_users').document(g.uid).get()
    if not doc.exists:
        # shouldn't happen — the OAuth callback creates this doc before the session is set
        return jsonify({"error": "not found"}), 404
    data = doc.to_dict()
    data["hasPushSubscription"] = bool(data.pop("pushSubscription", None))
    return jsonify(data)


@odds_bp.route('/api/odds/update-profile', methods=['POST'])
@require_auth
def update_profile():
    data = request.json
    username = (data.get("username") or "").strip()
    is_private = data.get("isPrivate")

    doc_ref = get_db().collection('odds_users').document(g.uid)
    if not doc_ref.get().exists:
        return jsonify({"status": "failed", "action": "no_user_found"})

    updates = {"displayName": username, "isPrivate": bool(is_private)}
    doc_ref.update(updates)
    return jsonify({"status": "success", "action": "updated"})


def _adjust_pick_count(db, game_id, home_delta, away_delta):
    game_ref = db.collection('odds_games').document(game_id)
    game = game_ref.get()
    if not game.exists:
        return
    data = game.to_dict()
    updates = {}
    if home_delta:
        updates['homePickCount'] = max(0, data.get('homePickCount', 0) + home_delta)
    if away_delta:
        updates['awayPickCount'] = max(0, data.get('awayPickCount', 0) + away_delta)
    if updates:
        game_ref.update(updates)
        cached = _week_cache['games'].get(game_id)
        if cached is not None:
            cached.update(updates)


def _lookup_game(db, game_id):
    """The game doc: from the week cache when it's a current-week game (no read), else straight from Firestore."""
    game = _current_week_games(db).get(game_id)
    if game is not None:
        return game
    snap = db.collection('odds_games').document(game_id).get()
    return snap.to_dict() if snap.exists else None


@odds_bp.route('/api/odds/update-pick', methods=['POST'])
@require_auth
def update_pick():
    """Set, switch or clear (selectedTeam null) the caller's pick for one game."""
    data = request.json
    game_id = data["gameId"]
    selected_team = data.get("selectedTeam")

    db = get_db()
    game = _lookup_game(db, game_id)
    if game is None:
        return jsonify({"error": "Game not found"}), 404
    if _game_view(game)['state'] != 'open':
        return jsonify({"error": "This game has already started"}), 409

    home_team, away_team = game.get('homeTeam'), game.get('awayTeam')
    if selected_team is not None and selected_team not in (home_team, away_team):
        return jsonify({"error": "selectedTeam does not match either team in this game"}), 400

    user_ref = db.collection('odds_users').document(g.uid)
    user_doc = user_ref.get()
    old_pick = user_doc.to_dict().get('picks', {}).get(game_id) if user_doc.exists else None
    old_team = old_pick.get("selectedTeam") if old_pick else None

    home_delta = 0
    away_delta = 0
    if old_team != selected_team:
        for team, sign in ((old_team, -1), (selected_team, 1)):
            if team == home_team:
                home_delta += sign
            elif team == away_team:
                away_delta += sign
    if home_delta or away_delta:
        _adjust_pick_count(db, game_id, home_delta, away_delta)

    if selected_team is None:
        if old_pick:
            user_ref.update({f"picks.{game_id}": firestore.DELETE_FIELD})
    else:
        user_ref.update({f"picks.{game_id}": {
            "homeTeam": data.get("homeTeam"),
            "awayTeam": data.get("awayTeam"),
            "selectedTeam": selected_team,
            "gameSpread": data.get("gameSpread")
        }})

    return jsonify({"status": "success"})


@odds_bp.route('/api/odds/stats/me')
@require_auth
def get_user_stats():
    return get_stats(g.uid)


def get_stats(uid):
    db = get_db()
    user_doc = db.collection('odds_users').document(uid).get()
    if not user_doc.exists:
        return jsonify({"status": "failed"})
    user = user_doc.to_dict()

    total_picks = 0
    user_points = 0
    selected_teams = []
    underdog_teams = []
    underdog_winners = 0
    favored_teams = []
    favored_winners = 0
    favorite_team = ''
    favorite_team_times_picked = 0
    best_team = ''
    best_team_win_count = 0
    worst_team = ''
    worst_team_loss_count = 0

    for pick_id, pick_data in user.get('picks', {}).items():
        game_doc = db.collection('odds_games').document(pick_id).get()
        if not game_doc.exists:
            continue
        game = game_doc.to_dict()
        try:
            is_winner = _grade_ats_pick(game, pick_data)
            if is_winner is None:
                continue
            if is_winner:
                user_points += 1

            is_favorite = True
            if '+' in str(pick_data.get('gameSpread')):
                is_favorite = False

            pick_info = {
                'is_winner': is_winner,
                'selected_team': pick_data.get('selectedTeam')
            }
            if is_favorite:
                favored_teams.append(pick_info)
            else:
                underdog_teams.append(pick_info)
            selected_teams.append(pick_info)

            total_picks += 1
        except Exception:
            pass

    if total_picks > 0:
        for underdog in underdog_teams:
            if underdog['is_winner']:
                underdog_winners += 1
        for favorite in favored_teams:
            if favorite['is_winner']:
                favored_winners += 1

        selected_team_names = []
        winning_team_names = []
        losing_team_names = []
        for team in selected_teams:
            selected_team_names.append(team['selected_team'])
            if team['is_winner']:
                winning_team_names.append(team['selected_team'])
            else:
                losing_team_names.append(team['selected_team'])
        favorite_team_counts = Counter(selected_team_names)
        most_frequent_selected_team_tuple = favorite_team_counts.most_common(1)
        if most_frequent_selected_team_tuple:
            favorite_team = most_frequent_selected_team_tuple[0][0]
            favorite_team_times_picked = most_frequent_selected_team_tuple[0][1]
        best_team_counts = Counter(winning_team_names)
        best_team_tuple = best_team_counts.most_common(1)
        if best_team_tuple:
            best_team = best_team_tuple[0][0]
            best_team_win_count = best_team_tuple[0][1]
        worst_team_counts = Counter(losing_team_names)
        worst_team_tuple = worst_team_counts.most_common(1)
        if worst_team_tuple:
            worst_team = worst_team_tuple[0][0]
            worst_team_loss_count = worst_team_tuple[0][1]

        return jsonify({
            "status": "success",
            "total": total_picks,
            "wins": user_points,
            "underdog_count": len(underdog_teams),
            "underdog_wins_count": underdog_winners,
            "favored_count": len(favored_teams),
            "favored_wins_count": favored_winners,
            "favorite_team": favorite_team,
            "favorite_team_count": favorite_team_times_picked,
            "best_team": best_team,
            "best_team_win_count": best_team_win_count,
            "best_team_pick_count": selected_team_names.count(best_team),
            "worst_team": worst_team,
            "worst_team_loss_count": worst_team_loss_count,
            "worst_team_pick_count": selected_team_names.count(worst_team)
        })

    return jsonify({"status": "failed"})
