import json, subprocess, sys, time
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
http_date = lambda dt: dt.strftime('%a, %d %b %Y %H:%M:%S GMT')
PAIRS = [('Detroit Lions', 'Philadelphia Eagles'), ('Kansas City Chiefs', 'Buffalo Bills'), ('Miami Dolphins', 'Minnesota Vikings'),
         ('Dallas Cowboys', 'Carolina Panthers'), ('Pittsburgh Steelers', 'Cleveland Browns'), ('Denver Broncos', 'Las Vegas Raiders')]
def games():
    out = []
    for i, (away, home) in enumerate(PAIRS):
        out.append({'gameId': f'g{i}', 'awayTeam': away, 'homeTeam': home, 'gameTime': http_date(now + timedelta(hours=3 + i)),
                    'gameSpread': -3.5, 'gameSpreadTeam': home, 'state': 'open', 'clock': None, 'homeScore': None, 'awayScore': None,
                    'homePickCount': 2, 'awayPickCount': 1, 'ouPoints': 44})
    return out

USED = ['Miami Dolphins', 'Minnesota Vikings', 'Kansas City Chiefs', 'Dallas Cowboys', 'Denver Broncos']
HISTORY = [{'week': w, 'selectedTeam': t, 'outcome': o} for w, t, o in [
    (1, 'Detroit Lions', 'win'), (2, 'Buffalo Bills', 'win'), (3, None, 'missed'), (4, 'Miami Dolphins', 'loss'), (5, 'Dallas Cowboys', 'win'),
    (6, 'Minnesota Vikings', 'win'), (7, 'Kansas City Chiefs', 'win'), (8, 'Denver Broncos', 'win'), (9, 'Philadelphia Eagles', 'pending')]]

