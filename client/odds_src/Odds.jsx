import React, {useState, useEffect, useRef } from 'react';
import './Odds.css';
import TimeSeparator from './TimeSeparator';
import GameRow from './GameRow.jsx';
import GameCard from './GameCard.jsx';
import HelpPopup from './HelpPopup.jsx';
import MenuButton from './MenuButton.jsx';
import WeeklyRecapPopup from './WeeklyRecapPopup.jsx';
import AppContext from './AppContext.jsx';
import { authFetch, POLL_INTERVAL_MS, LIVE_POLL_INTERVAL_MS } from './api.js';
import { showAlert } from './alerts.js';
import { lineFor } from './spread.js';
import { useShowAbbrevs } from './prefs.js';

const RECAP_SEEN_WEEK_KEY = 'odds-recap-seen-week';

const API_URL = import.meta.env.VITE_API_URL;

// the redesigned board is the default; /odds/?old=1 brings back the previous row layout
const useNewBoard = new URLSearchParams(window.location.search).get('old') !== '1';

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

function showSeparatorAt(games, index){
    return index === 0 || calculateShowTimeSeparator(games[index - 1], games[index], 10);
}

// when to poll next: fast while a game is live (the API serves the clock/score from
// memory), and never later than a kickoff so a card flips to live right on time
function nextPollDelay(gamesArray){
    let delay = gamesArray.some((game) => game.state === 'live') ? LIVE_POLL_INTERVAL_MS : POLL_INTERVAL_MS;
    const nowMs = Date.now();
    for(const game of gamesArray){
        const untilKickoff = new Date(game.gameTime).getTime() - nowMs;
        if(untilKickoff > 0 && untilKickoff + 2000 < delay){
            delay = untilKickoff + 2000;
        }
    }
    return delay;
}

