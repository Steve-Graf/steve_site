import './Odds.css';
import ProfilePopup from './ProfilePopup';
import React, {useState} from 'react';
import profileIcon from './assets/icons/profile.svg';

export default function MenuButton({title}) {
    const [showPopup, setShowPopup] = useState(false);

    function handleClick(){
        setShowPopup(true);
    }

    function handlePopupBackgroundClick(){
        setShowPopup(false);
    }

    return (
        <>
            {showPopup && 
                <ProfilePopup 
                    backgroundClick={handlePopupBackgroundClick}
                />
            }
            <div className="user-popup" onClick={() => handleClick()}>
                <div>{title}</div>
                <img className="user-popup-icon" src={profileIcon}/>
            </div>
        </>
    );
}