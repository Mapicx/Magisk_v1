import { createContext, useContext, useState, ReactNode } from 'react';

interface Message {
  role: 'user' | 'ai';
  content: string;
  isStreaming?: boolean;
}

interface ChatContextType {
  threadId: string | null;
  currentResume: File | null;
  jobDescription: string;
  messages: Message[];
  isLoading: boolean;
  isStreaming: boolean;
  resumeText: string;
  resumeFilePath: string;
  resumeFileName: string;
  setThreadId: (id: string | null) => void;
  setCurrentResume: (file: File | null) => void;
  setJobDescription: (jd: string) => void;
  setResumeText: (text: string) => void;
  setResumeFilePath: (path: string) => void;
  setResumeFileName: (name: string) => void;
  addMessage: (message: Message) => void;
  updateLastMessage: (content: string) => void;
  setMessages: (messages: Message[]) => void;
  setIsLoading: (loading: boolean) => void;
  setIsStreaming: (streaming: boolean) => void;
  resetChat: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider = ({ children }: { children: ReactNode }) => {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [currentResume, setCurrentResume] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const addMessage = (message: Message) => {
    setMessages(prev => [...prev, message]);
  };

  const resetChat = () => {
    setThreadId(null);
    setCurrentResume(null);
    setJobDescription('');
    setMessages([]);
    setIsLoading(false);
  };

  return (
    <ChatContext.Provider
      value={{
        threadId,
        currentResume,
        jobDescription,
        messages,
        isLoading,
        setThreadId,
        setCurrentResume,
        setJobDescription,
        addMessage,
        setMessages,
        setIsLoading,
        resetChat,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

export const useChatContext = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChatContext must be used within ChatProvider');
  }
  return context;
};
