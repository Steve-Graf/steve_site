import React, {useState, useEffect, useMemo} from 'react';
import './Odds.css';
import ColumnEntry from './ColumnEntry.jsx';
const API_URL = import.meta.env.VITE_API_URL;

function formatDate(date){
    const d = new Date(date);
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const year = d.getFullYear();

    return `${month}/${day}/${year}`;
}

async function updateGamePick(gameId, awayTeam, homeTeam, selectedTeam, spread, date){
    const playerCode = localStorage.getItem('userCode');
    try {
        const pickData = {
            playerCode: playerCode,
            gameId: gameId,
            awayTeam: awayTeam,
            homeTeam: homeTeam,
            selectedTeam: selectedTeam,
            gameSpread: spread,
            gameDate: formatDate(date)
        };
        const response = await fetch(API_URL+'update-pick', {
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
    } catch (e) {
        console.error('Failed to fetch game odds:', e);
    } finally {
        console.log('update finished');
    }
}

export default function OddsColumn({ gameId, awayTeam, homeTeam, selectedTeam, label, values, gameDate, canClick }) {
    const [selected, setSelected] = useState(null);
    const [isWinning, setIsWinning] = useState(-1);
    // this function is passed to the child element, so that setSelected is called here
    const handleClick = async (spreadValueIndex, entry) => {
        if(selected == entry){
            return;
        }
        if(entry != ""){
            setIsWinning(-1);
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
        }
    };

    // useEffect Hook runs after the component renders
    useEffect(() => {
        // Define the async function inside the useEffect
        const fetchGameState = async () => {
            try {
                const gameData = {
                    playerCode: localStorage.getItem('userCode'),
                    gameId: gameId
                };
                const response = await fetch(API_URL+'game-state', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(gameData)
                });
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                if(data.error){
                    return;
                }
                if(data['game_state'] == 'win'){
                    setIsWinning(1);
                }else{
                    setIsWinning(0);
                }
            } catch (e) {
                console.error('Failed to fetch game state:', e);
            }
        };
        if(label == 'Spread'){
            fetchGameState();
        }
    }, []);

    return (
        <div className="odds-column">
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