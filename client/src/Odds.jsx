import React, {useState, useEffect } from 'react';
import './Odds.css';

const API_URL = 'http://localhost:5000/api/odds/'

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
                console.error("Failed to fetch game odds:", e);
                setError(e.message);
            } finally {
                setLoading(false);
            }
            console.log(games);
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
                const bookmaker = game.bookmakers.find(b => b.key === "draftkings");
                const spreadMarket = bookmaker?.markets.find(m => m.key === "spreads");
                const awayOutcome = spreadMarket?.outcomes.find(o => o.name === game.away_team);
                const homeOutcome = spreadMarket?.outcomes.find(o => o.name === game.home_team);

                return (
                    <div key={index} style={{ marginBottom: "1rem" }}>
                        <h3>{game.away_team} @ {game.home_team}</h3>
                        <p>{game.away_team}: {awayOutcome?.price ?? "N/A"}</p>
                        <p>{game.home_team}: {homeOutcome?.price ?? "N/A"}</p>
                    </div>
                );
            })}
        </div>
    );
}
export default Odds