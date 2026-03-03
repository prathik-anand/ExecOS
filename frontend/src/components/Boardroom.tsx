import { useRef, useEffect, useState, KeyboardEvent } from 'react';
import { useChat, ChatMessage } from '../hooks/useChat';
import { useVoice } from '../hooks/useVoice';
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

function renderMarkdown(text: string): string {
    return text
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
        .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
        .replace(/^---$/gm, '<hr/>')
        .replace(/\n\n/g, '</p><p>');
}

interface MessageGroup {
    user: ChatMessage;
    thinking: ChatMessage[];
    answer: ChatMessage | null;
}

function groupMessages(msgs: ChatMessage[]): MessageGroup[] {
    const groups: MessageGroup[] = [];
    let current: MessageGroup | null = null;
    for (const msg of msgs) {
        if (msg.role === 'user') {
            if (current) groups.push(current);
            current = { user: msg, thinking: [], answer: null };
        } else if (current) {
            if (msg.role === 'assistant' && msg.isSynthesis) {
                current.answer = msg;
            } else if (msg.role !== 'routing') {
                current.thinking.push(msg);
            }
        }
    }
    if (current) groups.push(current);
    return groups;
}

function ThinkingBlock({ msgs }: { msgs: ChatMessage[] }) {
    const [open, setOpen] = useState(false);
    if (msgs.length === 0) return null;

    const agentCount = msgs.filter(m => m.role === 'assistant').length;

    return (
        <div className="mb-3">
            <button
                onClick={() => setOpen(v => !v)}
                className="flex items-center gap-1.5 text-xs"
                style={{
                    color: 'var(--text-muted)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '2px 0',
                }}
            >
                <span>{open ? '▼' : '▶'}</span>
                <span>Thought with {agentCount} advisor{agentCount !== 1 ? 's' : ''}</span>
            </button>
            {open && (
                <div
                    className="mt-2 rounded-lg overflow-hidden"
                    style={{ border: '1px solid var(--border)', background: 'var(--bg-elevated)' }}
                >
                    {msgs.map((msg, i) => {
                        if (msg.role === 'orchestration') {
                            return (
                                <div
                                    key={msg.id}
                                    className="px-3 py-2"
                                    style={{ borderBottom: '1px solid var(--border)', fontSize: '12px', color: 'var(--text-muted)' }}
                                >
                                    <span style={{ color: 'var(--text-secondary)' }}>Analysis: </span>
                                    {[msg.intent, msg.complexity].filter(Boolean).join(' · ')}
                                    {msg.reasoning && <span> — {msg.reasoning}</span>}
                                </div>
                            );
                        }
                        if (msg.role === 'assistant') {
                            const isLast = i === msgs.length - 1;
                            return (
                                <div
                                    key={msg.id}
                                    className="px-3 py-3"
                                    style={{ borderBottom: isLast ? 'none' : '1px solid var(--border)' }}
                                >
                                    <div className="flex items-center gap-2 mb-1.5">
                                        <span style={{ fontSize: '14px' }}>{msg.agent_emoji}</span>
                                        <span style={{
                                            fontSize: '11px',
                                            fontWeight: 600,
                                            color: msg.agent_color || 'var(--text-secondary)',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.06em',
                                        }}>
                                            {msg.agent_name || msg.agent}
                                        </span>
                                    </div>
                                    <div
                                        className="markdown"
                                        style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.6' }}
                                        dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
                                    />
                                </div>
                            );
                        }
                        return null;
                    })}
                </div>
            )}
        </div>
    );
}

