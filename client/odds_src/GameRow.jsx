import './Odds.css';
import TeamColumn from './TeamColumn.jsx';
import OddsColumn from './OddsColumn.jsx';
import ScoreColumn from './ScoreColumn.jsx';
import PopularityColumn from './PopularityColumn.jsx';

function formatSignedNumber(number, reciprocal){
    if(reciprocal){
        number *= -1;
    }
    if(number > 0){
        return '+'+number;
    }else{
        return number;
    }
}

export default function GameRow({game, selectedTeam, isFirstUpcomingGame}) {
    const awaySpread = formatSignedNumber(game.gameSpread, game.gameSpreadTeam != game.awayTeam);
    const homeSpread = formatSignedNumber(game.gameSpread, game.gameSpreadTeam != game.homeTeam);
    const currentTime = new Date();
    const gameTimeLocal = new Date(game.gameTime);
    return (
        <div className="odds-items-wrapper">
            <TeamColumn game={game} />

            <ScoreColumn
                awayScore={game.awayScore}
                homeScore={game.homeScore}
            />

            <OddsColumn
                gameId={game.gameId}
                awayTeam={game.awayTeam}
                homeTeam={game.homeTeam}
                label="Spread"
                values={[awaySpread, homeSpread]}
                canClick={currentTime < gameTimeLocal}
                selectedTeam={selectedTeam}
                gameDate={game.gameTime}
                isFirstUpcomingGame={isFirstUpcomingGame}
                homeScore={game.homeScore}
                awayScore={game.awayScore}
                gameSpread={game.gameSpread}
                gameSpreadTeam={game.gameSpreadTeam}
            />

            <PopularityColumn
                gameId={game.gameId}
                awayTeam={game.awayTeam}
                homeTeam={game.homeTeam}
                awayPickCount={game.awayPickCount}
                homePickCount={game.homePickCount}
            />

            {/* <OddsColumn
                label="Moneyline"
                values={[mlAway.price, mlHome.price]}
                canClick={false}
            /> */}

            {/* hidden for now — not interactive yet, may revisit later
            <OddsColumn
                label="O/U"
                values={[`O ${game.ouPoints}`, `U ${game.ouPoints}`]}
                canClick={false}
            /> */}
        </div>
    );
}