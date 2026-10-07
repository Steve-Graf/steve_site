import './Odds.css';
import Modal from './Modal.jsx';

function joinNames(names) {
    if (names.length === 0) return '';
    if (names.length === 1) return names[0];
    if (names.length === 2) return `${names[0]} and ${names[1]}`;
    return `${names.slice(0, -1).join(', ')}, and ${names[names.length - 1]}`;
}

export default function WeeklyRecapPopup({ recap, backgroundClick }) {
    return (
        <Modal onClose={backgroundClick} className="recap-popup-content" showClose={false}>
            <div className="popup-title">Week {recap.week} Recap</div>

            <div className="recap-sections">
                {recap.yourRecord && (
                    <div className="recap-section">
                        <div className="recap-section-label">Your record last week</div>
                        <div className="recap-section-line">
                            {recap.yourRecord.name} — {recap.yourRecord.wins}-{recap.yourRecord.losses}
                        </div>
                    </div>
                )}

                {recap.bestRecord && (
                    <div className="recap-section">
                        <div className="recap-section-label">Best record last week</div>
                        {recap.bestRecord.entries.map((entry) => (
                            <div className="recap-section-line" key={entry.name}>
                                {entry.name} — {entry.wins}-{entry.losses}
                            </div>
                        ))}
                    </div>
                )}

                <div className="recap-section">
                    <div className="recap-section-label">Still undefeated in survivor</div>
                    <div className="recap-section-line">
                        {recap.survivorAlive.count > 0
                            ? `${recap.survivorAlive.count} player${recap.survivorAlive.count === 1 ? '' : 's'}: ${joinNames(recap.survivorAlive.names)}`
                            : "Nobody's undefeated anymore."}
                    </div>
                </div>

                {recap.upset && (
                    <div className="recap-section">
                        <div className="recap-section-label">Biggest upset</div>
                        <div className="recap-section-line">
                            Only {recap.upset.correctCount} of {recap.upset.totalCount} people picked {recap.upset.correctTeam} to cover in {recap.upset.awayTeam} @ {recap.upset.homeTeam}.
                        </div>
                        <div className="recap-section-line">
                            {recap.upset.correctNames.length > 0
                                ? `Correctly picked by: ${joinNames(recap.upset.correctNames)}.`
                                : 'Nobody picked it!'}
                        </div>
                    </div>
                )}
            </div>

            <div className="popup-button" onClick={backgroundClick}>Got it</div>
        </Modal>
    );
}
