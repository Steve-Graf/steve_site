import './Odds.css';
import './Stats.css';
import Modal from './Modal.jsx';
import { isIOSDevice, isStandalonePWA } from './ios-install-banner.js';

// null on desktop, and once the site is already running as an installed app
function installPlatform() {
    if (isStandalonePWA()) return null;
    if (isIOSDevice()) return 'ios';
    if (/Android/i.test(window.navigator.userAgent)) return 'android';
    return null;
}

function Icon({ children }) {
    return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            {children}
        </svg>
    );
}

const ShareIcon = (
    <Icon>
        <path d="M12 15V3" />
        <path d="m8 7 4-4 4 4" />
        <path d="M8 11H7a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6a2 2 0 0 0-2-2h-1" />
    </Icon>
);

const AddToHomeIcon = (
    <Icon>
        <rect x="4" y="4" width="16" height="16" rx="3" />
        <path d="M12 8v8" />
        <path d="M8 12h8" />
    </Icon>
);

const MenuDotsIcon = (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <circle cx="12" cy="5" r="2" />
        <circle cx="12" cy="12" r="2" />
        <circle cx="12" cy="19" r="2" />
    </svg>
);

const InstallIcon = (
    <Icon>
        <rect x="6" y="2" width="12" height="20" rx="3" />
        <path d="M12 8v6" />
        <path d="m9.5 11.5 2.5 2.5 2.5-2.5" />
    </Icon>
);

const CheckIcon = (
    <Icon>
        <path d="m5 12.5 4.5 4.5L19 7" />
    </Icon>
);

const bold = (text) => <span className="bold-span">{text}</span>;

const INSTALL_STEPS = {
    ios: [
        { icon: ShareIcon, text: <>In Safari, tap the {bold('Share')} button.</> },
        { icon: AddToHomeIcon, text: <>Scroll down and tap {bold('Add to Home Screen')}.</> },
        { icon: CheckIcon, text: <>Tap {bold('Add')}.</> },
    ],
    android: [
        { icon: MenuDotsIcon, text: <>In Chrome, tap the {bold('⋮')} menu in the top corner.</> },
        { icon: InstallIcon, text: <>Tap {bold('Add to Home screen')} (or {bold('Install app')}).</> },
        { icon: CheckIcon, text: <>Tap {bold('Install')} to confirm.</> },
    ],
};

export default function HelpPopup({ useNewBoard, backgroundClick }) {
    const platform = installPlatform();

    return (
        <Modal onClose={backgroundClick} className="help-popup-content" showClose={false}>
            <div className="popup-title">New here?</div>

            <div className="recap-sections">
                <div className="recap-section-line">
                    Welcome to a hobby project I set up for my dad, Dave.
                </div>

                <div className="recap-section">
                    <div className="recap-section-label">Making picks</div>
                    <div className="recap-section-line">
                        {useNewBoard
                            ? "Tap a team on any game that hasn't started to save your pick."
                            : 'To save your picks, click on the tiles in the spread columns.'}
                    </div>
                </div>

                <div className="recap-section">
                    <div className="recap-section-label">Your account</div>
                    <div className="recap-section-line">
                        Sign in with your Google account any time to see your picks from any device. The "Profile" section is also where you can update your username for the leaderboards.
                    </div>
                </div>

                {platform && (
                    <div className="recap-section">
                        <div className="recap-section-label">Install as an app</div>
                        <ul className="help-steps" role="list">
                            {INSTALL_STEPS[platform].map((step, index) => (
                                <li className="help-step" key={index}>
                                    <span className="help-step-icon">{step.icon}</span>
                                    <span>{step.text}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>

            <div className="popup-button" onClick={backgroundClick}>Got it</div>
        </Modal>
    );
}
