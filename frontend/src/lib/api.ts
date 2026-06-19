import { CONFIG, getAuthApiBaseUrl } from '../config/config';
import type { RasaBotMessage } from './rasaParser';
import { parseRasaResponses } from './rasaParser';
import { clearSession, getStoredUser, getToken, setSession } from './session';
import type { AuthResponse, ContactMessage, Conversation, Itinerary, Role, SupportSession, UserProfile } from '../types/chat';

const RASA_BASE_URL = CONFIG.API_BASE_URL;

export { clearSession, getStoredUser, getToken, setSession };

export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = getToken();
  const headers = new Headers(options.headers);

  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  return fetch(`${getAuthApiBaseUrl()}${path}`, {
    ...options,
    headers,
  });
}

async function readJson<T>(response: Response): Promise<T> {
  const raw = await response.text();
  let data: unknown = null;

  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      data = { detail: raw };
    }
  }

  if (!response.ok) {
    const errorData = data && typeof data === 'object' ? (data as Record<string, unknown>) : {};
    const message = errorData.detail || errorData.error || errorData.message || raw || `Request failed (${response.status})`;
    throw new Error(String(message));
  }

  return data as T;
}

export async function login(email: string, password: string) {
  const response = await apiFetch('/api/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  const auth = await readJson<AuthResponse>(response);
  setSession(auth);
  return auth;
}

export async function register(name: string, email: string, password: string) {
  const response = await apiFetch('/api/register', {
    method: 'POST',
    body: JSON.stringify({ name, email, password }),
  });
  const auth = await readJson<AuthResponse>(response);
  setSession(auth);
  return auth;
}

export async function getUsers() {
  const response = await apiFetch('/api/users');
  return readJson<UserProfile[]>(response);
}

export async function updateUserRole(userId: string, role: Role) {
  const response = await apiFetch(`/api/users/${userId}/role`, {
    method: 'PATCH',
    body: JSON.stringify({ role }),
  });
  return readJson<UserProfile>(response);
}

export async function deleteUser(userId: string) {
  const response = await apiFetch(`/api/users/${userId}`, {
    method: 'DELETE',
  });
  return readJson<{ success: boolean }>(response);
}

export async function updateProfile(userId: string, updates: Partial<UserProfile>) {
  const response = await apiFetch(`/api/profile/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  });
  return readJson<{ success: boolean }>(response);
}

export async function sendContact(message: ContactMessage) {
  const response = await apiFetch('/api/contact', {
    method: 'POST',
    body: JSON.stringify(message),
  });
  return readJson<{ success: boolean }>(response);
}

export async function getContacts() {
  const response = await apiFetch('/api/contacts');
  return readJson<ContactMessage[]>(response);
}

export async function getChats() {
  const response = await apiFetch('/api/sessions');
  return readJson<SupportSession[]>(response);
}

export async function getOrCreateUserChat(userId: string) {
  const response = await apiFetch(`/api/sessions/user/${userId}`);
  return readJson<SupportSession>(response);
}

export async function getMessages(chatId: string) {
  const response = await apiFetch(`/api/sessions/${chatId}/conversations`);
  return readJson<Conversation[]>(response);
}

export async function saveMessage(message: {
  sesId: string;
  userId?: string | null;
  text: string;
}) {
  const response = await apiFetch('/api/conversations', {
    method: 'POST',
    body: JSON.stringify(message),
  });
  return readJson<{ success: boolean }>(response);
}

export async function requestHuman(chatId: string) {
  const response = await apiFetch(`/api/sessions/${chatId}/request-human`, {
    method: 'POST',
  });
  return readJson<{ success: boolean }>(response);
}

export async function getItineraries(userId: string) {
  const response = await apiFetch(`/api/itineraries/${userId}`);
  return readJson<Itinerary[]>(response);
}

export async function sendToRasa(sender: string, message: string, user?: UserProfile | null): Promise<RasaBotMessage[]> {
  try {
    const response = await fetch(`${RASA_BASE_URL}${CONFIG.RASA_WEBHOOK}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sender,
        message,
            metadata: user
          ? {
              userId: user.userId,
              user_id: user.userId,
              userName: user.name,
              user_name: user.name,
              email: user.email,
              role: user.role,
            }
          : undefined,
      }),
    });

    if (!response.ok) {
      throw new Error('Rasa server failed');
    }

    const data = await response.json();
    return parseRasaResponses(data);
  } catch (error) {
    console.error(error);
    return [{ text: 'NovaPlan.ai server unavailable.' }];
  }
}
