import json, re, subprocess, sys, time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

import os
DIST = os.environ['ODDS_DIST']  # built client; run via run_all.py
SCR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')  # screenshots (gitignored)
os.makedirs(SCR, exist_ok=True)
BASE = 'http://localhost:8099'
ok = []
def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + (f'  [{extra}]' if extra else ''))
    ok.append(bool(cond))

server = subprocess.Popen([sys.executable, '-m', 'http.server', '8099', '--directory', DIST], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)

now = datetime.now(timezone.utc)
http_date = lambda dt: dt.strftime('%a, %d %b %Y %H:%M:%S GMT')   # what Flask's jsonify emits
def game(gid, away, home, state, mins, spread_team, spread, **kw):
    g = {'gameId': gid, 'awayTeam': away, 'homeTeam': home, 'gameTime': http_date(now + timedelta(minutes=mins)),
         'gameSpread': spread, 'gameSpreadTeam': spread_team, 'state': state, 'clock': None, 'homeScore': None, 'awayScore': None,
         'homePickCount': 0, 'awayPickCount': 0, 'ouPoints': 44}
    g.update(kw); return g
def week(include_live=True, kickoff_soon=False):
    games = [
        game('g_mia', 'Miami Dolphins', 'Minnesota Vikings', 'final', -1800, 'Minnesota Vikings', -3.5, homeScore=15, awayScore=10, homePickCount=7, awayPickCount=5),
        game('g_ind', 'Indianapolis Colts', 'Washington Commanders', 'final', -1750, 'Indianapolis Colts', -4.5, homeScore=13, awayScore=30, homePickCount=8, awayPickCount=6),
        game('g_nyj', 'New York Jets', 'Chicago Bears', 'final', -1740, 'Chicago Bears', -3.5, homeScore=23, awayScore=12, homePickCount=9, awayPickCount=5),
    ]
    if include_live:
        games += [
            game('g_dal', 'Dallas Cowboys', 'Carolina Panthers', 'live', -130, 'Dallas Cowboys', -3.5, clock='Q3 4:12', homeScore=17, awayScore=24, homePickCount=3, awayPickCount=9),
            game('g_pit', 'Pittsburgh Steelers', 'Cleveland Browns', 'live', -125, 'Cleveland Browns', -2.5, clock='Halftime', homeScore=17, awayScore=13, homePickCount=9, awayPickCount=3),
        ]
    games += [
        game('g_det', 'Detroit Lions', 'Philadelphia Eagles', 'open', 180, 'Philadelphia Eagles', -3.5, homePickCount=8, awayPickCount=5),
        game('g_kc', 'Kansas City Chiefs', 'Buffalo Bills', 'open', 200, 'Buffalo Bills', -1.5, homePickCount=6, awayPickCount=7),
        game('g_sea', 'Seattle Seahawks', 'San Francisco 49ers', 'postponed', -60, 'San Francisco 49ers', -6.5, clock='Postponed'),
    ]
    if kickoff_soon:
        games.append(game('g_soon', 'Denver Broncos', 'Las Vegas Raiders', 'open', 0.5, 'Las Vegas Raiders', -2.5))
    return games

