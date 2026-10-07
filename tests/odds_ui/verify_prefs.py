import json, os, subprocess, sys, time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

DIST = os.environ['ODDS_DIST']  # built client; run via run_all.py
BASE = 'http://localhost:8099'
ok = []
def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + (f'  [{extra}]' if extra else ''))
    ok.append(bool(cond))

server = subprocess.Popen([sys.executable, '-m', 'http.server', '8099', '--directory', DIST], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)

now = datetime.now(timezone.utc)
http_date = lambda dt: dt.strftime('%a, %d %b %Y %H:%M:%S GMT')
GAMES = [{'gameId': 'g0', 'awayTeam': 'Dallas Cowboys', 'homeTeam': 'Carolina Panthers', 'gameTime': http_date(now + timedelta(hours=3)), 'gameSpread': -6.5, 'gameSpreadTeam': 'Dallas Cowboys',
          'state': 'open', 'clock': None, 'homeScore': None, 'awayScore': None, 'homePickCount': 2, 'awayPickCount': 1, 'ouPoints': 44}]
POSTS = []

def handle(route):
    req = route.request; url = req.url.split('/api/odds/')[1].split('?')[0]
    h = {'Access-Control-Allow-Origin': BASE, 'Access-Control-Allow-Credentials': 'true', 'Access-Control-Allow-Headers': 'content-type', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'}
    if req.method == 'OPTIONS': return route.fulfill(status=204, headers=h)
    if req.method == 'POST': POSTS.append(url)
    if url == 'sport/NFL': return route.fulfill(json=GAMES, headers=h)
    if url == 'player/me': return route.fulfill(json={'uid': 'u', 'email': 'a@b.c', 'displayName': 'Taylor', 'picks': {}, 'hasPushSubscription': False}, headers=h)
    if url == 'recap': return route.fulfill(json={'available': False}, headers=h)
    return route.fulfill(json={}, headers=h)

def load(page):
    page.goto(f'{BASE}/odds.html'); page.wait_for_selector('.gc-board', timeout=8000); page.wait_for_timeout(500)

def open_profile(page):
    page.locator('.user-popup-text', has_text='Profile').first.click(); page.wait_for_selector('#show-abbrevs-toggle', state='attached'); page.wait_for_timeout(250)

visible = lambda page: page.evaluate("[...document.querySelectorAll('.gc-abbr')].filter(a => getComputedStyle(a).display !== 'none').length")

try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={'width': 390, 'height': 800}); page = ctx.new_page(); errors = []
        page.on('pageerror', lambda e: errors.append(str(e)) if 'ServiceWorker' not in str(e) else None)
        page.route('**/api/odds/**', handle)
        page.route('**/odds/sw.js', lambda r: r.fulfill(body='', content_type='application/javascript'))
        # the first-visit Help popup would sit on top; mark it seen without touching the abbreviation key
        page.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('showPopup','false'); sessionStorage.setItem('seeded','1') }")
        load(page)

        check('P1 abbreviations are on by default for a visitor who never chose: chips visible, nothing stored, board class present',
              visible(page) == 2 and page.evaluate("localStorage.getItem('odds-show-abbrevs')") is None and page.evaluate("document.querySelector('.gc-board').classList.contains('gc-board--abbr')"))
        open_profile(page)
        box = page.locator('#show-abbrevs-toggle')
        label = page.locator('.private-toggle-label', has_text='Show team abbreviations').inner_text()
        check('P2 the Profile modal has a "Show team abbreviations" toggle, checked by default', box.count() == 1 and box.is_checked() and 'abbreviations' in label.lower(), label)

        page.locator('.toggle-switch:has(#show-abbrevs-toggle) .toggle-switch-slider').click(); page.wait_for_timeout(250)
        check('P3 turning it off hides the chips right away, behind the open modal, with no save needed', visible(page) == 0 and not page.evaluate("document.querySelector('.gc-board').classList.contains('gc-board--abbr')") and not box.is_checked() and not any('update-profile' in u for u in POSTS), str(POSTS))
        check('P4 the choice is stored on this device (localStorage)', page.evaluate("localStorage.getItem('odds-show-abbrevs')") == '0')

        page.locator('.popup-close').click(); page.wait_for_timeout(250)
        check('P5 the chips stay hidden after the modal closes', visible(page) == 0)
        page.reload(); page.wait_for_selector('.gc-board'); page.wait_for_timeout(500)
        check('P6 an explicit "off" survives a reload and is not overridden by the default', visible(page) == 0 and not page.evaluate("document.querySelector('.gc-board').classList.contains('gc-board--abbr')"))
        open_profile(page)
        check('P7 the toggle shows as off when the modal is reopened', not page.locator('#show-abbrevs-toggle').is_checked())

        page.locator('.toggle-switch:has(#show-abbrevs-toggle) .toggle-switch-slider').click(); page.wait_for_timeout(250)
        check('P8 turning it back on shows the chips again and stores that choice', visible(page) == 2 and page.evaluate("document.querySelector('.gc-board').classList.contains('gc-board--abbr')") and page.evaluate("localStorage.getItem('odds-show-abbrevs')") == '1')
        check('P9 no page errors', not errors, str(errors))
        ctx.close(); browser.close()
finally:
    server.terminate()

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
