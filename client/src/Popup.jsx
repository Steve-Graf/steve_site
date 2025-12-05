import './Odds.css';

export default function Popup({title, description}) {
    return (
        <div className="popup-background">
            <div className="popup-content">
                <div className="popup-title">{title}</div>
                <div className="popup-description" dangerouslySetInnerHTML={{ __html: description }}></div>
            </div>
        </div>
    );
}