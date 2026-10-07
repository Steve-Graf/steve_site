import { useSyncExternalStore } from 'react';

// Display preferences kept on this device (localStorage), shared live between the board and the Profile
// toggle. Nothing here is sent to the server.
const ABBREVS_KEY = 'odds-show-abbrevs';

// on unless the viewer has switched it off: nothing stored means they have never chosen
function readAbbrevs() {
    try {
        const stored = localStorage.getItem(ABBREVS_KEY);
        return stored === null ? true : stored === '1';
    } catch (e) {
        return true;
    }
}

let showAbbrevs = readAbbrevs();
const listeners = new Set();

function notify() {
    listeners.forEach((listener) => listener());
}

// another tab changed it
window.addEventListener('storage', (event) => {
    if (event.key === ABBREVS_KEY) {
        showAbbrevs = readAbbrevs();
        notify();
    }
});

export function setShowAbbrevs(on) {
    showAbbrevs = !!on;
    try {
        localStorage.setItem(ABBREVS_KEY, showAbbrevs ? '1' : '0');
    } catch (e) {
        // storage blocked: the choice still applies until the page is closed
    }
    notify();
}

function subscribe(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
}

// whether to show the team abbreviation chip under each logo (on by default)
export function useShowAbbrevs() {
    return useSyncExternalStore(subscribe, () => showAbbrevs, () => true);
}
