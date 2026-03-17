import { Copy, KeyRound, RefreshCw, Trash2, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { apiRequest } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState, SkeletonCards } from '../components/StateCards';
import { StatusBadge } from '../components/StatusBadge';
import { SystemStatusBanner } from '../components/SystemStatusBanner';
import { useAuth } from '../context/AuthContext';
import { openTelegramProxy } from '../telegram';
import type { TelegramProxyAccess, VPNKey } from '../types/models';

export function KeysPage() {
  const { systemStatus } = useAuth();
  const [keys, setKeys] = useState<VPNKey[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [proxyAccess, setProxyAccess] = useState<TelegramProxyAccess | null>(null);
  const [proxyChooserOpen, setProxyChooserOpen] = useState(false);

  useEffect(() => {
    apiRequest<VPNKey[]>('/keys')
      .then(setKeys)
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось загрузить профили'))
      .finally(() => setLoading(false));
    apiRequest<TelegramProxyAccess>('/system/telegram-proxy').then(setProxyAccess).catch(() => null);
  }, []);

  const copyUri = async (key: VPNKey) => {
    const uri = key.active_version?.connection_uri;
    if (!uri) return;
    await navigator.clipboard.writeText(uri);
    setMessage(`Служебная ссылка «${key.display_name}» скопирована.`);
  };

  const removeKey = async (keyId: string) => {
    if (!window.confirm('Удалить этот профиль из истории?')) return;

    try {
      await apiRequest(`/keys/${keyId}`, { method: 'DELETE' });
      setKeys((prev) => prev.filter((item) => item.id !== keyId));
      setMessage('Профиль удалён из истории.');
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось удалить профиль');
    }
  };

  const openProxy = () => {
    const proxies = proxyAccess?.proxies?.filter((item) => item.enabled && item.proxy_url) ?? [];
    if (!proxies.length) return;
    if (proxies.length === 1) {
      openTelegramProxy(proxies[0].proxy_url!);
      return;
    }
    setProxyChooserOpen(true);
  };

  const regionButtonLabel = (proxyAccess?.proxies?.filter((item) => item.enabled && item.proxy_url).length ?? 0) > 1
    ? 'Выбрать регион'
    : 'Открыть вариант';

  return (
    <section className="stack">
      <PageHeader title="Профили" subtitle="Все активные и архивные профили ZERO с быстрыми действиями" />
      <SystemStatusBanner status={systemStatus} compact />

      {loading && <SkeletonCards count={3} />}
      {error && <ErrorState text={error} />}
      {!loading && !error && keys.length === 0 && (
        <EmptyState title="Пока нет профилей" text="Создайте первую заявку в разделе «Купить», и здесь появится ваш профиль." />
      )}

      {!loading && !error && keys.map((key) => (
        <article key={key.id} className="glass-card key-card liquid-panel">
          <div className="row-between">
            <div>
              <p className="title-line">{key.display_name}</p>
              <p className="muted">
                {key.current_subscription
                  ? `Действует до ${new Date(key.current_subscription.expires_at).toLocaleDateString()}`
                  : 'Срок действия не найден'}
              </p>
            </div>
            <StatusBadge status={key.status} />
          </div>

          {key.active_version?.connection_uri ? (
            <p className="mono-block">{key.active_version.connection_uri}</p>
          ) : (
            <p className="muted">
              {key.status === 'revoked'
                ? 'Этот профиль уже отключён. Его можно удалить из истории или создать новый.'
                : 'Служебная ссылка появится здесь, как только профиль будет окончательно подготовлен.'}
            </p>
          )}

          <div className="action-row">
            <Link className="btn btn-primary" to={`/keys/${key.id}`}>
              <KeyRound size={16} /> Открыть
            </Link>
            {proxyAccess?.enabled && key.status === 'active' && (
              <button className="btn btn-ghost" onClick={openProxy}>
                <KeyRound size={16} /> {regionButtonLabel}
              </button>
            )}
            <button className="btn btn-ghost" onClick={() => void copyUri(key)} disabled={!key.active_version?.connection_uri}>
              <Copy size={16} /> Скопировать
            </button>
            <Link className="btn btn-ghost" to={`/keys/${key.id}/renew`}>
              <RefreshCw size={16} /> Продлить
            </Link>
            {(key.status !== 'active' || !key.active_version) && (
              <button className="btn btn-danger-soft" onClick={() => void removeKey(key.id)}>
                <Trash2 size={16} /> Удалить
              </button>
            )}
          </div>
        </article>
      ))}

      {proxyChooserOpen && proxyAccess && (
        <div className="modal-backdrop" onClick={() => setProxyChooserOpen(false)}>
          <div className="modal-card liquid-modal" onClick={(event) => event.stopPropagation()}>
            <div className="row-between">
              <div>
                <p className="title-line">Выберите регион</p>
                <p className="muted">Выберите подходящий вариант открытия профиля.</p>
              </div>
              <button className="icon-button" onClick={() => setProxyChooserOpen(false)}><X size={16} /></button>
            </div>
            <div className="stack compact-stack">
              {proxyAccess.proxies.filter((item) => item.enabled && item.proxy_url).map((item) => (
                <button
                  key={item.id}
                  className="btn btn-ghost proxy-choice-button"
                  onClick={() => {
                    openTelegramProxy(item.proxy_url!);
                    setProxyChooserOpen(false);
                  }}
                >
                  <KeyRound size={16} /> {item.country}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {message && <div className="toast-success">{message}</div>}
    </section>
  );
}
