import { Copy, ExternalLink, ShieldCheck } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { apiRequest } from '../api/client';

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
  const [publicAccess, setPublicAccess] = useState<PublicTelegramAccess | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProxy, setSelectedProxy] = useState<PublicTelegramAccess['proxies'][number] | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    apiRequest<PublicTelegramAccess>('/system/public-telegram-access')
      .then(setPublicAccess)
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось подготовить страницу доступа.'))
      .finally(() => setLoading(false));
  }, []);

  const availableProxies = useMemo(
    () => (publicAccess?.proxies ?? []).filter((item) => item.enabled && item.proxy_url),
    [publicAccess],
  );

  const revealProxy = () => {
    setCopied(false);
    setError(null);
    if (availableProxies.length === 0) {
      setSelectedProxy(null);
      setError('Ссылка пока не настроена. Добавьте активный маршрут в админке.');
      return;
    }
    const proxy = availableProxies[Math.floor(Math.random() * availableProxies.length)] ?? null;
    setSelectedProxy(proxy);
  };

  const copyProxy = async () => {
    if (!selectedProxy?.proxy_url) {
      return;
    }
    await navigator.clipboard.writeText(selectedProxy.proxy_url);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  return (
    <section className="browser-cover browser-cover-compact">
      <div className="browser-cover-logo">ZERO</div>
      <div className="browser-cover-mark" aria-hidden="true" />
      <div className="browser-cover-copy">
        <h1>ZERO</h1>
        <p>Эта страница работает как витрина. Для полноценной работы откройте бота и используйте служебную ссылку ниже, если нужен обходной маршрут.</p>
      </div>

      <div className="browser-auth-card browser-stub-card">
        <p className="title-line">Получить ссылку для входа</p>
        <p className="muted">Кнопка ниже покажет одну из активных служебных ссылок, которые уже указаны в панели администратора.</p>
        <button className="btn btn-primary browser-auth-submit" onClick={revealProxy} disabled={loading}>
          {loading ? 'Подготавливаем...' : 'Показать ссылку'}
        </button>

        {selectedProxy?.proxy_url && (
          <div className="proxy-reveal-card">
            <div className="row-between compact-row">
              <div>
                <p className="title-line">{selectedProxy.country}</p>
                <p className="muted">Скопируйте ссылку и откройте её в Telegram.</p>
              </div>
              <button className="icon-button" onClick={() => void copyProxy()} title="Скопировать ссылку">
                <Copy size={16} />
              </button>
            </div>
            <p className="mono-block proxy-link-block">{selectedProxy.proxy_url}</p>
            {copied && <p className="muted">Ссылка скопирована.</p>}
          </div>
        )}

        {error && <p className="browser-auth-error">{error}</p>}
      </div>

      <div className="browser-cover-actions">
        {publicAccess?.bot_url && (
          <a className="btn btn-ghost browser-cover-btn" href={publicAccess.bot_url} target="_blank" rel="noreferrer">
            <ExternalLink size={16} /> Открыть бота
          </a>
        )}
        <div className="browser-cover-note">
          <ShieldCheck size={16} />
          <span>Основной путь работы с ZERO остаётся через бота. Сайт здесь только помогает быстро получить служебную ссылку и перейти дальше.</span>
        </div>
      </div>
    </section>
  );
}
