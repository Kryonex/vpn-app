import { ExternalLink, ShieldCheck } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { apiRequest } from '../api/client';
import { openProxyThenBot } from '../telegram';

type PublicAuthConfig = {
  bot_username: string | null;
  mini_app_url: string | null;
};

type PublicTelegramAccess = {
  enabled: boolean;
  bot_url: string | null;
  proxies: Array<{
    id: string;
    country: string;
    proxy_url: string | null;
    button_text: string;
    enabled: boolean;
  }>;
};

export function ExternalBrowserAuth() {
  const [config, setConfig] = useState<PublicAuthConfig | null>(null);
  const [publicAccess, setPublicAccess] = useState<PublicTelegramAccess | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      apiRequest<PublicAuthConfig>('/auth/public-config'),
      apiRequest<PublicTelegramAccess>('/system/public-telegram-access'),
    ])
      .then(([authConfig, accessConfig]) => {
        setConfig(authConfig);
        setPublicAccess(accessConfig);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось подготовить страницу доступа.'))
      .finally(() => setLoading(false));
  }, []);

  const availableProxies = useMemo(
    () => (publicAccess?.proxies ?? []).filter((item) => item.enabled && item.proxy_url),
    [publicAccess],
  );

  const handleConnect = () => {
    if (!publicAccess?.bot_url || availableProxies.length === 0) {
      setError('Резервный доступ пока не настроен. Откройте бота напрямую или обратитесь к администратору.');
      return;
    }

    const proxy = availableProxies[Math.floor(Math.random() * availableProxies.length)];
    if (!proxy?.proxy_url) {
      setError('Не удалось выбрать служебный маршрут. Попробуйте ещё раз.');
      return;
    }

    setBusy(true);
    setError(null);
    openProxyThenBot(proxy.proxy_url, publicAccess.bot_url);
    window.setTimeout(() => setBusy(false), 1600);
  };

  return (
    <section className="browser-cover browser-cover-compact">
      <div className="browser-cover-logo">ZERO</div>
      <div className="browser-cover-mark" aria-hidden="true" />
      <div className="browser-cover-copy">
        <h1>ZERO</h1>
        <p>Сайт работает как витрина. Для доступа к личному кабинету и материалам откройте бота через служебный маршрут.</p>
      </div>

      <div className="browser-auth-card browser-stub-card">
        <p className="title-line">Получить доступ через бота</p>
        <p className="muted">
          Кнопка ниже сначала попробует открыть один из настроенных маршрутов доступа, а затем переведёт вас прямо в бота ZERO.
        </p>
        <button className="btn btn-primary browser-auth-submit" onClick={handleConnect} disabled={loading || busy || availableProxies.length === 0 || !publicAccess?.bot_url}>
          {busy ? 'Подключаем маршрут и открываем бота...' : 'Получить доступ через бота'}
        </button>
        {availableProxies.length > 0 && (
          <p className="muted">
            Доступно маршрутов: {availableProxies.length}. Для перехода будет выбран любой активный вариант из панели.
          </p>
        )}
        {error && <p className="browser-auth-error">{error}</p>}
      </div>

      <div className="browser-cover-actions">
        {publicAccess?.bot_url && (
          <a className="btn btn-ghost browser-cover-btn" href={publicAccess.bot_url} target="_blank" rel="noreferrer">
            <ExternalLink size={16} /> Открыть бота напрямую
          </a>
        )}
        {config?.mini_app_url && (
          <a className="btn btn-ghost browser-cover-btn" href={config.mini_app_url} target="_blank" rel="noreferrer">
            <ExternalLink size={16} /> Открыть сайт вручную
          </a>
        )}
        <div className="browser-cover-note">
          <ShieldCheck size={16} />
          <span>Основной сценарий для работы с ZERO остаётся через бота. Если Telegram открывается нестабильно, используйте кнопку подключения выше.</span>
        </div>
      </div>
    </section>
  );
}
