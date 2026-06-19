import ChatBot from '../components/chatbot/ChatBot';
import UserPortalLayout from '../components/layout/UserPortalLayout';

export default function ChatPage() {
  return (
    <UserPortalLayout>
      <main className="flex min-w-0 flex-1 p-4 sm:p-6">
        <ChatBot />
      </main>
    </UserPortalLayout>
  );
}
