import React, { createContext, useContext, useState, ReactNode } from 'react';

export type ToolTraceItem =
  | { type: 'call'; tool?: string; args?: Record<string, any> }
  | { type: 'result'; tool?: string; content?: string };

export type ChatMessage = {
  role: 'user' | 'ai';
  content: string;
  meta?: {
    tool_used?: boolean;
    tool_trace?: ToolTraceItem[];
    thinking_note?: string | null;
  };
};

type ChatContextType = {
  messages: ChatMessage[];
  addMessage: (m: ChatMessage) => void;
  resetChat: () => void;

  threadId: string | null;
  setThreadId: (v: string | null) => void;

  currentResume: File | null;
  setCurrentResume: (f: File | null) => void;

  jobDescription: string;
  setJobDescription: (v: string) => void;

  isLoading: boolean;
  setIsLoading: (v: boolean) => void;
};

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider = ({ children }: { children: ReactNode }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [currentResume, setCurrentResume] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const addMessage = (m: ChatMessage) => {
    setMessages((prev) => [...prev, m]);
  };

  const resetChat = () => {
    setMessages([]);
    setThreadId(null);
    setCurrentResume(null);
    setJobDescription('');
    setIsLoading(false);
  };

  return (
    <ChatContext.Provider
      value={{
        messages,
        addMessage,
        resetChat,
        threadId,
        setThreadId,
        currentResume,
        setCurrentResume,
        jobDescription,
        setJobDescription,
        isLoading,
        setIsLoading,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

export const useChatContext = () => {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error('useChatContext must be used within ChatProvider');
  return ctx;
};
