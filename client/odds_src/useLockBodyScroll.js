import { useEffect } from 'react';

// locks background scroll while any modal/popup is mounted — restores
// whatever overflow value was there before in case something else set it
export default function useLockBodyScroll() {
    useEffect(() => {
        const original = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        return () => {
            document.body.style.overflow = original;
        };
    }, []);
}
