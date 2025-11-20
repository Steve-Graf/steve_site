import React, {useState, useEffect } from 'react';
import './Odds.css';
import {nflTeams} from "./data/nflTeams"

const API_URL = 'http://localhost:5000/api/odds/'

function formatSignedNumber(number){
    if(number > 0){
        return '+'+number;
    }else{
        return number;
    }
}

function Odds() {
    const [games, setGames] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    
    // useEffect Hook runs after the component renders
    useEffect(() => {
        // Define the async function inside the useEffect
        const fetchGameOdds = async () => {
            try {
                const response = await fetch(API_URL+'NFL');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                if(data.error){
                    setError(data.error);
                    setLoading(false);
                    return;
                }
                console.log(data);
                const gamesArray = Array.isArray(data) ? data : [data];
                setGames(gamesArray);
            } catch (e) {
                console.error('Failed to fetch game odds:', e);
                setError(e.message);
            } finally {
                setLoading(false);
            }
        };

        fetchGameOdds();
    }, []);

    return (
        <div>
            {loading && <p>Loading...</p>}
            {error && <p>Error: {error}</p>}

            {!loading && !error && games.length === 0 && (
                <p>No games found.</p>
            )}
            {!loading && !error && games.map((game, index) => {
                const bookmaker = game.bookmakers.find(bookmaker => bookmaker.key == 'draftkings');
                const spreadMarket = bookmaker.markets.find(market => market.key == 'spreads');
                const spreadAway = spreadMarket.outcomes.find(outcome => outcome.name == game.away_team);
                const spreadHome = spreadMarket.outcomes.find(outcome => outcome.name == game.home_team);

                const mlMarket = bookmaker.markets.find(market => market.key == 'h2h')
                const mlAway = mlMarket.outcomes.find(outcome => outcome.name == game.away_team);
                const mlHome = mlMarket.outcomes.find(outcome => outcome.name == game.home_team);

                const ouMarket = bookmaker.markets.find(market => market.key == 'totals')
                const ouOver = ouMarket.outcomes.find(outcome => outcome.name == 'Over');
                const ouUnder = ouMarket.outcomes.find(outcome => outcome.name == 'Under');

                return (
                    <div key={index} className="odds-wrapper">
                        <div className="teams-wrapper">
                            <div>{nflTeams[game.away_team].abbrv}</div>
                            <div>@</div>
                            <div>{nflTeams[game.home_team].abbrv}</div>
                        </div>
                        
                        <div className="spread-wrapper odds-column">
                            <div className="column-title">Spread</div>
                            <div className="column-value">{formatSignedNumber(spreadAway.point)}</div>
                            <div className="column-value">{formatSignedNumber(spreadHome.point)}</div>
                        </div>

                        <div className="ml-wrapper odds-column">
                            <div className="column-title">Moneyline</div>
                            <div className="column-value">{formatSignedNumber(mlAway.price)}</div>
                            <div className="column-value">{formatSignedNumber(mlHome.price)}</div>
                        </div>

                        <div className="ou-wrapper odds-column">
                            <div className="column-title">O/U</div>
                            <div className="column-value">{ouOver.point}</div>
                        </div>
                        {/* <p>{game.away_team}: {formatSignedNumber(spreadAway.price)} {formatSignedNumber(spreadAway.point)} {formatSignedNumber(mlAway.price)}</p>
                        <p>{game.home_team}: {formatSignedNumber(spreadHome.price)} {formatSignedNumber(spreadHome.point)} {formatSignedNumber(mlHome.price)}</p> */}
                    </div>
                );
            })}
        </div>
    );
}
export default Odds