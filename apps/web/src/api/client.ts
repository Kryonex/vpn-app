function trimTrailingSlashes(value: string): string {
  return value.replace(/\/+$/, '');
}

function safeGetToken(): string | null {
  try {
    const token = localStorage.getItem('session_token');
    const normalized = token?.trim() || null;
    console.info('[auth] access token restored', {
      restored: Boolean(normalized),
    });
    return normalized;
  } catch {
    console.info('[auth] access token restored', {
      restored: false,
    });
    return null;
  }
}

function safeSetToken(token: string): void {
  try {
    localStorage.setItem('session_token', token.trim());
  } finally {
    console.info('[auth] access token stored', {
      stored: Boolean(token.trim()),
    });
  }
}

function safeClearToken(): void {
  try {
    localStorage.removeItem('session_token');
  } finally {
    console.info('[auth] access token cleared');
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
  return safeGetToken();
}

export function setAccessToken(token: string): void {
  safeSetToken(token);
}

export function clearAccessToken(): void {
  safeClearToken();
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
