import { Copy, QrCode, RefreshCw, Trash2 } from 'lucide-react';
import { QRCodeCanvas } from 'qrcode.react';
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { apiRequest, toJsonBody } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/StateCards';
import { StatusBadge } from '../components/StatusBadge';
import { SystemStatusBanner } from '../components/SystemStatusBanner';
import { useAuth } from '../context/AuthContext';
import type { VPNKey } from '../types/models';

export function KeyDetailsPage() {
  const { keyId } = useParams<{ keyId: string }>();
  const navigate = useNavigate();
  const { systemStatus } = useAuth();
  const [keyData, setKeyData] = useState<VPNKey | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [rotating, setRotating] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!keyId) {
      return;
    }
    setLoading(true);
    apiRequest<VPNKey>(`/keys/${keyId}`)
      .then(setKeyData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось загрузить ключ'))
      .finally(() => setLoading(false));
  }, [keyId]);

  const copyUri = async () => {
    const uri = keyData?.active_version?.connection_uri;
    if (!uri) {
      return;
    }
    await navigator.clipboard.writeText(uri);
    setMessage('URL подключения скопирован в буфер обмена.');
  };

  const rotate = async () => {
    if (!keyId) {
      return;
    }
    try {
      setRotating(true);
      await apiRequest(`/keys/${keyId}/rotate`, toJsonBody({}));
      setMessage('Ключ успешно перевыпущен.');
      const fresh = await apiRequest<VPNKey>(`/keys/${keyId}`);
      setKeyData(fresh);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось перевыпустить ключ');
    } finally {
      setRotating(false);
    }
  };

  const removeKey = async () => {
    if (!keyId || !window.confirm('Удалить этот нерабочий ключ из истории?')) {
      return;
    }
    try {
      setDeleting(true);
      await apiRequest(`/keys/${keyId}`, { method: 'DELETE' });
      navigate('/keys');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось удалить ключ');
    } finally {
      setDeleting(false);
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
  const deletionAllowed = keyData.status !== 'active' || !keyData.active_version;

  return (
    <section className="stack">
      <PageHeader title={keyData.display_name} subtitle="Детали ключа и действия по подписке" />
      <SystemStatusBanner status={systemStatus} compact />

      <article className="glass-card">
        <div className="row-between">
          <div>
            <p className="title-line">Текущее состояние</p>
            <p className="muted">
              {keyData.current_subscription
                ? `Подписка до ${new Date(keyData.current_subscription.expires_at).toLocaleString()}`
                : 'Подписка не найдена'}
            </p>
          </div>
          <StatusBadge status={keyData.status} />
        </div>
        <p className="muted">Версия ключа: {keyData.active_version?.version ?? 'нет активной версии'}</p>
      </article>

      {uri ? (
        <article className="glass-card">
          <p className="muted">URL подключения</p>
          <p className="mono-block">{uri}</p>
          <div className="action-row">
            <button className="btn btn-primary" onClick={copyUri}>
              <Copy size={16} /> Скопировать URL
            </button>
            <button
              className="btn btn-ghost"
              onClick={rotate}
              disabled={rotating || Boolean(systemStatus?.maintenance_mode)}
            >
              <RefreshCw size={16} className={rotating ? 'spin' : ''} /> Перевыпустить
            </button>
            <Link className="btn btn-ghost" to={`/keys/${keyData.id}/renew`}>
              <RefreshCw size={16} /> Продлить
            </Link>
          </div>
          <div className="qr-wrap">
            <div className="qr-card">
              <div className="qr-title">
                <QrCode size={16} /> QR-код
              </div>
              <QRCodeCanvas value={uri} size={180} bgColor="#0B1020" fgColor="#F8FAFC" />
            </div>
          </div>
        </article>
      ) : (
        <EmptyState
          title="URL подключения недоступен"
          text={
            keyData.status === 'revoked'
              ? 'Клиент удалён в панели или отозван. Вы можете перевыпустить ключ или удалить запись из истории.'
              : 'Продлите или перевыпустите ключ, чтобы получить новый URL подключения.'
          }
        />
      )}

      {deletionAllowed && (
        <button className="btn btn-danger-soft" onClick={removeKey} disabled={deleting}>
          <Trash2 size={16} /> Удалить ключ из истории
        </button>
      )}

      {error && <ErrorState text={error} />}
      {message && <div className="toast-success">{message}</div>}
    </section>
  );
}
