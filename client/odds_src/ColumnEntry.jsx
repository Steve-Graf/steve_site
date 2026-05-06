import './Odds.css';

export default function ColumnEntry({ value, isSelected, onClick, winning }) {
    // console.log(isWinning);
    return(
        <div
            key={value}
            className={`column-value ${isSelected ? "column-value-selected" : ""} ${winning === 1 ? "column-status-win" : winning === 0 ? "column-status-lose" : ""}`}
            onClick={onClick}
        >
            {value}
        </div>
    )
}