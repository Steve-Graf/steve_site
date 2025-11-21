import React, {useState, useEffect } from 'react';
import './Odds.css';
import {nflTeams} from "./data/nflTeams"
import TimeSeparator from './TimeSeparator';
import GameRow from './GameRow.jsx'

const API_URL = 'http://localhost:5000/api/odds/'

function getNextTuesday() {
    const now = new Date();
    const day = now.getDay();
    
    const daysUntilTuesday = (9 - day) % 7 || 7;
    const nextTuesday = new Date(now);
    nextTuesday.setDate(now.getDate() + daysUntilTuesday);
    nextTuesday.setHours(0, 0, 0, 0);
    return nextTuesday;
}

function Odds() {
    const [games, setGames] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedColumnValue, setSelectedColumnValue] = useState({});
    
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
            <h1 className="dave-title">
                Dave's Odds
            </h1>
            {loading && <p>Loading...</p>}
            {error && <p>Error: {error}</p>}

            {!loading && !error && games.length === 0 && (
                <p>No games found.</p>
            )}
            {!loading && !error && games.map((game, index) => {
                // only get games up to the upcoming monday?
                const gameTimeLocal = new Date(game.commence_time);
                const nextTuesday = getNextTuesday();
                if(gameTimeLocal > nextTuesday){
                    return;
                }

                let showTimeSeparator = false;
                if(index > 0){
                    const previousGame = games[index - 1];
                    if(previousGame.commence_time != game.commence_time){
                        showTimeSeparator = true;
                    }
                }else{
                    showTimeSeparator = true;
                }
                
                return (
                    <div key={index}>
                        {showTimeSeparator && <TimeSeparator game={game} />}
                        <GameRow key={index} game={game} />
                    </div>

                    // <div key={index} className="odds-wrapper">
                    //     {showTimeSeparator && <TimeSeparator game={game} />}
                    //     <div className="odds-headers-wrapper">
                    //         <div className="odds-header" style={{visibility:'hidden'}}></div>
                    //         <div className="odds-header">Spread</div>
                    //         <div className="odds-header">Moneyline</div>
                    //         <div className="odds-header">O/U</div>
                    //     </div>
                    //     <div className="odds-items-wrapper">
                    //         <div className="teams-wrapper teams-column">
                    //             {/* away team abbreviation*/}
                    //             <div className="teams-name" style={{color:nflTeams[game.away_team].colors.away,"--stroke-color":nflTeams[game.away_team].colors.home}}>
                    //                 {nflTeams[game.away_team].abbrv}
                    //             </div>

                    //             <div className="teams-at">@</div>

                    //             {/* home team abbreviation*/}
                    //             <div className="teams-name" style={{color:nflTeams[game.home_team].colors.home, "--stroke-color":nflTeams[game.home_team].colors.accent,zIndex:1}}>
                    //                 {nflTeams[game.home_team].abbrv}
                    //             </div>
                    //         </div>
                            
                    //         <div className="spread-wrapper odds-column">
                    //             <div className="column-value">{formatSignedNumber(spreadAway.point)}</div>
                    //             <div className="column-separator"></div>
                    //             <div className="column-value">{formatSignedNumber(spreadHome.point)}</div>
                    //         </div>

                    //         <div className="ml-wrapper odds-column">
                    //             <div className="column-value">{formatSignedNumber(mlAway.price)}</div>
                    //             <div className="column-separator"></div>
                    //             <div className="column-value">{formatSignedNumber(mlHome.price)}</div>
                    //         </div>

                    //         <div className="ou-wrapper odds-column">
                    //             <div className="column-value">O {ouOver.point}</div>
                    //             <div className="column-separator"></div>
                    //             <div className="column-value">U {ouOver.point}</div>
                    //         </div>
                    //     </div>
                    // </div>
                );
            })}
        </div>
    );
}
export default Odds