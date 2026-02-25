import { useState, useEffect, createContext, useContext, ReactNode } from 'react';

const API_BASE = '';

export interface AuthUser {
    id: string;
    email: string;
    name: string | null;
    role: string | null;
    company_name: string | null;
    company_stage: string | null;
    industry: string | null;
    team_size: string | null;
    current_challenges: string | null;
    goals: string | null;
    onboarding_complete: boolean;
}

interface AuthState {
    user: AuthUser | null;
    token: string | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (email: string, password: string) => Promise<void>;
    signup: (data: SignupData) => Promise<void>;
    logout: () => void;
}

export interface SignupData {
    email: string;
    password: string;
    name: string;
    role: string;
    company_name?: string;
    company_stage?: string;
    industry?: string;
    team_size?: string;
    current_challenges?: string;
    goals?: string;
}

const TOKEN_KEY = 'execos_token';

export const AuthContext = createContext<AuthState | null>(null);

export function useAuthState(): AuthState {
    const [user, setUser] = useState<AuthUser | null>(null);
    const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const existing = localStorage.getItem(TOKEN_KEY);
        if (!existing) {
            setIsLoading(false);
            return;
        }
        fetch(`${API_BASE}/api/auth/me`, {
            headers: { Authorization: `Bearer ${existing}` },
        })
            .then((r) => (r.ok ? r.json() : Promise.reject()))
            .then((data) => {
                setUser(data);
                setToken(existing);
            })
            .catch(() => {
                localStorage.removeItem(TOKEN_KEY);
                setToken(null);
            })
            .finally(() => setIsLoading(false));
    }, []);

    const login = async (email: string, password: string) => {
        const res = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Login failed');
        }
        const data = await res.json();
        localStorage.setItem(TOKEN_KEY, data.token);
        setToken(data.token);
        setUser(data.user);
    };

    const signup = async (signupData: SignupData) => {
        const res = await fetch(`${API_BASE}/api/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(signupData),
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Signup failed');
        }
        const data = await res.json();
        localStorage.setItem(TOKEN_KEY, data.token);
        setToken(data.token);
        setUser(data.user);
    };

    const logout = () => {
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setUser(null);
    };

    return { user, token, isAuthenticated: !!user, isLoading, login, signup, logout };
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
    return ctx;
}
