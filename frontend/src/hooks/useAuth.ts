import { useCallback, useEffect, useState } from 'react';
import * as authService from '../services/auth';
import { isAuthenticated as hasToken, clearTokens } from '../services/api';

export interface AuthUser {
  username: string;
  displayName: string;
  email: string;
  initials: string;
}

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

export interface UseAuthReturn {
  user: AuthUser | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

export function useAuth(): UseAuthReturn {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Restore session on mount if a token exists in localStorage
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
    setLoading(true);
    setError(null);
    try {
      const profile = await authService.login(username, password);
      setUser(toAuthUser(profile));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed.';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(
    async (username: string, email: string, password: string, displayName?: string) => {
      setLoading(true);
      setError(null);
      try {
        const profile = await authService.register(username, email, password, displayName);
        setUser(toAuthUser(profile));
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Registration failed.';
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return {
    user,
    isAuthenticated: !!user,
    loading,
    error,
    login,
    register,
    logout,
    clearError,
  };
}
