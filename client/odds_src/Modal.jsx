import './Odds.css';
import useLockBodyScroll from './useLockBodyScroll.js';

// showClose={false} for modals that already end in their own close button ("Got it")
export default function Modal({ onClose, className = '', showClose = true, children }) {
    useLockBodyScroll();
    return (
        <div className="popup-wrapper">
            <div className="popup-background" onClick={onClose}></div>
            <div className={`popup-content ${className}`.trim()}>
                {showClose && (
                    <button type="button" className="popup-close" aria-label="Close" onClick={onClose}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
                            <path d="M6 6l12 12" />
                            <path d="M18 6L6 18" />
                        </svg>
                    </button>
                )}
                <div className="popup-scroll">
                    {children}
                </div>
            </div>
        </div>
    );
}
