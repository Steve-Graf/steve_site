import './Odds.css';

export default function ColumnEntry({ value, isSelected, onClick }) {
    return(
        <div key={value} className={`column-value ${isSelected ? "column-value-selected" : ""}`} onClick={onClick}>
            {value}
        </div>
    )
}