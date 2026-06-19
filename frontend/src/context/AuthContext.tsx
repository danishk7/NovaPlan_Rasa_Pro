import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import { login as loginRequest, register as registerRequest } from '../lib/api';
import { clearSession, getStoredUser, updateStoredUser } from '../lib/session';
import type { UserProfile } from '../types/chat';

interface AuthContextValue {
  profile: UserProfile | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<UserProfile>;
  register: (name: string, email: string, password: string) => Promise<UserProfile>;
  updateProfile: (updates: Partial<UserProfile>) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<UserProfile | null>(() => getStoredUser());
  const [loading] = useState(false);

  const value = useMemo<AuthContextValue>(
    () => ({
      profile,
      loading,
      login: async (email, password) => {
        const auth = await loginRequest(email, password);
        setProfile(auth.user);
        return auth.user;
      },
      register: async (name, email, password) => {
        const auth = await registerRequest(name, email, password);
        setProfile(auth.user);
        return auth.user;
      },
      updateProfile: (updates) => {
        setProfile((current) => {
          if (!current) return current;
          return updateStoredUser(updates) ?? current;
        });
      },
      logout: () => {
        clearSession();
        setProfile(null);
      },
    }),
    [loading, profile],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }

  return context;
}
