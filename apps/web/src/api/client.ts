const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function getApiBase() {
  return API_BASE;
}

export async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('session_token');

  const headers = new Headers(options?.headers);
  headers.set('Content-Type', 'application/json');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = typeof payload?.detail === 'string' ? payload.detail : 'Request failed';
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
