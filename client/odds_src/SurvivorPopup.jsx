import './Odds.css';
import './Stats.css';
import { useContext, useEffect, useState } from "react";
import AppContext from "./AppContext.jsx";
import { authFetch } from './api.js';
import { showAlert } from './alerts.js';
import Modal from './Modal.jsx';
const API_URL = import.meta.env.VITE_API_URL;

function shortTeamName(fullName){
    if(!fullName) return fullName;
    const parts = fullName.trim().split(' ');
    return parts[parts.length - 1];
}

function hasStarted(game){
    return game && new Date(game.gameTime) <= new Date();
}

export default function SurvivorPopup({backgroundClick}) {
    const { games } = useContext(AppContext);
    const [state, setState] = useState(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);

    const fetchState = async () => {
        try {
            const response = await authFetch(API_URL+'survivor/state');
            const data = await response.json();
            if(data.error){
                showAlert(data.error, "warning");
                return;
            }
            setState(data);
        } catch (e) {
            console.error('Failed to fetch survivor state:', e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchState();
    }, []);

    async function pickTeam(gameId, selectedTeam){
        if(submitting) return;
        setSubmitting(true);
        try {
            const response = await authFetch(API_URL+'survivor/pick', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ gameId, selectedTeam })
            });
            const data = await response.json();
            if(data.error){
                showAlert(data.error, "warning");
                return;
            }
            showAlert("Survivor pick saved.");
            await fetchState();
        } catch (e) {
            console.error('Failed to submit survivor pick:', e);
        } finally {
            setSubmitting(false);
        }
    }

    // your pick for the week is locked in permanently once its own game kicks off —
    // even if other games in the week haven't started yet
    const currentPickGame = state?.currentPick
        ? (games || []).find((g) => g.gameId === state.currentPick.gameId)
        : null;
    const currentPickLocked = hasStarted(currentPickGame);
    const allGamesStarted = (games || []).length > 0 && (games || []).every((g) => hasStarted(g));

    function teamButton(game, team){
        const used = state.usedTeams.includes(team);
        const disabled = hasStarted(game) || currentPickLocked || used;
        return (
            <div
                className={`survivor-team-button ${state.currentPick?.selectedTeam === team ? 'survivor-team-selected' : ''}`}
                data-disabled={disabled}
                onClick={() => !disabled && pickTeam(game.gameId, team)}
            >
                {shortTeamName(team)}{used && ' (used)'}
            </div>
        );
    }

    return (
        <Modal onClose={backgroundClick} className="survivor-popup-content">
            <div className="popup-title">Survivor Pool{state ? ` — Week ${state.currentWeek}` : ''}</div>
            {!loading && state && (
                <>
                    <div className="popup-description leaderboard-subtitle">{state.stillUndefeated} player{state.stillUndefeated === 1 ? '' : 's'} {state.stillUndefeated === 1 ? 'is' : 'are'} still undefeated</div>
                    <div className="popup-description leaderboard-subtitle">You can continue to participate after losing, but you will not be eligible for the survivor pool reward.</div>
                </>
            )}

            {loading && <div className="popup-description">Loading...</div>}

            {!loading && state && (
                <>
                    {state.currentPick && (
                        <div className="survivor-current-pick">
                            Your pick: <span className="bold-span">{shortTeamName(state.currentPick.selectedTeam)}</span>
                            {currentPickLocked && ' (locked in)'}
                        </div>
                    )}
                    {!state.currentPick && allGamesStarted && (
                        <div className="survivor-current-pick">No pick made — this week's games have all started.</div>
                    )}
                    <div className="survivor-matchups-list">
                        {(games || []).map((game) => (
                            <div className="survivor-game-row" key={game.gameId}>
                                {teamButton(game, game.awayTeam)}
                                <div className="survivor-game-at">@</div>
                                {teamButton(game, game.homeTeam)}
                            </div>
                        ))}
                    </div>

                    {state.history.length > 0 && (
                        <>
                            <div className="popup-description" style={{marginTop: "15px"}}>History</div>
                            <div className="survivor-history-list">
                                {[...state.history].reverse().map((h) => (
                                    <div className="survivor-history-row" key={h.week}>
                                        <span>Week {h.week}</span>
                                        <span>{h.selectedTeam ? shortTeamName(h.selectedTeam) : 'No pick'}</span>
                                        <span className={`survivor-outcome-${h.outcome}`}>{h.outcome}</span>
                                    </div>
                                ))}
                            </div>
                        </>
                    )}
                </>
            )}
        </Modal>
    );
}
