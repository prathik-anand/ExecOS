import { useState } from 'react';
import { AuthProvider } from './hooks/AuthProvider';
import { useAuth } from './hooks/useAuth';
import LoginPage from './components/auth/LoginPage';
import SignupPage from './components/auth/SignupPage';
import Boardroom from './components/Boardroom';

type AuthView = 'login' | 'signup';

function AppContent() {
    const { isAuthenticated, isLoading, user, logout } = useAuth();
    const [authView, setAuthView] = useState<AuthView>('login');

    if (isLoading) {
        return (
            <div className="h-screen flex items-center justify-center" style={{ background: 'var(--bg-base)' }}>
                <div className="text-center">
                    <div className="text-4xl mb-4">🏛️</div>
                    <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Loading your Boardroom...</p>
                </div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return authView === 'login' ? (
            <LoginPage onNavigateSignup={() => setAuthView('signup')} />
        ) : (
            <SignupPage onNavigateLogin={() => setAuthView('login')} />
        );
    }

    return (
        <Boardroom
            user={user!}
            onLogout={logout}
        />
    );
}

export default function App() {
    return (
        <AuthProvider>
            <AppContent />
        </AuthProvider>
    );
}
