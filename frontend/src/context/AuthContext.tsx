import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import * as authService from '../services/auth';
import { clearTokens, isAuthenticated as hasToken } from '../services/api';

export interface AuthUser {
  username: string;
  displayName: string;
  email: string;
  initials: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (
    username: string,
    email: string,
    password: string,
    displayName?: string
  ) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

function buildInitials(displayName: string): string {
  const tokens = displayName.trim().split(/\s+/).filter(Boolean);
  if (tokens.length === 0) return 'U';
  if (tokens.length === 1) return tokens[0].slice(0, 2).toUpperCase();
  return `${tokens[0][0]}${tokens[1][0]}`.toUpperCase();
}

function toAuthUser(profile: authService.UserProfile): AuthUser {
  return {
    ...profile,
    initials: buildInitials(profile.displayName),
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!hasToken()) {
      setLoading(false);
      return;
    }

    authService
      .getProfile()
      .then((profile) => setUser(toAuthUser(profile)))
      .catch(() => {
        clearTokens();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const profile = await authService.login(username, password);
    setUser(toAuthUser(profile));
  }, []);

  const register = useCallback(
    async (username: string, email: string, password: string, displayName?: string) => {
      const profile = await authService.register(username, email, password, displayName);
      setUser(toAuthUser(profile));
    },
    []
  );

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: !!user,
      loading,
      login,
      register,
      logout,
    }),
    [user, loading, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
