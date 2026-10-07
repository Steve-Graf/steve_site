from flask import Flask, render_template, request, send_from_directory
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from odds import init_odds
from bingo import init_bingo
from bingo.config import BingoConfig
from golf import init_golf
from games import init_games
from tts import init_tts

app = Flask(__name__, static_folder='client/dist/assets', template_folder='client/dist')
# nginx sits in front of gunicorn — without this, Flask can't see that the original
# request came in over HTTPS, and url_for(_external=True) (used for OAuth redirect_uris)
# always generates http:// instead.
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
CORS(app, origins=['http://localhost:5173', 'https://stevegraf.com'], supports_credentials=True)

app.config.from_object(BingoConfig)
# the built pages (client/dist/*.html) point at fingerprinted bundle filenames that change on every
# `npm run build`. Flask only re-reads templates from disk when this is on (it defaults to debug mode),
# so without it a running gunicorn keeps serving HTML that references bundles the build just deleted.
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.after_request
def cache_built_assets(resp):
    # everything under /assets/ is a Vite build output with a content hash in its filename (a changed
    # file gets a new name), so browsers can keep it for a year instead of Flask's 4-hour default —
    # otherwise returning visitors re-download the fonts and bundles and see the font swap again
    if request.path.startswith('/assets/') and resp.status_code == 200:
        resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return resp

init_odds(app)
init_bingo(app)
init_golf(app)
init_games(app)
init_tts(app)

@app.route('/favicon.svg')
def favicon():
    return send_from_directory('static/favicons', 'option1-monogram.svg', mimetype='image/svg+xml')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/odds/')
def odds_template():
    return render_template('odds.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
