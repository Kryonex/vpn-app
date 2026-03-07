import { createContext, useContext, useEffect, useMemo, useState } from 'react';

import { apiRequest, toJsonBody } from '../api/client';
import { initTelegramSDK } from '../telegram';
import type { MeResponse } from '../types/models';

type AuthState = {
  isLoading: boolean;
  isAuthenticated: boolean;
  me: MeResponse | null;
  error: string | null;
  refreshMe: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isLoading, setIsLoading] = useState(true);
  const [me, setMe] = useState<MeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshMe = async () => {
    const data = await apiRequest<MeResponse>('/me');
    setMe(data);
  };

  useEffect(() => {
    const bootstrap = async () => {
      try {
        setIsLoading(true);
        const webApp = initTelegramSDK();

        let token = localStorage.getItem('session_token');
        if (!token) {
          // Важно: отправляем raw Telegram.WebApp.initData как есть.
          // Не реконструируем строку из initDataUnsafe.
          const rawInitData = webApp?.initData;
          const initData = rawInitData || import.meta.env.VITE_DEV_INIT_DATA || '';

          if (!initData) {
            throw new Error('Отсутствует Telegram initData. Откройте приложение через Telegram или задайте VITE_DEV_INIT_DATA.');
          }

          const auth = await apiRequest<{ access_token: string }>(
            '/auth/telegram',
            toJsonBody({ init_data: initData }),
          );
          token = auth.access_token;
          localStorage.setItem('session_token', token);
        }

        await refreshMe();
        setError(null);
      } catch (err) {
        localStorage.removeItem('session_token');
        const message = err instanceof Error ? err.message : 'Ошибка авторизации';
        setError(message);
      } finally {
        setIsLoading(false);
      }
    };

    void bootstrap();
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      isLoading,
      isAuthenticated: Boolean(me),
      me,
      error,
      refreshMe,
    }),
    [isLoading, me, error],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return value;
}
