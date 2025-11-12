import { useEffect, useRef, useState } from 'react';
import { useChatContext } from '@/context/ChatContext';
import ReactMarkdown from 'react-markdown';
import { Download, User, Bot } from 'lucide-react';
import { Button } from '@/components/ui/button';

export const ChatMessages = () => {
  const { messages } = useChatContext();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState<Record<number, boolean>>({});

  useEffect(() => {
    // ensure the container scrolls to bottom when messages change
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  const extractDownloadFilename = (content: string): string | null => {
    const match = content.match(/New resume saved at:.*?([^\s/]+_optimized_[^\s/]+\.pdf)/);
    return match ? match[1] : null;
    // Adjust this parser if your backend returns a different line for filename disclosure.
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
    // ensure this container takes available height and provides an internal scroll
    <div className="flex-1 h-full overflow-y-auto px-4 py-8">
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

                  {/* Download button if filename is present in content */}
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

                  {/* Collapsible: Thinking & Tools */}
                  {message.meta?.tool_trace && message.meta.tool_trace.length > 0 && (
                    <div className="mt-4 border rounded-md overflow-hidden">
                      <button
                        type="button"
                        onClick={() => setOpen((v) => ({ ...v, [index]: !v[index] }))}
                        className="w-full text-left px-3 py-2 text-sm font-medium bg-muted hover:bg-muted/80"
                      >
                        {open[index] ? '▾' : '▸'} Thinking & Tools
                      </button>

                      {open[index] && (
                        <div className="px-3 py-3 space-y-3">
                          {message.meta.thinking_note && (
                            <div className="text-xs text-muted-foreground">
                              {message.meta.thinking_note}
                            </div>
                          )}

                          <div className="space-y-2">
                            {message.meta.tool_trace.map((t, i) => (
                              <div key={i} className="text-xs bg-background border rounded p-2">
                                {t.type === 'call' ? (
                                  <div>
                                    <div className="font-semibold">🔧 Tool Call: {t.tool || 'unknown'}</div>
                                    {t.args && (
                                      <pre className="mt-1 whitespace-pre-wrap break-words text-[11px]">
                                        {JSON.stringify(t.args, null, 2)}
                                      </pre>
                                    )}
                                  </div>
                                ) : (
                                  <div>
                                    <div className="font-semibold">📦 Tool Result: {t.tool || 'unknown'}</div>
                                    {t.content && (
                                      <pre className="mt-1 whitespace-pre-wrap break-words text-[11px] max-h-48 overflow-auto">
                                        {t.content}
                                      </pre>
                                    )}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
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
