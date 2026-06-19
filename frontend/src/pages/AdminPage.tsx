import { useEffect, useState } from 'react';
import { Inbox, LogOut, MessageSquare, Shield, Trash2, Users } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { deleteUser, getChats, getContacts, getMessages, getUsers, updateUserRole } from '../lib/api';
import { useAuth } from '../hooks/useAuth';
import type { ContactMessage, Conversation, Role, SupportSession, UserProfile } from '../types/chat';

const roles: Role[] = ['user', 'support', 'admin'];

export default function AdminPage() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [chats, setChats] = useState<SupportSession[]>([]);
  const [contacts, setContacts] = useState<ContactMessage[]>([]);
  const [messages, setMessages] = useState<Conversation[]>([]);
  const [activeChat, setActiveChat] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'users' | 'chats' | 'contacts'>('users');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const refresh = () => {
    setError('');
    Promise.all([getUsers(), getChats(), getContacts()])
      .then(([userRows, chatRows, contactRows]) => {
        setUsers(userRows);
        setChats(chatRows);
        setContacts(contactRows);
        setActiveChat((current) => current || chatRows[0]?.sesId || '');
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Unable to load admin data'));
  };

  useEffect(refresh, []);

  useEffect(() => {
    if (!activeChat) {
      setMessages([]);
      return;
    }

    getMessages(activeChat)
      .then(setMessages)
      .catch((err) => setError(err instanceof Error ? err.message : 'Unable to load chat messages'));
  }, [activeChat]);

  const handleRole = async (userId: string, role: Role) => {
    setNotice('');
    try {
      const updated = await updateUserRole(userId, role);
      setUsers((current) => current.map((user) => (user.userId === userId ? { ...user, role: updated.role } : user)));
      setNotice('User role updated.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update role');
    }
  };

  const handleDelete = async (userId: string) => {
    setNotice('');
    try {
      await deleteUser(userId);
      setUsers((current) => current.filter((user) => user.userId !== userId));
      setNotice('User deleted.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to delete user');
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/admin/login');
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="hidden min-h-screen w-72 border-r border-slate-200 bg-white p-5 lg:flex lg:flex-col">
        <div className="mb-8 flex items-center gap-3">
          <Shield className="h-7 w-7 text-emerald-700" />
          <div>
            <h1 className="font-black text-slate-950">Admin Portal</h1>
            <p className="text-xs text-slate-500">Neon backend controls</p>
          </div>
        </div>
        <button onClick={() => setActiveTab('users')} className={tabClass(activeTab === 'users')}>
          <Users className="h-4 w-4" />
          User Management
        </button>
        <button onClick={() => setActiveTab('chats')} className={tabClass(activeTab === 'chats')}>
          <MessageSquare className="h-4 w-4" />
          Support Sessions
        </button>
        <button onClick={() => setActiveTab('contacts')} className={tabClass(activeTab === 'contacts')}>
          <Inbox className="h-4 w-4" />
          Contact Messages
        </button>
        <button onClick={handleLogout} className="mt-auto flex w-full items-center gap-3 rounded-lg border border-slate-200 px-4 py-3 text-left text-sm font-bold text-slate-600 transition hover:border-emerald-300 hover:text-emerald-800">
          <LogOut className="h-4 w-4" />
          Logout
        </button>
      </aside>

      <main className="min-w-0 flex-1 p-5 sm:p-8">
        <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <p className="text-sm font-bold uppercase tracking-widest text-emerald-700">Admin</p>
            <h2 className="text-3xl font-black text-slate-950">{activeTab === 'users' ? 'User Management' : activeTab === 'chats' ? 'Support Sessions' : 'Contact Messages'}</h2>
          </div>
          <div className="flex gap-2">
            <button onClick={refresh} className="w-fit rounded-lg border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 hover:border-emerald-500 hover:text-emerald-800">
              Refresh
            </button>
            <button onClick={handleLogout} className="inline-flex w-fit items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 hover:border-emerald-500 hover:text-emerald-800 lg:hidden">
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </div>

        {error && <p className="mb-4 rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-200">{error}</p>}
        {notice && <p className="mb-4 rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200">{notice}</p>}

        {activeTab === 'users' ? (
          <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="grid grid-cols-[1.3fr_1fr_0.8fr_1.2fr] gap-3 border-b border-slate-200 px-5 py-3 text-xs font-bold uppercase tracking-widest text-slate-500">
              <span>User</span>
              <span>Email</span>
              <span>Role</span>
              <span className="text-right">Actions</span>
            </div>
            {users.map((user) => (
              <div key={user.userId} className="grid grid-cols-[1.3fr_1fr_0.8fr_1.2fr] items-center gap-3 border-b border-slate-100 px-5 py-4 last:border-0">
                <div>
                  <p className="font-bold text-slate-950">{user.name}</p>
                  <p className="text-xs text-slate-500">{user.userId}</p>
                </div>
                <p className="truncate text-sm text-slate-600">{user.email}</p>
                <span className="w-fit rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-800">{user.role}</span>
                <div className="flex items-center justify-end gap-2">
                  <select value={user.role} onChange={(event) => handleRole(user.userId, event.target.value as Role)} className="rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm text-slate-950">
                    {roles.map((role) => (
                      <option key={role} value={role}>
                        {role}
                      </option>
                    ))}
                  </select>
                  <button onClick={() => handleDelete(user.userId)} className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-red-400/30 text-red-200 hover:bg-red-400/10" aria-label={`Delete ${user.name}`}>
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </section>
        ) : activeTab === 'chats' ? (
          <section className="grid gap-5 lg:grid-cols-[320px_1fr]">
            <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
              {chats.map((chat) => (
                <button key={chat.sesId} onClick={() => setActiveChat(chat.sesId)} className={`mb-2 w-full rounded-lg p-3 text-left ${activeChat === chat.sesId ? 'bg-emerald-50 text-emerald-900' : 'text-slate-600 hover:bg-slate-100'}`}>
                  <p className="font-bold">{chat.userName || chat.sesId}</p>
                  <p className="truncate text-xs">{chat.lastMessage || 'No message yet'}</p>
                </button>
              ))}
            </div>
            <div className="max-h-[640px] overflow-y-auto rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
              {messages.length === 0 ? (
                <p className="text-sm text-slate-500">No messages selected.</p>
              ) : (
                messages.map((message) => (
                  <div key={message.covId} className="mb-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
                    <p className="text-xs font-bold uppercase tracking-widest text-emerald-700">{message.userRole || 'bot'}</p>
                    <p className="mt-1 text-sm text-slate-700">{message.text}</p>
                  </div>
                ))
              )}
            </div>
          </section>
        ) : (
          <section className="grid gap-4">
            {contacts.map((contact) => (
              <article key={contact.conId || `${contact.email}-${contact.createdAt}`} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-widest text-emerald-700">{contact.topic || 'Contact'}</p>
                    <h3 className="mt-1 text-xl font-black text-slate-950">{contact.name}</h3>
                    <p className="text-sm text-slate-400">{contact.email}</p>
                  </div>
                  {contact.createdAt && <span className="text-xs text-slate-500">{new Date(contact.createdAt).toLocaleString()}</span>}
                </div>
                <p className="mt-4 rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-700">{contact.message}</p>
              </article>
            ))}
            {contacts.length === 0 && <p className="text-sm text-slate-500">No contact messages yet.</p>}
          </section>
        )}
      </main>
    </div>
  );
}

function tabClass(active: boolean) {
  return `mb-2 flex w-full items-center gap-3 rounded-lg px-4 py-3 text-left text-sm font-bold transition ${
    active ? 'bg-emerald-50 text-emerald-900' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950'
  }`;
}