function Odds() {
    const showAbbrevs = useShowAbbrevs();
    const [signedIn, setSignedIn] = useState(false);
    const [games, setGames] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showPopup, setShowPopup] = useState(true);
    const [error, setError] = useState(null);
    const [userLoading, setUserLoading] = useState(true);
    const [userError, setUserError] = useState(null);
    const [userData, setUserData] = useState([]);
    const [recap, setRecap] = useState(null);
    const [showRecap, setShowRecap] = useState(false);
    // a tapped pick shows immediately; dropped once the server answers
    const [pendingPicks, setPendingPicks] = useState({});
    const refreshGamesRef = useRef(() => {});

    function handleRecapClose(){
        if(recap){
            localStorage.setItem(RECAP_SEEN_WEEK_KEY, String(recap.week));
        }
        setShowRecap(false);
    }

    function getShowPopup(){
        let showPopup = localStorage.getItem('showPopup', true);
        if(showPopup == null || showPopup == 'null' || showPopup === 'true' || showPopup == true){
            localStorage.setItem('showPopup', false);
        }
        setShowPopup(showPopup === 'true');
    }

    function handlePopupBackgroundClick(){
        setShowPopup(false);
    }

    // /player/me doubles as the sign-in check: a 401 means signed out
    // exposed via context so a successful pick can refresh userData.picks
    // immediately, instead of waiting on a full page reload
    const fetchUserData = async () => {
        try {
            const response = await authFetch(API_URL+'player/me');
            if(response.status === 401){
                setSignedIn(false);
                return;
            }
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            if(data.error){
                setUserError(data.error);
                return;
            }
            setUserData(data);
            setSignedIn(true);
        } catch (e) {
            console.error('Failed to fetch user data:', e);
            setUserError(e.message);
        } finally {
            setUserLoading(false);
        }
    };

    // sets or switches a pick; there is no way to clear one (a wrong pick costs nothing)
    async function handlePick(game, team){
        if(!team){
            return;
        }
        if(!signedIn){
            showAlert("Please log in to make picks.", "warning");
            return;
        }
        setPendingPicks((pending) => ({ ...pending, [game.gameId]: team }));
        try {
            const response = await authFetch(API_URL+'update-pick', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    gameId: game.gameId,
                    homeTeam: game.homeTeam,
                    awayTeam: game.awayTeam,
                    selectedTeam: team,
                    gameSpread: lineFor(game, team),
                }),
            });
            if(response.status === 409){
                showAlert("That game has already started.", "warning");
                refreshGamesRef.current();
            }else if(!response.ok){
                throw new Error(`HTTP error! status: ${response.status}`);
            }else{
                showAlert("Pick updated.");
            }
            await fetchUserData();
        } catch (e) {
            console.error('Failed to save pick:', e);
            showAlert("Couldn't save your pick. Try again.", "warning");
        } finally {
            setPendingPicks((pending) => {
                const { [game.gameId]: _done, ...rest } = pending;
                return rest;
            });
        }
    }

    // useEffect Hook runs after the component renders
    useEffect(() => {
        let timer = null;
        let cancelled = false;
        let delay = POLL_INTERVAL_MS;

        // silent: true for background refreshes, so a transient failure doesn't
        // blank out an already-loaded board with an error message
        const fetchGameOdds = async ({ silent = false } = {}) => {
            try {
                const response = await authFetch(API_URL+'sport/NFL');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                if(data.error){
                    if(!silent){
                        setError(data.error);
                    }
                    return;
                }
                const gamesArray = Array.isArray(data) ? data : [data];
                setGames(gamesArray);
                delay = nextPollDelay(gamesArray);
            } catch (e) {
                console.error('Failed to fetch game odds:', e);
                if(!silent){
                    setError(e.message);
                }
            } finally {
                setLoading(false);
            }
        };

        // scores go stale otherwise — nothing else re-fetches after the initial load
        const tick = async ({ silent = true, force = false } = {}) => {
            clearTimeout(timer);
            if(force || document.visibilityState === 'visible'){
                await fetchGameOdds({ silent });
            }
            if(!cancelled){
                timer = setTimeout(() => tick(), delay);
            }
        };
        refreshGamesRef.current = () => tick();
        tick({ silent: false, force: true });

        const handleVisibilityChange = () => {
            if(document.visibilityState === 'visible'){
                tick();
            }
        };
        document.addEventListener('visibilitychange', handleVisibilityChange);

        fetchUserData();

        getShowPopup();

        return () => {
            cancelled = true;
            clearTimeout(timer);
            document.removeEventListener('visibilitychange', handleVisibilityChange);
        };
    }, []);

    // recap is open to everyone and shown automatically once per week. The server
    // reads the session cookie itself and only includes "yourRecord" for a signed-in
    // player who has a graded pick last week, so there's no need to wait on signedIn
    useEffect(() => {
        (async () => {
            try {
                const response = await authFetch(API_URL+'recap');
                const data = await response.json();
                if(data.available){
                    // always kept in state so the Recap menu button can re-open it
                    // later — only the auto-popup-on-load is gated by localStorage
                    setRecap(data);
                    if(localStorage.getItem(RECAP_SEEN_WEEK_KEY) !== String(data.week)){
                        setShowRecap(true);
                    }
                }
            } catch (e) {
                console.error('Failed to fetch weekly recap:', e);
            }
        })();
    }, []);

    const now = new Date();
    const firstUpcomingGameId = games.find((g) => new Date(g.gameTime) > now)?.gameId;

    return (
        <AppContext.Provider value={{ userData, signedIn, games, refreshUserData: fetchUserData }}>
            <div>
                <div id="alerts-wrapper"></div>
                <h1 className="dave-title">
                    Dave's Odds
                </h1>
                <div className="menu-buttons-wrapper">
                    <MenuButton id='profile' title={signedIn ? 'Profile' : 'Log In'}/>
                    <MenuButton id='stats' title={'Stats'}/>
                    <MenuButton id='survivor' title={'Survivor'}/>
                    <MenuButton id='points' title={'Leaderboard'}/>
                    {recap &&
                        <div onClick={() => setShowRecap(true)}><MenuButton id='recap' title={'Recap'}/></div>
                    }
                    <div onClick={() => setShowPopup(true)}><MenuButton id='help' title={'Help'}/></div>
                </div>
                {showPopup &&
                    <HelpPopup useNewBoard={useNewBoard} backgroundClick={handlePopupBackgroundClick}/>
                }
                {showRecap && recap && !showPopup &&
                    <WeeklyRecapPopup recap={recap} backgroundClick={handleRecapClose}/>
                }

                {(loading || userLoading) && <p className="status-p">Loading...</p>}
                {(error || userError) && <p className="status-p">Error: {error}</p>}

                {!loading && !error && games.length === 0 && (
                    <p className="status-p">No games found.</p>
                )}
                {useNewBoard && !loading && !error && !userLoading && !userError && (
                    <div className={`gc-board${showAbbrevs ? ' gc-board--abbr' : ''}`}>
                        {games.map((game, index) => {
                            const pending = Object.prototype.hasOwnProperty.call(pendingPicks, game.gameId);
                            const selectedTeam = pending
                                ? (pendingPicks[game.gameId] ?? '')
                                : getSelectedTeam(userData?.picks?.[game.gameId]);
                            return (
                                <div key={game.gameId}>
                                    {showSeparatorAt(games, index) && <TimeSeparator game={game} />}
                                    <GameCard game={game} selectedTeam={selectedTeam} onPick={handlePick} />
                                </div>
                            );
                        })}
                    </div>
                )}
                {!useNewBoard && !loading && !error && !userLoading && !userError && games.map((game, index) => {
                    let showTimeSeparator = false;
                    let minutesMargin = 10
                    if(index > 0){
                        const previousGame = games[index - 1];
                        showTimeSeparator = calculateShowTimeSeparator(previousGame, game, minutesMargin);
                    }else{
                        showTimeSeparator = true;
                    }

                    const selectedTeam = getSelectedTeam(userData?.picks?.[game.gameId]);

                    return (
                        <div key={index}>
                            {showTimeSeparator && <TimeSeparator game={game} />}
                            <GameRow
                                key={index}
                                game={game}
                                selectedTeam={selectedTeam}
                                isFirstUpcomingGame={game.gameId === firstUpcomingGameId}
                            />
                        </div>
                    );
                })}
            </div>
        </AppContext.Provider>
    );
}
export default Odds
