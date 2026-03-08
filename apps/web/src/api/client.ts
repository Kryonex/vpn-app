function trimTrailingSlashes(value: string): string {
  return value.replace(/\/+$/, '');
}

let accessTokenCache: string | null = null;

function safeReadToken(): string | null {
  try {
    const token = localStorage.getItem('session_token');
    return token?.trim() || null;
  } catch {
    return null;
  }
}

function safeWriteToken(token: string): void {
  try {
    localStorage.setItem('session_token', token.trim());
  } catch {
    // localStorage can be flaky in embedded webviews, memory cache still keeps auth alive.
  }
}

function safeRemoveToken(): void {
  try {
    localStorage.removeItem('session_token');
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

  return 'http://localhost:8000';
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

  const restored = safeReadToken();
  accessTokenCache = restored;
  console.info('[auth] access token restored', {
    restored: Boolean(restored),
    source: restored ? 'localStorage' : 'none',
  });
  return restored;
}

export function setAccessToken(token: string): void {
  const normalized = token.trim();
  accessTokenCache = normalized || null;
  if (normalized) {
    safeWriteToken(normalized);
  }
  console.info('[auth] access token stored', {
    stored: Boolean(normalized),
  });
}

export function clearAccessToken(): void {
  accessTokenCache = null;
  safeRemoveToken();
  console.info('[auth] access token cleared');
}

export async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAccessToken();
  const requestUrl = `${API_BASE}${path}`;

  const headers = new Headers(options?.headers);
  headers.set('Content-Type', 'application/json');
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
