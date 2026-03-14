import { Copy, KeyRound, RefreshCw, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { apiRequest } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState, SkeletonCards } from '../components/StateCards';
import { StatusBadge } from '../components/StatusBadge';
import { SystemStatusBanner } from '../components/SystemStatusBanner';
import { useAuth } from '../context/AuthContext';
import type { VPNKey } from '../types/models';

export function KeysPage() {
  const { systemStatus } = useAuth();
  const [keys, setKeys] = useState<VPNKey[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<VPNKey[]>('/keys')
      .then(setKeys)
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось загрузить ключи'))
      .finally(() => setLoading(false));
  }, []);

  const copyUri = async (key: VPNKey) => {
    const uri = key.active_version?.connection_uri;
    if (!uri) {
      return;
    }
    await navigator.clipboard.writeText(uri);
    setMessage(`Ссылка для ключа «${key.display_name}» скопирована.`);
  };

  const removeKey = async (keyId: string) => {
    if (!window.confirm('Удалить этот ключ из истории?')) {
      return;
    }

    try {
      await apiRequest(`/keys/${keyId}`, { method: 'DELETE' });
      setKeys((prev) => prev.filter((item) => item.id !== keyId));
      setMessage('Ключ удалён из истории.');
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось удалить ключ');
    }
  };

  return (
    <section className="stack">
      <PageHeader title="Ключи" subtitle="Все активные и архивные подключения с быстрыми действиями" />
      <SystemStatusBanner status={systemStatus} compact />

      {loading && <SkeletonCards count={3} />}
      {error && <ErrorState text={error} />}
      {!loading && !error && keys.length === 0 && (
        <EmptyState title="Пока нет ключей" text="Создайте первую заявку в разделе «Купить», и здесь появится ваше подключение." />
      )}

      {!loading &&
        !error &&
        keys.map((key) => (
          <article key={key.id} className="glass-card key-card">
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
                  ? 'Этот ключ уже отключён. Его можно удалить из истории или создать новое подключение.'
                  : 'Ссылка подключения появится здесь, как только ключ будет окончательно подготовлен.'}
              </p>
            )}

            <div className="action-row">
              <Link className="btn btn-primary" to={`/keys/${key.id}`}>
                <KeyRound size={16} /> Открыть
              </Link>
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

      {message && <div className="toast-success">{message}</div>}
    </section>
  );
}
