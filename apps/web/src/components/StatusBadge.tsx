import type { VPNKey } from '../types/models';

const statusMap: Record<VPNKey['status'] | string, { label: string; className: string }> = {
  active: { label: 'Активен', className: 'status-badge status-active' },
  expired: { label: 'Истек', className: 'status-badge status-expired' },
  revoked: { label: 'Отозван', className: 'status-badge status-revoked' },
  pending_payment: { label: 'Ожидает оплату', className: 'status-badge status-pending' },
};

export function StatusBadge({ status }: { status: string }) {
  const value = statusMap[status] ?? { label: status, className: 'status-badge status-pending' };
  return <span className={value.className}>{value.label}</span>;
}
