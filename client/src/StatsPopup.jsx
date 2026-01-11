import './Odds.css';
import './Stats.css';
import {useContext, useState, useEffect} from "react";
import AppContext from "./AppContext.jsx";
const API_URL = import.meta.env.VITE_API_URL;

export default function ProfilePopup({backgroundClick}) {
    const {userData} = useContext(AppContext);
    const [username, setUsername] = useState('');
    const [userCode, setUserCode] = useState('');
    const [totalWidth, setTotalWidth] = useState('0%');
    const [totalWins, setTotalWins] = useState(0);
    const [totalLosses, setTotalLosses] = useState(0);
    const [underdogWins, setUnderdogWins] = useState(0);
    const [underdogLosses, setUnderdogLosses] = useState(0);
    const [underdogWidth, setUnderdogWidth] = useState('0%');
    const [favoredWins, setFavoredWins] = useState(0);
    const [favoredLosses, setFavoredLosses] = useState(0);
    const [favoredWidth, setFavoredWidth] = useState('0%');
    const [favoriteTeam, setFavoriteTeam] = useState('');
    const [favoriteTeamCount, setFavoriteTeamCount] = useState(0);
    const [bestTeam, setBestTeam] = useState('');
    const [bestTeamCount, setBestTeamCount] = useState(0);
    const [worstTeam, setWorstTeam] = useState('');
    const [worstTeamCount, setWorstTeamCount] = useState(0);

    useEffect(() => {
        if (userData?.name) {
            if(userData.name != 'Unnamed'){
                setUsername(userData.name);
            }
        }
        if (userData?.playerCode) {
            setUserCode(userData.playerCode);
            getUserStats(userData.playerCode);
        }
    }, [userData]);

    async function getUserStats(code){
        const response = await fetch(API_URL+'stats/'+code);
        const data = await response.json();
        if(data.status == 'failed'){
            console.log('Could not retrieve stats for current user.');
        }else{
            console.log(data);
            if(data){
                const winningPercentage = parseInt((data.wins / data.total) * 100);
                setTotalWidth(winningPercentage);
                setTotalWins(data.wins);
                setTotalLosses(data.total - data.wins);
                setUnderdogWins(data.underdog_wins_count);
                setUnderdogLosses(data.underdog_count - data.underdog_wins_count);
                const underdogWinningPercentage = parseInt((data.underdog_wins_count / data.underdog_count) * 100);
                setUnderdogWidth(underdogWinningPercentage);
                setFavoredWins(data.favored_wins_count);
                setFavoredLosses(data.favored_count - data.favored_wins_count);
                const favoredWinningPercentage = parseInt((data.favored_wins_count / data.favored_count) * 100);
                setFavoredWidth(favoredWinningPercentage);
                setFavoriteTeam(data.favorite_team);
                setFavoriteTeamCount(data.favorite_team_count);
                setBestTeam(data.best_team);
                setBestTeamCount(data.best_team_win_count);
                setWorstTeam(data.worst_team);
                setWorstTeamCount(data.worst_team_loss_count);
            }
        }
    }

    return (
        <div className="popup-wrapper">
            <div className="popup-background" onClick={backgroundClick}></div>
            <div className="popup-content">
                <div className="popup-title">Your Stats</div>
                <div className="popup-description">
                    <div className="stats-row-label">Total</div>
                    <div className="stats-total-bar">
                        <div className="stats-total-bar-value-label wins-label">{totalWins}W</div>
                        <div className="stats-total-bar-value-label losses-label">{totalLosses}L</div>
                        <div className="stats-total-bar-wins-bkg" style={{width:totalWidth+'%'}}></div>
                    </div>

                    <div className="stats-row-label" style={{marginTop: "20px"}}>Underdog performances</div>
                    <div className="stats-total-bar">
                        <div className="stats-total-bar-value-label wins-label">{underdogWins}W</div>
                        <div className="stats-total-bar-value-label losses-label">{underdogLosses}L</div>
                        <div className="stats-total-bar-wins-bkg" style={{width:underdogWidth+'%'}}></div>
                    </div>

                    <div className="stats-row-label" style={{marginTop: "20px"}}>Favored performances</div>
                    <div className="stats-total-bar">
                        <div className="stats-total-bar-value-label wins-label">{favoredWins}W</div>
                        <div className="stats-total-bar-value-label losses-label">{favoredLosses}L</div>
                        <div className="stats-total-bar-wins-bkg" style={{width:favoredWidth+'%'}}></div>
                    </div>

                    
                    <div style={{marginTop: "20px"}}>
                        Your favorite team is the <span className="bold-span">{favoriteTeam}.</span> You've picked them to cover their spread <span className="bold-span">{favoriteTeamCount}</span> times.
                    </div>

                    <div style={{marginTop: "20px"}}>
                        Your best performing team is the <span className="bold-span">{bestTeam}.</span> They've covered the spread <span className="bold-span">{bestTeamCount}</span> times.
                    </div>

                    <div style={{marginTop: "20px"}}>
                        Your worst performing team is the <span className="bold-span">{worstTeam}.</span> They've failed to cover the spread <span className="bold-span">{worstTeamCount}</span> times.
                    </div>
                </div>
            </div>
        </div>
    );
}