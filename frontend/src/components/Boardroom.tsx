import { useRef, useEffect, useState, KeyboardEvent } from 'react';
import { useChat, ChatMessage } from '../hooks/useChat';
import { useVoice } from '../hooks/useVoice';
import AgentMessage from './AgentMessage';
import Sidebar from './Sidebar';
import { AuthUser } from '../hooks/useAuth';

interface BoardroomProps {
    user: AuthUser;
    onLogout: () => void;
}

const EXAMPLE_QUERIES = [
    "I'm a 2-person startup, 6 months runway. What should I do next?",
    "How do I price my SaaS product for B2B?",
    "We just got our first 100 customers. How do we scale?",
    "Should I raise a seed round now or wait?",
];

export default function Boardroom({ user, onLogout }: BoardroomProps) {
    const [inputValue, setInputValue] = useState('');
    const [activeAgents, setActiveAgents] = useState<string[]>([]);
    const [memoryCount, setMemoryCount] = useState(0);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    const { messages, sendMessage, isStreaming, clearMessages } = useChat((event) => {
        if (event.type === 'routing' && event.agents) {
            setActiveAgents(event.agents as string[]);
        }
        if (event.type === 'done' && typeof event.memory_count === 'number') {
            setMemoryCount(event.memory_count);
        }
    });

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    const { voiceState, error: voiceError, toggle: toggleVoice } = useVoice((transcript) => {
        if (transcript.trim()) sendMessage(transcript);
    });

    const handleSend = () => {
        const text = inputValue.trim();
        if (!text || isStreaming) return;
        setInputValue('');
        setActiveAgents([]);
        sendMessage(text);
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const userName = user.name || '';
    const messageCount = messages.filter((m) => m.role === 'user').length;

    const renderMessage = (msg: ChatMessage, i: number) => {
        if (msg.role === 'user') {
            return (
                <div key={msg.id} className="flex justify-end mb-4 animate-fade-in-up">
                    <div
                        className="px-4 py-3 rounded-2xl rounded-tr-sm max-w-lg"
                        style={{
                            background: 'var(--accent)',
                            color: 'white',
                            fontSize: '14px',
                            lineHeight: '1.5',
                        }}
                    >
                        {msg.content}
                    </div>
                </div>
            );
        }

        if (msg.role === 'orchestration') {
            const intentEmoji: Record<string, string> = {
                decision: '⚖️', analysis: '📊', planning: '🗺️', brainstorm: '💡', 'check-in': '📋',
            };
            const complexityColor: Record<string, string> = {
                simple: '#10b981', compound: '#f59e0b', complex: '#6366f1',
            };
            return (
                <div key={msg.id} className="mb-3 animate-fade-in-up">
                    <div
                        className="rounded-xl px-4 py-3"
                        style={{
                            background: 'var(--bg-elevated)',
                            border: '1px solid var(--border-active)',
                            fontSize: '12px',
                        }}
                    >
                        {/* Header row */}
                        <div className="flex items-center gap-3 flex-wrap mb-2">
                            <span style={{ color: 'var(--accent)', fontWeight: 600 }}>
                                🧠 Boardroom Analysis
                            </span>
                            {msg.intent && (
                                <span className="px-2 py-0.5 rounded-full" style={{ background: 'var(--accent-glow)', color: 'var(--accent)', border: '1px solid var(--border-active)' }}>
                                    {intentEmoji[msg.intent] || '🎯'} {msg.intent}
                                </span>
                            )}
                            {msg.complexity && (
                                <span className="px-2 py-0.5 rounded-full" style={{ background: `${complexityColor[msg.complexity]}15`, color: complexityColor[msg.complexity] || '#888', border: `1px solid ${complexityColor[msg.complexity] || '#888'}44` }}>
                                    {msg.complexity}
                                </span>
                            )}
                        </div>
                        {/* Sub-query pills */}
                        {msg.sub_queries && msg.sub_queries.length > 1 && (
                            <div className="flex flex-wrap gap-1.5 mb-1.5">
                                {msg.sub_queries.map((sq) => (
                                    <span key={sq.id} className="px-2 py-0.5 rounded-md" style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
                                        🔍 {sq.focus}
                                    </span>
                                ))}
                            </div>
                        )}
                        {/* Reasoning */}
                        {msg.reasoning && (
                            <p style={{ color: 'var(--text-muted)', marginTop: '4px' }}>{msg.reasoning}</p>
                        )}
                    </div>
                </div>
            );
        }

        if (msg.role === 'routing') {
            return (
                <div key={msg.id} className="flex items-center gap-2 mb-3 animate-slide-in">
                    <div
                        className="h-px flex-1"
                        style={{ background: 'var(--border)' }}
                    />
                    <span style={{ color: 'var(--text-muted)', fontSize: '12px', whiteSpace: 'nowrap' }}>
                        {msg.content}
                    </span>
                    <div className="h-px flex-1" style={{ background: 'var(--border)' }} />
                </div>
            );
        }

        if (msg.role === 'assistant') {
            return <AgentMessage key={msg.id} message={msg} />;
        }

        return null;
    };

    return (
        <div className="h-full flex" style={{ background: 'var(--bg-base)' }}>
            {/* Sidebar */}
            <Sidebar
                user={user}
                activeAgents={activeAgents}
                messageCount={messageCount}
                memoryCount={memoryCount}
                onClearSession={() => { clearMessages(); setActiveAgents([]); }}
                onLogout={onLogout}
            />

            {/* Main area */}
            <div className="flex-1 flex flex-col min-w-0">
                {/* Top bar */}
                <div
                    className="flex items-center justify-between px-6 py-4"
                    style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-surface)' }}
                >
                    <div>
                        <h1 className="font-semibold" style={{ color: 'var(--text-primary)', fontSize: '15px' }}>
                            The Boardroom
                        </h1>
                        <p style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                            {userName ? `Welcome back, ${userName}` : '14 CXO agents ready'}
                            {' · '}
                            {isStreaming ? (
                                <span style={{ color: 'var(--accent)' }}>Agents thinking...</span>
                            ) : (
                                <span>Ready</span>
                            )}
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        {isStreaming && (
                            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full" style={{ background: 'var(--accent-glow)', border: '1px solid var(--border-active)' }}>
                                <div className="flex gap-0.5">
                                    {[0, 1, 2].map((i) => (
                                        <div
                                            key={i}
                                            className="w-1 h-1 rounded-full animate-bounce"
                                            style={{ background: 'var(--accent)', animationDelay: `${i * 100}ms` }}
                                        />
                                    ))}
                                </div>
                                <span style={{ color: 'var(--accent)', fontSize: '12px' }}>Processing</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto px-6 py-6">
                    {messages.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center">
                            <div className="text-center mb-10">
                                <div className="text-4xl mb-4">🏛️</div>
                                <h2 className="text-xl font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                                    {userName ? `Good to have you back, ${userName}.` : 'The Boardroom is ready.'}
                                </h2>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
                                    Ask anything — your Cloud C-Suite will route to the right experts.
                                </p>
                            </div>

                            <div className="grid grid-cols-2 gap-3 max-w-2xl w-full">
                                {EXAMPLE_QUERIES.map((q) => (
                                    <button
                                        key={q}
                                        onClick={() => {
                                            setInputValue('');
                                            sendMessage(q);
                                        }}
                                        className="text-left p-4 rounded-xl transition-all"
                                        style={{
                                            background: 'var(--bg-elevated)',
                                            border: '1px solid var(--border)',
                                            color: 'var(--text-secondary)',
                                            fontSize: '13px',
                                            lineHeight: '1.5',
                                            cursor: 'pointer',
                                        }}
                                        onMouseEnter={(e) => {
                                            (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--accent)';
                                            (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)';
                                            (e.currentTarget as HTMLButtonElement).style.background = 'var(--accent-glow)';
                                        }}
                                        onMouseLeave={(e) => {
                                            (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border)';
                                            (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)';
                                            (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-elevated)';
                                        }}
                                    >
                                        {q}
                                    </button>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="max-w-3xl mx-auto">
                            {messages.map((msg, i) => renderMessage(msg, i))}
                            <div ref={messagesEndRef} />
                        </div>
                    )}
                </div>

                {/* Input area */}
                <div
                    className="px-6 py-4"
                    style={{ borderTop: '1px solid var(--border)', background: 'var(--bg-surface)' }}
                >
                    <div className="max-w-3xl mx-auto">
                        {/* Context chips */}
                        <div className="flex gap-2 mb-2 flex-wrap">
                            {user.company_stage && (
                                <span className="text-xs px-3 py-1 rounded-full" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
                                    {user.company_stage}
                                </span>
                            )}
                            {user.industry && (
                                <span className="text-xs px-3 py-1 rounded-full" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
                                    {user.industry}
                                </span>
                            )}
                            <span className="text-xs px-3 py-1 rounded-full" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
                                Tip: use @CEO, @CFO etc. to address specific agents
                            </span>
                        </div>

                        <div
                            className="flex items-end gap-3 p-3 rounded-xl"
                            style={{
                                background: 'var(--bg-elevated)',
                                border: `1px solid ${voiceState === 'recording' ? '#ef4444' : 'var(--border)'}`,
                                transition: 'border-color 0.2s',
                            }}
                        >
                            <textarea
                                ref={inputRef}
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder={voiceState === 'recording' ? 'Listening...' : 'Ask your Boardroom anything...'}
                                rows={2}
                                disabled={isStreaming || voiceState === 'processing'}
                                className="flex-1 resize-none bg-transparent outline-none"
                                style={{
                                    color: 'var(--text-primary)',
                                    fontSize: '14px',
                                    fontFamily: 'inherit',
                                    lineHeight: '1.5',
                                    maxHeight: '120px',
                                }}
                            />
                            {/* Mic button */}
                            <button
                                onClick={toggleVoice}
                                disabled={isStreaming}
                                title={voiceState === 'idle' ? 'Start voice input' : voiceState === 'recording' ? 'Stop recording' : 'Processing...'}
                                className="flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center transition-all"
                                style={{
                                    background: voiceState === 'recording' ? '#ef4444' : voiceState === 'processing' ? 'var(--bg-card)' : 'var(--bg-card)',
                                    border: `1px solid ${voiceState === 'recording' ? '#ef4444' : 'var(--border)'}`,
                                    cursor: isStreaming ? 'default' : 'pointer',
                                    fontSize: '15px',
                                    animation: voiceState === 'recording' ? 'pulse 1s infinite' : 'none',
                                }}
                            >
                                {voiceState === 'processing' ? '⏳' : voiceState === 'recording' ? '⏹' : '🎤'}
                            </button>
                            {/* Send button */}
                            <button
                                onClick={handleSend}
                                disabled={!inputValue.trim() || isStreaming}
                                className="flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center transition-all"
                                style={{
                                    background: inputValue.trim() && !isStreaming ? 'var(--accent)' : 'var(--bg-card)',
                                    border: 'none',
                                    cursor: inputValue.trim() && !isStreaming ? 'pointer' : 'default',
                                    color: 'white',
                                    fontSize: '16px',
                                }}
                            >
                                {isStreaming ? '⏸' : '↑'}
                            </button>
                        </div>
                        {voiceError && (
                            <div className="mt-1 text-xs px-2" style={{ color: '#f87171' }}>{voiceError}</div>
                        )}
                        <div className="text-center mt-2" style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
                            Press Enter to send · Shift+Enter for new line · 🎤 for voice
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
