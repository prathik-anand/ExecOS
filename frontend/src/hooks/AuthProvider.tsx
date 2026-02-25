import { AuthContext, useAuthState } from './useAuth';

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const auth = useAuthState();
    return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
}
