import './Odds.css';

function getRandomLineColor(){
    const lineColors = ['yellow'];
    const randomIndex = Math.floor(Math.random() * lineColors.length);
    return lineColors[randomIndex];
}

export default function TimeSeparator({game}) {
    const gameTimeLocal = new Date(game.gameTime);
    const dateFormatOptions = {
        weekday: "short",
        month: "numeric",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
    };
    const lineColor = getRandomLineColor();
    return (
        <div className="time-separator">
            <div className='time-separator-line' style={{backgroundColor:lineColor}}></div>
            <span className="time-separator-text">{gameTimeLocal.toLocaleString(undefined, dateFormatOptions)}</span>
            <div className='time-separator-line' style={{backgroundColor:lineColor}}></div>
        </div>
    );
}