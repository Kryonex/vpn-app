function trimTrailingSlashes(value: string): string {
  return value.replace(/\/+$/, '');
}

let accessTokenCache: string | null = null;

declare global {
  interface Window {
    __VPN_ACCESS_TOKEN__?: string;
  }
}

function safeReadToken(): string | null {
  try {
    const token = localStorage.getItem('session_token') || sessionStorage.getItem('session_token');
    return token?.trim() || null;
  } catch {
    return null;
  }
}

function safeWriteToken(token: string): void {
  try {
    localStorage.setItem('session_token', token.trim());
    sessionStorage.setItem('session_token', token.trim());
  } catch {
    // localStorage can be flaky in embedded webviews, memory cache still keeps auth alive.
  }
}

function safeRemoveToken(): void {
  try {
    localStorage.removeItem('session_token');
    sessionStorage.removeItem('session_token');
  } catch {
    // Ignore storage cleanup issues.
  }
}

function resolveApiBase(): string {
  const envBase = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (envBase && envBase.trim()) {
    return trimTrailingSlashes(envBase.trim());
  }

  if (typeof window !== 'undefined' && window.location?.origin) {
    return `${trimTrailingSlashes(window.location.origin)}/api`;
  }

  return 'http://localhost:18000';
}

const API_BASE = resolveApiBase();

export function getApiBase() {
  return API_BASE;
}

export function getAccessToken(): string | null {
  if (accessTokenCache) {
    console.info('[auth] access token restored', { restored: true, source: 'memory' });
    return accessTokenCache;
  }

  const windowToken = window.__VPN_ACCESS_TOKEN__?.trim() || null;
  if (windowToken) {
    accessTokenCache = windowToken;
    console.info('[auth] access token restored', { restored: true, source: 'window' });
    return windowToken;
  }

  const restored = safeReadToken();
  accessTokenCache = restored;
  if (restored) {
    window.__VPN_ACCESS_TOKEN__ = restored;
  }
  console.info('[auth] access token restored', {
    restored: Boolean(restored),
    source: restored ? 'storage' : 'none',
  });
  return restored;
}

export function setAccessToken(token: string): void {
  const normalized = token.trim();
  accessTokenCache = normalized || null;
  if (normalized) {
    window.__VPN_ACCESS_TOKEN__ = normalized;
    safeWriteToken(normalized);
  }
  console.info('[auth] access token stored', {
    stored: Boolean(normalized),
  });
}

export function clearAccessToken(): void {
  accessTokenCache = null;
  delete window.__VPN_ACCESS_TOKEN__;
  safeRemoveToken();
  console.info('[auth] access token cleared');
}

export async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAccessToken();
  const method = (options?.method || (options?.body ? 'POST' : 'GET')).toUpperCase();
  const isGetLike = method === 'GET' || method === 'HEAD';
  const requestPath = isGetLike
    ? `${path}${path.includes('?') ? '&' : '?'}_ts=${Date.now()}`
    : path;
  const requestUrl = `${API_BASE}${requestPath}`;

  const headers = new Headers(options?.headers);
  if (options?.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  if (!headers.has('Cache-Control')) {
    headers.set('Cache-Control', 'no-cache');
  }
  if (!headers.has('Pragma')) {
    headers.set('Pragma', 'no-cache');
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  console.info('[api] request', {
    path,
    hasAuthToken: Boolean(token),
  });

  let response: Response;
  try {
    response = await fetch(requestUrl, {
      ...options,
      cache: 'no-store',
      headers,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Неизвестная сетевая ошибка';
    throw new Error(`Ошибка сети при запросе ${requestUrl}: ${message}`);
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail =
      typeof payload?.detail === 'string' ? payload.detail : `Ошибка запроса (${response.status})`;
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export function toJsonBody(payload: unknown): RequestInit {
  return {
    method: 'POST',
    body: JSON.stringify(payload),
  };
}
