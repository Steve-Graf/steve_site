# Mobile login handoff — backend contract

The iOS app can't complete Google sign-in inside its embedded WKWebView (Google
blocks OAuth from embedded webviews). The app instead runs the Google step in a
system browser sheet (`ASWebAuthenticationSession`), which does **not** share
cookies with the app's webview. To get the user logged into the webview
afterward, the backend needs three small changes.

## 1. `/bingo/auth/login` — accept `?platform=ios`

When present, thread a `platform=ios` marker through the OAuth `state` param
sent to Google so it survives the round trip. If `state` is currently a bare
CSRF token, widen it to carry both fields, e.g.:

```
state = base64url(JSON({ "csrf": "<existing random token>", "platform": "ios" }))
```

(or a signed JWT with a `platform` claim — anything that still lets you
validate CSRF as before, and round-trips the flag.)

## 2. OAuth callback route (existing) — branch on `platform`

After validating `state`/CSRF as today:

- **`platform` absent or not `"ios"`**: unchanged — set the session cookie,
  redirect to `/bingo/`.
- **`platform == "ios"`**: don't set the cookie on this response. Instead:
  1. Mint a random opaque token, ≥128 bits (e.g. `secrets.token_urlsafe(32)`
     in Python, `crypto.randomBytes(32).toString('base64url')` in Node).
  2. Store it server-side (DB row / Redis / in-memory map) against the
     authenticated user, with a short TTL — **60–120 seconds**.
  3. Redirect to:
     ```
     socialbingo://auth-callback?token=<token>
     ```

## 3. New route — `GET /bingo/auth/mobile-complete?token=...`

- Look up the token.
  - **Missing / expired / already used** → redirect to `/bingo/auth/login`
    (the app will just show a normal login prompt).
  - **Valid** → invalidate it immediately (single-use), set the real
    persistent session cookie on *this* response (same attributes as the
    normal login flow: `HttpOnly`, `Secure`, appropriate `SameSite`), redirect
    to `/bingo/`.

This route must be reachable from the app's WKWebView (a normal https GET) —
that's what makes the resulting `Set-Cookie` land in the app's own cookie
store instead of the isolated auth-session one.

## Why this shape

- The one-time token is short-lived and single-use so it's safe to pass
  through a URL (custom-scheme redirect, then a plain GET) without being a
  long-lived credential if it leaks via logs/history.
- Regular browser users are entirely unaffected — this only activates when
  `platform=ios` is present, which only the app ever sends.

## Testing

Once deployed, the app's discovery/testing pass (see the iOS project's
`GoogleAuthHandler.swift` and `WebView.swift`) will exercise this end-to-end:
tap sign-in → Google consent in the system sheet → app loads
`/bingo/auth/mobile-complete?token=...` in its webview → lands on a logged-in
`/bingo/`. Force-quitting and relaunching the app should still show the user
logged in (cookie persisted in the app's `WKWebsiteDataStore`).
