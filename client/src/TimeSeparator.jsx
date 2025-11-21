import './Odds.css';

export default function TimeSeparator({game}) {
    const gameTimeLocal = new Date(game.commence_time);
    const dateFormatOptions = {
        weekday: "short",
        month: "numeric",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
    };
    return (
        <div className="time-separator">
            {gameTimeLocal.toLocaleString(undefined, dateFormatOptions)}
        </div>
    );
}