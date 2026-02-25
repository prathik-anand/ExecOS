import { useState, useEffect, useCallback } from 'react';

const SESSION_KEY = 'execos_session_id';

function generateUUID(): string {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = (Math.random() * 16) | 0;
        const v = c === 'x' ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
}

export function useSession() {
    const [sessionId, setSessionId] = useState<string>(() => {
        let id = localStorage.getItem(SESSION_KEY);
        if (!id) {
            id = generateUUID();
            localStorage.setItem(SESSION_KEY, id);
        }
        return id;
    });

    const clearSession = useCallback(() => {
        localStorage.removeItem(SESSION_KEY);
        const newId = generateUUID();
        localStorage.setItem(SESSION_KEY, newId);
        setSessionId(newId);
    }, []);

    return { sessionId, clearSession };
}