export default function Boardroom({ user, onLogout }: BoardroomProps) {
    const [inputValue, setInputValue] = useState('');
    const [activeAgents, setActiveAgents] = useState<string[]>([]);
    const [memoryCount, setMemoryCount] = useState(0);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    const { messages, sendMessage, isStreaming, clearMessages, sessions, loadSession, sessionId } = useChat((event) => {
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

    const groups = groupMessages(messages);
    const userName = user.name || '';

    return (
        <div className="h-full flex" style={{ background: 'var(--bg-base)' }}>
            <Sidebar
                user={user}
                activeAgents={activeAgents}
                sessions={sessions}
                currentSessionId={sessionId}
                memoryCount={memoryCount}
                onNewSession={() => { clearMessages(); setActiveAgents([]); }}
                onLoadSession={(id) => { loadSession(id); setActiveAgents([]); }}
                onLogout={onLogout}
            />

            <div className="flex-1 flex flex-col min-w-0">
                {/* Top bar */}
                <div
                    className="flex items-center px-6 py-4"
                    style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-surface)' }}
                >
                    <div>
                        <h1 className="font-semibold" style={{ color: 'var(--text-primary)', fontSize: '15px' }}>
                            The Boardroom
                        </h1>
                        <p style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                            {isStreaming ? (
                                <span style={{ color: 'var(--accent)' }}>Agents thinking...</span>
                            ) : (
                                userName ? `Welcome back, ${userName}` : '14 CXO agents ready'
                            )}
                        </p>
                    </div>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto px-6 py-6">
                    {groups.length === 0 ? (
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
                                        onClick={() => { setInputValue(''); sendMessage(q); }}
                                        className="text-left p-4 rounded-xl"
                                        style={{
                                            background: 'var(--bg-elevated)',
                                            border: '1px solid var(--border)',
                                            color: 'var(--text-secondary)',
                                            fontSize: '13px',
                                            lineHeight: '1.5',
                                            cursor: 'pointer',
                                        }}
                                        onMouseEnter={(e) => {
                                            const btn = e.currentTarget as HTMLButtonElement;
                                            btn.style.borderColor = 'var(--accent)';
                                            btn.style.color = 'var(--text-primary)';
                                            btn.style.background = 'var(--accent-glow)';
                                        }}
                                        onMouseLeave={(e) => {
                                            const btn = e.currentTarget as HTMLButtonElement;
                                            btn.style.borderColor = 'var(--border)';
                                            btn.style.color = 'var(--text-secondary)';
                                            btn.style.background = 'var(--bg-elevated)';
                                        }}
                                    >
                                        {q}
                                    </button>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="max-w-3xl mx-auto space-y-8">
                            {groups.map((group, i) => {
                                const isLast = i === groups.length - 1;
                                const stillThinking = isLast && isStreaming && !group.answer;
                                return (
                                    <div key={group.user.id} className="animate-fade-in-up">
                                        {/* User message */}
                                        <div className="flex justify-end mb-5">
                                            <div
                                                className="px-4 py-3 rounded-2xl rounded-tr-sm max-w-lg"
                                                style={{
                                                    background: 'var(--accent)',
                                                    color: 'white',
                                                    fontSize: '14px',
                                                    lineHeight: '1.5',
                                                }}
                                            >
                                                {group.user.content}
                                            </div>
                                        </div>

                                        {/* AI response */}
                                        <div className="flex gap-3">
                                            <div
                                                className="w-7 h-7 flex-shrink-0 rounded-lg flex items-center justify-center text-sm"
                                                style={{
                                                    background: 'var(--accent-glow)',
                                                    border: '1px solid var(--border-active)',
                                                    marginTop: '2px',
                                                }}
                                            >
                                                🏛️
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                {stillThinking ? (
                                                    <div className="flex items-center gap-2" style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
                                                        <div className="flex gap-1">
                                                            {[0, 1, 2].map(j => (
                                                                <div
                                                                    key={j}
                                                                    className="w-1.5 h-1.5 rounded-full animate-bounce"
                                                                    style={{ background: 'var(--accent)', animationDelay: `${j * 150}ms` }}
                                                                />
                                                            ))}
                                                        </div>
                                                        <span>
                                                            {group.thinking.filter(m => m.role === 'assistant').length > 0
                                                                ? `${group.thinking.filter(m => m.role === 'assistant').length} advisors weighed in — synthesizing...`
                                                                : 'Consulting your advisors...'}
                                                        </span>
                                                    </div>
                                                ) : (
                                                    <>
                                                        <ThinkingBlock msgs={group.thinking} />
                                                        {group.answer && (
                                                            <div
                                                                className="markdown"
                                                                style={{ fontSize: '14px', lineHeight: '1.75', color: 'var(--text-primary)' }}
                                                                dangerouslySetInnerHTML={{ __html: renderMarkdown(group.answer.content) }}
                                                            />
                                                        )}
                                                    </>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
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
                        <div
                            className="flex items-end gap-3 p-3 rounded-xl input-glow"
                            style={{
                                background: 'var(--bg-elevated)',
                                border: `1px solid ${voiceState === 'recording' ? '#ef4444' : 'var(--border)'}`,
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
                            <button
                                onClick={toggleVoice}
                                disabled={isStreaming}
                                title={voiceState === 'idle' ? 'Start voice input' : voiceState === 'recording' ? 'Stop recording' : 'Processing...'}
                                className="flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center"
                                style={{
                                    background: voiceState === 'recording' ? '#ef4444' : 'var(--bg-card)',
                                    border: `1px solid ${voiceState === 'recording' ? '#ef4444' : 'var(--border)'}`,
                                    cursor: isStreaming ? 'default' : 'pointer',
                                    fontSize: '15px',
                                }}
                            >
                                {voiceState === 'processing' ? '⏳' : voiceState === 'recording' ? '⏹' : '🎤'}
                            </button>
                            <button
                                onClick={handleSend}
                                disabled={!inputValue.trim() || isStreaming}
                                className="flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center"
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
                            Press Enter to send · Shift+Enter for new line
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
