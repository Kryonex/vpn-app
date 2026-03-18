import { ExternalLink, ShieldCheck } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { apiRequest, setAccessToken } from '../api/client';

type PublicAuthConfig = {
  enabled: boolean;
  bot_username: string | null;
  mini_app_url: string | null;
};

type TelegramWebsiteAuthPayload = {
  id: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  auth_date: number;
  hash: string;
};

declare global {
  interface Window {
    onTelegramWebsiteAuth?: (user: TelegramWebsiteAuthPayload) => void;
  }
}

export function ExternalBrowserAuth() {
  const widgetHostRef = useRef<HTMLDivElement | null>(null);
  const [config, setConfig] = useState<PublicAuthConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<PublicAuthConfig>('/auth/public-config')
      .then(setConfig)
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось подготовить веб-вход.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!config?.enabled || !config.bot_username || !widgetHostRef.current) {
      return;
    }

    const host = widgetHostRef.current;
    host.innerHTML = '';

    window.onTelegramWebsiteAuth = async (user: TelegramWebsiteAuthPayload) => {
      try {
        setBusy(true);
        setError(null);
        const response = await apiRequest<{ access_token: string }>('/auth/telegram-website', {
          method: 'POST',
          body: JSON.stringify(user),
        });
        console.info('[auth] website access token received', {
          received: Boolean(response.access_token),
        });
        setAccessToken(response.access_token);
        window.location.reload();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Не удалось выполнить вход через Telegram.');
      } finally {
        setBusy(false);
      }
    };

    const script = document.createElement('script');
    script.async = true;
    script.src = 'https://telegram.org/js/telegram-widget.js?22';
    script.setAttribute('data-telegram-login', config.bot_username);
    script.setAttribute('data-size', 'large');
    script.setAttribute('data-radius', '16');
    script.setAttribute('data-request-access', 'write');
    script.setAttribute('data-userpic', 'false');
    script.setAttribute('data-onauth', 'onTelegramWebsiteAuth(user)');
    host.appendChild(script);

    return () => {
      host.innerHTML = '';
      delete window.onTelegramWebsiteAuth;
    };
  }, [config]);

  return (
    <section className="browser-cover">
      <div className="browser-cover-logo">ZERO</div>
      <div className="browser-cover-mark" aria-hidden="true" />
      <div className="browser-cover-copy">
        <h1>ZERO</h1>
        <p>Откройте личный кабинет через Telegram и продолжайте работу с тем же профилем, заявками и сроками действия на сайте.</p>
      </div>

      <div className="browser-auth-card">
        <p className="title-line">Вход через Telegram</p>
        <p className="muted">Используйте тот же аккаунт Telegram, который уже связан с вашим профилем в боте.</p>
        {loading && <p className="muted">Подготавливаем веб-вход...</p>}
        {!loading && (
          <div className="browser-auth-widget" ref={widgetHostRef}>
            {!config?.enabled && (
              <p className="muted">Веб-вход пока недоступен. Проверьте настройку BOT_USERNAME на сервере.</p>
            )}
          </div>
        )}
        {busy && <p className="muted">Проверяем аккаунт и открываем кабинет...</p>}
        {error && <p className="browser-auth-error">{error}</p>}
      </div>

      <div className="browser-cover-actions">
        {config?.mini_app_url && (
          <a className="btn btn-ghost browser-cover-btn" href={config.mini_app_url} target="_blank" rel="noreferrer">
            <ExternalLink size={16} /> Открыть в Telegram
          </a>
        )}
        <div className="browser-cover-note">
          <ShieldCheck size={16} />
          <span>Сайт и бот используют один и тот же аккаунт, поэтому ваши данные синхронизируются автоматически.</span>
        </div>
      </div>
    </section>
  );
}
