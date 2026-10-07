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
GAMES = [{'gameId': 'g0', 'awayTeam': 'Detroit Lions', 'homeTeam': 'Philadelphia Eagles', 'gameTime': http_date(now + timedelta(hours=3)), 'gameSpread': -3.5,
          'gameSpreadTeam': 'Philadelphia Eagles', 'state': 'open', 'clock': None, 'homeScore': None, 'awayScore': None, 'homePickCount': 2, 'awayPickCount': 1, 'ouPoints': 44}]
RECAP = {'available': True, 'week': 4, 'yourRecord': None, 'bestRecord': {'entries': [{'name': 'Sam', 'wins': 12, 'losses': 3}]},
         'survivorAlive': {'count': 2, 'names': ['Sam', 'Jo']}, 'upset': None}
YOUR = {'name': 'Taylor', 'wins': 9, 'losses': 6}

def run(browser, signed_in, your_record):
    recap = dict(RECAP, yourRecord=your_record)
    def handle(route):
        req = route.request; url = req.url.split('/api/odds/')[1].split('?')[0]
        h = {'Access-Control-Allow-Origin': BASE, 'Access-Control-Allow-Credentials': 'true', 'Access-Control-Allow-Headers': 'content-type', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'}
        if req.method == 'OPTIONS': return route.fulfill(status=204, headers=h)
        if url == 'sport/NFL': return route.fulfill(json=GAMES, headers=h)
        if url == 'player/me':
            if not signed_in: return route.fulfill(status=401, json={'error': 'unauthorized'}, headers=h)
            return route.fulfill(json={'uid': 'u', 'email': 'a@b.c', 'displayName': 'Taylor', 'picks': {}, 'hasPushSubscription': False}, headers=h)
        if url == 'recap': return route.fulfill(json=recap, headers=h)
        return route.fulfill(json={}, headers=h)
    ctx = browser.new_context(viewport={'width': 390, 'height': 800}); page = ctx.new_page(); errors = []
    page.on('pageerror', lambda e: errors.append(str(e)) if 'ServiceWorker' not in str(e) else None)
    page.route('**/api/odds/**', handle)
    page.route('**/odds/sw.js', lambda r: r.fulfill(body='', content_type='application/javascript'))
    page.add_init_script("localStorage.setItem('showPopup','false')")  # no first-visit help popup; recap not yet seen
    page.goto(f'{BASE}/odds.html'); page.wait_for_selector('.gc-board', timeout=8000); page.wait_for_timeout(700)
    return ctx, page, errors

try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, signed_in, record, expect_section in (('signed out', False, None, False), ('signed in, has a last-week record', True, YOUR, True), ('signed in, no last-week record', True, None, False)):
            ctx, page, errors = run(browser, signed_in, record)
            check(f'{name}: recap opens by itself', page.locator('.recap-popup-content').count() == 1)
            text = page.locator('.recap-popup-content').inner_text() if page.locator('.recap-popup-content').count() else ''  # labels render uppercase
            low = text.lower()
            check(f'{name}: "Your record" section {"shown" if expect_section else "hidden"}', ('your record last week' in low) == expect_section, text[:80])
            check(f'{name}: shared sections still shown', 'best record last week' in low and 'still undefeated in survivor' in low)
            if expect_section: check(f'{name}: record text correct', 'Taylor' in text and '9-6' in text)
            page.locator('.recap-popup-content .popup-button').click(); page.wait_for_timeout(250)
            check(f'{name}: Got it closes it', page.locator('.recap-popup-content').count() == 0)
            check(f'{name}: Recap menu button present to reopen', page.locator('.user-popup-text', has_text='Recap').count() == 1)
            page.locator('.user-popup-text', has_text='Recap').first.click(); page.wait_for_timeout(250)
            check(f'{name}: Recap button reopens it', page.locator('.recap-popup-content').count() == 1)
            page.reload(); page.wait_for_selector('.gc-board'); page.wait_for_timeout(700)
            check(f'{name}: not auto-shown again after being seen', page.locator('.recap-popup-content').count() == 0)
            check(f'{name}: no page errors', not errors, str(errors))
            ctx.close()
        browser.close()
finally:
    server.terminate()

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
