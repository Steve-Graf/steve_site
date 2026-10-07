import json, os, re, subprocess, sys, time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

DIST = os.environ['ODDS_DIST']  # built client; run via run_all.py
SCR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
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
def game(gid, away, home, state, mins, spread_team, spread, **kw):
    g = {'gameId': gid, 'awayTeam': away, 'homeTeam': home, 'gameTime': http_date(now + timedelta(minutes=mins)), 'gameSpread': spread, 'gameSpreadTeam': spread_team,
         'state': state, 'clock': None, 'homeScore': None, 'awayScore': None, 'homePickCount': 3, 'awayPickCount': 2, 'ouPoints': 44}
    g.update(kw); return g
GAMES = [
    game('g_det', 'Detroit Lions', 'Philadelphia Eagles', 'live', -90, 'Philadelphia Eagles', -13.5, clock='Q3 4:12', homeScore=17, awayScore=24),     # DET +13.5, covering
    game('g_kc', 'Kansas City Chiefs', 'Buffalo Bills', 'final', -1800, 'Buffalo Bills', -1.5, homeScore=24, awayScore=27),                            # KC won
    game('g_nyj', 'New York Jets', 'Chicago Bears', 'final', -1700, 'Chicago Bears', -3.5, homeScore=23, awayScore=12),                                 # NYJ lost
    game('g_sea', 'Seattle Seahawks', 'San Francisco 49ers', 'postponed', -60, 'San Francisco 49ers', -6.5, clock='Postponed'),
    game('g_dal', 'Dallas Cowboys', 'Carolina Panthers', 'open', 180, 'Dallas Cowboys', -14.5),                                                      # CAR picked
    game('g_gb', 'Green Bay Packers', 'Tampa Bay Buccaneers', 'open', 200, 'Tampa Bay Buccaneers', -10.5, homePickCount=0, awayPickCount=0),         # no pick
]
PICKS = {'g_det': 'Detroit Lions', 'g_kc': 'Kansas City Chiefs', 'g_nyj': 'New York Jets', 'g_dal': 'Carolina Panthers'}

