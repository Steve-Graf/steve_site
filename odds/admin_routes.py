import hmac
from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for

from bingo.extensions import get_db

from .live_state import read_live_state
from .survivor_routes import _build_survivor_history, _current_week_number, _games_by_id_for_survivors, _week_bounds

odds_admin_bp = Blueprint('odds_admin', __name__, template_folder='templates')

# how long a worker can go without a heartbeat before the dashboard flags it as stale —
# scores_refresh's slowest normal gap is its 5-minute idle tick; odds_refresh's is 12h (Tue/Wed/Sat)
WORKER_STALE_AFTER_SECONDS = {
    'scoresRefresh': 12 * 60,
    'oddsRefresh': 16 * 3600,
}


def _humanize_ago(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    seconds = (datetime.now(timezone.utc) - dt).total_seconds()
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = int(seconds // 86400)
    return f"{days} day{'s' if days != 1 else ''} ago"


def _scores_worker_heartbeat():
    """The scores worker publishes its heartbeat in its live-state file (no Firestore write),
    shaped like an odds_meta/health entry so _worker_health can grade it the same way."""
    live = read_live_state()
    if not live or not live.get('updatedAtTs'):
        return None
    failed = live.get('errorAtTs', 0) > live['updatedAtTs']
    return {'scoresRefresh': {
        'lastRunAt': datetime.fromtimestamp(live['updatedAtTs'], tz=timezone.utc),
        'status': 'error' if failed else 'ok',
        'error': live.get('error') if failed else None,
    }}


def _worker_health(health_doc, service, label):
    service_data = (health_doc or {}).get(service)
    if not service_data or not service_data.get('lastRunAt'):
        return {"label": label, "state": "unknown", "detail": "No heartbeat recorded yet"}

    last_run = service_data['lastRunAt']
    if last_run.tzinfo is None:
        last_run = last_run.replace(tzinfo=timezone.utc)
    stale_after = WORKER_STALE_AFTER_SECONDS[service]
    age_seconds = (datetime.now(timezone.utc) - last_run).total_seconds()

    if service_data.get('status') == 'error':
        state = 'error'
    elif age_seconds > stale_after:
        state = 'stale'
    else:
        state = 'ok'

    return {
        "label": label,
        "state": state,
        "detail": f"Last run {_humanize_ago(last_run)}",
        "error": service_data.get('error'),
    }


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('odds_admin'):
            return redirect(url_for('odds_admin.admin_login'))
        return f(*args, **kwargs)
    return decorated


@odds_admin_bp.route('/odds/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('odds_admin'):
        return redirect(url_for('odds_admin.admin_dashboard'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        valid = (
            hmac.compare_digest(username, current_app.config['ODDS_ADMIN_USERNAME'])
            and hmac.compare_digest(password, current_app.config['ODDS_ADMIN_PASSWORD'])
        )
        if valid:
            session['odds_admin'] = True
            session.permanent = True
            return redirect(url_for('odds_admin.admin_dashboard'))
        error = 'Incorrect username or password.'

    return render_template('odds_admin/login.html', error=error)


@odds_admin_bp.route('/odds/admin/logout')
def admin_logout():
    session.pop('odds_admin', None)
    return redirect(url_for('odds_admin.admin_login'))


@odds_admin_bp.route('/odds/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    current_week = _current_week_number()

    week_games = []
    if current_week is not None:
        bounds = _week_bounds(current_week)
        if bounds:
            start, end = bounds
            docs = (
                db.collection('odds_games')
                .where('gameTime', '>=', start)
                .where('gameTime', '<=', end)
                .stream()
            )
            week_games = sorted((doc.to_dict() for doc in docs), key=lambda g: g['gameTime'])

    week_game_ids = {g['gameId'] for g in week_games}

    all_users = [doc.to_dict() for doc in db.collection('odds_users').stream()]
    all_survivors = [u.get('survivor') or {} for u in all_users if (u.get('survivor') or {}).get('picks')]
    all_games_by_id = _games_by_id_for_survivors(db, all_survivors)

    total_users = len(all_users)
    weekly_pickers = 0
    total_picks_ever = 0
    survivor_joined = 0
    survivor_this_week = 0
    survivor_wins = 0
    survivor_losses = 0

    survivor_standings = []

    for user in all_users:
        picks = user.get('picks') or {}
        total_picks_ever += len(picks)
        if week_game_ids & picks.keys():
            weekly_pickers += 1

        survivor = user.get('survivor') or {}
        survivor_picks = survivor.get('picks') or {}
        if survivor_picks:
            survivor_joined += 1
            if current_week is not None:
                if str(current_week) in survivor_picks:
                    survivor_this_week += 1
                history = _build_survivor_history(all_games_by_id, survivor, current_week)
                wins = 0
                losses = 0
                for entry in history:
                    if entry['outcome'] == 'win':
                        wins += 1
                        survivor_wins += 1
                    elif entry['outcome'] in ('loss', 'missed'):
                        losses += 1
                        survivor_losses += 1
                current_pick = survivor_picks.get(str(current_week)) if current_week is not None else None
                survivor_standings.append({
                    "displayName": user.get('displayName') or 'Unnamed',
                    "wins": wins,
                    "losses": losses,
                    "current_pick": current_pick.get('selectedTeam') if current_pick else None,
                })

    survivor_standings.sort(key=lambda r: (-r['wins'], r['losses']))

    week_games_view = [
        {
            "matchup": f"{g['awayTeam']} @ {g['homeTeam']}",
            "away_picks": g.get('awayPickCount', 0),
            "home_picks": g.get('homePickCount', 0),
            "total_picks": g.get('awayPickCount', 0) + g.get('homePickCount', 0),
        }
        for g in week_games
    ]

    health_doc = db.collection('odds_meta').document('health').get()
    health_data = health_doc.to_dict() if health_doc.exists else None
    worker_health = [
        _worker_health(_scores_worker_heartbeat(), 'scoresRefresh', 'Live scores (scores_refresh)'),
        _worker_health(health_data, 'oddsRefresh', 'Spreads/odds (odds_refresh)'),
    ]

    return render_template(
        'odds_admin/dashboard.html',
        worker_health=worker_health,
        current_week=current_week,
        total_users=total_users,
        weekly_pickers=weekly_pickers,
        total_picks_ever=total_picks_ever,
        week_games=week_games_view,
        survivor_joined=survivor_joined,
        survivor_this_week=survivor_this_week,
        survivor_wins=survivor_wins,
        survivor_losses=survivor_losses,
        survivor_standings=survivor_standings,
    )
