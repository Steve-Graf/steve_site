export const POLL_INTERVAL_MS = 60000;
// while a game is in progress the API serves the clock/score from memory, so polling faster costs no Firestore reads
export const LIVE_POLL_INTERVAL_MS = 20000;

export function authFetch(url, options = {}) {
    return fetch(url, { ...options, credentials: 'include' });
}
