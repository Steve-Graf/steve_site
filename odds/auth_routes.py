from datetime import datetime, timezone

from flask import Blueprint, redirect, session, url_for

from bingo.extensions import get_db, oauth

odds_auth_bp = Blueprint('odds_auth', __name__)


def _get_or_create_user(google_user):
    db = get_db()
    uid = google_user["sub"]
    ref = db.collection('odds_users').document(uid)
    doc = ref.get()
    data = {
        "uid": uid,
        "email": google_user["email"],
        "displayName": google_user.get("name", "Unnamed").strip(),
        "photoURL": google_user.get("picture"),
    }
    if doc.exists:
        ref.update(data)
    else:
        ref.set({**data, "createdAt": datetime.now(timezone.utc), "picks": {}})
    return uid


@odds_auth_bp.route('/api/odds/auth/login')
def login():
    redirect_uri = url_for('odds_auth.callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@odds_auth_bp.route('/api/odds/auth/callback')
def callback():
    token = oauth.google.authorize_access_token()
    google_user = token.get('userinfo')
    if google_user:
        session.permanent = True
        session['odds_user_id'] = _get_or_create_user(google_user)
    return redirect('/odds/')


@odds_auth_bp.route('/api/odds/auth/logout')
def logout():
    session.pop('odds_user_id', None)
    return redirect('/odds/')
