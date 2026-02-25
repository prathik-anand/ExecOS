import { useState, useCallback, useEffect } from 'react';
import { useAuth } from './useAuth';

export interface SubQueryInfo {
    id: string;
    focus: string;
    agents: string[];
}

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant' | 'routing' | 'orchestration';
    content: string;
    agent?: string;
    agent_name?: string;
    agent_emoji?: string;
    agent_color?: string;
    isSynthesis?: boolean;
    // orchestration metadata
    intent?: string;
    complexity?: string;
    sub_queries?: SubQueryInfo[];
    reasoning?: string;
}

type SSEEventCallback = (event: Record<string, unknown>) => void;

export function useChat(onEvent?: SSEEventCallback) {
    const { token } = useAuth();
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isStreaming, setIsStreaming] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);

    const addMessage = useCallback((msg: Omit<ChatMessage, 'id'>) => {
        const id = crypto.randomUUID();
        setMessages((prev) => [...prev, { ...msg, id }]);
        return id;
    }, []);

    const sendMessage = useCallback(
        async (text: string) => {
            if (!text.trim() || isStreaming || !token) return;

            addMessage({ role: 'user', content: text });
            setIsStreaming(true);

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({ message: text, session_id: sessionId }),
                });

                // Capture session ID from response header
                const newSessionId = res.headers.get('X-Session-ID');
                if (newSessionId) setSessionId(newSessionId);

                if (!res.ok || !res.body) {
                    addMessage({ role: 'assistant', content: 'Error connecting to the Boardroom. Please try again.' });
                    return;
                }

                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';

                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue;
                        try {
                            const event: Record<string, unknown> = JSON.parse(line.slice(6));
                            onEvent?.(event);

                            if (event.type === 'orchestration') {
                                addMessage({
                                    role: 'orchestration',
                                    content: event.content as string,
                                    intent: event.intent as string,
                                    complexity: event.complexity as string,
                                    sub_queries: event.sub_queries as SubQueryInfo[],
                                    reasoning: event.reasoning as string,
                                });
                            } else if (event.type === 'routing') {
                                addMessage({ role: 'routing', content: event.content as string });
                            } else if (event.type === 'agent_response') {
                                addMessage({
                                    role: 'assistant',
                                    content: event.content as string,
                                    agent: event.agent as string,
                                    agent_name: event.agent_name as string,
                                    agent_emoji: event.agent_emoji as string,
                                    agent_color: event.agent_color as string,
                                });
                            } else if (event.type === 'synthesis') {
                                addMessage({
                                    role: 'assistant',
                                    content: event.content as string,
                                    isSynthesis: true,
                                });
                            }
                        } catch {
                            // ignore parse errors
                        }
                    }
                }
            } catch (err) {
                addMessage({ role: 'assistant', content: 'Connection error. Please check your internet and try again.' });
            } finally {
                setIsStreaming(false);
            }
        },
        [token, isStreaming, sessionId, addMessage, onEvent]
    );

    const clearMessages = useCallback(() => {
        setMessages([]);
        setSessionId(null);
    }, []);

    return { messages, sendMessage, isStreaming, clearMessages };
}
