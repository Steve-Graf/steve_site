from functools import wraps

from flask import g, jsonify, session


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        uid = session.get("odds_user_id")
        if not uid:
            return jsonify({"error": "unauthorized"}), 401
        g.uid = uid
        return f(*args, **kwargs)

    return wrapper
