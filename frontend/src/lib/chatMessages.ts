import type { ChatMessage, Conversation } from '../types/chat';
import type { RasaBotMessage } from './rasaParser';

export function storedToChatMessage(message: Conversation): ChatMessage {
  let text = message.text;
  let rasa: RasaBotMessage | undefined;

  try {
    const parsed = JSON.parse(message.text) as {
      text?: string;
      custom?: RasaBotMessage['custom'];
      buttons?: RasaBotMessage['buttons'];
    };

    if (parsed && typeof parsed === 'object') {
      text = parsed.text ?? '';
      rasa = {
        text,
        custom: parsed.custom,
        buttons: parsed.buttons,
      };
    }
  } catch {
    // Historical messages may be plain text.
  }

  const sender = message.userRole === 'support'
    ? 'support'
    : message.userRole === 'admin'
      ? 'admin'
      : rasa || !message.userId
        ? 'bot'
        : 'user';

  return {
    id: String(message.covId),
    sender,
    text,
    rasa,
    timestamp: message.timestamp,
  };
}

export function chatMessageKey(message: ChatMessage) {
  return message.id ?? `${message.sender}:${message.text}:${message.timestamp ?? ''}`;
}

export function appendUniqueMessages(current: ChatMessage[], next: ChatMessage[]) {
  const seen = new Set(current.map(chatMessageKey));
  const merged = [...current];

  for (const message of next) {
    const key = chatMessageKey(message);
    if (!seen.has(key)) {
      seen.add(key);
      merged.push(message);
    }
  }

  return merged;
}
