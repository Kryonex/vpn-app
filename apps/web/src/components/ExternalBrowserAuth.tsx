import { ExternalLink, ShieldCheck } from 'lucide-react';
import type { FormEvent } from 'react';
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
  const [webBusy, setWebBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loginId, setLoginId] = useState('');
  const [password, setPassword] = useState('');

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

  const handleWebLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      setWebBusy(true);
      setError(null);
      const response = await apiRequest<{ access_token: string }>('/auth/web-login', {
        method: 'POST',
        body: JSON.stringify({
          login_id: loginId,
          password,
        }),
      });
      console.info('[auth] web access token received', {
        received: Boolean(response.access_token),
      });
      setAccessToken(response.access_token);
      window.location.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось выполнить вход на сайте.');
    } finally {
      setWebBusy(false);
    }
  };

  return (
    <section className="browser-cover">
      <div className="browser-cover-logo">ZERO</div>
      <div className="browser-cover-mark" aria-hidden="true" />
      <div className="browser-cover-copy">
        <h1>ZERO</h1>
        <p>Войдите на сайте с тем же профилем, который уже используется в боте. История, сроки и заявки останутся общими.</p>
      </div>

      <div className="browser-auth-card">
        <p className="title-line">Вход на сайте</p>
        <p className="muted">Используйте ID входа и пароль, которые уже привязаны к вашему профилю ZERO.</p>
        <form className="browser-auth-form" onSubmit={handleWebLogin}>
          <label className="field-label">
            <span>ID входа</span>
            <input
              className="input"
              value={loginId}
              onChange={(event) => setLoginId(event.target.value.toUpperCase())}
              placeholder="Например, ZEROA1B2C3"
              autoCapitalize="characters"
              autoCorrect="off"
            />
          </label>
          <label className="field-label">
            <span>Пароль</span>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Введите пароль для сайта"
            />
          </label>
          <button className="btn btn-primary browser-auth-submit" type="submit" disabled={webBusy || !loginId || !password}>
            {webBusy ? 'Открываем кабинет...' : 'Войти на сайт'}
          </button>
        </form>
        <p className="muted">
          ID входа и временный пароль можно взять в сообщении бота `/start`, а затем сменить пароль уже внутри кабинета.
        </p>
      </div>

      <div className="browser-auth-card">
        <p className="title-line">Вход через Telegram</p>
        <p className="muted">Этот способ оставлен как запасной. Если виджет работает нестабильно, используйте вход по ID выше.</p>
        {loading && <p className="muted">Подготавливаем веб-вход...</p>}
        {!loading && (
          <div className="browser-auth-widget" ref={widgetHostRef}>
            {!config?.enabled && (
              <p className="muted">Веб-вход через Telegram пока недоступен. Проверьте настройку BOT_USERNAME на сервере.</p>
            )}
          </div>
        )}
        {busy && <p className="muted">Проверяем аккаунт и открываем кабинет...</p>}
      </div>
      {error && <p className="browser-auth-error">{error}</p>}

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
