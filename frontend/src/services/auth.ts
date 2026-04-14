import { api, setTokens, clearTokens } from './api';

export interface UserProfile {
  username: string;
  displayName: string;
  email: string;
}

// Backend response shapes

interface TokenResponse {
  access: string;
  refresh: string;
}

interface RegisterResponse {
  username: string;
  email: string;
  profile: { display_name: string; avatar_url: string; created_at: string };
  tokens: { access: string; refresh: string };
}

interface ProfileResponse {
  id: number;
  username: string;
  email: string;
  profile: { display_name: string; avatar_url: string; created_at: string };
}

// ── Auth operations ───────────────────────────────────────────────────────────

export async function login(username: string, password: string): Promise<UserProfile> {
  const data = await api.post<TokenResponse>('/auth/token/', { username, password });
  setTokens(data.access, data.refresh);
  // Fetch profile to get display_name and email
  return getProfile();
}

export async function register(
  username: string,
  email: string,
  password: string,
  displayName?: string
): Promise<UserProfile> {
  const data = await api.post<RegisterResponse>('/auth/register/', {
    username,
    email,
    password,
    display_name: displayName ?? '',
  });
  setTokens(data.tokens.access, data.tokens.refresh);
  return {
    username: data.username,
    email: data.email,
    displayName: data.profile.display_name || data.username,
  };
}

export async function getProfile(): Promise<UserProfile> {
  const data = await api.get<ProfileResponse>('/profile/');
  return {
    username: data.username,
    email: data.email,
    displayName: data.profile.display_name || data.username,
  };
}

export function logout(): void {
  clearTokens();
}
