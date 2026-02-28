import { useState, FormEvent } from 'react';
import { useAuth, SignupData } from '../../hooks/useAuth';

interface SignupPageProps {
    onNavigateLogin: () => void;
}

const COMPANY_STAGES = ['Pre-idea', 'Idea / Concept', 'MVP / Building', 'Early Traction', 'PMF Found', 'Scaling', 'Growth'];
const TEAM_SIZES = ['Solo founder', '2–5', '6–15', '16–50', '51–200', '200+'];

const inputStyle = {
    background: 'var(--bg-elevated)',
    border: '1px solid var(--border)',
    color: 'var(--text-primary)',
    fontSize: '14px',
};

function InputField({ label, field, type = 'text', placeholder, value, onChange }: {
    label: string;
    field: keyof SignupData;
    type?: string;
    placeholder?: string;
    value: string;
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) {
    return (
        <div className="mb-4">
            <label className="block text-sm mb-1.5" style={{ color: 'var(--text-secondary)' }}>{label}</label>
            <input
                type={type}
                value={value}
                onChange={onChange}
                placeholder={placeholder}
                className="w-full px-4 py-3 rounded-xl outline-none transition-all"
                style={inputStyle}
                onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
                onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
            />
        </div>
    );
}

export default function SignupPage({ onNavigateLogin }: SignupPageProps) {
    const { signup } = useAuth();
    const [step, setStep] = useState<1 | 2>(1);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const [form, setForm] = useState<SignupData>({
        email: '',
        password: '',
        name: '',
        role: '',
        company_name: '',
        company_stage: '',
        industry: '',
        team_size: '',
        current_challenges: '',
        goals: '',
    });

    const set = (field: keyof SignupData) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
        setForm((prev) => ({ ...prev, [field]: e.target.value }));

    const setInput = (field: keyof SignupData) => (e: React.ChangeEvent<HTMLInputElement>) =>
        setForm((prev) => ({ ...prev, [field]: e.target.value }));

    const handleNext = (e: FormEvent) => {
        e.preventDefault();
        setError('');
        if (!form.email || !form.password || form.password.length < 8) {
            setError('Password must be at least 8 characters');
            return;
        }
        setStep(2);
    };

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!form.name || !form.role) {
            setError('Name and role are required');
            return;
        }
        setError('');
        setLoading(true);
        try {
            await signup(form);
        } catch (err: any) {
            setError(err.message || 'Signup failed');
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center py-12" style={{ background: 'var(--bg-base)' }}>
            <div className="w-full max-w-lg px-4">
                {/* Logo */}
                <div className="text-center mb-8">
                    <div className="text-4xl mb-3">🏛️</div>
                    <h1 className="text-2xl font-bold mb-1" style={{ color: 'var(--text-primary)' }}>Join ExecOS</h1>
                    <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Your Cloud C-Suite is ready</p>
                </div>

                {/* Step indicator */}
                <div className="flex items-center gap-2 mb-6">
                    {[1, 2].map((s) => (
                        <div key={s} className="flex items-center gap-2 flex-1">
                            <div
                                className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold"
                                style={{
                                    background: step >= s ? 'var(--accent)' : 'var(--bg-elevated)',
                                    color: step >= s ? 'white' : 'var(--text-muted)',
                                    border: `1px solid ${step >= s ? 'var(--accent)' : 'var(--border)'}`,
                                }}
                            >
                                {s}
                            </div>
                            <span style={{ color: step >= s ? 'var(--text-primary)' : 'var(--text-muted)', fontSize: '12px' }}>
                                {s === 1 ? 'Account' : 'Your Profile'}
                            </span>
                            {s < 2 && <div className="flex-1 h-px" style={{ background: step > s ? 'var(--accent)' : 'var(--border)' }} />}
                        </div>
                    ))}
                </div>

                <div className="rounded-2xl p-8" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
                    {step === 1 ? (
                        <form onSubmit={handleNext}>
                            <InputField label="Email" field="email" type="email" placeholder="you@company.com" value={form.email} onChange={setInput('email')} />
                            <InputField label="Password (min 8 chars)" field="password" type="password" placeholder="••••••••" value={form.password} onChange={setInput('password')} />

                            {error && (
                                <div className="mb-4 px-4 py-3 rounded-xl text-sm" style={{ background: '#7f1d1d22', border: '1px solid #7f1d1d', color: '#fca5a5' }}>
                                    {error}
                                </div>
                            )}

                            <button
                                type="submit"
                                className="w-full py-3 rounded-xl font-semibold mt-2"
                                style={{ background: 'var(--accent)', color: 'white', border: 'none', cursor: 'pointer', fontSize: '15px' }}
                            >
                                Continue →
                            </button>
                        </form>
                    ) : (
                        <form onSubmit={handleSubmit}>
                            <div className="grid grid-cols-2 gap-4 mb-4">
                                <div>
                                    <label className="block text-sm mb-1.5" style={{ color: 'var(--text-secondary)' }}>Your name *</label>
                                    <input
                                        type="text" value={form.name} onChange={set('name')} placeholder="Alex Chen" required
                                        className="w-full px-4 py-3 rounded-xl outline-none transition-all" style={inputStyle}
                                        onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
                                        onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm mb-1.5" style={{ color: 'var(--text-secondary)' }}>Your title / role *</label>
                                    <input
                                        type="text" value={form.role} onChange={set('role')} placeholder="CEO & Co-founder" required
                                        className="w-full px-4 py-3 rounded-xl outline-none transition-all" style={inputStyle}
                                        onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
                                        onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4 mb-4">
                                <div>
                                    <label className="block text-sm mb-1.5" style={{ color: 'var(--text-secondary)' }}>Company name</label>
                                    <input
                                        type="text" value={form.company_name} onChange={set('company_name')} placeholder="Acme Inc."
                                        className="w-full px-4 py-3 rounded-xl outline-none transition-all" style={inputStyle}
                                        onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
                                        onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm mb-1.5" style={{ color: 'var(--text-secondary)' }}>Industry</label>
                                    <input
                                        type="text" value={form.industry} onChange={set('industry')} placeholder="B2B SaaS, Fintech..."
                                        className="w-full px-4 py-3 rounded-xl outline-none transition-all" style={inputStyle}
                                        onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
                                        onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4 mb-4">
                                <div>
                                    <label className="block text-sm mb-1.5" style={{ color: 'var(--text-secondary)' }}>Company stage</label>
                                    <select value={form.company_stage} onChange={set('company_stage')}
                                        className="w-full px-4 py-3 rounded-xl outline-none" style={{ ...inputStyle, cursor: 'pointer' }}>
                                        <option value="">Select stage</option>
                                        {COMPANY_STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm mb-1.5" style={{ color: 'var(--text-secondary)' }}>Team size</label>
                                    <select value={form.team_size} onChange={set('team_size')}
                                        className="w-full px-4 py-3 rounded-xl outline-none" style={{ ...inputStyle, cursor: 'pointer' }}>
                                        <option value="">Select size</option>
                                        {TEAM_SIZES.map((s) => <option key={s} value={s}>{s}</option>)}
                                    </select>
                                </div>
                            </div>

                            <div className="mb-4">
                                <label className="block text-sm mb-1.5" style={{ color: 'var(--text-secondary)' }}>Your biggest challenge right now</label>
                                <textarea value={form.current_challenges} onChange={set('current_challenges')}
                                    placeholder="E.g. struggling to find product-market fit, need to hire fast..."
                                    rows={2}
                                    className="w-full px-4 py-3 rounded-xl outline-none resize-none" style={inputStyle}
                                    onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
                                    onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
                                />
                            </div>

                            <div className="mb-5">
                                <label className="block text-sm mb-1.5" style={{ color: 'var(--text-secondary)' }}>What's your #1 goal for the next 90 days?</label>
                                <textarea value={form.goals} onChange={set('goals')}
                                    placeholder="E.g. close 10 enterprise customers, raise seed round..."
                                    rows={2}
                                    className="w-full px-4 py-3 rounded-xl outline-none resize-none" style={inputStyle}
                                    onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
                                    onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
                                />
                            </div>

                            {error && (
                                <div className="mb-4 px-4 py-3 rounded-xl text-sm" style={{ background: '#7f1d1d22', border: '1px solid #7f1d1d', color: '#fca5a5' }}>
                                    {error}
                                </div>
                            )}

                            <div className="flex gap-3">
                                <button
                                    type="button" onClick={() => setStep(1)}
                                    className="py-3 px-5 rounded-xl font-medium"
                                    style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)', border: '1px solid var(--border)', cursor: 'pointer', fontSize: '14px' }}
                                >
                                    ← Back
                                </button>
                                <button
                                    type="submit" disabled={loading}
                                    className="flex-1 py-3 rounded-xl font-semibold"
                                    style={{ background: loading ? 'var(--bg-elevated)' : 'var(--accent)', color: 'white', border: 'none', cursor: loading ? 'not-allowed' : 'pointer', fontSize: '15px' }}
                                >
                                    {loading ? 'Creating account...' : 'Enter the Boardroom →'}
                                </button>
                            </div>
                        </form>
                    )}

                    <div className="mt-5 text-center" style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                        Already have an account?{' '}
                        <button onClick={onNavigateLogin}
                            style={{ color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px' }}>
                            Sign in
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
