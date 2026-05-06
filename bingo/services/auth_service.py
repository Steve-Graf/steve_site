from datetime import datetime, timezone
from ..extensions import get_db


def get_or_create_user(google_user: dict) -> dict:
    db = get_db()
    uid = google_user["sub"]
    ref = db.collection("users").document(uid)
    doc = ref.get()
    data = {
        "email": google_user["email"],
        "name": google_user["name"],
        "avatar_url": google_user.get("picture"),
    }
    if doc.exists:
        ref.update(data)
    else:
        ref.set({**data, "created_at": datetime.now(timezone.utc)})
    return {"id": uid, **data}
