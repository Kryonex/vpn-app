import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';

import { apiRequest, clearAccessToken, getAccessToken, setAccessToken, toJsonBody } from '../api/client';
import { initTelegramSDK, type TGUser, waitForTelegramWebApp } from '../telegram';
import type { MeResponse, SystemStatus } from '../types/models';

type AuthState = {
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isExternalBrowser: boolean;
  telegramProfile: TGUser | null;
  me: MeResponse | null;
  systemStatus: SystemStatus | null;
  error: string | null;
  refreshMe: () => Promise<void>;
  refreshSystemStatus: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const bootstrapStartedRef = useRef(false);
  const [isLoading, setIsLoading] = useState(true);
  const [me, setMe] = useState<MeResponse | null>(null);
  const [telegramProfile, setTelegramProfile] = useState<TGUser | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isExternalBrowser, setIsExternalBrowser] = useState(false);
  const configuredAdminId = Number(import.meta.env.VITE_TELEGRAM_ADMIN_ID || 0) || 0;

  const refreshMe = async () => {
    const data = await apiRequest<MeResponse>('/me');
    setMe(data);
  };

  const refreshSystemStatus = async () => {
    const data = await apiRequest<SystemStatus>('/system/status');
    setSystemStatus(data);
  };

  const refreshSystemStatusSafe = async () => {
    try {
      await refreshSystemStatus();
    } catch (err) {
      console.info('[auth] system status skipped', {
        reason: err instanceof Error ? err.message : 'unknown_error',
      });
      setSystemStatus(null);
    }
  };

  useEffect(() => {
    if (bootstrapStartedRef.current) {
      console.info('[auth] bootstrap skipped', {
        reason: 'already_started',
      });
      return;
    }
    bootstrapStartedRef.current = true;

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

        let token = getAccessToken();
        if (!token) {
          const rawInitData = window.Telegram?.WebApp?.initData || webApp?.initData || '';
          const initData = rawInitData || import.meta.env.VITE_DEV_INIT_DATA || '';
          console.info('[auth] initData source', {
            fromTelegram: Boolean(rawInitData),
            fromDevFallback: Boolean(!rawInitData && import.meta.env.VITE_DEV_INIT_DATA),
          });

          if (!initData) {
            setIsExternalBrowser(true);
            throw new Error('Отсутствует Telegram initData. Откройте приложение через Telegram.');
          }

          const auth = await apiRequest<{ access_token: string }>(
            '/auth/telegram',
            toJsonBody({ init_data: initData }),
          );
          console.info('[auth] access token received', {
            received: Boolean(auth.access_token),
          });
          token = auth.access_token;
          setAccessToken(token);
        } else {
          console.info('[auth] access token already available', {
            available: Boolean(token),
          });
        }

        await refreshMe();
        await refreshSystemStatusSafe();
        setIsExternalBrowser(false);
        setError(null);
      } catch (err) {
        clearAccessToken();
        const message = err instanceof Error ? err.message : 'Ошибка авторизации';
        setError(message);
      } finally {
        setIsLoading(false);
      }
    };

    void bootstrap();
  }, []);

  const isAdmin =
    Boolean(me?.telegram?.telegram_user_id) &&
    configuredAdminId > 0 &&
    me?.telegram?.telegram_user_id === configuredAdminId;

  useEffect(() => {
    console.info('[auth] admin eligibility resolved', {
      hasMe: Boolean(me),
      hasTelegramUser: Boolean(me?.telegram?.telegram_user_id),
      configuredAdminId: configuredAdminId > 0,
      isAdmin,
    });
  }, [configuredAdminId, isAdmin, me]);

  const value = useMemo<AuthState>(
    () => ({
      isLoading,
      isAuthenticated: Boolean(me),
      isAdmin,
      isExternalBrowser,
      telegramProfile,
      me,
      systemStatus,
      error,
      refreshMe,
      refreshSystemStatus,
    }),
    [error, isAdmin, isExternalBrowser, isLoading, me, systemStatus, telegramProfile],
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
