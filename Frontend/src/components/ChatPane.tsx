import { useChatContext } from '@/context/ChatContext';
import { InitialForm } from './InitialForm';
import { ChatMessages } from './ChatMessages';
import { ChatInput } from './ChatInput';

export const ChatPane = () => {
  const { threadId } = useChatContext();

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden">
      {!threadId ? (
        <InitialForm />
      ) : (
        <>
          <ChatMessages />
          <ChatInput />
        </>
      )}
    </div>
  );
};
