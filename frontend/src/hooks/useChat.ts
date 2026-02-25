import { useState, useCallback, useRef } from 'react';

export type SSEEventType =
    | 'routing'
    | 'agent_reasoning'
    | 'agent_response'
    | 'synthesis_start'
    | 'synthesis'
    | 'onboarding_question'
    | 'onboarding_complete'
    | 'done'
    | 'error';

export interface SSEEvent {
    type: SSEEventType;
    content?: string;
    agent?: string;
    agent_name?: string;
    agent_emoji?: string;
    agent_color?: string;
    agents?: string[];
    step?: number;
    total?: number;
    question?: {
        id: string;
        question: string;
        field: string;
        placeholder?: string;
        options?: string[];
        skip_label?: string;
    };
}

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant' | 'routing' | 'onboarding';
    content: string;
    events?: SSEEvent[];
    agentKey?: string;
    agentName?: string;
    agentEmoji?: string;
    agentColor?: string;
    isSynthesis?: boolean;
    timestamp: Date;
}

export function useChat(sessionId: string, onEvent?: (event: SSEEvent) => void) {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isStreaming, setIsStreaming] = useState(false);
    const abortRef = useRef<AbortController | null>(null);

    const sendMessage = useCallback(
        async (text: string) => {
            if (isStreaming) return;

            // Add user message
            if (text.trim()) {
                const userMsg: ChatMessage = {
                    id: `user-${Date.now()}`,
                    role: 'user',
                    content: text,
                    timestamp: new Date(),
                };
                setMessages((prev) => [...prev, userMsg]);
            }

            setIsStreaming(true);
            abortRef.current = new AbortController();

            const collectedEvents: SSEEvent[] = [];
            let agentMessages: Record<string, string> = {};
            let synthesisContent = '';
            let routingMsg: ChatMessage | null = null;

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Session-ID': sessionId,
                    },
                    body: JSON.stringify({ message: text }),
                    signal: abortRef.current.signal,
                });

                const reader = response.body!.getReader();
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
                            const event: SSEEvent = JSON.parse(line.slice(6));
                            collectedEvents.push(event);
                            onEvent?.(event);

                            if (event.type === 'routing' && event.agents) {
                                routingMsg = {
                                    id: `routing-${Date.now()}`,
                                    role: 'routing',
                                    content: event.content || '',
                                    agents: event.agents,
                                    timestamp: new Date(),
                                } as ChatMessage & { agents: string[] };
                                setMessages((prev) => [...prev, routingMsg!]);
                            } else if (event.type === 'agent_response' && event.agent) {
                                agentMessages[event.agent] = event.content || '';
                                const agentMsg: ChatMessage = {
                                    id: `agent-${event.agent}-${Date.now()}`,
                                    role: 'assistant',
                                    content: event.content || '',
                                    agentKey: event.agent,
                                    agentName: event.agent_name,
                                    agentEmoji: event.agent_emoji,
                                    agentColor: event.agent_color,
                                    isSynthesis: false,
                                    events: collectedEvents,
                                    timestamp: new Date(),
                                };
                                setMessages((prev) => {
                                    // update or add
                                    const existing = prev.findIndex((m) => m.agentKey === event.agent && !m.isSynthesis);
                                    if (existing >= 0) {
                                        const next = [...prev];
                                        next[existing] = agentMsg;
                                        return next;
                                    }
                                    return [...prev, agentMsg];
                                });
                            } else if (event.type === 'synthesis') {
                                synthesisContent = event.content || '';
                                const synthMsg: ChatMessage = {
                                    id: `synthesis-${Date.now()}`,
                                    role: 'assistant',
                                    content: synthesisContent,
                                    agentEmoji: '🏛️',
                                    agentName: 'Boardroom',
                                    agentColor: '#6366f1',
                                    isSynthesis: true,
                                    timestamp: new Date(),
                                };
                                setMessages((prev) => [...prev, synthMsg]);
                            } else if (event.type === 'onboarding_question' || event.type === 'onboarding_complete') {
                                const obMsg: ChatMessage = {
                                    id: `ob-${Date.now()}`,
                                    role: 'onboarding',
                                    content: event.content || event.question?.question || '',
                                    events: [event],
                                    timestamp: new Date(),
                                };
                                setMessages((prev) => [...prev, obMsg]);
                            }
                        } catch {
                            // skip malformed
                        }
                    }
                }
            } catch (err) {
                if ((err as Error).name !== 'AbortError') {
                    console.error('Stream error:', err);
                }
            } finally {
                setIsStreaming(false);
                abortRef.current = null;
            }
        },
        [sessionId, isStreaming, onEvent]
    );

    const clearMessages = useCallback(() => {
        setMessages([]);
    }, []);

    return { messages, sendMessage, isStreaming, clearMessages };
}
