import './Odds.css';
import {useContext, useState, useEffect} from "react";
import AppContext from "./AppContext.jsx";
import { authFetch } from './api.js';
import { showAlert } from './alerts.js';
import { subscribeToPush, unsubscribeFromPush } from './push.js';
import Modal from './Modal.jsx';
import { setShowAbbrevs, useShowAbbrevs } from './prefs.js';
const API_URL = import.meta.env.VITE_API_URL;

export default function ProfilePopup({backgroundClick}) {
    const {userData, refreshUserData} = useContext(AppContext);
    const showAbbrevs = useShowAbbrevs();
    const [username, setUsername] = useState('');
    const [isPrivate, setIsPrivate] = useState(false);
    const [notificationsEnabled, setNotificationsEnabled] = useState(false);
    const [notificationsBusy, setNotificationsBusy] = useState(false);

    useEffect(() => {
        if (userData?.displayName && userData.displayName !== 'Unnamed') {
            setUsername(userData.displayName);
        }
        setIsPrivate(!!userData?.isPrivate);
        setNotificationsEnabled(!!userData?.hasPushSubscription);
    }, [userData]);

    async function toggleNotifications(enabled){
        setNotificationsEnabled(enabled);
        setNotificationsBusy(true);
        try {
            if (enabled) {
                await subscribeToPush();
                showAlert("Notifications enabled.");
            } else {
                await unsubscribeFromPush();
                showAlert("Notifications disabled.");
            }
            if (refreshUserData) {
                await refreshUserData();
            }
        } catch (e) {
            setNotificationsEnabled(!enabled);
            showAlert(e.message || "Couldn't update notification settings.", "warning");
        } finally {
            setNotificationsBusy(false);
        }
    }

    async function updateProfile(){
        const postData = {
            "username": username,
            "isPrivate": isPrivate
        };
        const response = await authFetch(API_URL+'update-profile', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(postData)
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        if(data.status == 'success'){
            if(refreshUserData){
                await refreshUserData();
            }
            showAlert("Profile updated.");
            backgroundClick();
        }
    }

    return (
        <Modal onClose={backgroundClick}>
            <div className="popup-title">Profile</div>
            {userData?.photoURL && (
                <img className="profile-avatar" src={userData.photoURL} alt="" referrerPolicy="no-referrer" />
            )}
            <div className="popup-description">Signed in as {userData?.email}. Your username is what shows up on the leaderboards.</div>
            <input
                id="username-input"
                name="username-input"
                className="input-field"
                type="text"
                placeholder="Username"
                value={username ?? ''}
                onChange={e => setUsername(e.target.value)}
                autoComplete='off'
            />
            <div className="private-toggle-row">
                <label className="toggle-switch">
                    <input
                        type="checkbox"
                        checked={isPrivate}
                        onChange={e => setIsPrivate(e.target.checked)}
                    />
                    <span className="toggle-switch-slider"></span>
                </label>
                <div className="private-toggle-label">Private (hide me from leaderboards)</div>
            </div>
            <div className="private-toggle-row">
                <label className="toggle-switch">
                    <input
                        type="checkbox"
                        checked={notificationsEnabled}
                        disabled={notificationsBusy}
                        onChange={e => toggleNotifications(e.target.checked)}
                    />
                    <span className="toggle-switch-slider"></span>
                </label>
                <div className="private-toggle-label">Enable notifications (new week, Sunday reminders)</div>
            </div>
            {/* a display preference kept on this device; takes effect right away, no need to press Update profile */}
            <div className="private-toggle-row">
                <label className="toggle-switch">
                    <input
                        type="checkbox"
                        id="show-abbrevs-toggle"
                        checked={showAbbrevs}
                        onChange={e => setShowAbbrevs(e.target.checked)}
                    />
                    <span className="toggle-switch-slider"></span>
                </label>
                <div className="private-toggle-label">Show team abbreviations under the logos</div>
            </div>
            <div className="popup-button" onClick={() => updateProfile()}>Update profile</div>
            <a className="popup-button popup-button-secondary" href={API_URL+'auth/logout'}>Sign out</a>
        </Modal>
    );
}
