import json

from google.cloud import firestore
from pywebpush import WebPushException, webpush

# sibling-module import, not package-relative — this file is used by the
# standalone notify_*.py scripts (run directly, not through the Flask app),
# which put this file's own directory (odds/) on sys.path, same as keys.py
import keys


def send_push_to_all(db, title, body, url='/odds/'):
    """Send a Web Push notification to every odds_users doc with a stored
    subscription. Expired/gone subscriptions (404/410 from the push service)
    are deleted so they stop being retried every week; any other per-user
    failure is logged and skipped rather than aborting the whole batch."""
    sent = 0
    for doc in db.collection('odds_users').stream():
        user = doc.to_dict()
        subscription = user.get('pushSubscription')
        if not subscription:
            continue
        try:
            webpush(
                subscription_info=subscription,
                data=json.dumps({"title": title, "body": body, "url": url}),
                vapid_private_key=keys.vapid_private_key,
                vapid_claims={"sub": keys.vapid_claim_email},
            )
            sent += 1
        except WebPushException as e:
            status_code = e.response.status_code if e.response is not None else None
            if status_code in (404, 410):
                print(f"Subscription for user {doc.id} is gone ({status_code}), removing it")
                doc.reference.update({'pushSubscription': firestore.DELETE_FIELD})
            else:
                print(f"Push failed for user {doc.id}: {e}")
    print(f"Sent push notification to {sent} subscriber(s): {title!r}")
    return sent
