// the picked team's line as the board has always sent and stored it: a negative
// number for the favorite, a "+3.5" string for the underdog (stats rely on the "+")
export function formatSignedNumber(number, reciprocal) {
    if (reciprocal) {
        number *= -1;
    }
    if (number > 0) {
        return '+' + number;
    }
    return number;
}

export function lineFor(game, team) {
    return formatSignedNumber(game.gameSpread, game.gameSpreadTeam !== team);
}

// for display only: a proper minus sign
export function displayLine(value) {
    return String(value).replace('-', '−');
}

// how far the team is from covering: positive covers, negative is short, zero is a push
export function coverMargin(game, side) {
    const team = side === 'home' ? game.homeTeam : game.awayTeam;
    const own = side === 'home' ? game.homeScore : game.awayScore;
    const opp = side === 'home' ? game.awayScore : game.homeScore;
    if (own == null || opp == null) {
        return null;
    }
    const line = game.gameSpreadTeam === team ? game.gameSpread : -game.gameSpread;
    return own - opp + line;
}
