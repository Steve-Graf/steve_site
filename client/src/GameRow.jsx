import './Odds.css';
import TeamColumn from './TeamColumn.jsx';
import OddsColumn from './OddsColumn.jsx';

export default function GameRow({game}) {
    const gameTimeLocal = new Date(game.commence_time);

    const bookmaker = game.bookmakers.find(bookmaker => bookmaker.key == 'draftkings');
    const spreadMarket = bookmaker.markets.find(market => market.key == 'spreads');
    const spreadAway = spreadMarket.outcomes.find(outcome => outcome.name == game.away_team);
    const spreadHome = spreadMarket.outcomes.find(outcome => outcome.name == game.home_team);

    const mlMarket = bookmaker.markets.find(market => market.key == 'h2h')
    const mlAway = mlMarket.outcomes.find(outcome => outcome.name == game.away_team);
    const mlHome = mlMarket.outcomes.find(outcome => outcome.name == game.home_team);

    const ouMarket = bookmaker.markets.find(market => market.key == 'totals')
    const ouOver = ouMarket.outcomes.find(outcome => outcome.name == 'Over');
    const ouUnder = ouMarket.outcomes.find(outcome => outcome.name == 'Under');

    return (
        <div className="odds-items-wrapper">
            <TeamColumn game={game} />

            <OddsColumn
                label="Spread"
                values={[spreadAway.point, spreadHome.point]}
            />

            <OddsColumn
                label="Moneyline"
                values={[mlAway.price, mlHome.price]}
            />

            <OddsColumn
                label="O/U"
                values={[`O ${ouOver.point}`, `U ${ouUnder.point}`]}
            />
        </div>
    );
}