class Api:
    def __init__(self, used=USED, history=HISTORY):
        self.used, self.history, self.survivor_posts = used, history, []
    def handle(self, route):
        req = route.request; url = req.url.split('/api/odds/')[1].split('?')[0]
        h = {'Access-Control-Allow-Origin': BASE, 'Access-Control-Allow-Credentials': 'true', 'Access-Control-Allow-Headers': 'content-type', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'}
        if req.method == 'OPTIONS': return route.fulfill(status=204, headers=h)
        if url == 'sport/NFL': return route.fulfill(json=games(), headers=h)
        if url == 'player/me': return route.fulfill(json={'uid': 'u', 'email': 'a@b.c', 'displayName': 'T', 'picks': {}, 'hasPushSubscription': False}, headers=h)
        if url == 'recap': return route.fulfill(json={'available': False}, headers=h)
        if url == 'survivor/state':
            return route.fulfill(json={'currentWeek': 9, 'stillUndefeated': 3, 'usedTeams': self.used, 'history': self.history,
                                       'currentPick': {'gameId': 'g0', 'selectedTeam': 'Philadelphia Eagles'}}, headers=h)
        if url == 'survivor/pick':
            self.survivor_posts.append(json.loads(req.post_data)); return route.fulfill(json={'status': 'success'}, headers=h)
        return route.fulfill(json={}, headers=h)

def open_page(browser, api, flag='', init_script=None, **ctx_kw):
    ctx = browser.new_context(**ctx_kw)
    if init_script: ctx.add_init_script(init_script)
    page = ctx.new_page(); errors = []
    page.on('pageerror', lambda e: errors.append(str(e)) if 'ServiceWorker' not in str(e) else None)  # test server has no sw.js; the real server does
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' and 'Failed to load resource' not in m.text and 'ServiceWorker' not in m.text and 'fetching the script' not in m.text else None)
    page.route('**/api/odds/**', api.handle)
    page.route('**/odds/sw.js', lambda r: r.fulfill(body='', content_type='application/javascript'))
    page.goto(f'{BASE}/odds.html{flag}')
    page.wait_for_selector('.odds-items-wrapper' if 'old=1' in flag else '.gc-board', timeout=8000)
    page.evaluate("localStorage.setItem('showPopup','false')")
    page.wait_for_timeout(400)
    # the first-visit help popup may be up; close it with its own button so the later Help click starts clean
    if page.locator('.help-popup-content').count():
        page.locator('.help-popup-content .popup-button').click()
    return ctx, page, errors

def open_help(page):
    page.locator('text=Help').first.click(); page.wait_for_selector('.help-popup-content')
def labels(page): return page.locator('.help-popup-content .recap-section-label').all_inner_texts()
def steps(page): return page.locator('.help-step').all_inner_texts()

try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        IPHONE, PIXEL = p.devices['iPhone 13'], p.devices['Pixel 7']

        # ---------------------------------------------------------------- help: desktop
        ctx, page, errors = open_page(browser, Api(), viewport={'width': 1000, 'height': 900})
        open_help(page)
        check('H1 desktop: section headers present, no install section', [l.lower() for l in labels(page)] == ['making picks', 'your account'], str(labels(page)))
        check('H2 desktop: no install steps at all', page.locator('.help-step').count() == 0)
        help_text = page.locator('.help-popup-content').inner_text().lower()
        check('H3 desktop: says how to pick, and no longer mentions undo', 'tap a team on any game' in help_text and 'undo' not in help_text and 'again' not in help_text, help_text[:120])
        page.screenshot(path=f'{SCR}/help_desktop.png')
        page.locator('.help-popup-content .popup-button').click()
        check('H4 Got it closes the help popup', page.locator('.help-popup-content').count() == 0)
        check('H5 desktop: no page errors', not errors, str(errors))
        ctx.close()

        # ---------------------------------------------------------------- help: iOS
        ctx, page, errors = open_page(browser, Api(), **IPHONE)
        open_help(page)
        check('H6 iOS: Install as an app section is shown', 'install as an app' in [l.lower() for l in labels(page)], str(labels(page)))
        st = steps(page)
        check('H7 iOS: three steps with Share / Add to Home Screen / Add', len(st) == 3 and 'Share' in st[0] and 'Add to Home Screen' in st[1] and st[2].strip().startswith('Tap Add'), str(st))
        check('H8 iOS: every step has an icon', page.locator('.help-step .help-step-icon svg').count() == 3)
        check('H9 iOS: no Android wording', 'Android' not in page.locator('.help-popup-content').inner_text() and 'Chrome' not in page.locator('.help-popup-content').inner_text())
        box = page.locator('.help-popup-content').bounding_box()
        check('H10 iPhone 13 (390x664): popup fully on screen at the top', box['y'] >= 0, str(box))
        page.screenshot(path=f'{SCR}/help_ios.png')
        check('H11 iOS: no page errors', not errors, str(errors))
        ctx.close()

        # ---------------------------------------------------------------- help: iOS already installed (standalone)
        ctx, page, errors = open_page(browser, Api(), init_script="Object.defineProperty(navigator,'standalone',{value:true})", **IPHONE)
        open_help(page)
        check('H12 iOS installed app: install section hidden', page.locator('.help-step').count() == 0 and 'install as an app' not in [l.lower() for l in labels(page)])
        ctx.close()

        # ---------------------------------------------------------------- help: Android
        ctx, page, errors = open_page(browser, Api(), **PIXEL)
        open_help(page)
        st = steps(page)
        check('H13 Android: three steps with menu / Add to Home screen / Install', len(st) == 3 and '⋮' in st[0] and 'Add to Home screen' in st[1] and 'Install' in st[2], str(st))
        check('H14 Android: no iPhone wording', 'Safari' not in page.locator('.help-popup-content').inner_text() and 'Share' not in page.locator('.help-popup-content').inner_text())
        page.screenshot(path=f'{SCR}/help_android.png')
        check('H15 Android: no page errors', not errors, str(errors))
        ctx.close()

        # ---------------------------------------------------------------- help: small phone + old board text
        ctx, page, errors = open_page(browser, Api(), viewport={'width': 320, 'height': 568}, user_agent=IPHONE['user_agent'], is_mobile=True, has_touch=True, flag='')
        open_help(page)
        el = page.locator('.help-popup-content')
        box = el.bounding_box()
        dims = el.evaluate('e => ({sh: e.scrollHeight, ch: e.clientHeight})')
        check('H16 320x568: popup inside the viewport (top and bottom)', box['y'] >= 0 and box['y'] + box['height'] <= 568, str(box))
        check('H17 320x568: Got it reachable (visible or scrollable)', page.locator('.help-popup-content .popup-button').count() == 1 and dims['sh'] >= dims['ch'], str(dims))
        page.screenshot(path=f'{SCR}/help_small.png')
        ctx.close()
        ctx, page, errors = open_page(browser, Api(), flag='?old=1', viewport={'width': 1000, 'height': 900})
        open_help(page)
        check('H18 ?old=1: help says click the spread tiles', 'click on the tiles in the spread columns' in page.locator('.help-popup-content').inner_text())
        ctx.close()

        # ---------------------------------------------------------------- survivor
        def open_survivor(page):
            page.locator('text=Survivor').first.click(); page.wait_for_selector('.survivor-popup-content .survivor-matchups-list')
        api = Api()
        ctx, page, errors = open_page(browser, api, viewport={'width': 400, 'height': 800})
        open_survivor(page)
        rows = page.locator('.survivor-game-row')
        check('S1 all six games listed, each with two team buttons and an @', rows.count() == 6 and page.locator('.survivor-team-button').count() == 12 and page.locator('.survivor-game-at').count() == 6)
        used_btns = page.locator('.survivor-team-button:has-text("(used)")')
        used_names = sorted(t.replace(' (used)', '') for t in used_btns.all_inner_texts())
        check('S2 exactly the five used teams are labeled (used)', used_names == ['Broncos', 'Chiefs', 'Cowboys', 'Dolphins', 'Vikings'], str(used_names))
        check('S3 used teams are disabled; the rest are enabled', all(b.get_attribute('data-disabled') == 'true' for b in used_btns.all())
              and page.locator('.survivor-team-button[data-disabled="false"]').count() == 7, str(page.locator('.survivor-team-button[data-disabled="false"]').count()))
        check('S4 a game with one used team still offers the opponent (Cowboys used, Panthers enabled)',
              page.locator('.survivor-game-row:has-text("Cowboys") .survivor-team-button:has-text("Panthers")').get_attribute('data-disabled') == 'false')
        check('S5 current pick (Eagles) still shown and highlighted', page.locator('.survivor-team-selected').count() == 1 and page.locator('.survivor-team-selected').inner_text() == 'Eagles')
        hist = page.locator('.survivor-history-list')
        info = hist.evaluate('e => ({sh: e.scrollHeight, ch: e.clientHeight, oy: getComputedStyle(e).overflowY, ob: getComputedStyle(e).overscrollBehaviorY})')
        check('S6 History is capped and scrollable', info['ch'] <= 144 and info['sh'] > info['ch'] and info['oy'] == 'auto' and info['ob'] == 'contain', str(info))
        first = hist.locator('.survivor-history-row').first.inner_text().replace(chr(10), ' ')
        check('S7 newest week is first', first.startswith('Week 9'), first)
        hist.evaluate('e => e.scrollTop = e.scrollHeight')
        last = hist.locator('.survivor-history-row').last.inner_text().replace(chr(10), ' ')
        check('S8 scrolling reaches Week 1', last.startswith('Week 1'), last)
        outer = page.locator('.survivor-popup-content').evaluate('e => ({sh: e.scrollHeight, ch: e.clientHeight, top: e.getBoundingClientRect().top})')
        check('S9 400x800: popup on screen', outer['top'] >= 0, str(outer))
        page.screenshot(path=f'{SCR}/survivor_restored.png')
        page.locator('.survivor-game-row:has-text("Cowboys") .survivor-team-button:has-text("Cowboys")').click(); page.wait_for_timeout(250)
        check('S10a clicking a used team does nothing', api.survivor_posts == [], str(api.survivor_posts))
        page.locator('.survivor-game-row:has-text("Cowboys") .survivor-team-button:has-text("Panthers")').click(); page.wait_for_timeout(300)
        check('S10b clicking the unused opponent posts that pick', api.survivor_posts == [{'gameId': 'g3', 'selectedTeam': 'Carolina Panthers'}], str(api.survivor_posts))
        check('S11 survivor: no page errors', not errors, str(errors))
        ctx.close()

        # nothing used yet -> no labels, no History section
        ctx, page, errors = open_page(browser, Api(used=[], history=[]), viewport={'width': 400, 'height': 800})
        open_survivor(page)
        check('S12 nothing used: 12 enabled buttons, no (used), no History', page.locator('.survivor-team-button[data-disabled="false"]').count() == 12 and '(used)' not in page.locator('.survivor-matchups-list').inner_text() and page.locator('.survivor-history-list').count() == 0)
        ctx.close()
        browser.close()
finally:
    server.terminate()

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
