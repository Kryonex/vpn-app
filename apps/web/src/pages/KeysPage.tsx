import { KeyRound, RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { apiRequest } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/StateCards';
import { StatusBadge } from '../components/StatusBadge';
import type { VPNKey } from '../types/models';

export function KeysPage() {
  const [keys, setKeys] = useState<VPNKey[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiRequest<VPNKey[]>('/keys')
      .then(setKeys)
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось загрузить ключи'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="stack">
      <PageHeader title="Мои ключи" subtitle="Статус, срок действия и действия по каждому ключу" />

      {loading && <LoadingState text="Загружаем ключи..." />}
      {error && <ErrorState text={error} />}
      {!loading && !error && keys.length === 0 && (
        <EmptyState title="Ключей пока нет" text="Купите первый тариф, чтобы создать VPN-ключ." />
      )}

      {!loading && !error && keys.map((key) => (
        <article key={key.id} className="glass-card key-card">
          <div className="row-between">
            <p className="title-line">{key.display_name}</p>
            <StatusBadge status={key.status} />
          </div>
          <p className="muted">
            Срок действия: {key.current_subscription
              ? new Date(key.current_subscription.expires_at).toLocaleDateString()
              : 'нет данных'}
          </p>
          <div className="action-row">
            <Link className="btn btn-primary" to={`/keys/${key.id}`}>
              <KeyRound size={16} /> Подробнее
            </Link>
            <Link className="btn btn-ghost" to={`/keys/${key.id}/renew`}>
              <RefreshCw size={16} /> Продлить
            </Link>
          </div>
        </article>
      ))}
    </section>
  );
}
