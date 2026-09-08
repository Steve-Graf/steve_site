import secrets
from datetime import datetime, timedelta, timezone

from firebase_admin import firestore

from ..extensions import get_db

TOKEN_TTL_SECONDS = 90


def mint_mobile_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    get_db().collection("mobile_login_tokens").document(token).set({
        "user_id": user_id,
        "expires_at": datetime.now(timezone.utc) + timedelta(seconds=TOKEN_TTL_SECONDS),
    })
    return token


@firestore.transactional
def _consume_mobile_token_txn(transaction, token_ref):
    snapshot = token_ref.get(transaction=transaction)
    if not snapshot.exists:
        return None

    data = snapshot.to_dict()
    transaction.delete(token_ref)

    expires_at = data.get("expires_at")
    if expires_at is None or expires_at < datetime.now(timezone.utc):
        return None
    return data.get("user_id")


def consume_mobile_token(token: str):
    if not token:
        return None
    db = get_db()
    token_ref = db.collection("mobile_login_tokens").document(token)
    return _consume_mobile_token_txn(db.transaction(), token_ref)
