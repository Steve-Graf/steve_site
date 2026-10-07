import './Odds.css';
import ProfilePopup from './ProfilePopup';
import StatsPopup from './StatsPopup';
import SurvivorPopup from './SurvivorPopup';
import LeaderboardPopup from './LeaderboardPopup';
import React, {useState, useEffect, useContext} from 'react';
import AppContext from './AppContext.jsx';
import {showAlert} from './alerts.js';
import profileIcon from './assets/icons/profile.svg';
import statsIcon from './assets/icons/list.svg';
import survivorIcon from './assets/icons/shield.svg';
import pointsIcon from './assets/icons/numbered-list.svg';
import helpIcon from './assets/icons/info-thick.svg';
import recapIcon from './assets/icons/star.svg';
const API_URL = import.meta.env.VITE_API_URL;

export default function MenuButton({id, title}) {
    const { signedIn } = useContext(AppContext);
    const [showPopup, setShowPopup] = useState(false);
    const [iconSource, setIconSource] = useState(profileIcon);

    useEffect(() => {
        if(id == 'profile'){
            setIconSource(profileIcon);
        }else if(id == 'stats'){
            setIconSource(statsIcon);
        }else if(id == 'survivor'){
            setIconSource(survivorIcon);
        }else if(id == 'points'){
            setIconSource(pointsIcon);
        }else if(id == 'help'){
            setIconSource(helpIcon);
        }else if(id == 'recap'){
            setIconSource(recapIcon);
        }
    });

    function handleClick(){
        if(id == 'survivor' && !signedIn){
            showAlert("Please log in to join the survivor pool.", "warning");
            return;
        }
        setShowPopup(true);
    }

    function handlePopupBackgroundClick(){
        setShowPopup(false);
    }

    if(id == 'profile' && !signedIn){
        return (
            <a className="user-popup" href={API_URL+'auth/login'}>
                <img className="user-popup-icon" src={profileIcon}/>
                <div className="user-popup-text">Log In</div>
            </a>
        );
    }

    return (
        <>
            {(showPopup && id == 'profile') &&
                <ProfilePopup
                    backgroundClick={handlePopupBackgroundClick}
                />
            }
            {(showPopup && id == 'stats') &&
                <StatsPopup
                    backgroundClick={handlePopupBackgroundClick}
                />
            }
            {(showPopup && id == 'survivor') &&
                <SurvivorPopup
                    backgroundClick={handlePopupBackgroundClick}
                />
            }
            {(showPopup && id == 'points') &&
                <LeaderboardPopup
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