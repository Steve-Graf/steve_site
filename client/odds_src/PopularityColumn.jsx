import './Odds.css';
import { useState } from 'react';
import { nflTeams } from './data/nflTeams';
import GamePickersPopup from './GamePickersPopup.jsx';

const MIN_VISIBLE_PERCENT = 8;
const MIN_LABEL_PERCENT = 30;

function computeSegments(awayCount, homeCount){
    const total = awayCount + homeCount;
    if(total === 0){
        return { awayPct: 0, homePct: 0, awayRawPct: 0, homeRawPct: 0, hasData: false };
    }
    const awayRawPct = (awayCount / total) * 100;
    const homeRawPct = 100 - awayRawPct;
    let awayPct = awayRawPct;
    let homePct = homeRawPct;
    if(awayCount > 0 && awayPct < MIN_VISIBLE_PERCENT){
        awayPct = MIN_VISIBLE_PERCENT;
        homePct = 100 - MIN_VISIBLE_PERCENT;
    }else if(homeCount > 0 && homePct < MIN_VISIBLE_PERCENT){
        homePct = MIN_VISIBLE_PERCENT;
        awayPct = 100 - MIN_VISIBLE_PERCENT;
    }
    return { awayPct, homePct, awayRawPct, homeRawPct, hasData: true };
}

export default function PopularityColumn({ gameId, awayTeam, homeTeam, awayPickCount, homePickCount }) {
    const [showPickers, setShowPickers] = useState(false);
    const awayCount = awayPickCount || 0;
    const homeCount = homePickCount || 0;
    const { awayPct, homePct, awayRawPct, homeRawPct, hasData } = computeSegments(awayCount, homeCount);

    // matches the --stroke-color used for each team's abbreviation in TeamColumn.jsx
    const awayColor = nflTeams[awayTeam]?.colors?.home;
    const homeColor = nflTeams[homeTeam]?.colors?.accent;
    // the team's other color, for the percentage label against its own bar
    const awayTextColor = nflTeams[awayTeam]?.colors?.accent;
    const homeTextColor = nflTeams[homeTeam]?.colors?.home;
    const awayAbbrv = nflTeams[awayTeam]?.abbrv || awayTeam;
    const homeAbbrv = nflTeams[homeTeam]?.abbrv || homeTeam;
    const showAwayPct = hasData && awayRawPct >= MIN_LABEL_PERCENT;
    const showHomePct = hasData && homeRawPct >= MIN_LABEL_PERCENT;

    return (
        <div className="odds-column">
            <div className="popularity-clickable" onClick={() => setShowPickers(true)}>
                <div className="column-header">Popularity</div>
                <div className="popularity-bar-wrapper">
                    {hasData ? (
                        <>
                            <div
                                className="popularity-bar-segment"
                                style={{ height: `${awayPct}%`, background: awayColor }}
                                title={`${awayAbbrv}: ${awayCount} pick${awayCount === 1 ? '' : 's'}`}
                            >
                                {showAwayPct && (
                                    <span className="popularity-bar-pct" style={{ color: awayTextColor }}>
                                        {Math.round(awayRawPct)}%
                                    </span>
                                )}
                            </div>
                            <div
                                className="popularity-bar-segment"
                                style={{ height: `${homePct}%`, background: homeColor }}
                                title={`${homeAbbrv}: ${homeCount} pick${homeCount === 1 ? '' : 's'}`}
                            >
                                {showHomePct && (
                                    <span className="popularity-bar-pct" style={{ color: homeTextColor }}>
                                        {Math.round(homeRawPct)}%
                                    </span>
                                )}
                            </div>
                        </>
                    ) : (
                        <div className="popularity-bar-empty">No picks yet</div>
                    )}
                </div>
            </div>
            {showPickers && (
                <GamePickersPopup gameId={gameId} backgroundClick={() => setShowPickers(false)} />
            )}
        </div>
    );
}
