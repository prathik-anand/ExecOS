import { useState, useRef, useCallback } from 'react';

const GEMINI_MODEL = import.meta.env.VITE_GEMINI_MODEL || 'gemini-2.0-flash';
const GEMINI_API_URL = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent`;

export type VoiceState = 'idle' | 'recording' | 'processing';

export function useVoice(onTranscript: (text: string) => void) {
    const [voiceState, setVoiceState] = useState<VoiceState>('idle');
    const [error, setError] = useState<string | null>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const chunksRef = useRef<Blob[]>([]);

    const startRecording = useCallback(async () => {
        setError(null);
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            chunksRef.current = [];

            mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) chunksRef.current.push(e.data);
            };

            mediaRecorder.start();
            setVoiceState('recording');
        } catch {
            setError('Microphone access denied');
        }
    }, []);

    const stopRecording = useCallback(async () => {
        const mediaRecorder = mediaRecorderRef.current;
        if (!mediaRecorder || mediaRecorder.state === 'inactive') return;

        setVoiceState('processing');

        await new Promise<void>((resolve) => {
            mediaRecorder.onstop = () => resolve();
            mediaRecorder.stop();
            mediaRecorder.stream.getTracks().forEach((t) => t.stop());
        });

        const apiKey = import.meta.env.VITE_GEMINI_API_KEY;
        if (!apiKey) {
            setError('VITE_GEMINI_API_KEY not set in .env');
            setVoiceState('idle');
            return;
        }

        try {
            const mimeType = chunksRef.current[0]?.type || 'audio/webm';
            const audioBlob = new Blob(chunksRef.current, { type: mimeType });
            const base64 = await blobToBase64(audioBlob);

            const res = await fetch(`${GEMINI_API_URL}?key=${apiKey}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contents: [{
                        parts: [
                            { text: 'Transcribe this audio exactly as spoken. Return only the spoken words, no commentary.' },
                            { inline_data: { mime_type: mimeType, data: base64 } },
                        ],
                    }],
                    generationConfig: { temperature: 0 },
                }),
            });

            const data = await res.json();
            if (!res.ok) {
                setError(data?.error?.message || 'Gemini API error');
                return;
            }

            const transcript = data?.candidates?.[0]?.content?.parts?.[0]?.text?.trim();
            if (transcript) onTranscript(transcript);
        } catch (err) {
            setError('Transcription failed. Check your API key.');
        } finally {
            setVoiceState('idle');
        }
    }, [onTranscript]);

    const toggle = useCallback(() => {
        if (voiceState === 'idle') startRecording();
        else if (voiceState === 'recording') stopRecording();
    }, [voiceState, startRecording, stopRecording]);

    return { voiceState, error, toggle };
}

function blobToBase64(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
            const result = reader.result as string;
            resolve(result.split(',')[1]);
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}
