import { useState, useRef, useEffect } from 'react';
import { SSEEvent } from '../hooks/useChat';

interface OnboardingProps {
    sessionId: string;
    onComplete: (context: Record<string, string>) => void;
}

interface Question {
    id: string;
    question: string;
    field: string;
    placeholder?: string;
    options?: string[];
    skip_label?: string;
}

export default function Onboarding({ sessionId, onComplete }: OnboardingProps) {
    const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
    const [step, setStep] = useState(0);
    const [total, setTotal] = useState(8);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [context, setContext] = useState<Record<string, string>>({});
    const [history, setHistory] = useState<Array<{ q: string; a: string }>>([]);
    const [isAnimating, setIsAnimating] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Load initial question
    useEffect(() => {
        fetch('/api/session/start', {
            headers: { 'X-Session-ID': sessionId },
        })
            .then((r) => r.json())
            .then((data) => {
                if (data.onboarding_complete) {
                    onComplete(data.context);
                } else if (data.question) {
                    setCurrentQuestion(data.question);
                    setStep(data.step || 0);
                    setTotal(data.total || 8);
                    setIsLoading(false);
                }
            })
            .catch(() => setIsLoading(false));
    }, [sessionId, onComplete]);

    useEffect(() => {
        if (!isLoading && currentQuestion) {
            setTimeout(() => {
                inputRef.current?.focus();
                textareaRef.current?.focus();
            }, 400);
        }
    }, [currentQuestion, isLoading]);

    const submit = async (value: string) => {
        if (!currentQuestion || isAnimating) return;

        const answer = value.trim();
        setIsAnimating(true);

        // Add to history
        if (answer) {
            setContext((prev) => ({ ...prev, [currentQuestion.field]: answer }));
            setHistory((prev) => [...prev, { q: currentQuestion.question, a: answer }]);
        }

        setInputValue('');

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': sessionId,
                },
                body: JSON.stringify({ message: answer || 'skip' }),
            });

            const reader = response.body!.getReader();
            const decoder = new TextDecoder();
            let buf = '';

            while (true) {
                const { done, value: chunk } = await reader.read();
                if (done) break;
                buf += decoder.decode(chunk, { stream: true });
                const lines = buf.split('\n');
                buf = lines.pop() || '';

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    try {
                        const event: SSEEvent = JSON.parse(line.slice(6));
                        if (event.type === 'onboarding_question' && event.question) {
                            setCurrentQuestion(event.question);
                            setStep(event.step || 0);
                            setTotal(event.total || 8);
                        } else if (event.type === 'onboarding_complete') {
                            onComplete(context);
                            return;
                        }
                    } catch { /**/ }
                }
            }
        } finally {
            setIsAnimating(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submit(inputValue);
        }
    };

    const isTextarea = currentQuestion?.id === 'challenges' || currentQuestion?.id === 'goals';
    const progress = total > 0 ? (step / total) * 100 : 0;

    if (isLoading) {
        return (
            <div className="h-full flex items-center justify-center" style={{ background: 'var(--bg-base)' }}>
                <div className="flex items-center gap-3" style={{ color: 'var(--text-secondary)' }}>
                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: 'var(--accent)', animationDelay: '0ms' }} />
                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: 'var(--accent)', animationDelay: '150ms' }} />
                    <div className="w-2 h-2 rounded-full animate-bounce" style={{ background: 'var(--accent)', animationDelay: '300ms' }} />
                </div>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col" style={{ background: 'var(--bg-base)' }}>
            {/* Header */}
            <div className="flex items-center justify-between px-8 py-5" style={{ borderBottom: '1px solid var(--border)' }}>
                <div className="flex items-center gap-3">
                    <span className="text-xl">🏛️</span>
                    <span className="font-semibold tracking-wide" style={{ color: 'var(--text-primary)' }}>ExecOS</span>
                </div>
                <div className="flex items-center gap-2" style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                    <span>Setting up your C-Suite</span>
                    <span>{step}/{total}</span>
                </div>
            </div>

            {/* Progress bar */}
            <div style={{ height: '2px', background: 'var(--bg-elevated)' }}>
                <div
                    className="h-full transition-all duration-500 ease-out"
                    style={{ width: `${progress}%`, background: 'linear-gradient(90deg, #6366f1, #8b5cf6)' }}
                />
            </div>

            {/* Main area */}
            <div className="flex-1 flex flex-col justify-center items-center px-8 overflow-y-auto">
                <div className="w-full max-w-xl">

                    {/* Conversation history */}
                    {history.length > 0 && (
                        <div className="mb-8 space-y-3">
                            {history.slice(-3).map((h, i) => (
                                <div key={i} className="animate-fade-in-up">
                                    <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '2px' }}>{h.q}</p>
                                    <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>→ {h.a}</p>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Current question */}
                    {currentQuestion && (
                        <div className="animate-fade-in-up">
                            <p
                                className="mb-6 font-medium leading-relaxed"
                                style={{ fontSize: '1.3rem', color: 'var(--text-primary)', lineHeight: '1.5' }}
                            >
                                {currentQuestion.question}
                            </p>

                            {/* Options or input */}
                            {currentQuestion.options ? (
                                <div className="space-y-2 mb-4">
                                    {currentQuestion.options.map((opt) => (
                                        <button
                                            key={opt}
                                            onClick={() => submit(opt)}
                                            disabled={isAnimating}
                                            className="w-full text-left px-5 py-3 rounded-xl font-medium transition-all duration-150"
                                            style={{
                                                background: 'var(--bg-elevated)',
                                                border: '1px solid var(--border)',
                                                color: 'var(--text-primary)',
                                                fontSize: '15px',
                                            }}
                                            onMouseEnter={(e) => {
                                                (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--accent)';
                                                (e.currentTarget as HTMLButtonElement).style.background = 'var(--accent-glow)';
                                            }}
                                            onMouseLeave={(e) => {
                                                (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border)';
                                                (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-elevated)';
                                            }}
                                        >
                                            {opt}
                                        </button>
                                    ))}
                                </div>
                            ) : isTextarea ? (
                                <textarea
                                    ref={textareaRef}
                                    value={inputValue}
                                    onChange={(e) => setInputValue(e.target.value)}
                                    onKeyDown={handleKeyDown}
                                    placeholder={currentQuestion.placeholder || 'Type your answer...'}
                                    rows={3}
                                    className="input-glow w-full px-5 py-4 rounded-xl resize-none"
                                    style={{
                                        background: 'var(--bg-elevated)',
                                        border: '1px solid var(--border)',
                                        color: 'var(--text-primary)',
                                        fontSize: '15px',
                                        fontFamily: 'inherit',
                                    }}
                                />
                            ) : (
                                <input
                                    ref={inputRef}
                                    type="text"
                                    value={inputValue}
                                    onChange={(e) => setInputValue(e.target.value)}
                                    onKeyDown={handleKeyDown}
                                    placeholder={currentQuestion.placeholder || 'Type your answer...'}
                                    className="input-glow w-full px-5 py-4 rounded-xl"
                                    style={{
                                        background: 'var(--bg-elevated)',
                                        border: '1px solid var(--border)',
                                        color: 'var(--text-primary)',
                                        fontSize: '15px',
                                    }}
                                />
                            )}

                            <div className="flex items-center justify-between mt-3">
                                <button
                                    onClick={() => submit('skip')}
                                    disabled={isAnimating}
                                    style={{ color: 'var(--text-muted)', fontSize: '13px', background: 'none', border: 'none', cursor: 'pointer' }}
                                >
                                    {currentQuestion.skip_label || 'Skip for now'} →
                                </button>

                                {!currentQuestion.options && (
                                    <button
                                        onClick={() => submit(inputValue)}
                                        disabled={isAnimating || !inputValue.trim()}
                                        className="px-6 py-2.5 rounded-lg font-medium transition-all"
                                        style={{
                                            background: inputValue.trim() ? 'var(--accent)' : 'var(--bg-elevated)',
                                            color: inputValue.trim() ? 'white' : 'var(--text-muted)',
                                            border: 'none',
                                            cursor: inputValue.trim() ? 'pointer' : 'default',
                                            fontSize: '14px',
                                        }}
                                    >
                                        {isAnimating ? '...' : 'Continue →'}
                                    </button>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Dots */}
            <div className="flex justify-center gap-1.5 py-6">
                {Array.from({ length: total }).map((_, i) => (
                    <div
                        key={i}
                        className="rounded-full transition-all duration-300"
                        style={{
                            width: i === step - 1 ? '20px' : '6px',
                            height: '6px',
                            background: i < step ? 'var(--accent)' : 'var(--bg-elevated)',
                        }}
                    />
                ))}
            </div>
        </div>
    );
}
