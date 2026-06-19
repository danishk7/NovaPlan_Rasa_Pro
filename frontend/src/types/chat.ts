import type { RasaBotMessage } from '../lib/rasaParser';

export interface ChatMessage {
  id?: string;
  sender: 'user' | 'bot' | 'support' | 'admin';
  text: string;
  rasa?: RasaBotMessage;
  timestamp?: string;
}

export type Role = 'user' | 'admin' | 'support';

export interface UserProfile {
  userId: string;
  name: string;
  email: string;
  role: Role;
  bio?: string;
  location?: string;
  loyaltyTier?: string;
}

export interface BlogPost {
  id: string;
  userId?: string;
  userName?: string;
  title: string;
  content: string;
  imageUrl?: string;
  createdAt?: string;
}

export interface ContactMessage {
  conId?: string | number;
  name: string;
  email: string;
  topic: string;
  message: string;
  createdAt?: string;
}

export interface AuthResponse {
  token: string;
  user: UserProfile;
}

export interface SupportSession {
  sesId: string;
  userId?: string;
  userName?: string;
  status?: string;
  lastMessage?: string;
  updatedAt?: string;
  needsHuman?: boolean | 'true' | 'false' | string;
}

export interface Conversation {
  covId: string | number;
  sesId: string;
  userId?: string | null;
  userName?: string | null;
  userRole?: 'user' | 'support' | 'admin' | null;
  text: string;
  timestamp: string;
}

export interface Itinerary {
  itnId: string;
  userId: string;
  time?: string;
  title: string;
  note?: string;
  summary?: Record<string, unknown> | string;
  status?: string;
  createdAt?: string;
}

export interface Airport {
  code: string;
  name: string;
  city: string;
  lat: number;
  lon: number;
}
