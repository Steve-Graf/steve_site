import './GameCard.css';
import TeamBadge from './TeamBadge.jsx';
import PopularityBar from './PopularityBar.jsx';
import { nflTeams } from './data/nflTeams';
import { lineFor, displayLine, coverMargin } from './spread.js';

// The server decides a game's state. The one local override: lock the moment kickoff
// passes, so a tap in the gap before the next poll doesn't round-trip to a rejection.
function effectiveState(game) {
    const state = game.state || 'open';
    if (state === 'open' && new Date(game.gameTime) <= new Date()) {
        return 'live';
    }
    return state;
}

function resultOf(state, pickedSide, game) {
    if (!pickedSide || (state !== 'live' && state !== 'final')) {
        return null;
    }
    const margin = coverMargin(game, pickedSide);
    if (margin == null) {
        return null;
    }
    if (state === 'live') {
        return margin > 0 ? 'cov' : margin < 0 ? 'unc' : 'push';
    }
    return margin < 0 ? 'lost' : 'won'; // a push counts as a win
}

export default function GameCard({ game, selectedTeam, onPick }) {
    const state = effectiveState(game);
    const open = state === 'open';
    const scored = state === 'live' || state === 'final';
    const pickedSide = selectedTeam === game.awayTeam ? 'away' : selectedTeam === game.homeTeam ? 'home' : null;
    const result = resultOf(state, pickedSide, game);

    // One chip floats on the card's top edge, so it takes no room inside the card:
    // live shows the clock, postponed says so, and an open game says what to do (then confirms the pick).
    // A finished game has none; the final score and the green or red plate say the rest.
    let chip = null;
    if (state === 'live') {
        chip = (
            <span className="gc-chip gc-chip--live">
                <i className="gc-dot" />
                Live{game.clock ? ` · ${game.clock}` : ''}
            </span>
        );
    } else if (state === 'postponed') {
        chip = <span className="gc-chip gc-chip--muted">{game.clock || 'Postponed'}</span>;
    } else if (open) {
        chip = pickedSide
            ? <span className="gc-chip gc-chip--picked">✓ Picked</span>
            : <span className="gc-chip gc-chip--tap">Tap to pick</span>;
    }

    // Each team is a bug (name over logo) joined to a plate. The plate holds the score once there is one,
    // and the spread before that. The away side reads bug then plate and the home side plate then bug, so
    // the plates (scores or spreads) meet in the middle of the card.
    const renderTeam = (side) => {
        const team = side === 'home' ? game.homeTeam : game.awayTeam;
        const score = side === 'home' ? game.homeScore : game.awayScore;
        const selected = pickedSide === side;
        const line = displayLine(lineFor(game, team));
        const accent = nflTeams[team]?.colors?.accent;
        const style = accent ? { '--a': accent } : undefined;

        const bug = <TeamBadge team={team} />;
        const plate = (
            <span className="gc-plate">
                {scored ? (score != null ? score : '–') : line}
                {/* once the game has started the spread hangs off the picked team's plate */}
                {scored && selected && <span className="gc-line">{line}</span>}
            </span>
        );
        const body = side === 'away' ? <>{bug}{plate}</> : <>{plate}{bug}</>;

        if (open) {
            return (
                <button
                    type="button"
                    className={`gc-team${selected ? ' gc-pick gc-pend' : ''}`}
                    style={style}
                    aria-pressed={selected}
                    aria-label={selected ? `Your pick: ${team} ${line}` : `Pick ${team} ${line}`}
                    // a pick can be switched to the other team before kickoff, but not taken away:
                    // there is no penalty for a wrong pick, so tapping your own pick does nothing
                    onClick={() => { if (!selected) onPick(game, team); }}
                >
                    {body}
                </button>
            );
        }
        // postponed games have no score and no result yet, so a pick looks like it does before kickoff
        const pickClass = !selected ? '' : scored && result ? ` gc-pick gc-${result}` : ' gc-pick gc-pend';
        return (
            <div className={`gc-team gc-static${pickClass}`} style={style}>
                {body}
            </div>
        );
    };

    return (
        <article className={`gc-card${open ? ' gc-card--open' : ''}${scored ? ' gc-card--scored' : ''}${chip ? ' gc-card--chip' : ''}`}>
            {chip && <div className={`gc-top${open ? ' gc-top--center' : ''}`}>{chip}</div>}
            <div className="gc-teams">
                {renderTeam('away')}
                {renderTeam('home')}
            </div>
            <PopularityBar game={game} />
        </article>
    );
}
