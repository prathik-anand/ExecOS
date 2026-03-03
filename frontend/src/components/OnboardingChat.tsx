import { useState, useEffect, useRef, KeyboardEvent } from 'react';
import { useAuth } from '../hooks/useAuth';

interface QAPair {
    q: string;
    a: string;
    field: string;
}

interface NextQuestionResponse {
    complete: boolean;
    question?: string;
    field?: string;
    options?: string[];
    step?: number;
    total?: number;
}

export default function OnboardingChat() {
    const { token, refreshUser } = useAuth();
    const [answers, setAnswers] = useState<QAPair[]>([]);
    const [currentQuestion, setCurrentQuestion] = useState<NextQuestionResponse | null>(null);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isDone, setIsDone] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const bottomRef = useRef<HTMLDivElement>(null);

    const fetchNextQuestion = async (currentAnswers: QAPair[]) => {
        setIsLoading(true);
        try {
            const res = await fetch('/api/v1/onboard/next', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ answers: currentAnswers }),
            });
            if (!res.ok) return;
            const data: NextQuestionResponse = await res.json();
            setCurrentQuestion(data);
            if (data.complete) {
                // auto-complete if AI says so
                await finishOnboarding(currentAnswers);
            }
        } finally {
            setIsLoading(false);
            setTimeout(() => {
                inputRef.current?.focus();
                textareaRef.current?.focus();
            }, 300);
        }
    };

    const finishOnboarding = async (finalAnswers: QAPair[]) => {
        setIsSubmitting(true);
        try {
            const res = await fetch('/api/v1/onboard/complete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ answers: finalAnswers }),
            });
            if (res.ok) {
                setIsDone(true);
                await refreshUser();
            }
        } finally {
            setIsSubmitting(false);
        }
    };

    useEffect(() => {
        fetchNextQuestion([]);
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [answers, currentQuestion]);

    const submitAnswer = async (answer: string) => {
        if (!currentQuestion?.question || isSubmitting) return;
        const value = answer.trim();

        const newPair: QAPair = {
            q: currentQuestion.question,
            a: value || 'skip',
            field: currentQuestion.field || 'other',
        };
        const newAnswers = [...answers, newPair];
        setAnswers(newAnswers);
        setInputValue('');
        setCurrentQuestion(null);

        await fetchNextQuestion(newAnswers);
    };

    const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submitAnswer(inputValue);
        }
    };

    const progress = currentQuestion?.total
        ? Math.round(((currentQuestion.step || 0) / currentQuestion.total) * 100)
        : 0;

    const isTextarea = currentQuestion?.field === 'goals' || currentQuestion?.field === 'challenges';

    if (isDone) {
        return (
            <div className="h-full flex flex-col items-center justify-center" style={{ background: 'var(--bg-base)' }}>
                <div className="text-center">
                    <div className="text-5xl mb-4">🏛️</div>
                    <h2 className="text-xl font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                        Your Boardroom is ready.
                    </h2>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
                        Taking you in...
                    </p>
                    <div className="flex justify-center gap-1 mt-4">
                        {[0, 1, 2].map((i) => (
                            <div
                                key={i}
                                className="w-2 h-2 rounded-full animate-bounce"
                                style={{ background: 'var(--accent)', animationDelay: `${i * 150}ms` }}
                            />
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col" style={{ background: 'var(--bg-base)' }}>
            {/* Header */}
            <div
                className="flex items-center justify-between px-8 py-4"
                style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-surface)' }}
            >
                <div className="flex items-center gap-3">
                    <span className="text-xl">🏛️</span>
                    <span className="font-semibold tracking-wide" style={{ color: 'var(--text-primary)' }}>ExecOS</span>
                </div>
                <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                    Setting up your C-Suite
                    {currentQuestion?.total && currentQuestion?.step !== undefined && (
                        <span className="ml-2">{currentQuestion.step}/{currentQuestion.total}</span>
                    )}
                </div>
            </div>

            {/* Progress bar */}
            <div style={{ height: '2px', background: 'var(--bg-elevated)' }}>
                <div
                    className="h-full transition-all duration-500"
                    style={{ width: `${progress}%`, background: 'linear-gradient(90deg, #6366f1, #8b5cf6)' }}
                />
            </div>

            {/* Chat area */}
            <div className="flex-1 overflow-y-auto px-6 py-6">
                <div className="max-w-xl mx-auto space-y-6">
                    {/* Previous Q&A pairs */}
                    {answers.map((pair, i) => (
                        <div key={i} className="space-y-2 animate-fade-in-up">
                            {/* Question (left / assistant) */}
                            <div className="flex gap-3">
                                <div
                                    className="w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-sm"
                                    style={{ background: 'var(--accent-glow)', border: '1px solid var(--border-active)' }}
                                >
                                    🏛️
                                </div>
                                <div
                                    className="px-4 py-3 rounded-2xl rounded-tl-sm max-w-md"
                                    style={{
                                        background: 'var(--bg-elevated)',
                                        border: '1px solid var(--border)',
                                        color: 'var(--text-secondary)',
                                        fontSize: '14px',
                                    }}
                                >
                                    {pair.q}
                                </div>
                            </div>
                            {/* Answer (right / user) */}
                            {pair.a !== 'skip' && (
                                <div className="flex justify-end">
                                    <div
                                        className="px-4 py-3 rounded-2xl rounded-tr-sm max-w-md"
                                        style={{
                                            background: 'var(--accent)',
                                            color: 'white',
                                            fontSize: '14px',
                                        }}
                                    >
                                        {pair.a}
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}

                    {/* Current question */}
                    {currentQuestion && !currentQuestion.complete && currentQuestion.question && (
                        <div className="animate-fade-in-up">
                            <div className="flex gap-3 mb-4">
                                <div
                                    className="w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-sm"
                                    style={{ background: 'var(--accent-glow)', border: '1px solid var(--border-active)' }}
                                >
                                    🏛️
                                </div>
                                <div
                                    className="px-4 py-3 rounded-2xl rounded-tl-sm"
                                    style={{
                                        background: 'var(--bg-elevated)',
                                        border: '1px solid var(--border-active)',
                                        color: 'var(--text-primary)',
                                        fontSize: '15px',
                                        lineHeight: '1.5',
                                        fontWeight: 500,
                                    }}
                                >
                                    {currentQuestion.question}
                                </div>
                            </div>

                            {/* Options or input */}
                            {currentQuestion.options ? (
                                <div className="flex flex-col gap-2 ml-10">
                                    {currentQuestion.options.map((opt) => (
                                        <button
                                            key={opt}
                                            onClick={() => submitAnswer(opt)}
                                            disabled={isSubmitting}
                                            className="text-left px-4 py-3 rounded-xl font-medium transition-all"
                                            style={{
                                                background: 'var(--bg-elevated)',
                                                border: '1px solid var(--border)',
                                                color: 'var(--text-primary)',
                                                fontSize: '14px',
                                                cursor: 'pointer',
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
                                    <button
                                        onClick={() => submitAnswer('skip')}
                                        style={{ color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px', textAlign: 'left', padding: '4px 0' }}
                                    >
                                        Skip for now →
                                    </button>
                                </div>
                            ) : (
                                <div className="ml-10">
                                    {isTextarea ? (
                                        <textarea
                                            ref={textareaRef}
                                            value={inputValue}
                                            onChange={(e) => setInputValue(e.target.value)}
                                            onKeyDown={handleKeyDown}
                                            placeholder="Type your answer..."
                                            rows={3}
                                            className="w-full px-4 py-3 rounded-xl resize-none outline-none transition-all"
                                            style={{
                                                background: 'var(--bg-elevated)',
                                                border: '1px solid var(--border)',
                                                color: 'var(--text-primary)',
                                                fontSize: '14px',
                                                fontFamily: 'inherit',
                                            }}
                                            onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
                                            onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
                                        />
                                    ) : (
                                        <input
                                            ref={inputRef}
                                            type="text"
                                            value={inputValue}
                                            onChange={(e) => setInputValue(e.target.value)}
                                            onKeyDown={handleKeyDown}
                                            placeholder="Type your answer..."
                                            className="w-full px-4 py-3 rounded-xl outline-none transition-all"
                                            style={{
                                                background: 'var(--bg-elevated)',
                                                border: '1px solid var(--border)',
                                                color: 'var(--text-primary)',
                                                fontSize: '14px',
                                            }}
                                            onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
                                            onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
                                        />
                                    )}
                                    <div className="flex items-center justify-between mt-2">
                                        <button
                                            onClick={() => submitAnswer('skip')}
                                            style={{ color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px' }}
                                        >
                                            Skip for now →
                                        </button>
                                        <button
                                            onClick={() => submitAnswer(inputValue)}
                                            disabled={isSubmitting || !inputValue.trim()}
                                            className="px-5 py-2 rounded-lg font-medium transition-all"
                                            style={{
                                                background: inputValue.trim() ? 'var(--accent)' : 'var(--bg-elevated)',
                                                color: inputValue.trim() ? 'white' : 'var(--text-muted)',
                                                border: 'none',
                                                cursor: inputValue.trim() ? 'pointer' : 'default',
                                                fontSize: '14px',
                                            }}
                                        >
                                            {isSubmitting ? '...' : 'Continue →'}
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Loading state */}
                    {isLoading && (
                        <div className="flex gap-3 animate-fade-in-up">
                            <div
                                className="w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-sm"
                                style={{ background: 'var(--accent-glow)', border: '1px solid var(--border-active)' }}
                            >
                                🏛️
                            </div>
                            <div
                                className="px-4 py-3 rounded-2xl rounded-tl-sm flex items-center gap-1"
                                style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
                            >
                                {[0, 1, 2].map((i) => (
                                    <div
                                        key={i}
                                        className="w-1.5 h-1.5 rounded-full animate-bounce"
                                        style={{ background: 'var(--accent)', animationDelay: `${i * 150}ms` }}
                                    />
                                ))}
                            </div>
                        </div>
                    )}

                    <div ref={bottomRef} />
                </div>
            </div>

            {/* Footer: finish early option */}
            {answers.length >= 3 && !isLoading && currentQuestion && !currentQuestion.complete && (
                <div
                    className="px-6 py-3 flex justify-center"
                    style={{ borderTop: '1px solid var(--border)', background: 'var(--bg-surface)' }}
                >
                    <button
                        onClick={() => finishOnboarding(answers)}
                        disabled={isSubmitting}
                        style={{ color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px' }}
                    >
                        {isSubmitting ? 'Saving...' : 'Skip remaining → Enter the Boardroom'}
                    </button>
                </div>
            )}
        </div>
    );
}
