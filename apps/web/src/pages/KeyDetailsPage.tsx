import { Copy, ExternalLink, KeyRound, QrCode, RefreshCw, Trash2, X } from 'lucide-react';
import { QRCodeCanvas } from 'qrcode.react';
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { apiRequest, toJsonBody } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/StateCards';
import { StatusBadge } from '../components/StatusBadge';
import { SystemStatusBanner } from '../components/SystemStatusBanner';
import { useAuth } from '../context/AuthContext';
import { openTelegramProxy } from '../telegram';
import type { TelegramProxyAccess, VPNKey } from '../types/models';

const connectionGuide = [
  'Нажмите «Открыть в приложении», если подходящее приложение уже установлено и умеет обрабатывать такие ссылки.',
  'Если кнопка не сработает, скопируйте ссылку ниже и вставьте её вручную в подходящее совместимое приложение.',
  'Для быстрого импорта можно использовать QR-код прямо с этого экрана.',
] as const;

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
  const [proxyAccess, setProxyAccess] = useState<TelegramProxyAccess | null>(null);
  const [proxyChooserOpen, setProxyChooserOpen] = useState(false);

  useEffect(() => {
    if (!keyId) return;
    setLoading(true);
    apiRequest<VPNKey>(`/keys/${keyId}`)
      .then(setKeyData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось загрузить доступ'))
      .finally(() => setLoading(false));
    apiRequest<TelegramProxyAccess>('/system/telegram-proxy').then(setProxyAccess).catch(() => null);
  }, [keyId]);

  const copyUri = async () => {
    const uri = keyData?.active_version?.connection_uri;
    if (!uri) return;
    await navigator.clipboard.writeText(uri);
    setMessage('Служебная ссылка скопирована.');
  };

  const rotate = async () => {
    if (!keyId) return;
    try {
      setRotating(true);
      await apiRequest(`/keys/${keyId}/rotate`, toJsonBody({}));
      setMessage('Конфигурация успешно обновлена.');
      const fresh = await apiRequest<VPNKey>(`/keys/${keyId}`);
      setKeyData(fresh);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось обновить конфигурацию');
    } finally {
      setRotating(false);
    }
  };

  const removeKey = async () => {
    if (!keyId || !window.confirm('Удалить этот доступ из истории?')) return;
    try {
      setDeleting(true);
      await apiRequest(`/keys/${keyId}`, { method: 'DELETE' });
      navigate('/keys');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось удалить доступ');
    } finally {
      setDeleting(false);
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

  if (loading) return <LoadingState text="Загружаем данные доступа..." />;
  if (error && !keyData) return <ErrorState text={error} />;
  if (!keyData) return <EmptyState title="Доступ не найден" text="Возможно, он уже удалён или ещё не успел загрузиться." />;

  const uri = keyData.active_version?.connection_uri;
  const deletionAllowed = keyData.status !== 'active' || !keyData.active_version;
  const happHref = uri || null;
  const regionButtonLabel = (proxyAccess?.proxies?.filter((item) => item.enabled && item.proxy_url).length ?? 0) > 1
    ? 'Выбрать регион'
    : 'Открыть вариант';

  return (
    <section className="stack">
      <PageHeader title={keyData.display_name} subtitle="Профиль, срок действия и быстрые действия" />
      <SystemStatusBanner status={systemStatus} compact />

      <article className="glass-card liquid-panel">
        <div className="row-between">
          <div>
            <p className="title-line">Текущий статус</p>
            <p className="muted">
              {keyData.current_subscription
                ? `Действует до ${new Date(keyData.current_subscription.expires_at).toLocaleString()}`
                : 'Статус доступа не найден'}
            </p>
          </div>
          <StatusBadge status={keyData.status} />
        </div>
        <p className="muted">Версия конфигурации: {keyData.active_version?.version ?? 'нет активной версии'}</p>
      </article>

      {uri ? (
        <>
          <article className="glass-card liquid-panel">
            <p className="muted">Служебная ссылка</p>
            <p className="mono-block">{uri}</p>
            <div className="action-row">
              {happHref && (
                <a className="btn btn-primary" href={happHref}>
                  <ExternalLink size={16} /> Открыть в приложении
                </a>
              )}
              <button className="btn btn-ghost" onClick={copyUri}>
                <Copy size={16} /> Скопировать
              </button>
              {proxyAccess?.enabled && keyData.status === 'active' && (
                <button className="btn btn-ghost" onClick={openProxy}>
                  <KeyRound size={16} /> {regionButtonLabel}
                </button>
              )}
              <button className="btn btn-ghost" onClick={rotate} disabled={rotating || Boolean(systemStatus?.maintenance_mode)}>
                <RefreshCw size={16} className={rotating ? 'spin' : ''} /> Обновить
              </button>
              <Link className="btn btn-ghost" to={`/keys/${keyData.id}/renew`}>
                <RefreshCw size={16} /> Продлить
              </Link>
            </div>
          </article>

          <article className="glass-card liquid-panel">
            <p className="title-line">Как открыть профиль ZERO</p>
            <div className="stack compact-stack">
              {connectionGuide.map((item, index) => (
                <div key={item} className="hint-row">
                  <span className="step-badge">{index + 1}</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
            <div className="qr-wrap">
              <div className="qr-card liquid-panel">
                <div className="qr-title">
                  <QrCode size={16} /> QR-код
                </div>
                <QRCodeCanvas value={uri} size={180} bgColor="#0f0f0f" fgColor="#f5f5f5" />
              </div>
            </div>
          </article>
        </>
      ) : (
        <EmptyState
          title="Служебная ссылка пока недоступна"
          text={
            keyData.status === 'revoked'
              ? 'Этот доступ уже отключён. Вы можете удалить его из истории или создать новый.'
              : 'Конфигурация ещё подготавливается. Обновите страницу немного позже.'
          }
        />
      )}

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

      {deletionAllowed && (
        <button className="btn btn-danger-soft" onClick={removeKey} disabled={deleting}>
          <Trash2 size={16} /> Удалить доступ из истории
        </button>
      )}

      {error && <ErrorState text={error} />}
      {message && <div className="toast-success">{message}</div>}
    </section>
  );
}
