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
    return [{'gameId': f'g{i}', 'awayTeam': a, 'homeTeam': h, 'gameTime': http_date(now + timedelta(hours=3 + i)), 'gameSpread': -3.5, 'gameSpreadTeam': h,
             'state': 'open', 'clock': None, 'homeScore': None, 'awayScore': None, 'homePickCount': 2, 'awayPickCount': 1, 'ouPoints': 44} for i, (a, h) in enumerate(PAIRS)]
HISTORY = [{'week': w, 'selectedTeam': 'Detroit Lions', 'outcome': 'win'} for w in range(1, 10)]
RECAP = {'available': True, 'week': 4, 'yourRecord': {'name': 'T', 'wins': 9, 'losses': 6}, 'bestRecord': {'entries': [{'name': 'Sam', 'wins': 12, 'losses': 3}]},
         'survivorAlive': {'count': 2, 'names': ['Sam', 'Jo']}, 'upset': {'correctCount': 1, 'totalCount': 9, 'correctTeam': 'Browns', 'awayTeam': 'Steelers', 'homeTeam': 'Browns', 'correctNames': ['Jo']}}

class Api:
    def __init__(self): self.posts = []
    def handle(self, route):
        req = route.request; url = req.url.split('/api/odds/')[1].split('?')[0]
        h = {'Access-Control-Allow-Origin': BASE, 'Access-Control-Allow-Credentials': 'true', 'Access-Control-Allow-Headers': 'content-type', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'}
        if req.method == 'OPTIONS': return route.fulfill(status=204, headers=h)
        if req.method == 'POST': self.posts.append(url)
        if url == 'sport/NFL': return route.fulfill(json=games(), headers=h)
        if url == 'player/me': return route.fulfill(json={'uid': 'u', 'email': 'a@b.c', 'displayName': 'Taylor', 'picks': {}, 'hasPushSubscription': False}, headers=h)
        if url == 'recap': return route.fulfill(json=RECAP, headers=h)
        if url == 'leaderboard': return route.fulfill(json={'entries': [{'rank': i, 'displayName': f'Player {i}', 'wins': 20 - i, 'losses': i, 'isYou': i == 3} for i in range(1, 25)]}, headers=h)
        if url == 'stats/me': return route.fulfill(json={'wins': 20, 'total': 30, 'underdog_wins_count': 6, 'underdog_count': 12, 'favored_wins_count': 14, 'favored_count': 18,
                                                           'favorite_team': 'Lions', 'favorite_team_count': 5, 'best_team': 'Eagles', 'best_team_win_count': 4, 'worst_team': 'Jets', 'worst_team_loss_count': 3}, headers=h)
        if url == 'survivor/state': return route.fulfill(json={'currentWeek': 9, 'stillUndefeated': 3, 'usedTeams': ['Miami Dolphins'], 'history': HISTORY, 'currentPick': None}, headers=h)
        if url.startswith('game-pickers/'):
            return route.fulfill(json={'homeTeam': 'Philadelphia Eagles', 'awayTeam': 'Detroit Lions', 'homeCount': 2, 'awayCount': 1,
                                       'homePickers': [{'displayName': 'Sam', 'isYou': False}, {'displayName': 'Alex', 'isYou': False}], 'awayPickers': [{'displayName': 'Jo', 'isYou': False}]}, headers=h)
        return route.fulfill(json={}, headers=h)

def new_page(browser, api, **ctx_kw):
    ctx = browser.new_context(**ctx_kw); page = ctx.new_page(); errors = []
    page.on('pageerror', lambda e: errors.append(str(e)) if 'ServiceWorker' not in str(e) else None)
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' and 'Failed to load resource' not in m.text and 'ServiceWorker' not in m.text and 'fetching the script' not in m.text else None)
    page.route('**/api/odds/**', api.handle)
    page.route('**/odds/sw.js', lambda r: r.fulfill(body='', content_type='application/javascript'))
    return ctx, page, errors

def load(page, first_visit=False, recap_seen=True):
    # localStorage must be set before the app reads it: seed it through an init script
    seed = ["localStorage.setItem('showPopup','%s')" % ('true' if first_visit else 'false')]
    if recap_seen: seed.append("localStorage.setItem('odds-recap-seen-week','4')")
    page.add_init_script(';'.join(seed))
    page.goto(f'{BASE}/odds.html'); page.wait_for_selector('.gc-board', timeout=8000); page.wait_for_timeout(500)

def modal_open(page): return page.locator('.popup-content').count() == 1
def menu(page, label): page.locator('.user-popup-text', has_text=label).first.click(); page.wait_for_selector('.popup-content'); page.wait_for_timeout(300)

# (menu label, class that identifies the modal, expects a "Got it" button)
MODALS = [('Help', '.help-popup-content', True), ('Recap', '.recap-popup-content', True), ('Profile', None, False), ('Stats', None, False),
          ('Survivor', '.survivor-popup-content', False), ('Leaderboard', '.leaderboard-popup-content', False)]

try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        PHONE = dict(viewport={'width': 390, 'height': 664}, user_agent=p.devices['iPhone 13']['user_agent'], is_mobile=True, has_touch=True)

        # ----------------------------------------------- every modal: X present, closes, geometry
        for label, cls, got_it in MODALS:
            api = Api(); ctx, page, errors = new_page(browser, api, **PHONE); load(page)
            menu(page, label)
            modal = page.locator('.popup-content')
            x = page.locator('.popup-content .popup-close')
            check(f'{label}: "Got it" button {"kept" if got_it else "absent"}', (page.locator('.popup-content .popup-button:has-text("Got it")').count() == 1) == got_it)
            if got_it:
                check(f'{label}: no X (it has its own Got it button)', x.count() == 0)
                page.locator('.popup-content .popup-button:has-text("Got it")').click(); page.wait_for_timeout(250)
                check(f'{label}: Got it closes it', not modal_open(page))
                check(f'{label}: body scroll lock released after close', page.evaluate("document.body.style.overflow") != 'hidden')
                menu(page, label); page.locator('.popup-background').click(position={'x': 5, 'y': 5}); page.wait_for_timeout(250)
                check(f'{label}: tapping outside still closes it', not modal_open(page))
                check(f'{label}: no page errors', not errors, str(errors))
                ctx.close(); continue
            check(f'{label}: exactly one X button, labelled Close', x.count() == 1 and x.get_attribute('aria-label') == 'Close')
            mb, xb = modal.bounding_box(), x.bounding_box()
            title = page.locator('.popup-content .popup-title').evaluate("e => {const r=document.createRange(); r.selectNodeContents(e); const b=r.getBoundingClientRect(); return {x:b.x,y:b.y,width:b.width,height:b.height}}")
            inside = xb['x'] >= mb['x'] and xb['x'] + xb['width'] <= mb['x'] + mb['width'] and xb['y'] >= mb['y']
            check(f'{label}: X sits inside the top-right corner', inside and xb['x'] + xb['width'] > mb['x'] + mb['width'] - 12 and xb['y'] - mb['y'] < 10, f'x={xb} modal={mb}')
            check(f'{label}: X clear of the title text', (xb['y'] + xb['height'] <= title['y'] + 1) or (xb['x'] >= title['x'] + title['width'] - 1) or (title['y'] + title['height'] <= xb['y']), f'xbottom={xb["y"]+xb["height"]:.0f} title_top={title["y"]:.0f}')
            check(f'{label}: X is at least 32x32 (tappable)', xb['width'] >= 32 and xb['height'] >= 32)
            check(f'{label}: whole modal fits on a 390x664 screen top', mb['y'] >= 0, str(mb['y']))
            if label == 'Profile': page.fill('#username-input', 'Edited name nobody saved')
            x.click(); page.wait_for_timeout(250)
            check(f'{label}: clicking X closes it', not modal_open(page))
            check(f'{label}: body scroll lock released after close', page.evaluate("document.body.style.overflow") != 'hidden')
            if label == 'Profile': check('Profile: closing with X does not save (no update-profile POST)', 'update-profile' not in api.posts, str(api.posts))
            menu(page, label); page.locator('.popup-background').click(position={'x': 5, 'y': 5}); page.wait_for_timeout(250)
            check(f'{label}: tapping outside still closes it', not modal_open(page))
            check(f'{label}: no page errors', not errors, str(errors))
            ctx.close()

        # ----------------------------------------------- "who picked" popup (opened from a game card)
        api = Api(); ctx, page, errors = new_page(browser, api, **PHONE); load(page)
        page.locator('.gc-pop').first.click(); page.wait_for_selector('.pickers-popup-content'); page.wait_for_timeout(300)
        check('Pickers: X present, no Got it', page.locator('.popup-content .popup-close').count() == 1 and page.locator('.popup-content .popup-button').count() == 0)
        xb, tb = page.locator('.popup-close').bounding_box(), page.locator('.popup-title').evaluate("e => {const r=document.createRange(); r.selectNodeContents(e); const b=r.getBoundingClientRect(); return {x:b.x,y:b.y,width:b.width,height:b.height}}")
        check('Pickers: X clear of the title text', xb['x'] >= tb['x'] + tb['width'] or xb['y'] + xb['height'] <= tb['y'])
        page.locator('.popup-close').click(); page.wait_for_timeout(250)
        check('Pickers: X closes it and the page is still intact', not modal_open(page) and page.locator('.gc-card').count() == 6)
        ctx.close()

        # ----------------------------------------------- first-visit help popup closes with Got it
        api = Api(); ctx, page, errors = new_page(browser, api, **PHONE); load(page, first_visit=True)
        check('First visit: help popup opens by itself', page.locator('.help-popup-content').count() == 1)
        page.locator('.help-popup-content .popup-button').click(); page.wait_for_timeout(250)
        check('First visit: Got it closes it', page.locator('.help-popup-content').count() == 0)
        ctx.close()

        # ----------------------------------------------- X stays put while a tall modal scrolls (short phone)
        api = Api(); ctx, page, errors = new_page(browser, api, viewport={'width': 320, 'height': 568}, user_agent=p.devices['iPhone 13']['user_agent'], is_mobile=True, has_touch=True); load(page)
        menu(page, 'Survivor')
        modal = page.locator('.popup-content'); scroller = page.locator('.popup-scroll')
        before = page.locator('.popup-close').bounding_box(); mb0 = modal.bounding_box()
        check('Scroll: survivor modal overflows and scrolls at 320x568', scroller.evaluate('e => e.scrollHeight > e.clientHeight'))
        check('Scroll: modal never taller than 85% of the screen', mb0['height'] <= 568 * 0.85 + 1, str(mb0['height']))
        check('Scroll: modal top on screen at 320x568', mb0['y'] >= 0, str(mb0['y']))
        scroller.evaluate('e => e.scrollTop = 120')
        after = page.locator('.popup-close').bounding_box(); mb1 = modal.bounding_box()
        check('Scroll: content really moved', scroller.evaluate('e => e.scrollTop') > 50)
        check('Scroll: X stays pinned in the same screen spot while content scrolls', abs(after['y'] - before['y']) < 1.5 and abs(after['x'] - before['x']) < 1.5 and abs(mb1['y'] - mb0['y']) < 1.5, f'before={before["y"]:.1f} after={after["y"]:.1f}')
        check('Scroll: X fully on screen', after['y'] >= 0 and after['x'] + after['width'] <= 320)
        page.screenshot(path=f'{SCR}/close_scrolled.png')
        page.locator('.popup-close').click(); page.wait_for_timeout(250)
        check('Scroll: X still closes it after scrolling', not modal_open(page))
        ctx.close()

        # ----------------------------------------------- very short screen (landscape phone): nothing clipped
        api = Api(); ctx, page, errors = new_page(browser, api, viewport={'width': 667, 'height': 375}, user_agent=p.devices['iPhone 13']['user_agent'], is_mobile=True, has_touch=True); load(page)
        for label in ('Profile', 'Stats', 'Survivor'):
            menu(page, label); mb = page.locator('.popup-content').bounding_box(); xb = page.locator('.popup-close').bounding_box()
            check(f'Landscape 667x375: {label} top edge and X on screen', mb['y'] >= 0 and xb['y'] >= 0 and mb['y'] + mb['height'] <= 375 + 1, f'modal={mb["y"]:.0f}..{mb["y"]+mb["height"]:.0f}')
            page.locator('.popup-close').click(); page.wait_for_timeout(200)
        ctx.close()

        # ----------------------------------------------- desktop + screenshots
        for label, shot in (('Survivor', 'close_survivor'), ('Profile', 'close_profile')):
            api = Api(); ctx, page, errors = new_page(browser, api, viewport={'width': 1000, 'height': 800}); load(page)
            menu(page, label); page.screenshot(path=f'{SCR}/{shot}_desktop.png')
            page.locator('.popup-close').hover(); page.wait_for_timeout(100)
            check(f'{label} desktop: X closes', (page.locator('.popup-close').click(), page.wait_for_timeout(200), not modal_open(page))[2])
            ctx.close()
        api = Api(); ctx, page, errors = new_page(browser, api, **PHONE); load(page)
        menu(page, 'Survivor'); page.screenshot(path=f'{SCR}/close_survivor_phone.png'); ctx.close()
        browser.close()
finally:
    server.terminate()

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
