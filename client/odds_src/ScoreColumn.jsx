import React, {useState, useEffect, useMemo} from 'react';
import './Odds.css';
import ColumnEntry from './ColumnEntry.jsx';
const API_URL = import.meta.env.VITE_API_URL;

export default function ScoreColumn({ awayScore, homeScore }) {
    return (
        <div className="odds-column">
            <div className="column-header">Score</div>
            <ColumnEntry value={awayScore} isSelected={false} />
            <div className="column-separator"></div>
            <ColumnEntry value={homeScore} isSelected={false} />
        </div>
    );
}