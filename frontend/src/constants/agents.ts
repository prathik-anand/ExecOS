export interface AgentInfo {
    emoji: string;
    color: string;
    name: string;
}

export const AGENT_INFO: Record<string, AgentInfo> = {
    CEO:   { emoji: '👑', color: '#6366f1', name: 'Chief Executive Officer' },
    CFO:   { emoji: '💰', color: '#10b981', name: 'Chief Financial Officer' },
    CTO:   { emoji: '⚙️',  color: '#3b82f6', name: 'Chief Technology Officer' },
    CPO:   { emoji: '🎯', color: '#f59e0b', name: 'Chief Product Officer' },
    CMO:   { emoji: '📣', color: '#ec4899', name: 'Chief Marketing Officer' },
    CSO:   { emoji: '🤝', color: '#14b8a6', name: 'Chief Sales Officer' },
    CPeO:  { emoji: '🧑‍🤝‍🧑', color: '#8b5cf6', name: 'Chief People Officer' },
    CCO:   { emoji: '❤️',  color: '#f97316', name: 'Chief Customer Officer' },
    CLO:   { emoji: '⚖️',  color: '#6b7280', name: 'Chief Legal Officer' },
    COO:   { emoji: '🔧', color: '#84cc16', name: 'Chief Operating Officer' },
    CSci:  { emoji: '🔬', color: '#06b6d4', name: 'Chief Scientist' },
    CIO:   { emoji: '🗄️',  color: '#a855f7', name: 'Chief Information Officer' },
    CAIO:  { emoji: '🤖', color: '#f43f5e', name: 'Chief AI Officer' },
    CArch: { emoji: '🏗️', color: '#d97706', name: 'Chief Architect' },
};
