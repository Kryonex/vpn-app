import { Copy, ExternalLink, QrCode, RefreshCw, Trash2 } from 'lucide-react';
import { QRCodeCanvas } from 'qrcode.react';
import { useEffect, useMemo, useState } from 'react';
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
    setMessage('Ссылка подключения скопирована.');
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
    if (!keyId || !window.confirm('Удалить этот ключ из истории?')) {
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
    return <EmptyState title="Ключ не найден" text="Возможно, он уже удалён или ещё не успел загрузиться." />;
  }

  const uri = keyData.active_version?.connection_uri;
  const deletionAllowed = keyData.status !== 'active' || !keyData.active_version;
  const happHref = uri || null;
  const connectionGuide = useMemo(() => ([
    'Нажмите «Добавить в Happ», если приложение установлено и поддерживает открытие ссылок подключения.',
    'Если кнопка не сработает, скопируйте ссылку ниже и вставьте её вручную в Happ или другое совместимое приложение.',
    'Для быстрого импорта также можно отсканировать QR-код прямо с экрана.',
  ]), []);

  return (
    <section className="stack">
      <PageHeader title={keyData.display_name} subtitle="Подключение, срок действия и быстрые действия" />
      <SystemStatusBanner status={systemStatus} compact />

      <article className="glass-card">
        <div className="row-between">
          <div>
            <p className="title-line">Текущий статус</p>
            <p className="muted">
              {keyData.current_subscription
                ? `Действует до ${new Date(keyData.current_subscription.expires_at).toLocaleString()}`
                : 'Подписка не найдена'}
            </p>
          </div>
          <StatusBadge status={keyData.status} />
        </div>
        <p className="muted">Версия ключа: {keyData.active_version?.version ?? 'нет активной версии'}</p>
      </article>

      {uri ? (
        <>
          <article className="glass-card">
            <p className="muted">Ссылка подключения</p>
            <p className="mono-block">{uri}</p>
            <div className="action-row">
              {happHref && (
                <a className="btn btn-primary" href={happHref}>
                  <ExternalLink size={16} /> Добавить в Happ
                </a>
              )}
              <button className="btn btn-ghost" onClick={copyUri}>
                <Copy size={16} /> Скопировать
              </button>
              <button className="btn btn-ghost" onClick={rotate} disabled={rotating || Boolean(systemStatus?.maintenance_mode)}>
                <RefreshCw size={16} className={rotating ? 'spin' : ''} /> Перевыпустить
              </button>
              <Link className="btn btn-ghost" to={`/keys/${keyData.id}/renew`}>
                <RefreshCw size={16} /> Продлить
              </Link>
            </div>
          </article>

          <article className="glass-card">
            <p className="title-line">Как добавить ключ</p>
            <div className="stack compact-stack">
              {connectionGuide.map((item, index) => (
                <div key={item} className="hint-row">
                  <span className="step-badge">{index + 1}</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
            <div className="qr-wrap">
              <div className="qr-card">
                <div className="qr-title">
                  <QrCode size={16} /> QR-код
                </div>
                <QRCodeCanvas value={uri} size={180} bgColor="#050505" fgColor="#FAFAFA" />
              </div>
            </div>
          </article>
        </>
      ) : (
        <EmptyState
          title="Ссылка подключения пока недоступна"
          text={
            keyData.status === 'revoked'
              ? 'Этот ключ уже отключён. Вы можете удалить его из истории или создать новый доступ.'
              : 'Ключ ещё подготавливается. Обновите страницу немного позже.'
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
