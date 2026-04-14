/**
 * Base HTTP client for the DocLens backend.
 *
 * All successful responses are wrapped by the backend's ApiRenderer:
 *   { "data": <actual payload> }
 * All error responses come from the custom exception handler:
 *   { "error": { "code": "...", "message": "...", "field_errors": {} } }
 *
 * This module unwraps the envelope automatically and manages JWT tokens
 * in localStorage (access + refresh).
 */

const BASE_URL = '/api';
const ACCESS_KEY = 'auth_access';
const REFRESH_KEY = 'auth_refresh';

// ── Token storage ─────────────────────────────────────────────────────────────

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

// ── Error type ────────────────────────────────────────────────────────────────

export class ApiRequestError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly fieldErrors: Record<string, string[]> = {}
  ) {
    super(message);
    this.name = 'ApiRequestError';
  }
}

// ── Token refresh ─────────────────────────────────────────────────────────────

async function refreshAccessToken(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;

  try {
    const res = await fetch(`${BASE_URL}/auth/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) {
      clearTokens();
      return false;
    }
    const json = await res.json();
    const data = json.data ?? json;
    // ROTATE_REFRESH_TOKENS=True means a new refresh token is issued each time
    setTokens(data.access, data.refresh ?? refresh);
    return true;
  } catch {
    return false;
  }
}

// ── Core request ──────────────────────────────────────────────────────────────

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  isRetry = false
): Promise<T> {
  const token = getAccessToken();
  const headers: Record<string, string> = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (body !== undefined && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body:
      body instanceof FormData
        ? body
        : body !== undefined
          ? JSON.stringify(body)
          : undefined,
  });

  // Expired token — try to refresh once, then retry the original request
  if (res.status === 401 && !isRetry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return request<T>(method, path, body, true);
    }
    clearTokens();
    throw new ApiRequestError(
      401,
      'UNAUTHORIZED',
      'Your session has expired. Please log in again.'
    );
  }

  // 204 No Content — nothing to parse
  if (res.status === 204) return undefined as unknown as T;

  const json = await res.json();

  if (!res.ok) {
    const err = json.error ?? {
      code: 'ERROR',
      message: 'An unexpected error occurred.',
      field_errors: {},
    };
    // If the generic message is unhelpful but field errors exist, surface the first one
    const fieldErrors: Record<string, string[]> = err.field_errors ?? {};
    const firstFieldMessage = Object.values(fieldErrors).flat()[0];
    const message =
      firstFieldMessage && err.message === 'Invalid request data.'
        ? firstFieldMessage
        : err.message;
    throw new ApiRequestError(res.status, err.code, message, fieldErrors);
  }

  // Unwrap the { "data": ... } envelope
  return (json.data ?? json) as T;
}

// ── Public API ────────────────────────────────────────────────────────────────

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  postForm: <T>(path: string, form: FormData) => request<T>('POST', path, form),
  del: (path: string) => request<void>('DELETE', path),
};