class Api:
    def __init__(self, games, signed_in=True):
        self.games, self.signed_in = games, signed_in
        self.picks = {'g_nyj': {'selectedTeam': 'New York Jets'}, 'g_ind': {'selectedTeam': 'Indianapolis Colts'},
                      'g_dal': {'selectedTeam': 'Dallas Cowboys'}, 'g_pit': {'selectedTeam': 'Pittsburgh Steelers'}, 'g_kc': {'selectedTeam': 'Kansas City Chiefs'}}
        self.board_gets = 0; self.posts = []; self.flip_after = None
    def handle(self, route):
        req = route.request; url = req.url.split('/api/odds/')[1].split('?')[0]
        h = {'Access-Control-Allow-Origin': BASE, 'Access-Control-Allow-Credentials': 'true', 'Access-Control-Allow-Headers': 'content-type', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'}
        if req.method == 'OPTIONS': return route.fulfill(status=204, headers=h)
        if url == 'sport/NFL':
            self.board_gets += 1
            if self.flip_after and self.board_gets >= self.flip_after:
                for g in self.games:
                    if g['gameId'] == 'g_soon': g.update(state='live', clock='Q1 15:00', homeScore=0, awayScore=0)
            return route.fulfill(json=self.games, headers=h)
        if url == 'player/me':
            if not self.signed_in: return route.fulfill(status=401, json={'error': 'unauthorized'}, headers=h)
            return route.fulfill(json={'uid': 'u', 'email': 'a@b.c', 'displayName': 'T', 'picks': self.picks, 'hasPushSubscription': False}, headers=h)
        if url == 'update-pick':
            body = json.loads(req.post_data); self.posts.append(body)
            if body['gameId'] == 'g_race': return route.fulfill(status=409, json={'error': 'This game has already started'}, headers=h)
            if body['selectedTeam'] is None: self.picks.pop(body['gameId'], None)
            else: self.picks[body['gameId']] = {'selectedTeam': body['selectedTeam']}
            return route.fulfill(json={'status': 'success'}, headers=h)
        if url == 'recap': return route.fulfill(json={'available': False}, headers=h)
        if url.startswith('game-pickers/'):
            return route.fulfill(json={'homeTeam': 'Philadelphia Eagles', 'awayTeam': 'Detroit Lions', 'homeCount': 2, 'awayCount': 1,
                                       'homePickers': [{'displayName': 'Sam', 'isYou': False}, {'displayName': 'Alex', 'isYou': False}],
                                       'awayPickers': [{'displayName': 'Jo', 'isYou': False}]}, headers=h)
        return route.fulfill(json={}, headers=h)

def open_page(browser, api, w=1000, h=900, flag='', clock=False):
    ctx = browser.new_context(viewport={'width': w, 'height': h})
    page = ctx.new_page(); errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
    page.route('**/api/odds/**', api.handle)
    page.route('**/odds/sw.js', lambda r: r.fulfill(body='', content_type='application/javascript'))
    if clock: page.clock.install()
    page.goto(f'{BASE}/odds.html{flag}')
    page.wait_for_selector('.odds-items-wrapper' if 'old=1' in flag else '.gc-board', timeout=8000)
    # dismiss the first-visit help popup so it doesn't cover the board
    page.evaluate("localStorage.setItem('showPopup','false')")
    if page.locator('.popup-title:has-text("New here")').count():
        page.locator('.popup-background').first.click(position={'x': 5, 'y': 5})
    return ctx, page, errors

try:
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------------------------------------------------- visuals + structure
        api = Api(week())
        ctx, page, errors = open_page(browser, api)
        page.wait_for_timeout(600)
        cards = page.locator('.gc-card')
        check('U1 eight cards render for eight games', cards.count() == 8, str(cards.count()))
        check('U2 every card except a finished one carries a floating status chip', page.locator('.gc-top').count() == 5 and page.locator('.gc-card--scored:not(:has(.gc-chip--live)) .gc-top').count() == 0, str(page.locator('.gc-top').count()))
        check('U3 live chips show the server clock', {t.lower() for t in page.locator('.gc-chip--live').all_inner_texts()} == {'live · q3 4:12', 'live · halftime'}, str(page.locator('.gc-chip--live').all_inner_texts()))
        board_text = page.locator('.gc-board').inner_text().lower()
        chip_text = ' '.join(page.locator('.gc-chip').all_inner_texts()).lower()
        check('U4 finished games show no Final / Won / Lost / No pick text', not re.search(r'\b(final|won|lost)\b', board_text) and 'no pick' not in chip_text and page.locator('.gc-chip').count() == 5, chip_text)
        check('U5 postponed card is labeled', 'postponed' in [t.lower() for t in page.locator('.gc-chip--muted').all_inner_texts()])
        check('U6 live pick colors: DAL covering green, PIT short red', page.locator('.gc-cov').count() == 1 and page.locator('.gc-unc').count() == 1)
        check('U7 final pick colors: IND won, NYJ lost', page.locator('.gc-won').count() == 1 and page.locator('.gc-lost').count() == 1)
        check('U8 logos load (no broken images)', page.evaluate("[...document.querySelectorAll('.gc-badge img')].every(i=>i.complete&&i.naturalWidth>0)"))
        check('U9 Barlow Condensed is what renders', page.evaluate("document.fonts.check('800 26px \"Barlow Condensed\"') && getComputedStyle(document.querySelector('.gc-plate')).fontFamily.includes('Barlow Condensed')"))
        check('U10 yard-line separators reused', page.locator('.gc-board .time-separator').count() >= 1)
        check('U11 minus sign is typographic in the display (−3.5)', '−3.5' in page.locator('.gc-board').inner_text())
        page.locator('.gc-board').screenshot(path=f'{SCR}/ui_board_desktop.png')

        # ---------------------------------------------------- picks
        det, phi = page.locator('button[aria-label^="Pick Detroit Lions"]'), page.locator('button[aria-label^="Pick Philadelphia Eagles"]')
        det.click()
        page.wait_for_function("document.querySelector('button[aria-label^=\"Your pick: Detroit Lions\"]')", timeout=3000)
        page.wait_for_timeout(300)
        b = api.posts[-1]
        check('U12 pick sends gameId, teams, selectedTeam and the underdog line as a "+" string', (b['gameId'], b['selectedTeam'], b['gameSpread']) == ('g_det', 'Detroit Lions', '+3.5'), json.dumps(b))
        phi.click(); page.wait_for_timeout(400)
        b = api.posts[-1]
        check('U13 switching sides sends the favorite line as a number (-3.5)', (b['selectedTeam'], b['gameSpread']) == ('Philadelphia Eagles', -3.5), json.dumps(b))
        posts_before = len(api.posts)
        page.locator('button[aria-label^="Your pick: Philadelphia Eagles"]').click(); page.wait_for_timeout(400)
        check('U14 tapping your own pick again does nothing: no request is sent', len(api.posts) == posts_before, f'{posts_before} -> {len(api.posts)}')
        check('U15 the pick stays: Eagles still picked, Lions still unpicked, and no "removed" toast', page.locator('button[aria-label^="Your pick: Philadelphia Eagles"]').count() == 1 and page.locator('button[aria-label^="Pick Detroit Lions"]').count() == 1 and 'removed' not in page.locator('#alerts-wrapper').inner_text().lower())
        check('U15b no pick label offers to remove it', page.locator('button[aria-label*="remove" i]').count() == 0)
        check('U16 a success toast was shown for each action', page.locator('.alert-notification').count() >= 1)

        # late pick rejected by the server -> warning + the board is refreshed
        api.games.append(game('g_race', 'Green Bay Packers', 'Tampa Bay Buccaneers', 'open', 120, 'Tampa Bay Buccaneers', -2.5))
        gets_before = api.board_gets
        page.evaluate("document.querySelector('#alerts-wrapper').innerHTML=''")
        ctx.pages[0].evaluate("1")
        page.goto(f'{BASE}/odds.html'); page.wait_for_selector('.gc-board'); page.wait_for_timeout(400)
        gets_before = api.board_gets
        page.locator('button[aria-label^="Pick Green Bay Packers"]').click(); page.wait_for_timeout(600)
        check('U17 a 409 shows "already started" and triggers a board refresh', 'already started' in page.locator('#alerts-wrapper').inner_text().lower() and api.board_gets > gets_before, f'gets {gets_before}->{api.board_gets}')

        # popularity strip is a button that opens who-picked-what, and locks scroll
        page.locator('.gc-pop').first.click(); page.wait_for_timeout(300)
        check('U18 popularity opens the "Who Picked What" popup and locks scroll', page.locator('.popup-title:has-text("Who Picked What")').count() == 1 and page.evaluate("document.body.style.overflow") == 'hidden')
        errors = [e for e in errors if 'ServiceWorker' not in e and '404' not in e]   # the static test server has no /odds/sw.js
        check('U19 no console errors on the new board', errors == [], str(errors[:2]))
        ctx.close()

        # ---------------------------------------------------- signed out
        api2 = Api(week(), signed_in=False)
        ctx, page, errors = open_page(browser, api2)
        page.locator('button[aria-label^="Pick Detroit Lions"]').click(); page.wait_for_timeout(300)
        check('U20 signed out: tapping a tile asks you to log in and sends nothing', 'log in' in page.locator('#alerts-wrapper').inner_text().lower() and api2.posts == [])
        ctx.close()

        # ---------------------------------------------------- responsive
        for w, name in [(390, 'mobile'), (320, 'narrow')]:
            ctx, page, errors = open_page(browser, Api(week()), w=w, h=844)
            page.wait_for_timeout(500)
            overflow = page.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")
            tiles_overflow = page.evaluate("[...document.querySelectorAll('.gc-team')].filter(t=>t.scrollWidth>t.clientWidth+1).length")
            check(f'U21 {w}px: no horizontal scroll and no tile overflow', overflow <= 0 and tiles_overflow == 0, f'page overflow {overflow}, tiles {tiles_overflow}')
            page.screenshot(path=f'{SCR}/ui_board_{name}.png', clip={'x': 0, 'y': 0, 'width': w, 'height': 1500}, full_page=True)
            ctx.close()

        # ---------------------------------------------------- polling cadence (fake clock)
        def count_gets(api, steps, step_ms=20000, flag=''):
            ctx, page, _ = open_page(browser, api, flag=flag, clock=True)
            page.wait_for_timeout(500)
            start = api.board_gets
            for _ in range(steps):
                page.clock.run_for(step_ms); page.wait_for_timeout(350)
            ctx.close()
            return api.board_gets - start
        a = Api(week(include_live=True)); n = count_gets(a, 3)
        check('U22 a live game on the board -> polls every 20s (3 polls in 60s)', n == 3, f'{n} polls')
        a = Api(week(include_live=False)); n = count_gets(a, 3, step_ms=19000)
        check('U23 nothing live -> no poll before 60s (57s elapsed)', n == 0, f'{n} polls')
        a = Api(week(include_live=False)); n = count_gets(a, 4)
        check('U24 nothing live -> one poll by 80s', n == 1, f'{n} polls')
        a = Api(week(include_live=False, kickoff_soon=True)); a.flip_after = 2; ctx, page, _ = open_page(browser, a, clock=True); page.wait_for_timeout(500)
        start = a.board_gets
        page.clock.run_for(33000); page.wait_for_timeout(500)
        flipped = page.locator('.gc-chip--live').count()
        check('U25 a kickoff in 30s wakes the poll at ~32s and the card flips to live', a.board_gets - start == 1 and flipped >= 1, f'polls {a.board_gets-start}, live chips {flipped}')
        ctx.close()

        # ---------------------------------------------------- default board untouched
        ctx, page, errors = open_page(browser, Api(week()), flag='?old=1')
        check('U26 with ?old=1 the old board renders and the new one does not', page.locator('.odds-items-wrapper').count() > 0 and page.locator('.gc-board').count() == 0)
        page.screenshot(path=f'{SCR}/ui_old_board.png', clip={'x': 0, 'y': 0, 'width': 1000, 'height': 900})
        ctx.close()
        ctx, page, errors = open_page(browser, Api(week()))
        check('U27 with no flag the NEW board is the default (and the old rows are absent)', page.locator('.gc-board').count() == 1 and page.locator('.odds-items-wrapper').count() == 0)
        ctx.close()
        browser.close()
finally:
    server.terminate()

print('\nUI results:', f'{sum(ok)}/{len(ok)} passed')
sys.exit(0 if all(ok) else 1)
