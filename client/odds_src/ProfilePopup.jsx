import './Odds.css';
import {useContext, useState, useEffect} from "react";
import AppContext from "./AppContext.jsx";
import eyeIcon from './assets/icons/eye.svg';
import eyeSlashIcon from './assets/icons/eye-slash.svg';
const API_URL = import.meta.env.VITE_API_URL;

export default function ProfilePopup({backgroundClick}) {
    const {userData} = useContext(AppContext);
    const [username, setUsername] = useState('');
    const [userCode, setUserCode] = useState('');
    const [isPasswordVisible, setPasswordVisible] = useState(false);

    useEffect(() => {
        if (userData?.name) {
            if(userData.name != 'Unnamed'){
                setUsername(userData.name);
            }
        }
        if (userData?.playerCode) {
            setUserCode(userData.playerCode);
        }
    }, [userData]);

    function userCodeError(){
        let userCodeInputElement = document.getElementById('usercode-input');
        userCodeInputElement.style.border = '1px solid red';
    }

    async function updateUserCode(){
        if(userCode.length != 4){
            userCodeError();
            return;
        }

        const postData = {
            "username": username,
            "playerCode": userCode
        };
        const response = await fetch(API_URL+'update-username', {
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
        if(data.status == 'failed'){
            userCodeError();
        }else{
            const currentUserCode = localStorage.getItem('userCode', null);
            localStorage.setItem('userCode', userCode);
            if(currentUserCode != userCode || userData.name != username){
                window.location.reload();
            }else{
                backgroundClick();
            }
        }
        console.log(data);
    }

    function toggleCodeVisibility(){
        setPasswordVisible(!isPasswordVisible)
        var x = document.getElementById("usercode-input");
        if (x.type === "password") {
            x.style.fontSize = '16px';
        } else {
            x.style.fontSize = '32px';
        }
    }

    function formatUserCode(){
        let userCodeInputElement = document.getElementById('usercode-input');
        userCodeInputElement.style.border = '0';
        let userCode = userCodeInputElement.value;
        if(userCode.length > 4){
            userCode = userCode.slice(0, 4);
        }
        setUserCode(userCode);
        return userCode;
    }

    return (
        <div className="popup-wrapper">
            <div className="popup-background" onClick={backgroundClick}></div>
            <div className="popup-content">
                <div className="popup-title">Profile</div>
                <div className="popup-description">Use these input fields to update your username or change your user code. Your user code is the equivalent to a password, so be careful sharing it. Understand that your username will be visible to anyone accessing the leaderboards.</div>
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
                <div style={{position:'relative'}}>
                    <input
                        id="usercode-input"
                        name="usercode-input"
                        className="input-field password-field"
                        type={isPasswordVisible ? 'text' : 'password'}
                        value={userCode ?? ''}
                        onChange={formatUserCode}
                    />
                    <div className="visibility-toggle-wrapper" onClick={toggleCodeVisibility}>
                        <img
                            className="visibility-toggle-icon"
                            id="eye-icon"
                            src={eyeIcon}
                            style={{ display: isPasswordVisible ? "block" : "none" }}
                        />
                        <img
                            className="visibility-toggle-icon"
                            id="eye-slash-icon"
                            src={eyeSlashIcon}
                            style={{ display: isPasswordVisible ? "none" : "block" }}
                        />
                    </div>
                </div>
                <div className="popup-button" onClick={() => updateUserCode()}>Update profile</div>
            </div>
        </div>
    );
}