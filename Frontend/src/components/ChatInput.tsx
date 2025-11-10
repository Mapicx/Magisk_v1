import { useState } from 'react';
import axios from 'axios';
import { Send } from 'lucide-react';
import { useChatContext } from '@/context/ChatContext';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

export const ChatInput = () => {
  const { threadId, currentResume, jobDescription, addMessage, setIsLoading, isLoading } = useChatContext();
  const [input, setInput] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!input.trim() || !threadId || !currentResume) return;

    const userMessage = input.trim();
    setInput('');
    addMessage({ role: 'user', content: userMessage });
    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append('file', currentResume);
      formData.append('job_description', jobDescription);
      formData.append('thread_id', threadId);
      formData.append('user_message', userMessage);

      const response = await axios.post('http://localhost:8000/optimize_resume', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      addMessage({
        role: 'ai',
        content: response.data.ai_response,
        meta: {
          tool_used: response.data.tool_used,
          tool_trace: response.data.tool_trace,
          thinking_note: response.data.thinking_note ?? null,
        },
      });
    } catch (error: any) {
      console.error('Error:', error);
      toast.error(error.response?.data?.detail || 'Failed to send message');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="border-t border-border bg-background">
      <div className="max-w-3xl mx-auto p-4">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            placeholder="Ask follow-up questions..."
            disabled={isLoading}
            className="flex-1 p-3 bg-card border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-ring resize-none min_h-[56px] max-h-[200px]"
            rows={1}
          />
          <Button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-4 h-14"
          >
            <Send className="h-5 w-5" />
          </Button>
        </form>
      </div>
    </div>
  );
};
