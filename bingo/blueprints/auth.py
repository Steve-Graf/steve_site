from flask import Blueprint, redirect, url_for, session, flash
from ..extensions import oauth
from ..services.auth_service import get_or_create_user

auth_bp = Blueprint("bingo_auth", __name__)


@auth_bp.route("/login")
def login():
    redirect_uri = url_for("bingo_auth.callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/callback")
def callback():
    token = oauth.google.authorize_access_token()
    google_user = token.get("userinfo")
    if not google_user:
        flash("Authentication failed. Please try again.", "error")
        return redirect(url_for("bingo_pages.login"))
    user = get_or_create_user(google_user)
    session["user_id"] = user["id"]
    return redirect(url_for("bingo_pages.index"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("bingo_pages.index"))
