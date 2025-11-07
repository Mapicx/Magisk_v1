import { Plus } from 'lucide-react';
import { useChatContext } from '@/context/ChatContext';
import { Button } from '@/components/ui/button';

export const Sidebar = () => {
  const { resetChat } = useChatContext();

  return (
    <aside className="w-64 bg-sidebar-background border-r border-sidebar-border flex flex-col h-screen">
      <div className="p-4">
        <Button
          onClick={resetChat}
          className="w-full justify-start gap-2 bg-sidebar-accent hover:bg-sidebar-accent/80"
          variant="secondary"
        >
          <Plus className="h-4 w-4" />
          New Chat
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-3">
        <div className="text-xs text-muted-foreground mb-2 px-2">Recent Chats</div>
        <div className="space-y-1">
          <div className="text-sm text-muted-foreground px-2 py-2 rounded hover:bg-sidebar-accent/50 cursor-pointer">
            Previous optimization...
          </div>
          <div className="text-sm text-muted-foreground px-2 py-2 rounded hover:bg-sidebar-accent/50 cursor-pointer">
            Resume review...
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-sidebar-border">
        <div className="text-xs text-muted-foreground">Resume Optimizer AI</div>
      </div>
    </aside>
  );
};
