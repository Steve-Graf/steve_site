import base64
import json
import secrets

from flask import Blueprint, redirect, url_for, session, flash, request
from ..extensions import oauth
from ..services.auth_service import get_or_create_user
from ..services.mobile_auth_service import mint_mobile_token, consume_mobile_token

auth_bp = Blueprint("bingo_auth", __name__)


def _encode_state(platform=None):
    payload = {"csrf": secrets.token_urlsafe(16)}
    if platform:
        payload["platform"] = platform
    raw = json.dumps(payload).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_platform(state):
    if not state:
        return None
    padded = state + "=" * (-len(state) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()))
    except (ValueError, TypeError):
        return None
    return payload.get("platform")


@auth_bp.route("/login")
def login():
    redirect_uri = url_for("bingo_auth.callback", _external=True)
    platform = request.args.get("platform")
    return oauth.google.authorize_redirect(redirect_uri, state=_encode_state(platform))


@auth_bp.route("/callback")
def callback():
    platform = _decode_platform(request.args.get("state"))

    token = oauth.google.authorize_access_token()
    google_user = token.get("userinfo")
    if not google_user:
        flash("Authentication failed. Please try again.", "error")
        return redirect(url_for("bingo_pages.login"))
    user = get_or_create_user(google_user)

    if platform == "ios":
        mobile_token = mint_mobile_token(user["id"])
        return redirect(f"socialbingo://auth-callback?token={mobile_token}")

    session["user_id"] = user["id"]
    return redirect(url_for("bingo_pages.index"))


@auth_bp.route("/mobile-complete")
def mobile_complete():
    user_id = consume_mobile_token(request.args.get("token", ""))
    if not user_id:
        return redirect(url_for("bingo_pages.login"))

    session["user_id"] = user_id
    return redirect(url_for("bingo_pages.index"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("bingo_pages.index"))
