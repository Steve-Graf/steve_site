from datetime import datetime, timezone


def record_heartbeat(db, service, status='ok', error=None):
    """Record a single heartbeat for a background worker (scores_refresh,
    odds_refresh) so the admin dashboard can show whether it's still alive
    and ticking — every call fully replaces that service's nested map, so
    `error` always reflects only the most recent run, not history."""
    db.collection('odds_meta').document('health').set({
        service: {
            'lastRunAt': datetime.now(timezone.utc),
            'status': status,
            'error': str(error) if error else None,
        }
    }, merge=True)
