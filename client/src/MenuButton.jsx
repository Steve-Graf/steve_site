import './Odds.css';
import ProfilePopup from './ProfilePopup';
import React, {useState} from 'react';
import profileIcon from './assets/icons/profile.svg';

export default function MenuButton({title}) {
    const [showPopup, setShowPopup] = useState(true);

    function handleClick(){
        // console.log(title);
        alert('Coming soon!');
    }

    return (
        <>
            {/* {showPopup && 
                <ProfilePopup />
            } */}
            <div className="user-popup" onClick={() => handleClick()}>
                <div>{title}</div>
                {/* <img className="user-popup-icon" src="/images/profile.svg"/> */}
                <img className="user-popup-icon" src={profileIcon}/>
            </div>
        </>
    );
}