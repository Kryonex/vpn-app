import { Copy, QrCode, RefreshCw } from 'lucide-react';
import { QRCodeCanvas } from 'qrcode.react';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { apiRequest, toJsonBody } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/StateCards';
import { StatusBadge } from '../components/StatusBadge';
import type { VPNKey } from '../types/models';

export function KeyDetailsPage() {
  const { keyId } = useParams<{ keyId: string }>();
  const [keyData, setKeyData] = useState<VPNKey | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [rotating, setRotating] = useState(false);

  useEffect(() => {
    if (!keyId) return;
    setLoading(true);
    apiRequest<VPNKey>(`/keys/${keyId}`)
      .then(setKeyData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось загрузить ключ'))
      .finally(() => setLoading(false));
  }, [keyId]);

  const copyUri = async () => {
    const uri = keyData?.active_version?.connection_uri;
    if (!uri) return;
    await navigator.clipboard.writeText(uri);
    setMessage('Ключ скопирован в буфер обмена');
  };

  const rotate = async () => {
    if (!keyId) return;
    try {
      setRotating(true);
      await apiRequest(`/keys/${keyId}/rotate`, toJsonBody({}));
      setMessage('Ключ успешно перевыпущен');
      const fresh = await apiRequest<VPNKey>(`/keys/${keyId}`);
      setKeyData(fresh);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось перевыпустить ключ');
    } finally {
      setRotating(false);
    }
  };

  if (loading) {
    return <LoadingState text="Загружаем данные ключа..." />;
  }

  if (error && !keyData) {
    return <ErrorState text={error} />;
  }

  if (!keyData) {
    return <EmptyState title="Ключ не найден" text="Откройте карточку ключа заново из списка." />;
  }

  const uri = keyData.active_version?.connection_uri;

  return (
    <section className="stack">
      <PageHeader title={keyData.display_name} subtitle="Детали ключа и управление" />

      <article className="glass-card">
        <div className="row-between">
          <p className="title-line">Статус</p>
          <StatusBadge status={keyData.status} />
        </div>
        <p className="muted">
          Срок действия: {keyData.current_subscription
            ? new Date(keyData.current_subscription.expires_at).toLocaleString()
            : 'нет данных'}
        </p>
        <p className="muted">Версия: {keyData.active_version?.version ?? '-'}</p>
      </article>

      {uri ? (
        <article className="glass-card">
          <p className="muted">URI для подключения</p>
          <p className="mono-block">{uri}</p>
          <div className="action-row">
            <button className="btn btn-primary" onClick={copyUri}>
              <Copy size={16} /> Скопировать ключ
            </button>
            <button className="btn btn-ghost" onClick={rotate} disabled={rotating}>
              <RefreshCw size={16} className={rotating ? 'spin' : ''} /> Перевыпустить
            </button>
            <Link className="btn btn-ghost" to={`/keys/${keyData.id}/renew`}>
              <RefreshCw size={16} /> Продлить
            </Link>
          </div>
          <div className="qr-wrap">
            <div className="qr-card">
              <div className="qr-title"><QrCode size={16} /> QR-код</div>
              <QRCodeCanvas value={uri} size={180} bgColor="#0f1420" fgColor="#dbe7ff" />
            </div>
          </div>
        </article>
      ) : (
        <EmptyState
          title="Нет активного URI"
          text={
            keyData.status === 'revoked'
              ? 'Клиент удален в панели или отозван. Выполните перевыпуск ключа.'
              : 'Продлите или перевыпустите ключ, чтобы получить новый конфиг.'
          }
        />
      )}

      {error && <ErrorState text={error} />}
      {message && <div className="toast-success">{message}</div>}
    </section>
  );
}
