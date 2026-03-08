function trimTrailingSlashes(value: string): string {
  return value.replace(/\/+$/, '');
}

let accessTokenCache: string | null = null;

function safeGetStorage(key: string): string | null {
  try {
    return localStorage.getItem(key) || sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSetStorage(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
    sessionStorage.setItem(key, value);
  } catch {
    // Ignore storage issues in restricted Telegram webviews.
  }
}

function safeRemoveStorage(key: string): void {
  try {
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
  } catch {
    // Ignore storage issues in restricted Telegram webviews.
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
    return accessTokenCache;
  }
  const stored = safeGetStorage('session_token');
  accessTokenCache = stored?.trim() || null;
  return accessTokenCache;
}

export function setAccessToken(token: string): void {
  accessTokenCache = token.trim();
  safeSetStorage('session_token', accessTokenCache);
}

export function clearAccessToken(): void {
  accessTokenCache = null;
  safeRemoveStorage('session_token');
}

function getAdminToken(): string | null {
  const envToken = (import.meta.env.VITE_ADMIN_BEARER_TOKEN as string | undefined)?.trim();
  if (envToken) {
    return envToken;
  }
  return getAccessToken();
}

export async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const isAdminPath = path.startsWith('/admin');
  const token = isAdminPath ? getAdminToken() : getAccessToken();
  const requestUrl = `${API_BASE}${path}`;

  const headers = new Headers(options?.headers);
  headers.set('Content-Type', 'application/json');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  console.info('[api] request', {
    path,
    isAdminPath,
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
