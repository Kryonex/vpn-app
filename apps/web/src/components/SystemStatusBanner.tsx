import { AlertTriangle, ShieldAlert, Wrench } from 'lucide-react';

import type { SystemStatus } from '../types/models';

function statusTitle(status: SystemStatus['status']) {
  switch (status) {
    case 'degraded':
      return 'Есть временные сбои';
    case 'maintenance':
      return 'Идут технические работы';
    case 'panel_unavailable':
      return 'Сервис выдачи ключей временно недоступен';
    case 'server_unavailable':
      return 'Сервер временно недоступен';
    default:
      return 'Система работает стабильно';
  }
}

export function SystemStatusBanner({
  status,
  compact = false,
}: {
  status: SystemStatus | null;
  compact?: boolean;
}) {
  if (!status || !status.show_to_all || status.status === 'online') {
    return null;
  }

  const Icon = status.maintenance_mode ? Wrench : status.status === 'degraded' ? AlertTriangle : ShieldAlert;
  const className = compact ? 'status-banner compact' : 'status-banner';

  return (
    <article className={className}>
      <div className="status-banner-icon">
        <Icon size={18} />
      </div>
      <div>
        <p className="status-banner-title">{statusTitle(status.status)}</p>
        <p className="status-banner-text">
          {status.message || 'Часть действий может быть временно ограничена.'}
        </p>
        {status.scheduled_for && (
          <p className="status-banner-meta">
            Плановое время: {new Date(status.scheduled_for).toLocaleString()}
          </p>
        )}
      </div>
    </article>
  );
}
