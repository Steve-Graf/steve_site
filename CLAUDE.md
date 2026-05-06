# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projects

This repo hosts two independent apps under a single Flask server, deployed at stevegraf.com.

### NFL Odds Tracker
Pick NFL game winners against the spread; tracks win/loss stats across a season.

- **Entry points**: `app.py` (Flask), `client/` (React/Vite frontend)
- **Key files**:
  - [app.py](app.py) — Flask entry point; registers blueprints and template routes
  - [odds/odds_routes.py](odds/odds_routes.py) — all odds API routes and MongoDB logic
  - [client/odds_src/Odds.jsx](client/odds_src/Odds.jsx) — main React component
  - [client/odds_src/GameRow.jsx](client/odds_src/GameRow.jsx) — individual game row with pick UI
  - [odds/nfl_schedule.json](odds/nfl_schedule.json) — hardcoded NFL week schedule
- **Background workers** (run independently or via cron):
  - `odds/odds_refresh.py` — fetch spreads from The Odds API
  - `odds/scores_refresh.py` — poll ESPN for live scores (60s intervals)
  - `odds/points_refresh.py` — recalculate user points after games
  - `odds/trend_update.py` — update pick count trends
- **Database**: MongoDB (`mongodb://localhost:27017/`). Direct pymongo, no ORM. Collections: `games`, `users`.
- **User identity**: random 4-character code in `localStorage`; no authentication.

### Social Bingo
Create and share bingo boards; players get unique random boards drawn from a shared tile pool.

- **Entry points**: registered as a Flask Blueprint at `/bingo`
- **Key files**:
  - [bingo/__init__.py](bingo/__init__.py) — initializes Firebase, OAuth, and registers blueprints
  - [bingo/blueprints/pages.py](bingo/blueprints/pages.py) — server-rendered page routes
  - [bingo/blueprints/api.py](bingo/blueprints/api.py) — JSON API routes
  - [bingo/blueprints/auth.py](bingo/blueprints/auth.py) — Google OAuth flow
  - [bingo/services/bingo_service.py](bingo/services/bingo_service.py) — board generation and bingo-check logic
  - [bingo/static/](bingo/static/) — CSS and JS (no build step; plain files)
  - [bingo/templates/](bingo/templates/) — Jinja2 templates
- **Database**: Firestore (credentials in `bingo/firebase_credentials.json`, git-ignored).
- **User identity**: Google OAuth via Authlib; session stored server-side.

## Running the server

```bash
source venv/bin/activate
python app.py      # Flask dev server at localhost:5000
```

```bash
cd client
npm run dev        # React/Vite dev server at localhost:5173
npm run build      # Production build → client/dist/
```

## Environment

- `client/.env` — `VITE_API_URL=http://localhost:5000/api/odds/`
- `client/.env.production` — `VITE_API_URL=https://stevegraf.com/api/odds/`
- `odds/keys.py` (git-ignored) — The Odds API key
- `bingo/.env` (git-ignored) — `SECRET_KEY`, Firebase path, Google OAuth credentials
