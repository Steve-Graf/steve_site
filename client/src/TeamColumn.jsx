import './Odds.css';
import {nflTeams} from "./data/nflTeams"

export default function TeamColumn({game}) {
    return (
        <div className="teams-wrapper teams-column">
            <div className="teams-name" style={{color:nflTeams[game.awayTeam].colors.accent,"--stroke-color":nflTeams[game.awayTeam].colors.home}}>
                {nflTeams[game.awayTeam].abbrv}
            </div>

            <div className="teams-at">@</div>

            {/* home team abbreviation*/}
            <div className="teams-name" style={{color:nflTeams[game.homeTeam].colors.home, "--stroke-color":nflTeams[game.homeTeam].colors.accent,zIndex:1}}>
                {nflTeams[game.homeTeam].abbrv}
            </div>
        </div>
    );
}