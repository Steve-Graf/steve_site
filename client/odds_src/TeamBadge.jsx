import './GameCard.css';
import { nflTeams } from './data/nflTeams';
import { logoFor } from './logos.js';

// The team bug: the logo, centered, in the team's colors. The abbreviation is a small chip hanging off the
// bug's bottom edge; it is always rendered but only shown while the viewer has it switched on in Profile
// (on by default; the board gets a gc-board--abbr class), so nothing about the layout changes while it is off.
export default function TeamBadge({ team }) {
    const info = nflTeams[team];
    const label = info ? info.abbrv : team;
    const logo = info ? logoFor(info.abbrv) : null;
    const style = info ? { '--c': info.colors.home, '--a': info.colors.accent } : undefined;
    return (
        <span className="gc-badge" style={style}>
            {logo && <img src={logo} alt="" width="40" height="40" />}
            <span className="gc-abbr">{label}</span>
        </span>
    );
}
