import type { AuthResponse, UserProfile } from '../types/chat';

const TOKEN_KEY = 'nova_token';
const USER_KEY = 'nova_user';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setSession(auth: AuthResponse) {
  localStorage.setItem(TOKEN_KEY, auth.token);
  localStorage.setItem(USER_KEY, JSON.stringify(auth.user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getStoredUser(): UserProfile | null {
  const raw = localStorage.getItem(USER_KEY);

  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as UserProfile;
  } catch {
    clearSession();
    return null;
  }
}

export function updateStoredUser(updates: Partial<UserProfile>) {
  const current = getStoredUser();
  if (!current) return null;

  const next = { ...current, ...updates };
  localStorage.setItem(USER_KEY, JSON.stringify(next));
  return next;
}
