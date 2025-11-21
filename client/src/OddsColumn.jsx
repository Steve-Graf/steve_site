import './Odds.css';

function formatSignedNumber(number){
    if(number > 0){
        return '+'+number;
    }else{
        return number;
    }
}

export default function OddsColumn({ label, values }) {
    return (
        <div className="odds-column">
            <div className="column-header">{label}</div>
            <div key={values[0]} className="column-value">
                {formatSignedNumber(values[0])}
            </div>
            <div className="column-separator"></div>
            <div key={values[1]} className="column-value">
                {formatSignedNumber(values[1])}
            </div>
        </div>
    );
}