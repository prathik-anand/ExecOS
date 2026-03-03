import { useState } from 'react';
import { AuthUser } from '../hooks/useAuth';
import { SessionSummary } from '../hooks/useChat';
import { AGENT_INFO } from '../constants/agents';

interface SidebarProps {
    user: AuthUser;
    activeAgents: string[];
    sessions: SessionSummary[];
    currentSessionId: string | null;
    memoryCount: number;
    onNewSession: () => void;
    onLoadSession: (id: string) => void;
    onLogout: () => void;
}

function formatRelativeTime(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    if (days < 7) return `${days}d ago`;
    return new Date(iso).toLocaleDateString();
}

export default function Sidebar({
    user, activeAgents, sessions, currentSessionId, memoryCount,
    onNewSession, onLoadSession, onLogout,
}: SidebarProps) {
    const [view, setView] = useState<'chats' | 'agents'>('chats');

    return (
        <div
            className="h-full flex flex-col"
            style={{
                background: 'var(--bg-surface)',
                borderRight: '1px solid var(--border)',
                width: '240px',
                minWidth: '240px',
            }}
        >
            {/* Logo + compact user context */}
            <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
                <div className="flex items-center gap-2.5 mb-2">
                    <span className="text-xl">🏛️</span>
                    <div>
                        <div className="font-bold tracking-wide" style={{ color: 'var(--text-primary)', fontSize: '15px' }}>ExecOS</div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Cloud C-Suite</div>
                    </div>
                </div>
                <div className="flex items-center gap-1.5 flex-wrap">
                    {user.name && (
                        <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{user.name}</span>
                    )}
                    {user.company_stage && (
                        <span
                            className="px-1.5 py-0.5 rounded text-xs"
                            style={{ background: 'var(--accent-glow)', color: 'var(--accent)', border: '1px solid var(--border-active)' }}
                        >
                            {user.company_stage}
                        </span>
                    )}
                    {memoryCount > 0 && (
                        <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>· 🧠 {memoryCount}</span>
                    )}
                </div>
            </div>

            {/* Tab toggle: Chats / Agents */}
            <div className="px-3 pt-3 pb-2" style={{ borderBottom: '1px solid var(--border)' }}>
                <div
                    className="flex rounded-lg p-0.5"
                    style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
                >
                    {(['chats', 'agents'] as const).map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setView(tab)}
                            className="flex-1 py-1.5 rounded-md text-xs font-medium transition-all"
                            style={{
                                background: view === tab ? 'var(--accent)' : 'transparent',
                                color: view === tab ? 'white' : 'var(--text-muted)',
                                border: 'none',
                                cursor: 'pointer',
                            }}
                        >
                            {tab === 'chats' ? '💬 Chats' : '👔 Agents'}
                        </button>
                    ))}
                </div>
            </div>

            {/* Scrollable body */}
            <div className="flex-1 overflow-y-auto px-3 py-2">
                {view === 'chats' ? (
                    <div className="space-y-0.5">
                        {sessions.length === 0 ? (
                            <div className="text-center py-10" style={{ color: 'var(--text-muted)', fontSize: '12px', lineHeight: '1.6' }}>
                                No conversations yet.<br />Start by asking the Boardroom anything.
                            </div>
                        ) : (
                            sessions.map((s) => {
                                const isActive = s.id === currentSessionId;
                                return (
                                    <button
                                        key={s.id}
                                        onClick={() => onLoadSession(s.id)}
                                        className="w-full text-left px-3 py-2.5 rounded-lg transition-all"
                                        style={{
                                            background: isActive ? 'var(--accent-glow)' : 'transparent',
                                            border: `1px solid ${isActive ? 'var(--border-active)' : 'transparent'}`,
                                            cursor: 'pointer',
                                        }}
                                        onMouseEnter={(e) => {
                                            if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-elevated)';
                                        }}
                                        onMouseLeave={(e) => {
                                            if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
                                        }}
                                    >
                                        <div
                                            className="text-xs truncate"
                                            style={{
                                                color: isActive ? 'var(--accent)' : 'var(--text-primary)',
                                                fontWeight: isActive ? 500 : 400,
                                                lineHeight: '1.4',
                                            }}
                                        >
                                            {s.title}
                                        </div>
                                        <div style={{ color: 'var(--text-muted)', fontSize: '10px', marginTop: '2px' }}>
                                            {formatRelativeTime(s.last_active_at)}
                                        </div>
                                    </button>
                                );
                            })
                        )}
                    </div>
                ) : (
                    <div className="space-y-0.5 pt-1">
                        <div className="text-xs font-semibold uppercase tracking-widest mb-2 px-1" style={{ color: 'var(--text-muted)' }}>
                            Cloud C-Suite
                        </div>
                        {Object.entries(AGENT_INFO).map(([key, info]) => {
                            const isActive = activeAgents.includes(key);
                            return (
                                <div
                                    key={key}
                                    className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg"
                                    style={{
                                        background: isActive ? `${info.color}15` : 'transparent',
                                        border: isActive ? `1px solid ${info.color}33` : '1px solid transparent',
                                    }}
                                >
                                    <span className="text-base" style={{ lineHeight: 1 }}>{info.emoji}</span>
                                    <div className="flex-1 min-w-0">
                                        <div className="text-xs font-semibold" style={{ color: isActive ? info.color : 'var(--text-secondary)' }}>
                                            {key}
                                        </div>
                                    </div>
                                    {isActive && (
                                        <div className="w-1.5 h-1.5 rounded-full" style={{ background: info.color }} />
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="px-4 py-4" style={{ borderTop: '1px solid var(--border)' }}>
                <button
                    onClick={onNewSession}
                    className="w-full text-xs py-2 rounded-lg transition-colors mb-2"
                    style={{
                        background: 'transparent',
                        border: '1px solid var(--border)',
                        color: 'var(--text-muted)',
                        cursor: 'pointer',
                    }}
                    onMouseEnter={(e) => {
                        (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--accent)';
                        (e.currentTarget as HTMLButtonElement).style.color = 'var(--accent)';
                    }}
                    onMouseLeave={(e) => {
                        (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border)';
                        (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-muted)';
                    }}
                >
                    + New Session
                </button>
                <button
                    onClick={onLogout}
                    className="w-full text-xs py-2 rounded-lg transition-colors"
                    style={{
                        background: 'transparent',
                        border: '1px solid var(--border)',
                        color: 'var(--text-muted)',
                        cursor: 'pointer',
                    }}
                    onMouseEnter={(e) => {
                        (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--danger)';
                        (e.currentTarget as HTMLButtonElement).style.color = 'var(--danger)';
                    }}
                    onMouseLeave={(e) => {
                        (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border)';
                        (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-muted)';
                    }}
                >
                    Sign Out
                </button>
            </div>
        </div>
    );
}
