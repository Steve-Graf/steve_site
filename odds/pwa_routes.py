import os

from flask import Blueprint, Response, g, jsonify, request, send_from_directory
from google.cloud import firestore

from bingo.extensions import get_db

from . import keys
from .auth import require_auth

DIST_ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'client', 'dist', 'icons'
)

odds_pwa_bp = Blueprint('odds_pwa', __name__)


@odds_pwa_bp.route('/odds/manifest.webmanifest')
def manifest():
    resp = jsonify({
        "name": "Dave's Odds",
        "short_name": "Dave's Odds",
        "description": "Pick NFL games against the spread and track your record across the season.",
        "start_url": "/odds/",
        "scope": "/odds/",
        "display": "standalone",
        "background_color": "#496542",
        "theme_color": "#619e51",
        "icons": [
            {"src": "/odds/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/odds/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "/odds/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    })
    resp.mimetype = "application/manifest+json"
    resp.headers["Cache-Control"] = "no-store"
    return resp


@odds_pwa_bp.route('/odds/sw.js')
def service_worker():
    # Fetch handler is required for Chrome/Android to treat the site as an
    # installable PWA, but it does no caching so it can't ever serve stale
    # content during active dev. push/notificationclick handle Web Push.
    resp = Response(
        """
self.addEventListener('install', () => { self.skipWaiting(); });
self.addEventListener('activate', (event) => { event.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', () => {});

self.addEventListener('push', (event) => {
    let data = {};
    try { data = event.data ? event.data.json() : {}; } catch (e) {}
    const title = data.title || "Dave's Odds";
    const options = {
        body: data.body || '',
        icon: '/odds/icons/icon-192.png',
        badge: '/odds/icons/icon-192.png',
        data: { url: data.url || '/odds/' },
    };
    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const url = (event.notification.data && event.notification.data.url) || '/odds/';
    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
            for (const client of windowClients) {
                if (client.url.includes('/odds/') && 'focus' in client) {
                    return client.focus();
                }
            }
            if (self.clients.openWindow) {
                return self.clients.openWindow(url);
            }
        })
    );
});
""",
        mimetype="application/javascript",
    )
    resp.headers["Cache-Control"] = "no-store"
    return resp


@odds_pwa_bp.route('/odds/icons/<path:filename>')
def icons(filename):
    return send_from_directory(DIST_ICONS_DIR, filename)


@odds_pwa_bp.route('/api/odds/push/vapid-public-key')
def get_vapid_public_key():
    return jsonify({"publicKey": keys.vapid_public_key})


@odds_pwa_bp.route('/api/odds/push/subscribe', methods=['POST'])
@require_auth
def push_subscribe():
    subscription = request.json
    if not subscription or 'endpoint' not in subscription:
        return jsonify({"error": "invalid subscription"}), 400
    get_db().collection('odds_users').document(g.uid).update({'pushSubscription': subscription})
    return jsonify({"status": "success"})


@odds_pwa_bp.route('/api/odds/push/unsubscribe', methods=['POST'])
@require_auth
def push_unsubscribe():
    get_db().collection('odds_users').document(g.uid).update({'pushSubscription': firestore.DELETE_FIELD})
    return jsonify({"status": "success"})
