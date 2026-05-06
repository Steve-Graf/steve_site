from flask import Flask, render_template
from flask_cors import CORS
from odds.odds_routes import odds_bp
from bingo import init_bingo
from bingo.config import BingoConfig

app = Flask(__name__, static_folder='client/dist/assets', template_folder='client/dist')
CORS(app, origins=['http://localhost:5173', 'https://stevegraf.com'])

app.config.from_object(BingoConfig)

app.register_blueprint(odds_bp)
init_bingo(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/odds/')
def odds_template():
    return render_template('odds.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
