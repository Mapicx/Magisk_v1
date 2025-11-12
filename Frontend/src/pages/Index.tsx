import { Sidebar } from '@/components/Sidebar';
import { ChatPane } from '@/components/ChatPane';

const Index = () => {
  return (
    // Use min-h-screen and remove overflow-hidden so inner scroll containers can work correctly.
    <div className="flex w-full min-h-screen">
      <Sidebar />
      <ChatPane />
    </div>
  );
};

export default Index;
