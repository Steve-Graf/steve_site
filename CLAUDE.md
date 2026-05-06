# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NFL sports betting odds tracker — users pick game winners against the spread, and the app tracks win/loss stats across a season. Deployed at stevegraf.com.

## Commands

### Frontend (React/Vite)
```bash
cd client
npm run dev        # Dev server at localhost:5173
npm run build      # Production build → client/dist/
npm run lint       # ESLint check
npm run preview    # Preview production build locally
```

### Backend (Flask)
```bash
source venv/bin/activate
python app.py      # Flask API server at localhost:5000 (debug mode)
```

### Background Workers (run independently or via cron)
```bash
python odds/odds_refresh.py    # Fetch odds from The Odds API (3–12 hour intervals)
python odds/scores_refresh.py  # Poll ESPN for live scores (60s intervals)
python odds/points_refresh.py  # Recalculate user points
python odds/trend_update.py    # Update pick count trends
```

## Architecture

**Frontend**: Multi-page Vite app with two entry points — `index.html` (portfolio) and `odds.html` (odds picking app). The React app mounts on `odds.html`. API base URL is set via `VITE_API_URL` in `.env` (dev) and `.env.production`.

**Backend**: Flask serves REST endpoints under `/api/odds/`. SSL certs (`cert.pem`, `key.pem`) are present for HTTPS. CORS is configured for `localhost:5173` and `stevegraf.com`.

**Database**: Single local MongoDB instance at `mongodb://localhost:27017/`. No ORM or migration tooling — direct pymongo calls. Key collections: `games` (odds, scores, pick counts) and `users` (player code, picks, stats).

**User identity**: Each user gets a random 4-character code stored in `localStorage`. This maps to a MongoDB user document. No authentication.

## Key Files

- [app.py](app.py) — Flask app entry point; registers odds Blueprint and template routes
- [odds/odds_routes.py](odds/odds_routes.py) — Flask Blueprint with all odds routes, MongoDB logic, and helper functions
- [client/odds_src/Odds.jsx](client/odds_src/Odds.jsx) — main React component; owns game list, pick state, score polling
- [client/odds_src/AppContext.jsx](client/odds_src/AppContext.jsx) — React context providing player code and user data
- [client/odds_src/GameRow.jsx](client/odds_src/GameRow.jsx) — individual game row with pick UI
- [odds/nfl_schedule.json](odds/nfl_schedule.json) — hardcoded NFL week schedule used to determine current week
- [odds/keys.py](odds/keys.py) — API credentials (git-ignored; required for odds_refresh.py)

## Data Flow

1. `odds/odds_refresh.py` pulls DraftKings spreads from The Odds API → writes to `games` collection
2. `odds/scores_refresh.py` polls ESPN every 60s during games → updates `homeScore`/`awayScore`
3. Frontend fetches games via `GET /api/odds/sport/americanfootball_nfl`, user picks via `GET /api/odds/player/<code>`
4. Pick submission hits `POST /api/odds/update-pick` → updates both `users.picks` and game pick counts
5. `odds/points_refresh.py` runs after games complete to evaluate picks against spread and update win/loss stats

## Environment

- `client/.env` — `VITE_API_URL=http://localhost:5000/api/odds/`
- `client/.env.production` — `VITE_API_URL=https://stevegraf.com/api/odds/`
- `odds/keys.py` (git-ignored) — The Odds API key and any other secrets
