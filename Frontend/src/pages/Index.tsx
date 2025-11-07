import { Sidebar } from '@/components/Sidebar';
import { ChatPane } from '@/components/ChatPane';

const Index = () => {
  return (
    <div className="flex w-full h-screen overflow-hidden">
      <Sidebar />
      <ChatPane />
    </div>
  );
};

export default Index;
