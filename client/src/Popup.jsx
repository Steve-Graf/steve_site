import './Odds.css';

export default function Popup({title, description, backgroundClick}) {
    return (
        <div className="popup-wrapper">
            <div className="popup-background" onClick={backgroundClick}></div>
            <div className="popup-content">
                <div className="popup-title">{title}</div>
                <div className="popup-description" dangerouslySetInnerHTML={{ __html: description }}></div>
            </div>
        </div>
    );
}