import './Odds.css';
import {nflTeams} from "./data/nflTeams"

export default function TeamColumn({game}) {
    return (
        <div className="teams-wrapper teams-column">
            <div className="teams-name" style={{color:nflTeams[game.away_team].colors.away,"--stroke-color":nflTeams[game.away_team].colors.home}}>
                {nflTeams[game.away_team].abbrv}
            </div>

            <div className="teams-at">@</div>

            {/* home team abbreviation*/}
            <div className="teams-name" style={{color:nflTeams[game.home_team].colors.home, "--stroke-color":nflTeams[game.home_team].colors.accent,zIndex:1}}>
                {nflTeams[game.home_team].abbrv}
            </div>
        </div>
    );
}