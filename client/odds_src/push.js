import { authFetch } from './api.js';
import { isIOSDevice, isStandalonePWA } from './ios-install-banner.js';
const API_URL = import.meta.env.VITE_API_URL;

function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    return Uint8Array.from([...rawData].map(char => char.charCodeAt(0)));
}

export function needsIOSInstallFirst() {
    return isIOSDevice() && !isStandalonePWA();
}

export async function subscribeToPush() {
    if (needsIOSInstallFirst()) {
        throw new Error("Add Dave's Odds to your home screen first (tap Share, then \"Add to Home Screen\"), then enable notifications from there.");
    }
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        throw new Error('Push notifications are not supported in this browser.');
    }

    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
        throw new Error('Notification permission was not granted.');
    }

    const registration = await navigator.serviceWorker.ready;
    const keyResponse = await authFetch(API_URL + 'push/vapid-public-key');
    const { publicKey } = await keyResponse.json();

    const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
    });

    const response = await authFetch(API_URL + 'push/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(subscription.toJSON()),
    });
    if (!response.ok) {
        throw new Error('Failed to save push subscription.');
    }
}

export async function unsubscribeFromPush() {
    if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.getSubscription();
        if (subscription) {
            await subscription.unsubscribe();
        }
    }
    await authFetch(API_URL + 'push/unsubscribe', { method: 'POST' });
}
