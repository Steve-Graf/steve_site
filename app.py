from flask import Flask, render_template, jsonify
from flask_cors import CORS
import requests
import keys

app = Flask(__name__, static_folder='client/dist/assets', template_folder='client/dist')
CORS(app, origins=['http://localhost:5173', 'https://stevegraf.com'])

@app.route('/')
def home():
    return render_template('index.html')

# delete response_json logic when done with dev
global response_json
response_json = ''
@app.route('/api/odds/<sport>')
def odds(sport):
    api_key = keys.odds_api
    sport_key = ''
    if(sport == 'NFL'):
        sport_key = 'americanfootball_nfl'
    if(sport == 'NCAA'):
        sport_key = 'americanfootball_ncaaf'
    api_url = f'https://api.the-odds-api.com/v4/sports/{sport_key}/odds/'
    params = {"apiKey":api_key, "regions":"us", "markets":"h2h,spreads,totals", "oddsFormat":"american", "bookmakers":"draftkings"}
    try:
        global response_json
        if(response_json == ''):
            print('Pinging Odds API...')
            response = requests.get(api_url, params=params)
            response.raise_for_status()
            if(response.status_code == 200):
                response_json = response.json()
                return response.json()
            else:
                return jsonify([{"error", "Non 200 success status"}])
        else:
            print("Returning stored response json for testing purposes")
            return response_json
    except requests.exceptions.Timeout:
        print("Request timed out")
        return jsonify({"error": "Request timed out"})
    except requests.exceptions.HTTPError as e:
        print("HTTP error:", e)
        return jsonify({"error": f"HTTP error: {e}"})
    except Exception as e:
        print("Other error:", e)
        return jsonify({"error": f"Other error: {e}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)