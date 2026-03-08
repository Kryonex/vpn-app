import { createContext, useContext, useEffect, useMemo, useState } from 'react';

import { apiRequest, toJsonBody } from '../api/client';
import { initTelegramSDK, type TGUser, waitForTelegramWebApp } from '../telegram';
import type { MeResponse, SystemStatus } from '../types/models';

type AuthState = {
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  telegramProfile: TGUser | null;
  me: MeResponse | null;
  systemStatus: SystemStatus | null;
  error: string | null;
  refreshMe: () => Promise<void>;
  refreshSystemStatus: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isLoading, setIsLoading] = useState(true);
  const [me, setMe] = useState<MeResponse | null>(null);
  const [telegramProfile, setTelegramProfile] = useState<TGUser | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshMe = async () => {
    const data = await apiRequest<MeResponse>('/me');
    setMe(data);
  };

  const refreshSystemStatus = async () => {
    const data = await apiRequest<SystemStatus>('/system/status');
    setSystemStatus(data);
  };

  useEffect(() => {
    const bootstrap = async () => {
      try {
        setIsLoading(true);
        initTelegramSDK();
        const webApp = await waitForTelegramWebApp();
        console.info('[auth] telegram bootstrap', {
          hasTelegram: Boolean(window.Telegram),
          hasWebApp: Boolean(window.Telegram?.WebApp),
          hasInitData: Boolean(webApp?.initData),
        });
        setTelegramProfile(webApp?.initDataUnsafe?.user ?? null);

        let token = localStorage.getItem('session_token');
        if (!token) {
          // Важно: отправляем raw Telegram.WebApp.initData как есть.
          // Не реконструируем строку из initDataUnsafe.
          const rawInitData = window.Telegram?.WebApp?.initData || webApp?.initData || '';
          const initData = rawInitData || import.meta.env.VITE_DEV_INIT_DATA || '';
          console.info('[auth] initData source', {
            fromTelegram: Boolean(rawInitData),
            fromDevFallback: Boolean(!rawInitData && import.meta.env.VITE_DEV_INIT_DATA),
          });

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

        await Promise.all([refreshMe(), refreshSystemStatus()]);
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
      isAdmin:
        Boolean(me?.telegram?.telegram_user_id) &&
        Number(import.meta.env.VITE_TELEGRAM_ADMIN_ID || 0) > 0 &&
        me?.telegram?.telegram_user_id === Number(import.meta.env.VITE_TELEGRAM_ADMIN_ID || 0),
      telegramProfile,
      me,
      systemStatus,
      error,
      refreshMe,
      refreshSystemStatus,
    }),
    [isLoading, me, systemStatus, error, telegramProfile],
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
