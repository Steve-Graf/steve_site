import './Odds.css';
import ProfilePopup from './ProfilePopup';
import React, {useState, useEffect} from 'react';
import profileIcon from './assets/icons/profile.svg';
import statsIcon from './assets/icons/list.svg';
import pointsIcon from './assets/icons/numbered-list.svg';
import helpIcon from './assets/icons/info-thick.svg';

export default function MenuButton({id, title}) {
    const [showPopup, setShowPopup] = useState(false);
    const [iconSource, setIconSource] = useState(profileIcon);

    useEffect(() => {
        if(id == 'profile'){
            setIconSource(profileIcon);
        }else if(id == 'stats'){
            setIconSource(statsIcon);
        }else if(id == 'points'){
            setIconSource(pointsIcon);
        }else if(id == 'help'){
            setIconSource(helpIcon);
        }
    });

    function handleClick(){
        setShowPopup(true);
        if(id == 'stats' || id == 'points'){
            alert('Coming soon!');
        }
    }

    function handlePopupBackgroundClick(){
        setShowPopup(false);
    }

    return (
        <>
            {(showPopup && id == 'profile') && 
                <ProfilePopup 
                    backgroundClick={handlePopupBackgroundClick}
                />
            }
            <div className="user-popup" onClick={() => handleClick()}>
                <img className="user-popup-icon" src={iconSource}/>
                <div className="user-popup-text">{title}</div>
            </div>
        </>
    );
}