import { useState } from 'react';
import type { ChatMessage } from '../hooks/useChat';

interface AgentMessageProps {
    message: ChatMessage;
}

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
        .replace(/\n\n/g, '</p><p>')
        .replace(/^(.+)$/gm, (line) => {
            if (line.startsWith('<')) return line;
            return line;
        });
}

export default function AgentMessageComponent({ message }: AgentMessageProps) {
    const [expanded, setExpanded] = useState(true);

    const isBoardroom = message.isSynthesis || message.agentName === 'Boardroom';

    return (
        <div className="animate-fade-in-up mb-4">
            {/* Agent header */}
            <div className="flex items-center gap-2 mb-2">
                <div
                    className="w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold"
                    style={{
                        background: message.agentColor ? `${message.agentColor}22` : 'var(--bg-elevated)',
                        border: `1px solid ${message.agentColor ? message.agentColor + '44' : 'var(--border)'}`,
                    }}
                >
                    {message.agentEmoji || '🤖'}
                </div>
                <span
                    className="text-xs font-semibold uppercase tracking-widest"
                    style={{ color: message.agentColor || 'var(--text-secondary)' }}
                >
                    {message.agentName || message.agentKey || 'Agent'}
                </span>
                {message.isSynthesis && (
                    <span
                        className="text-xs px-2 py-0.5 rounded-full"
                        style={{ background: 'var(--accent-glow)', color: 'var(--accent)', border: '1px solid var(--border-active)' }}
                    >
                        Executive Briefing
                    </span>
                )}
                <button
                    onClick={() => setExpanded(!expanded)}
                    className="ml-auto text-xs"
                    style={{ color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}
                >
                    {expanded ? '▲ collapse' : '▼ expand'}
                </button>
            </div>

            {/* Message content */}
            {expanded && (
                <div
                    className="rounded-xl p-4"
                    style={{
                        background: isBoardroom ? 'var(--bg-elevated)' : 'var(--bg-card)',
                        border: isBoardroom
                            ? '1px solid var(--border-active)'
                            : `1px solid ${message.agentColor ? message.agentColor + '22' : 'var(--border)'}`,
                        fontSize: '14px',
                        lineHeight: '1.65',
                        color: 'var(--text-primary)',
                    }}
                >
                    <div
                        className="markdown"
                        dangerouslySetInnerHTML={{
                            __html: renderMarkdown(message.content),
                        }}
                    />
                </div>
            )}
        </div>
    );
}
