import React, {useState, useMemo, useContext} from 'react';
import './Odds.css';
import ColumnEntry from './ColumnEntry.jsx';
import AppContext from './AppContext.jsx';
const API_URL = import.meta.env.VITE_API_URL;
import {showAlert} from './alerts.js';
import {authFetch} from './api.js';

// mirrors the backend's _grade_ats_pick() in odds/odds_routes.py exactly
// (including: a push counts as a win for whichever team was picked) so the
// board doesn't need a separate poll just to know if your pick is winning —
// everything it needs is already in the props from the board's own refresh.
function computeIsWinning({ homeScore, awayScore, gameSpread, gameSpreadTeam, homeTeam, awayTeam, gameDate, selectedTeam }){
    if(!selectedTeam){
        return -1;
    }
    if(new Date(gameDate) > new Date()){
        return -1;
    }
    const homeScoreNum = parseFloat(homeScore);
    const awayScoreNum = parseFloat(awayScore);
    if(Number.isNaN(homeScoreNum) || Number.isNaN(awayScoreNum)){
        return -1;
    }

    let homePoints = homeScoreNum;
    let awayPoints = awayScoreNum;
    const spread = gameSpread || 0;
    if(gameSpreadTeam === homeTeam){
        homePoints += spread;
    }else if(gameSpreadTeam === awayTeam){
        awayPoints += spread;
    }

    let spreadCoverer = 'Push';
    if(homePoints > awayPoints){
        spreadCoverer = homeTeam;
    }else if(awayPoints > homePoints){
        spreadCoverer = awayTeam;
    }

    return (spreadCoverer === 'Push' || selectedTeam === spreadCoverer) ? 1 : 0;
}

function formatDate(date){
    const d = new Date(date);
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const year = d.getFullYear();

    return `${month}/${day}/${year}`;
}

async function updateGamePick(gameId, awayTeam, homeTeam, selectedTeam, spread, date){
    try {
        const pickData = {
            gameId: gameId,
            awayTeam: awayTeam,
            homeTeam: homeTeam,
            selectedTeam: selectedTeam,
            gameSpread: spread,
            gameDate: formatDate(date)
        };
        const response = await authFetch(API_URL+'update-pick', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(pickData)
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log(data);
        showAlert("Pick updated.");
    } catch (e) {
        console.error('Failed to fetch game odds:', e);
    } finally {
        console.log('update finished');
    }
}

export default function OddsColumn({ gameId, awayTeam, homeTeam, selectedTeam, label, values, gameDate, canClick, isFirstUpcomingGame, homeScore, awayScore, gameSpread, gameSpreadTeam }) {
    const { signedIn, userData, refreshUserData } = useContext(AppContext);
    const [selected, setSelected] = useState(null);
    const noPicksYet = signedIn && Object.keys(userData?.picks || {}).length === 0;
    const showHint = label === 'Spread' && isFirstUpcomingGame && canClick && noPicksYet;
    // derived straight from props already refreshed by the board's own poll —
    // no separate network call needed just to know if the pick is winning
    const isWinning = useMemo(
        () => computeIsWinning({ homeScore, awayScore, gameSpread, gameSpreadTeam, homeTeam, awayTeam, gameDate, selectedTeam }),
        [homeScore, awayScore, gameSpread, gameSpreadTeam, homeTeam, awayTeam, gameDate, selectedTeam]
    );
    // this function is passed to the child element, so that setSelected is called here
    const handleClick = async (spreadValueIndex, entry) => {
        if(selected == entry){
            return;
        }
        if(entry != ""){
            if(!signedIn){
                showAlert("Please log in to make picks.", "warning");
                return;
            }
            if (selected === entry) {
                setSelected(null);
            } else {
                setSelected(entry);
            }
            let newSelectedTeam = ''
            if(entry == 'away'){
                newSelectedTeam = awayTeam;
            }else if(entry == 'home'){
                newSelectedTeam = homeTeam;
            }
            await updateGamePick(gameId, awayTeam, homeTeam, newSelectedTeam, values[spreadValueIndex], gameDate);
            if(refreshUserData){
                await refreshUserData();
            }
        }
    };

    return (
        <div className={`odds-column ${showHint ? 'odds-column-hint' : ''}`}>
            <div className="column-header">{label}</div>
            <ColumnEntry
                value={values[0]} isSelected={(label == 'Spread') && (selected == "away" || (selectedTeam == awayTeam && selected == null))}
                onClick={() => canClick ? handleClick(0, "away") : handleClick(-1, "")}
                winning = {!canClick ? isWinning : -1}
            />
            <div className="column-separator"></div>
            <ColumnEntry
                value={values[1]} isSelected={(label == 'Spread') && (selected == "home" || (selectedTeam == homeTeam && selected == null))}
                onClick={() => canClick ? handleClick(1, "home") : handleClick(-1, "")}
                winning = {!canClick ? isWinning : -1}
            />
        </div>
    );
}