function trimTrailingSlashes(value: string): string {
  return value.replace(/\/+$/, '');
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

export async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('session_token');
  const requestUrl = `${API_BASE}${path}`;

  const headers = new Headers(options?.headers);
  headers.set('Content-Type', 'application/json');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

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
