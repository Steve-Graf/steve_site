import './Odds.css';
import { useEffect, useRef, useState } from "react";
import { authFetch } from './api.js';
import { nflTeams } from './data/nflTeams';
import Modal from './Modal.jsx';
const API_URL = import.meta.env.VITE_API_URL;

const SCROLL_END_SLOP_PX = 2;

function renderList(pickers){
    if(pickers.length === 0){
        return <div className="pickers-empty">No picks yet</div>;
    }
    return pickers.map((p, i) => (
        <div className={`pickers-name-row ${p.isYou ? 'pickers-name-row-you' : ''}`} key={i}>
            {p.displayName}{p.isYou && <span className="pickers-you-tag">you</span>}
        </div>
    ));
}

export default function GamePickersPopup({ gameId, backgroundClick }) {
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState(null);
    const [showScrollFade, setShowScrollFade] = useState(false);
    const listsRef = useRef(null);

    useEffect(() => {
        (async () => {
            try {
                const response = await authFetch(API_URL + 'game-pickers/' + gameId);
                const json = await response.json();
                if (!json.error) {
                    setData(json);
                }
            } catch (e) {
                console.error('Failed to fetch game pickers:', e);
            } finally {
                setLoading(false);
            }
        })();
    }, [gameId]);

    function updateScrollFade(){
        const el = listsRef.current;
        if(!el) return;
        const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - SCROLL_END_SLOP_PX;
        setShowScrollFade(el.scrollHeight > el.clientHeight && !atBottom);
    }

    useEffect(() => {
        updateScrollFade();
    }, [data]);

    const homeColor = data ? nflTeams[data.homeTeam]?.colors?.accent : null;
    const awayColor = data ? nflTeams[data.awayTeam]?.colors?.home : null;
    const homeAbbrv = data ? (nflTeams[data.homeTeam]?.abbrv || data.homeTeam) : '';
    const awayAbbrv = data ? (nflTeams[data.awayTeam]?.abbrv || data.awayTeam) : '';

    return (
        <Modal onClose={backgroundClick} className="pickers-popup-content">
            <div className="popup-title">Who Picked What</div>

            {loading && <div className="popup-description">Loading...</div>}

            {!loading && !data && (
                <div className="popup-description">Couldn't load picks for this game.</div>
            )}

            {!loading && data && (
                <>
                    <div className="pickers-halves">
                        <div className="pickers-half">
                            <div className="pickers-team-header" style={{borderColor: awayColor}}>
                                <span>{awayAbbrv}</span>
                                <span className="pickers-team-count">{data.awayCount} pick{data.awayCount === 1 ? '' : 's'}</span>
                            </div>
                        </div>
                        <div className="pickers-half">
                            <div className="pickers-team-header" style={{borderColor: homeColor}}>
                                <span>{homeAbbrv}</span>
                                <span className="pickers-team-count">{data.homeCount} pick{data.homeCount === 1 ? '' : 's'}</span>
                            </div>
                        </div>
                    </div>
                    <div className="pickers-scroll-wrap">
                        <div className="pickers-name-lists" ref={listsRef} onScroll={updateScrollFade}>
                            <div className="pickers-name-list">
                                {renderList(data.awayPickers)}
                            </div>
                            <div className="pickers-name-list">
                                {renderList(data.homePickers)}
                            </div>
                        </div>
                        {showScrollFade && <div className="pickers-scroll-fade"></div>}
                    </div>
                </>
            )}
        </Modal>
    );
}
