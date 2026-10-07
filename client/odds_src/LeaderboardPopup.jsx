import './Odds.css';
import { useEffect, useState } from "react";
import { authFetch } from './api.js';
import Modal from './Modal.jsx';
const API_URL = import.meta.env.VITE_API_URL;

export default function LeaderboardPopup({backgroundClick}) {
    const [loading, setLoading] = useState(true);
    const [entries, setEntries] = useState([]);

    useEffect(() => {
        (async () => {
            try {
                const response = await authFetch(API_URL+'leaderboard');
                const data = await response.json();
                setEntries(data.entries || []);
            } catch (e) {
                console.error('Failed to fetch leaderboard:', e);
            } finally {
                setLoading(false);
            }
        })();
    }, []);

    return (
        <Modal onClose={backgroundClick} className="leaderboard-popup-content">
            <div className="popup-title">Leaderboard</div>
            <div className="popup-description leaderboard-subtitle">Most correct picks against the spread</div>

            {loading && <div className="popup-description">Loading...</div>}

            {!loading && entries.length === 0 && (
                <div className="popup-description">No picks with a final score yet.</div>
            )}

            {!loading && entries.length > 0 && (
                <div className="leaderboard-list">
                    {entries.map((entry) => (
                        <div className={`leaderboard-row ${entry.isYou ? 'leaderboard-row-you' : ''}`} key={entry.rank}>
                            <div className="leaderboard-rank">{entry.rank}</div>
                            <div className="leaderboard-name">
                                {entry.displayName}{entry.isYou && <span className="leaderboard-you-tag">you</span>}
                            </div>
                            <div className="leaderboard-record">{entry.wins}-{entry.losses}</div>
                        </div>
                    ))}
                </div>
            )}
        </Modal>
    );
}
