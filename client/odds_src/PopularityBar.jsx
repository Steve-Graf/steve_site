import './GameCard.css';
import { useState } from 'react';
import { nflTeams } from './data/nflTeams';
import GamePickersPopup from './GamePickersPopup.jsx';

const MIN_VISIBLE_PERCENT = 8;

function computeSegments(awayCount, homeCount) {
    const total = awayCount + homeCount;
    if (total === 0) {
        return null;
    }
    const awayPct = Math.round((awayCount / total) * 100);
    const homePct = 100 - awayPct;
    let awayWidth = awayPct;
    let homeWidth = homePct;
    if (awayCount > 0 && awayWidth < MIN_VISIBLE_PERCENT) {
        awayWidth = MIN_VISIBLE_PERCENT;
        homeWidth = 100 - MIN_VISIBLE_PERCENT;
    } else if (homeCount > 0 && homeWidth < MIN_VISIBLE_PERCENT) {
        homeWidth = MIN_VISIBLE_PERCENT;
        awayWidth = 100 - MIN_VISIBLE_PERCENT;
    }
    return { awayPct, homePct, awayWidth, homeWidth };
}

const EYE = (
    <svg className="gc-pop-eye" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
        <path d="M12 5C7.52 5 3.73 7.94 2.46 12c1.27 4.06 5.06 7 9.54 7s8.27-2.94 9.54-7C20.27 7.94 16.48 5 12 5Z" />
    </svg>
);

export default function PopularityBar({ game }) {
    const [showPickers, setShowPickers] = useState(false);
    const segments = computeSegments(game.awayPickCount || 0, game.homePickCount || 0);
    const awayName = nflTeams[game.awayTeam]?.abbrv || game.awayTeam;
    const homeName = nflTeams[game.homeTeam]?.abbrv || game.homeTeam;
    const awayColor = nflTeams[game.awayTeam]?.colors?.home;
    const homeColor = nflTeams[game.homeTeam]?.colors?.home;
    const label = segments
        ? `Popularity: ${awayName} ${segments.awayPct} percent, ${homeName} ${segments.homePct} percent. Show who picked each team.`
        : 'Popularity: no picks yet. Show who picked each team.';

    return (
        <>
            <button type="button" className="gc-pop" aria-label={label} onClick={() => setShowPickers(true)}>
                {segments ? (
                    <span className="gc-pop-row">
                        <span className="gc-pop-pct">{segments.awayPct}%</span>
                        <span className="gc-pop-bar">
                            <i style={{ width: `${segments.awayWidth}%`, background: awayColor }} />
                            <i style={{ width: `${segments.homeWidth}%`, background: homeColor }} />
                        </span>
                        <span className="gc-pop-pct">{segments.homePct}%</span>
                        {EYE}
                    </span>
                ) : (
                    <span className="gc-pop-row">
                        <span className="gc-pop-empty">No picks yet</span>
                        {EYE}
                    </span>
                )}
            </button>
            {showPickers && (
                <GamePickersPopup gameId={game.gameId} backgroundClick={() => setShowPickers(false)} />
            )}
        </>
    );
}
