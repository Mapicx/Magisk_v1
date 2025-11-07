import { useEffect, useRef } from 'react';
import { useChatContext } from '@/context/ChatContext';
import ReactMarkdown from 'react-markdown';
import { Download, User, Bot } from 'lucide-react';
import { Button } from '@/components/ui/button';

export const ChatMessages = () => {
  const { messages } = useChatContext();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const extractDownloadFilename = (content: string): string | null => {
    const match = content.match(/New resume saved at:.*?([^\s/]+_optimized_[^\s/]+\.pdf)/);
    return match ? match[1] : null;
  };

  const handleDownload = async (filename: string) => {
    try {
      const response = await fetch(`http://localhost:8000/download_optimized/${filename}`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto px-4 py-8">
      <div className="max-w-3xl mx-auto space-y-6">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex gap-4 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {message.role === 'ai' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="h-5 w-5 text-primary" />
              </div>
            )}
            
            <div
              className={`max-w-[80%] rounded-lg p-4 ${
                message.role === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-card border border-border'
              }`}
            >
              {message.role === 'ai' ? (
                <div className="prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                  {extractDownloadFilename(message.content) && (
                    <Button
                      onClick={() => handleDownload(extractDownloadFilename(message.content)!)}
                      className="mt-4 gap-2"
                      variant="secondary"
                    >
                      <Download className="h-4 w-4" />
                      Download Optimized Resume
                    </Button>
                  )}
                </div>
              ) : (
                <p className="whitespace-pre-wrap">{message.content}</p>
              )}
            </div>

            {message.role === 'user' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                <User className="h-5 w-5" />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};