POSTS = []
def handle(route):
    req = route.request; url = req.url.split('/api/odds/')[1].split('?')[0]
    if url == 'update-pick' and req.method == 'POST': POSTS.append(json.loads(req.post_data))
    h = {'Access-Control-Allow-Origin': BASE, 'Access-Control-Allow-Credentials': 'true', 'Access-Control-Allow-Headers': 'content-type', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'}
    if req.method == 'OPTIONS': return route.fulfill(status=204, headers=h)
    if url == 'sport/NFL': return route.fulfill(json=GAMES, headers=h)
    if url == 'player/me': return route.fulfill(json={'uid': 'u', 'email': 'a@b.c', 'displayName': 'T', 'picks': {k: {'selectedTeam': v} for k, v in PICKS.items()}, 'hasPushSubscription': False}, headers=h)
    if url == 'recap': return route.fulfill(json={'available': False}, headers=h)
    return route.fulfill(json={}, headers=h)

def open_page(browser, w, abbrevs=None):
    ctx = browser.new_context(viewport={'width': w, 'height': 900}); page = ctx.new_page(); errors = []
    # the Profile toggle's stored value; leaving it unset means the viewer never chose, which is the default (on)
    if abbrevs is not None: page.add_init_script("localStorage.setItem('odds-show-abbrevs','%s')" % ('1' if abbrevs else '0'))
    page.on('pageerror', lambda e: errors.append(str(e)) if 'ServiceWorker' not in str(e) else None)
    page.route('**/api/odds/**', handle)
    page.route('**/odds/sw.js', lambda r: r.fulfill(body='', content_type='application/javascript'))
    page.add_init_script("localStorage.setItem('showPopup','false')")
    page.goto(f'{BASE}/odds.html'); page.wait_for_selector('.gc-board', timeout=8000); page.wait_for_timeout(600)
    return ctx, page, errors

RGB = lambda r, g, b: f'rgb({r}, {g}, {b})'
WIN, LOSE, INK, WHITE, YELLOW = RGB(89, 237, 116), RGB(255, 93, 93), RGB(46, 31, 1), RGB(255, 255, 255), RGB(255, 230, 0)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx, page, errors = open_page(browser, 390)
        ev = page.evaluate
        check('C1 six cards render', page.locator('.gc-card').count() == 6, str(page.locator('.gc-card').count()))

        # --- structure: a bug joined to a plate; the plate holds the score, or the spread before a score exists
        started = ev("[...document.querySelectorAll('.gc-card--scored .gc-team')].map(t => ({score: t.querySelector('.gc-plate').firstChild.textContent, pick: t.classList.contains('gc-pick'), chip: !!t.querySelector('.gc-plate .gc-line')}))")
        check('C2 started games: every plate shows a score, and only the picked team has the hanging spread chip',
              len(started) == 6 and all(re.fullmatch(r'\d+', s['score']) for s in started) and all(s['chip'] == s['pick'] for s in started) and sum(s['chip'] for s in started) == 3, str(started))
        unscored = ev("[...document.querySelectorAll('.gc-card:not(.gc-card--scored) .gc-team')].map(t => ({text: t.querySelector('.gc-plate').textContent, chip: !!t.querySelector('.gc-line')}))")
        check('C3 open and postponed games: the plate shows the spread and there is no hanging chip', len(unscored) == 6 and all(re.fullmatch(r'[+−]\d+(\.\d)?', u['text']) and not u['chip'] for u in unscored), str(unscored))
        text = page.locator('.gc-board').inner_text().lower()
        check('C4 no "@", no popularity title, no Final / Won / Lost text', page.locator('.gc-at').count() == 0 and 'popularity' not in text and not re.search(r'\b(final|won|lost)\b', text))
        check('C5 every popularity strip ends in the eye icon, inline with the bar', ev("[...document.querySelectorAll('.gc-pop')].every(p => { const e = p.querySelector('.gc-pop-eye'), r = p.querySelector('.gc-pop-row'); return e && r && e.parentElement === r && Math.abs((e.getBoundingClientRect().top + 7.5) - (r.getBoundingClientRect().top + r.getBoundingClientRect().height / 2)) < 3 })"))
        order = ev("[...document.querySelectorAll('.gc-card')].map(c => [...c.querySelectorAll('.gc-team')].map(t => [...t.children].map(k => k.className.split(' ')[0]).join(',')))")
        check('C6 away reads bug then plate and home reads plate then bug, so the plates meet in the middle', all(o == ['gc-badge,gc-plate', 'gc-plate,gc-badge'] for o in order), str(order[:2]))
        cols = ev("[...document.querySelectorAll('.gc-teams')].map(t => getComputedStyle(t).gridTemplateColumns.split(' ').length)")
        check('C7 every card splits into two equal halves', all(c == 2 for c in cols), str(cols))
        check('C8 open tiles are buttons you can tap, and the others are not', page.locator('.gc-card--open button.gc-team').count() == 4 and page.locator('.gc-card:not(.gc-card--open) button.gc-team').count() == 0)

        # --- the floating status chip: live, postponed, and an open game's "Tap to pick" / "Picked"
        chips = sorted(ev("[...document.querySelectorAll('.gc-chip')].map(c => c.textContent.trim().toLowerCase())"))
        check('C9 four chips: live, postponed, one "Tap to pick" and one "Picked"; none on finished games',
              chips == ['live · q3 4:12', 'postponed', 'tap to pick', '✓ picked'] and page.locator('.gc-card--scored:not(:has(.gc-chip--live)) .gc-top').count() == 0, str(chips))
        tops = ev("[...document.querySelectorAll('.gc-card--chip')].map(c => Math.round(c.querySelector('.gc-top').getBoundingClientRect().top - c.getBoundingClientRect().top))")
        check('C10 chips straddle the card edge (above its top)', len(tops) == 4 and all(t < 0 for t in tops), str(tops))
        clear = ev("[...document.querySelectorAll('.gc-card--chip')].map(c => { const prev = c.previousElementSibling, chip = c.querySelector('.gc-chip').getBoundingClientRect(); return prev && prev.classList.contains('gc-card') ? Math.round(chip.top - prev.getBoundingClientRect().bottom) : null }).filter(v => v !== null)")
        check('C11 a chip never touches the card above it (6px or more clear)', all(v >= 6 for v in clear), str(clear))
        centred = ev("[...document.querySelectorAll('.gc-card--open .gc-chip')].map(ch => { const c = ch.closest('.gc-card').getBoundingClientRect(), r = ch.getBoundingClientRect(); return +(((r.left + r.right) / 2) - ((c.left + c.right) / 2)).toFixed(1) })")
        check('C12 an open game\'s chip is centered on the card', len(centred) == 2 and all(abs(v) <= 1.5 for v in centred), str(centred))

        # --- the hanging spread chip
        hang = ev("[...document.querySelectorAll('.gc-line')].map(l => { const p = l.closest('.gc-plate').getBoundingClientRect(), r = l.getBoundingClientRect(); return {dx: +(((r.left + r.right) / 2) - ((p.left + p.right) / 2)).toFixed(1), straddles: r.top < p.bottom && p.bottom < r.bottom} })")
        check('C13 the spread chip is centered under its plate and overlaps the plate\'s bottom edge', len(hang) == 3 and all(abs(h['dx']) <= 1.5 and h['straddles'] for h in hang), str(hang))
        check('C14 every spread chip is the original yellow, whatever the game state', ev("[...document.querySelectorAll('.gc-line')].every(l => getComputedStyle(l).backgroundColor === '%s')" % YELLOW))

        # --- plate colors carry the game state
        col = lambda sel: ev("[...document.querySelectorAll('%s')].map(e => getComputedStyle(e).backgroundColor)" % sel)
        check('C15 covering and won plates are green; lost is red', col('.gc-cov .gc-plate') == [WIN] and col('.gc-won .gc-plate') == [WIN] and col('.gc-lost .gc-plate') == [LOSE], f"{col('.gc-cov .gc-plate')} {col('.gc-won .gc-plate')} {col('.gc-lost .gc-plate')}")
        check('C16 a pick before kickoff is a dark plate; every unpicked plate is white', col('.gc-pend .gc-plate') == [INK] and all(c == WHITE for c in col('.gc-team:not(.gc-pick) .gc-plate')) and len(col('.gc-team:not(.gc-pick) .gc-plate')) == 8, str(col('.gc-pend .gc-plate')))

        # --- one 2px divider where the bug meets the plate, not two
        join = ev("""[...document.querySelectorAll('.gc-team')].map(t => { const pl = t.querySelector('.gc-plate'), away = pl === t.lastElementChild;
            const xs = [...getComputedStyle(pl).boxShadow.matchAll(/(-?\\d+)px\\s+(-?\\d+)px/g)].map(m => +m[1]);
            return away ? (xs.includes(-2) && !xs.includes(2)) : (xs.includes(2) && !xs.includes(-2)) })""")
        check('C17 the plate leaves out its edge on the joined side (one divider line)', len(join) == 12 and all(join), str(join))

        # --- the bug: stacked, identical everywhere, as tall as its plate
        sizes = ev("[...new Set([...document.querySelectorAll('.gc-badge')].map(b => Math.round(b.getBoundingClientRect().width) + 'x' + Math.round(b.getBoundingClientRect().height)))]")
        check('C18 every bug is the same size whatever the abbreviation', len(sizes) == 1, str(sizes))
        logo = ev("""[...document.querySelectorAll('.gc-badge')].map(b => { const cs = getComputedStyle(b), inner = b.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight),
            r = b.getBoundingClientRect(), img = b.querySelector('img'), i = img.getBoundingClientRect();
            return {pct: +(i.width / inner * 100).toFixed(1), dx: +(((i.left + i.right) / 2) - ((r.left + r.right) / 2)).toFixed(1), dy: +(((i.top + i.bottom) / 2) - ((r.top + r.bottom) / 2)).toFixed(1), margin: getComputedStyle(img).marginTop, inside: i.left >= r.left - .5 && i.right <= r.right + .5 && i.top >= r.top - .5 && i.bottom <= r.bottom + .5} })""")
        check('C19 every logo is centered in its bug at 84% of the bug\'s inner width, with no negative margin and nothing spilling out',
              len(logo) == 12 and all(abs(l['pct'] - 84) <= 1 and abs(l['dx']) <= 1 and abs(l['dy']) <= 1 and l['margin'] == '0px' and l['inside'] for l in logo), str(logo[:2]))
        abbr = ev("[...document.querySelectorAll('.gc-abbr')].map(a => ({text: a.textContent, shown: getComputedStyle(a).display !== 'none'}))")
        check('C19b with nothing stored, the abbreviation chips are on by default: one per bug, each showing its team',
              sorted(a['text'] for a in abbr) == sorted(['DET', 'PHI', 'KC', 'BUF', 'NYJ', 'CHI', 'SEA', 'SF', 'DAL', 'CAR', 'GB', 'TB']) and all(a['shown'] for a in abbr)
              and page.locator('.gc-bug-name').count() == 0, str(abbr[:2]))
        check('C19c the board carries the abbreviation class by default', ev("document.querySelector('.gc-board').classList.contains('gc-board--abbr')"))
        flush = ev("[...document.querySelectorAll('.gc-team')].map(t => Math.abs(t.querySelector('.gc-plate').getBoundingClientRect().height - t.querySelector('.gc-badge').getBoundingClientRect().height))")
        check('C20 each plate is as tall as its bug', all(f <= 1 for f in flush), str(flush))

        # --- compactness guard
        hs = ev("({scored: Math.round(document.querySelector('.gc-card--scored').getBoundingClientRect().height), open: Math.round(document.querySelector('.gc-card--open').getBoundingClientRect().height)})")
        check('C21 with the default chips on, a started card and an open card are each 150px or shorter at 390px', hs['scored'] <= 150 and hs['open'] <= 150, str(hs))
        check('C22 postponed card shows a bug and plate on each side with no score', page.locator('.gc-card:has(.gc-chip--muted) .gc-badge').count() == 2 and page.locator('.gc-card:has(.gc-chip--muted) .gc-line').count() == 0)
        page.locator('.gc-board').screenshot(path=f'{SCR}/cards_390.png')

        # --- a pick can be switched but never taken away
        picked = page.locator('button[aria-label^="Your pick: Carolina Panthers"]')
        check('C23a the picked tile\'s label does not offer to remove it, and it looks inert (default cursor)',
              picked.count() == 1 and 'remove' not in picked.get_attribute('aria-label').lower() and ev("getComputedStyle(document.querySelector('button.gc-team.gc-pick')).cursor") == 'default')
        before = len(POSTS)
        picked.click(); page.wait_for_timeout(400)
        check('C23b tapping your own pick sends nothing and changes nothing', len(POSTS) == before and picked.count() == 1, f'{before} -> {len(POSTS)}')
        page.locator('button[aria-label^="Pick Dallas Cowboys"]').click(); page.wait_for_timeout(400)
        check('C23c tapping the other team still switches the pick (sends that team)', len(POSTS) == before + 1 and POSTS[-1]['selectedTeam'] == 'Dallas Cowboys', str(POSTS[-1:]))
        check('C24 no page errors', not errors, str(errors))
        ctx.close()

        # --- with abbreviations switched on (the Profile toggle): a small chip hangs off each bug's bottom edge
        ctx, page, errors = open_page(browser, 390, abbrevs=True)
        ev = page.evaluate
        check('C26a the board gets its abbreviation class and every chip is visible', ev("document.querySelector('.gc-board').classList.contains('gc-board--abbr')") and ev("[...document.querySelectorAll('.gc-abbr')].every(a => getComputedStyle(a).display !== 'none')") and page.locator('.gc-abbr').count() == 12)
        geo = ev("""[...document.querySelectorAll('.gc-badge')].map(b => { const r = b.getBoundingClientRect(), a = b.querySelector('.gc-abbr').getBoundingClientRect(), pop = b.closest('.gc-card').querySelector('.gc-pop').getBoundingClientRect();
            return {dx: +(((a.left + a.right) / 2) - ((r.left + r.right) / 2)).toFixed(1), straddles: a.top < r.bottom && r.bottom < a.bottom, narrower: a.width <= r.width, clear: a.bottom <= pop.top + 1} })""")
        check('C26b each chip is centered under its bug, overlaps the bug\'s bottom edge, is narrower than the bug and stays clear of the popularity strip',
              len(geo) == 12 and all(abs(g['dx']) <= 1.5 and g['straddles'] and g['narrower'] and g['clear'] for g in geo), str([g for g in geo if not (abs(g['dx']) <= 1.5 and g['straddles'] and g['narrower'] and g['clear'])][:2]))
        look = ev("({bg: getComputedStyle(document.querySelector('.gc-abbr')).backgroundColor, bug: getComputedStyle(document.querySelector('.gc-badge')).backgroundColor, text: getComputedStyle(document.querySelector('.gc-abbr')).color})")
        check('C26c a chip is white lettering on its team\'s own color', look['bg'] == look['bug'] and look['text'] == WHITE, str(look))
        hs2 = ev("({scored: Math.round(document.querySelector('.gc-card--scored').getBoundingClientRect().height), open: Math.round(document.querySelector('.gc-card--open').getBoundingClientRect().height)})")
        check('C26d cards stay compact with chips on (150px or shorter)', hs2['scored'] <= 150 and hs2['open'] <= 150, str(hs2))
        page.locator('.gc-board').screenshot(path=f'{SCR}/cards_390_abbr.png')
        ctx.close()
        ctx, page, errors = open_page(browser, 390, abbrevs=False)
        check('C26e switched off (stored "0"), the chips are hidden and the board has no abbreviation class', page.evaluate("[...document.querySelectorAll('.gc-abbr')].every(a => getComputedStyle(a).display === 'none') && !document.querySelector('.gc-board').classList.contains('gc-board--abbr')"))
        ctx.close()

        # --- fit at small phones, including the smallest one the app supports, with the chips off and on
        for w, abbrevs in [(w, a) for w in (414, 390, 375, 360, 340, 320) for a in (False, True)]:
            ctx, page, errors = open_page(browser, w, abbrevs)
            page.evaluate("document.querySelectorAll('.gc-abbr').forEach(n => { n.textContent = 'WAS' })")   # about the widest abbreviation in the league
            name_fits = page.evaluate("[...document.querySelectorAll('.gc-badge')].every(b => b.querySelector('.gc-abbr').getBoundingClientRect().width <= b.getBoundingClientRect().width)")
            over_tiles =page.evaluate("[...document.querySelectorAll('.gc-team')].filter(t => t.scrollWidth > t.clientWidth + 1).length")
            over_page = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            clipped = page.evaluate("[...document.querySelectorAll('.gc-team')].filter(t => { const r = t.getBoundingClientRect(); return [...t.children].some(c => { const b = c.getBoundingClientRect(); return b.left < r.left - 0.5 || b.right > r.right + 0.5 }) }).length")
            plate_text = page.evaluate("[...document.querySelectorAll('.gc-plate')].filter(p => p.scrollWidth > p.clientWidth + 1).length")
            wide_chip = page.evaluate("[...document.querySelectorAll('.gc-line')].filter(l => { const p = l.closest('.gc-plate').getBoundingClientRect(), r = l.getBoundingClientRect(); return r.width > p.width + 2 }).length")
            check(f'C25 {w}px, abbreviations {"on" if abbrevs else "off"}: no tile overflow, no clipped contents, no page scroll, numbers and chips fit', over_tiles == 0 and clipped == 0 and over_page <= 0 and plate_text == 0 and wide_chip == 0 and name_fits, f'tiles={over_tiles} clipped={clipped} page={over_page} plates={plate_text} chips={wide_chip} name_fits={name_fits}')
            if w in (360, 320): page.locator('.gc-board').screenshot(path=f'{SCR}/cards_{w}{"_abbr" if abbrevs else ""}.png')
            ctx.close()
        browser.close()
finally:
    server.terminate()

print(f"\n{sum(ok)}/{len(ok)} checks passed")
sys.exit(0 if all(ok) else 1)
