import { useCallback } from 'react';
import { useChatContext } from '@/context/ChatContext';
import { toast } from 'sonner';

interface StreamingOptions {
    onToken?: (token: string) => void;
    onToolStart?: (message: string) => void;
    onToolResult?: (result: string) => void;
    onError?: (error: string) => void;
    onComplete?: () => void;
}

export const useStreaming = () => {
    const {
        addMessage,
        updateLastMessage,
        setIsStreaming,
        setIsLoading,
        threadId,
        currentResume,
        jobDescription,
        resumeText,
        resumeFilePath,
        resumeFileName
    } = useChatContext();

    const streamInitialOptimization = useCallback(async (
        userMessage: string,
        options: StreamingOptions = {}
    ) => {
        if (!currentResume) {
            toast.error('No resume file selected');
            return;
        }

        setIsLoading(true);
        setIsStreaming(true);

        // Add user message immediately
        addMessage({ role: 'user', content: userMessage });

        // Add empty AI message that will be streamed into
        addMessage({ role: 'ai', content: '', isStreaming: true });

        try {
            const formData = new FormData();
            formData.append('file', currentResume);
            formData.append('job_description', jobDescription);
            formData.append('user_message', userMessage);
            if (threadId) formData.append('thread_id', threadId);

            const response = await fetch('http://localhost:8000/stream_optimize_resume', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body?.getReader();
            if (!reader) {
                throw new Error('No reader available');
            }

            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);

                        if (data === '[DONE]') {
                            options.onComplete?.();
                            setIsStreaming(false);
                            setIsLoading(false);
                            return;
                        }

                        try {
                            const parsed = JSON.parse(data);

                            switch (parsed.type) {
                                case 'token':
                                    updateLastMessage(parsed.token);
                                    options.onToken?.(parsed.token);
                                    break;
                                case 'tool_start':
                                    updateLastMessage(`\n\n🔧 ${parsed.message}\n\n`);
                                    options.onToolStart?.(parsed.message);
                                    break;
                                case 'tool_result':
                                    updateLastMessage(parsed.message);
                                    options.onToolResult?.(parsed.message);
                                    break;
                                case 'error':
                                    toast.error(parsed.message);
                                    options.onError?.(parsed.message);
                                    break;
                            }
                        } catch (e) {
                            console.error('Failed to parse SSE data:', e);
                        }
                    }
                }
            }
        } catch (error: any) {
            console.error('Streaming error:', error);
            toast.error(error.message || 'Failed to stream response');
            options.onError?.(error.message);
        } finally {
            setIsStreaming(false);
            setIsLoading(false);
        }
    }, [currentResume, jobDescription, threadId, addMessage, updateLastMessage, setIsStreaming, setIsLoading]);

    const streamFollowUpChat = useCallback(async (
        userMessage: string,
        options: StreamingOptions = {}
    ) => {
        if (!threadId || !resumeText) {
            toast.error('No active chat session');
            return;
        }

        setIsLoading(true);
        setIsStreaming(true);

        // Add user message immediately
        addMessage({ role: 'user', content: userMessage });

        // Add empty AI message that will be streamed into
        addMessage({ role: 'ai', content: '', isStreaming: true });

        try {
            const formData = new FormData();
            formData.append('user_message', userMessage);
            formData.append('thread_id', threadId);
            formData.append('resume_text', resumeText);
            formData.append('job_description', jobDescription);
            formData.append('resume_file_path', resumeFilePath);
            formData.append('resume_file_name', resumeFileName);

            const response = await fetch('http://localhost:8000/stream_chat', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body?.getReader();
            if (!reader) {
                throw new Error('No reader available');
            }

            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);

                        if (data === '[DONE]') {
                            options.onComplete?.();
                            setIsStreaming(false);
                            setIsLoading(false);
                            return;
                        }

                        try {
                            const parsed = JSON.parse(data);

                            switch (parsed.type) {
                                case 'token':
                                    updateLastMessage(parsed.token);
                                    options.onToken?.(parsed.token);
                                    break;
                                case 'tool_start':
                                    updateLastMessage(`\n\n🔧 ${parsed.message}\n\n`);
                                    options.onToolStart?.(parsed.message);
                                    break;
                                case 'tool_result':
                                    updateLastMessage(parsed.message);
                                    options.onToolResult?.(parsed.message);
                                    break;
                                case 'error':
                                    toast.error(parsed.message);
                                    options.onError?.(parsed.message);
                                    break;
                            }
                        } catch (e) {
                            console.error('Failed to parse SSE data:', e);
                        }
                    }
                }
            }
        } catch (error: any) {
            console.error('Streaming error:', error);
            toast.error(error.message || 'Failed to stream response');
            options.onError?.(error.message);
        } finally {
            setIsStreaming(false);
            setIsLoading(false);
        }
    }, [threadId, resumeText, jobDescription, resumeFilePath, resumeFileName, addMessage, updateLastMessage, setIsStreaming, setIsLoading]);

    return {
        streamInitialOptimization,
        streamFollowUpChat
    };
};