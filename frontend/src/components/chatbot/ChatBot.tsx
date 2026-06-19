import { useEffect, useMemo, useRef, useState } from 'react';
import { getMessages, getOrCreateUserChat, requestHuman, saveMessage, sendToRasa } from '../../lib/api';
import type { ChatMessage as MessageType, SupportSession } from '../../types/chat';
import { appendUniqueMessages, chatMessageKey, storedToChatMessage } from '../../lib/chatMessages';
import { useAuth } from '../../hooks/useAuth';
import useSpeechRecognition from '../../hooks/useSpeechRecognition';
import ChatInput from './ChatInput';
import ChatMessage from './ChatMessage';
import QuickReplies from './QuickReplies';
import VoiceInput from './VoiceInput';

const initialMessages: MessageType[] = [
  {
    id: 'welcome-local',
    sender: 'bot',
    text: 'Hi, I am NovaPlan.ai. Ask me about flights, hotels, trip planning, or sustainable travel.',
  },
];

export default function ChatBot() {
  const { profile } = useAuth();
  const [messages, setMessages] = useState<MessageType[]>(initialMessages);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [chat, setChat] = useState<SupportSession | null>(null);
  const [humanMode, setHumanMode] = useState(false);
  const [supportNoticeShown, setSupportNoticeShown] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const { transcript, listening, startListening } = useSpeechRecognition();

  const rasaSender = useMemo(() => profile?.userId ?? 'novaplan-web-user', [profile?.userId]);

  useEffect(() => {
    if (!profile?.userId) return;

    getOrCreateUserChat(profile.userId)
      .then((preparedChat) => {
        setChat(preparedChat);
        setHumanMode(false);
        return getMessages(preparedChat.sesId);
      })
      .then((storedMessages) => {
        if (storedMessages.length) {
          setMessages(storedMessages.map(storedToChatMessage));
        }
      })
      .catch((fetchError) => {
        console.error('Unable to prepare user chat', fetchError);
        setError(fetchError instanceof Error ? fetchError.message : 'Unable to prepare chat session');
      });
  }, [profile?.userId]);

  useEffect(() => {
    if (!chat?.sesId || !humanMode) return;

    const loadSupportUpdates = () => {
      getMessages(chat.sesId)
        .then((storedMessages) => {
          const supportMessages = storedMessages.map(storedToChatMessage).filter((message) => message.sender === 'support');
          if (supportMessages.length) {
            setMessages((current) => appendUniqueMessages(current, supportMessages));
          }
        })
        .catch((fetchError) => console.error('Unable to poll support messages', fetchError));
    };

    loadSupportUpdates();
    const intervalId = window.setInterval(loadSupportUpdates, 7000);
    return () => window.clearInterval(intervalId);
  }, [chat?.sesId, humanMode]);

  useEffect(() => {
    if (transcript) setQuery(transcript);
  }, [transcript]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages.length, loading]);

  const persistMessage = (message: {
    userId?: string | null;
    text: string;
  }) => {
    if (!chat) return;
    saveMessage({ sesId: chat.sesId, ...message }).catch((saveError) => console.error('Unable to save message', saveError));
  };

  const handleRequestHuman = () => {
    if (!chat) {
      setError('Chat session is still loading. Please try again in a moment.');
      return;
    }

    setError('');
    requestHuman(chat.sesId)
      .then(() => {
        setHumanMode(true);
        setSupportNoticeShown(true);
        setMessages((current) =>
          appendUniqueMessages(current, [
            {
              id: `handover-${Date.now()}`,
              sender: 'bot',
              text: 'Human support has been notified. Continue typing here and a support agent can respond from the support console.',
              rasa: {
                text: 'Human support has been notified. Continue typing here and a support agent can respond from the support console.',
                custom: { type: 'escalation_banner', data: { severity: 'normal' } },
              },
            },
          ]),
        );
      })
      .catch((requestError) => {
        console.error('Unable to request human support', requestError);
        setError(requestError instanceof Error ? requestError.message : 'Unable to request human support');
      });
  };

  const handleReturnToBot = () => {
    setHumanMode(false);
    setSupportNoticeShown(false);
    setError('');
    setMessages((current) =>
      appendUniqueMessages(current, [
        {
          id: `bot-mode-${Date.now()}`,
          sender: 'bot',
          text: 'You are back with the NovaPlan AI assistant.',
        },
      ]),
    );
  };

  const handleSend = async (overrideText?: string) => {
    const text = (overrideText ?? query).trim();
    if (!text || loading) return;

    const localUserMessage: MessageType = {
      id: `local-user-${Date.now()}`,
      sender: 'user',
      text,
      timestamp: new Date().toISOString(),
    };

    setQuery('');
    setError('');
    setMessages((current) => appendUniqueMessages(current, [localUserMessage]));
    setLoading(true);

    if (chat && profile) {
      persistMessage({
        userId: profile.userId,
        text,
      });
    }

    if (humanMode) {
      if (!supportNoticeShown) {
        setSupportNoticeShown(true);
        setMessages((current) =>
          appendUniqueMessages(current, [
            {
              id: `support-mode-${Date.now()}`,
              sender: 'bot',
              text: 'Your message has been sent to human support. A support agent can reply from the support console.',
            },
          ]),
        );
      }
      setLoading(false);
      return;
    }

    try {
      const responses = await sendToRasa(rasaSender, text, profile);
      const messagesToAppend: MessageType[] =
        responses.length > 0
          ? responses.map((rasa, index) => ({
              id: `rasa-${Date.now()}-${index}`,
              sender: 'bot' as const,
              text: rasa.text ?? '',
              rasa,
              timestamp: new Date().toISOString(),
            }))
          : [{ id: `empty-${Date.now()}`, sender: 'bot' as const, text: 'I did not receive a reply. Please try again.' }];

      setMessages((current) => appendUniqueMessages(current, messagesToAppend));

      if (responses.some((response) => response.custom?.type === 'escalation_banner')) {
        setHumanMode(true);
        setSupportNoticeShown(true);
        if (chat) {
          requestHuman(chat.sesId).catch((requestError) => console.error('Unable to flag chat for human support', requestError));
        }
      }

      if (chat) {
        messagesToAppend.forEach((message) => {
          persistMessage({
            userId: null,
            text: message.rasa ? JSON.stringify({ text: message.text, custom: message.rasa.custom, buttons: message.rasa.buttons }) : message.text,
          });
        });
      }
    } catch (sendError) {
      console.error(sendError);
      setMessages((current) => appendUniqueMessages(current, [{ id: `error-${Date.now()}`, sender: 'bot', text: 'NovaPlan.ai server unavailable.' }]));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-3rem)] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <header className="border-b border-slate-200 bg-white px-5 py-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-lg font-bold text-slate-950">NovaPlan Concierge</h1>
            <p className="text-sm text-slate-600">
              {humanMode ? 'Human support mode - messages are saved for the support team' : 'Sustainable AI travel assistant'}
            </p>
          </div>
          {humanMode ? (
            <button
              type="button"
              onClick={handleReturnToBot}
              className="rounded-lg border border-emerald-300 px-3 py-2 text-xs font-bold text-emerald-800 transition hover:bg-emerald-50"
            >
              Back to chatbot
            </button>
          ) : (
            <button
              type="button"
              onClick={handleRequestHuman}
              disabled={!chat}
              className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-bold text-slate-700 transition hover:border-emerald-500 hover:text-emerald-800 disabled:opacity-40"
            >
              Talk to support
            </button>
          )}
        </div>
        {humanMode && (
          <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900">
            You are in human support mode. Your next messages will be visible to the support agent instead of being sent to the AI assistant.
          </div>
        )}
        {error && <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700">{error}</div>}
      </header>

      {!humanMode && <QuickReplies onSelect={(reply) => void handleSend(reply)} />}

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto overscroll-contain bg-slate-50 px-4 py-5">
        {messages.map((message) => (
          <div key={chatMessageKey(message)}>
            <ChatMessage message={message} onQuickReply={(reply) => void handleSend(reply)} onRequestHuman={handleRequestHuman} />
          </div>
        ))}
        {loading && <div className="text-sm text-slate-500">Thinking...</div>}
        <div ref={messagesEndRef} />
      </div>

      <div className="flex items-end gap-2 border-t border-slate-200 bg-white p-4">
        <VoiceInput onVoice={startListening} listening={listening} />
        <ChatInput value={query} onChange={setQuery} onSend={handleSend} disabled={loading} humanMode={humanMode} />
      </div>
    </div>
  );
}
