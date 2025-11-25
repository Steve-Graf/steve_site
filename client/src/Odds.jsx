import React, {useState, useEffect } from 'react';
import './Odds.css';
import TimeSeparator from './TimeSeparator';
import GameRow from './GameRow.jsx';

const API_URL = import.meta.env.VITE_API_URL;

function getNextTuesday() {
    const now = new Date();
    const day = now.getDay();
    
    const daysUntilTuesday = (9 - day) % 7 || 7;
    const nextTuesday = new Date(now);
    nextTuesday.setDate(now.getDate() + daysUntilTuesday);
    nextTuesday.setHours(0, 0, 0, 0);
    return nextTuesday;
}

function generateRandomFourCharString() {
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789';
    let result = '';
    const charactersLength = characters.length;
    for (let i = 0; i < 4; i++) {
    result += characters.charAt(Math.floor(Math.random() * charactersLength));
    }
    return result;
}

function getLocalStorageUserCode(){
    let userCode = localStorage.getItem('userCode', null);
    if(userCode == null || userCode == 'null'){
        userCode = generateRandomFourCharString();
        localStorage.setItem('userCode', userCode);
    }
    return userCode;
}

function getSelectedTeam(currentGame){
    if(typeof currentGame == 'undefined'){
        return "";
    }
    if(typeof currentGame['selectedTeam'] != 'undefined'){
        return currentGame['selectedTeam'];
    }
    return "";
}

function calculateShowTimeSeparator(previousGame, currentGame, minutesMargin){
    const previousGameTime = new Date(previousGame.gameTime);
    const currentGameTime = new Date(currentGame.gameTime);
    const diffMs = Math.abs(previousGameTime - currentGameTime);
    const diffMins = diffMs / (1000 * 60);
    if(diffMins > minutesMargin){
        return true;
    }
    return false;
}

function Odds() {
    const [games, setGames] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [userLoading, setUserLoading] = useState(true);
    const [userError, setUserError] = useState(null);
    const [userData, setUserData] = useState([]);
    
    // useEffect Hook runs after the component renders
    useEffect(() => {
        // Define the async function inside the useEffect
        const fetchGameOdds = async () => {
            try {
                const response = await fetch(API_URL+'sport/NFL');
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

        const localStorageUserCode = getLocalStorageUserCode();
        const fetchPicksByCode = async () => {
            try {
                const response = await fetch(API_URL+'player/'+localStorageUserCode);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                if(data.error){
                    setUserError(data.error);
                    setUserLoading(false);
                    return;
                }
                console.log(data);
                setUserData(data);
            } catch (e) {
                console.error('Failed to fetch game odds:', e);
                setUserError(e.message);
            } finally {
                setUserLoading(false);
            }
        };
        fetchPicksByCode();
    }, []);

    return (
        <div>
            <h1 className="dave-title">
                Dave's Odds
            </h1>
            {(loading || userLoading) && <p>Loading...</p>}
            {(error || userError) && <p>Error: {error}</p>}

            {!loading && !error && games.length === 0 && (
                <p>No games found.</p>
            )}
            {!loading && !error && !userLoading && !userError && games.map((game, index) => {
                // only get games up to the upcoming monday?
                const gameTimeLocal = new Date(game.commence_time);
                const nextTuesday = getNextTuesday();
                if(gameTimeLocal > nextTuesday){
                    return;
                }

                let showTimeSeparator = false;
                let minutesMargin = 10
                if(index > 0){
                    const previousGame = games[index - 1];
                    showTimeSeparator = calculateShowTimeSeparator(previousGame, game, minutesMargin);
                }else{
                    showTimeSeparator = true;
                }

                const selectedTeam = getSelectedTeam(userData['picks'][game.gameId]);

                return (
                    <div key={index}>
                        {showTimeSeparator && <TimeSeparator game={game} />}
                        <GameRow key={index} game={game} selectedTeam={selectedTeam} />
                    </div>
                );
            })}
        </div>
    );
}
export default Odds