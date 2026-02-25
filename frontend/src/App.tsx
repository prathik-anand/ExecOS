import { useState, useCallback } from 'react';
import { useSession } from './hooks/useSession';
import Onboarding from './components/Onboarding';
import Boardroom from './components/Boardroom';

type AppState = 'onboarding' | 'boardroom';

export default function App() {
    const { sessionId, clearSession } = useSession();
    const [appState, setAppState] = useState<AppState>('onboarding');
    const [context, setContext] = useState<Record<string, string>>({});

    const handleOnboardingComplete = useCallback((completedContext: Record<string, string>) => {
        setContext(completedContext);
        setAppState('boardroom');
    }, []);

    const handleResetSession = useCallback(() => {
        clearSession();
        setContext({});
        setAppState('onboarding');
    }, [clearSession]);

    return (
        <div style={{ height: '100vh', width: '100vw', overflow: 'hidden' }}>
            {appState === 'onboarding' ? (
                <Onboarding
                    sessionId={sessionId}
                    onComplete={handleOnboardingComplete}
                />
            ) : (
                <Boardroom
                    sessionId={sessionId}
                    initialContext={context}
                    onResetSession={handleResetSession}
                />
            )}
        </div>
    );
}
