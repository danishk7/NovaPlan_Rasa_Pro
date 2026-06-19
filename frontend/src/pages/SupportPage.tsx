import { useEffect, useState } from 'react';
import { Headphones, LogOut, Send } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getChats, getMessages, saveMessage } from '../lib/api';
import { useAuth } from '../hooks/useAuth';
import type { Conversation, SupportSession } from '../types/chat';
import { storedToChatMessage } from '../lib/chatMessages';
import ChatMessage from '../components/chatbot/ChatMessage';

export default function SupportPage() {
  const { profile, logout } = useAuth();
  const navigate = useNavigate();
  const [chats, setChats] = useState<SupportSession[]>([]);
  const [messages, setMessages] = useState<Conversation[]>([]);
  const [activeChat, setActiveChat] = useState('');
  const [reply, setReply] = useState('');
  const [status, setStatus] = useState('');

  const refreshChats = () => {
    getChats()
      .then((rows) => {
        const requested = rows.filter((chat) => chat.needsHuman === true || chat.needsHuman === 'true');
        setChats(requested.length ? requested : rows);
        setActiveChat((current) => current || requested[0]?.sesId || rows[0]?.sesId || '');
      })
      .catch((error) => setStatus(error instanceof Error ? error.message : 'Unable to load support chats'));
  };

  useEffect(refreshChats, []);

  useEffect(() => {
    if (!activeChat) {
      setMessages([]);
      return;
    }

    getMessages(activeChat)
      .then(setMessages)
      .catch((error) => setStatus(error instanceof Error ? error.message : 'Unable to load messages'));
  }, [activeChat]);

  const sendReply = async () => {
    const text = reply.trim();
    if (!text || !activeChat || !profile) {
      return;
    }

    setReply('');
    await saveMessage({
      sesId: activeChat,
      userId: profile.userId,
      text,
    });
    setMessages((current) => [
      ...current,
      {
        covId: `${Date.now()}`,
        sesId: activeChat,
        userId: profile.userId,
        userName: profile.name,
        userRole: 'support',
        text,
        timestamp: new Date().toISOString(),
      },
    ]);
    refreshChats();
  };

  const handleLogout = () => {
    logout();
    navigate('/admin/login');
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 text-slate-950">
      <aside className="flex h-screen w-80 shrink-0 flex-col border-r border-slate-200 bg-white p-4">
        <div className="mb-5 flex items-center gap-3 px-2">
          <Headphones className="h-6 w-6 text-emerald-700" />
          <div>
            <h1 className="font-black">Support Console</h1>
            <p className="text-xs text-slate-500">Human chat queue</p>
          </div>
        </div>
        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
          {chats.map((chat) => (
            <button
              key={chat.sesId}
              onClick={() => setActiveChat(chat.sesId)}
              className={`w-full rounded-xl p-3 text-left transition ${
                activeChat === chat.sesId ? 'bg-emerald-50 text-emerald-900' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950'
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="font-bold">{chat.userName || chat.sesId}</p>
                {(chat.needsHuman === true || chat.needsHuman === 'true') && <span className="rounded-full bg-red-50 px-2 py-1 text-[10px] font-bold text-red-700">NEEDS HELP</span>}
              </div>
              <p className="mt-1 truncate text-xs">{chat.lastMessage || 'No messages yet'}</p>
            </button>
          ))}
        </div>
        <button onClick={handleLogout} className="mt-4 flex w-full items-center gap-3 rounded-lg border border-slate-200 px-4 py-3 text-left text-sm font-bold text-slate-600 transition hover:border-emerald-300 hover:text-emerald-800">
          <LogOut className="h-4 w-4" />
          Logout
        </button>
      </aside>

      <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <header className="border-b border-slate-200 bg-white p-5">
          <p className="text-sm font-bold uppercase tracking-widest text-emerald-700">Conversation</p>
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-2xl font-black">{chats.find((chat) => chat.sesId === activeChat)?.userName || 'Select a chat'}</h2>
            <button onClick={handleLogout} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 hover:border-emerald-500 hover:text-emerald-800 md:hidden">
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </header>

        {status && <p className="mx-5 mt-4 rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-200">{status}</p>}

        <div className="min-h-0 flex-1 overflow-y-auto p-5">
          {messages.map((message) => (
            <div key={message.covId} className="mb-3">
              <ChatMessage message={storedToChatMessage(message)} interactive={false} />
            </div>
          ))}
        </div>

        <div className="shrink-0 border-t border-slate-200 bg-white p-4">
          <div className="flex gap-2">
            <input
              value={reply}
              onChange={(event) => setReply(event.target.value)}
              onKeyDown={(event) => event.key === 'Enter' && sendReply()}
              placeholder="Reply as support..."
              className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-4 py-3 text-slate-950 outline-none focus:border-emerald-500"
            />
            <button onClick={sendReply} className="inline-flex h-12 w-12 items-center justify-center rounded-lg bg-emerald-600 text-white hover:bg-emerald-700" aria-label="Send support reply">
              <Send className="h-5 w-5" />
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
