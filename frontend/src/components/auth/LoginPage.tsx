import { useState, FormEvent } from 'react';
import { useAuth } from '../../hooks/useAuth';

interface LoginPageProps {
    onNavigateSignup: () => void;
}

export default function LoginPage({ onNavigateSignup }: LoginPageProps) {
    const { login } = useAuth();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await login(email, password);
        } catch (err: any) {
            setError(err.message || 'Login failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--bg-base)' }}>
            <div className="w-full max-w-md px-4">
                {/* Logo */}
                <div className="text-center mb-10">
                    <div className="text-5xl mb-4">🏛️</div>
                    <h1 className="text-2xl font-bold mb-1" style={{ color: 'var(--text-primary)' }}>Welcome back</h1>
                    <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Sign in to your Boardroom</p>
                </div>

                {/* Card */}
                <div className="rounded-2xl p-8" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
                    <form onSubmit={handleSubmit}>
                        <div className="mb-5">
                            <label className="block text-sm mb-2" style={{ color: 'var(--text-secondary)' }}>Email</label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="you@company.com"
                                required
                                className="w-full px-4 py-3 rounded-xl outline-none transition-all"
                                style={{
                                    background: 'var(--bg-elevated)',
                                    border: '1px solid var(--border)',
                                    color: 'var(--text-primary)',
                                    fontSize: '14px',
                                }}
                                onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
                                onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
                            />
                        </div>

                        <div className="mb-6">
                            <label className="block text-sm mb-2" style={{ color: 'var(--text-secondary)' }}>Password</label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                                className="w-full px-4 py-3 rounded-xl outline-none transition-all"
                                style={{
                                    background: 'var(--bg-elevated)',
                                    border: '1px solid var(--border)',
                                    color: 'var(--text-primary)',
                                    fontSize: '14px',
                                }}
                                onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
                                onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
                            />
                        </div>

                        {error && (
                            <div className="mb-4 px-4 py-3 rounded-xl text-sm" style={{ background: '#7f1d1d22', border: '1px solid #7f1d1d', color: '#fca5a5' }}>
                                {error}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-3 rounded-xl font-semibold transition-all"
                            style={{
                                background: loading ? 'var(--bg-elevated)' : 'var(--accent)',
                                color: 'white',
                                border: 'none',
                                cursor: loading ? 'not-allowed' : 'pointer',
                                fontSize: '15px',
                            }}
                        >
                            {loading ? 'Signing in...' : 'Sign in →'}
                        </button>
                    </form>

                    <div className="mt-6 text-center" style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                        Don't have an account?{' '}
                        <button
                            onClick={onNavigateSignup}
                            style={{ color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px' }}
                        >
                            Create account
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
