interface SidebarProps {
    context: Record<string, string>;
    activeAgents: string[];
    messageCount: number;
    onClearSession: () => void;
}

const AGENT_INFO: Record<string, { emoji: string; color: string; name: string }> = {
    CEO: { emoji: '👑', color: '#6366f1', name: 'Chief Executive Officer' },
    CFO: { emoji: '💰', color: '#10b981', name: 'Chief Financial Officer' },
    CTO: { emoji: '⚙️', color: '#3b82f6', name: 'Chief Technology Officer' },
    CPO: { emoji: '🎯', color: '#f59e0b', name: 'Chief Product Officer' },
    CMO: { emoji: '📣', color: '#ec4899', name: 'Chief Marketing Officer' },
    CSO: { emoji: '🤝', color: '#14b8a6', name: 'Chief Sales Officer' },
    CPeO: { emoji: '🧑‍🤝‍🧑', color: '#8b5cf6', name: 'Chief People Officer' },
    CCO: { emoji: '❤️', color: '#f97316', name: 'Chief Customer Officer' },
    CLO: { emoji: '⚖️', color: '#6b7280', name: 'Chief Legal Officer' },
    COO: { emoji: '🔧', color: '#84cc16', name: 'Chief Operating Officer' },
    CSci: { emoji: '🔬', color: '#06b6d4', name: 'Chief Scientist' },
    CIO: { emoji: '🗄️', color: '#a855f7', name: 'Chief Information Officer' },
    CAIO: { emoji: '🤖', color: '#f43f5e', name: 'Chief AI Officer' },
    CArch: { emoji: '🏗️', color: '#d97706', name: 'Chief Architect' },
};

export default function Sidebar({ context, activeAgents, messageCount, onClearSession }: SidebarProps) {
    const allAgentKeys = Object.keys(AGENT_INFO);

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
            {/* Logo */}
            <div className="px-5 py-5" style={{ borderBottom: '1px solid var(--border)' }}>
                <div className="flex items-center gap-2.5">
                    <span className="text-xl">🏛️</span>
                    <div>
                        <div className="font-bold tracking-wide" style={{ color: 'var(--text-primary)', fontSize: '15px' }}>ExecOS</div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Cloud C-Suite</div>
                    </div>
                </div>
            </div>

            {/* Context profile */}
            {Object.keys(context).length > 0 && (
                <div className="px-4 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
                    <div className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: 'var(--text-muted)' }}>
                        Your Profile
                    </div>
                    <div className="space-y-1.5">
                        {context.name && (
                            <div>
                                <div style={{ color: 'var(--text-primary)', fontSize: '14px', fontWeight: '500' }}>{context.name}</div>
                            </div>
                        )}
                        {context.role && (
                            <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{context.role}</div>
                        )}
                        {context.company_name && (
                            <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{context.company_name}</div>
                        )}
                        {context.company_stage && (
                            <div
                                className="inline-block mt-1 px-2 py-0.5 rounded text-xs"
                                style={{ background: 'var(--accent-glow)', color: 'var(--accent)', border: '1px solid var(--border-active)' }}
                            >
                                {context.company_stage}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Cloud C-Suite */}
            <div className="flex-1 overflow-y-auto px-4 py-4">
                <div className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: 'var(--text-muted)' }}>
                    Cloud C-Suite
                </div>
                <div className="space-y-1">
                    {allAgentKeys.map((key) => {
                        const info = AGENT_INFO[key];
                        const isActive = activeAgents.includes(key);
                        return (
                            <div
                                key={key}
                                className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg transition-all"
                                style={{
                                    background: isActive ? `${info.color}15` : 'transparent',
                                    border: isActive ? `1px solid ${info.color}33` : '1px solid transparent',
                                }}
                            >
                                <span className="text-base" style={{ lineHeight: 1 }}>{info.emoji}</span>
                                <div className="flex-1 min-w-0">
                                    <div
                                        className="text-xs font-semibold"
                                        style={{ color: isActive ? info.color : 'var(--text-secondary)' }}
                                    >
                                        {key}
                                    </div>
                                </div>
                                {isActive && (
                                    <div
                                        className="w-1.5 h-1.5 rounded-full"
                                        style={{ background: info.color }}
                                    />
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Footer stats */}
            <div className="px-4 py-4" style={{ borderTop: '1px solid var(--border)' }}>
                <div className="flex items-center justify-between mb-3">
                    <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                        {messageCount} exchanges
                    </div>
                    <div className="flex items-center gap-1">
                        <div className="w-1.5 h-1.5 rounded-full" style={{ background: '#10b981' }} />
                        <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Online</span>
                    </div>
                </div>
                <button
                    onClick={onClearSession}
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
                    New Session
                </button>
            </div>
        </div>
    );
}
