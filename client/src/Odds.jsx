import React, {useState, useEffect } from 'react';
import './Odds.css';
import TimeSeparator from './TimeSeparator';
import GameRow from './GameRow.jsx';
import Popup from './Popup.jsx';
import MenuButton from './MenuButton.jsx';
import AppContext from './AppContext.jsx';

const API_URL = import.meta.env.VITE_API_URL;

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

async function getGameScores(gamesArr){
    const postData = {
        "games":gamesArr
    };
    console.log(API_URL+'scores');
    const response = await fetch(API_URL+'scores', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(postData)
    });
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    console.log(data['updatedGames']);
}

function Odds() {
    const [games, setGames] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showPopup, setShowPopup] = useState(true);
    const [error, setError] = useState(null);
    const [userLoading, setUserLoading] = useState(true);
    const [userError, setUserError] = useState(null);
    const [userData, setUserData] = useState([]);

    function getShowPopup(){
        let showPopup = localStorage.getItem('showPopup', true);
        if(showPopup == null || showPopup === 'true' || showPopup == true){
            localStorage.setItem('showPopup', false);
        }
        setShowPopup(showPopup === 'true');
    }

    function handlePopupBackgroundClick(){
        setShowPopup(false);
    }
    
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
                getGameScores(gamesArray);
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

        getShowPopup();
    }, []);

    return (
        <div>
            <AppContext.Provider value={{ userData }}>
                <MenuButton title={'Profile'}/>
            </AppContext.Provider>
            <h1 className="dave-title">
                Dave's Odds
            </h1>
            {showPopup && 
                <Popup title={'New here?'} description={'Welcome to a hobby project I set up for my dad, Dave.<br><br>To save your picks, click on the spread and O/U columns.<br><br>I\'ve assigned each new user a unique code. You can view this code in the "Profile" section. The "Profile" section is also where you can update your username for the leaderboards.<br><br>PLEASE NOTE: This code is unique and should be treated as your password. You can use this code to login to other devices.'} backgroundClick={handlePopupBackgroundClick}/>
            }
            
            {(loading || userLoading) && <p className="status-p">Loading...</p>}
            {(error || userError) && <p className="status-p">Error: {error}</p>}

            {!loading && !error && games.length === 0 && (
                <p className="status-p">No games found.</p>
            )}
            {!loading && !error && !userLoading && !userError && games.map((game, index) => {
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