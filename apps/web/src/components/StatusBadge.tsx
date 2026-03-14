import type { VPNKey } from '../types/models';

const statusMap: Record<VPNKey['status'] | string, { label: string; className: string }> = {
  active: { label: 'Активен', className: 'status-badge status-active' },
  expired: { label: 'Истёк', className: 'status-badge status-expired' },
  revoked: { label: 'Отозван', className: 'status-badge status-revoked' },
  pending_payment: { label: 'Ждёт оплаты', className: 'status-badge status-pending' },
  pending: { label: 'В ожидании', className: 'status-badge status-pending' },
  waiting_for_capture: { label: 'Ожидает', className: 'status-badge status-pending' },
  succeeded: { label: 'Оплачен', className: 'status-badge status-active' },
  failed: { label: 'Ошибка', className: 'status-badge status-revoked' },
  canceled: { label: 'Отменён', className: 'status-badge status-revoked' },
};

export function StatusBadge({ status }: { status: string }) {
  const value = statusMap[status] ?? { label: status, className: 'status-badge status-pending' };
  return <span className={value.className}>{value.label}</span>;
}
