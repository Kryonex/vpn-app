import { CalendarClock, CircleCheckBig, Clock3, CircleX } from 'lucide-react';
import { useEffect, useState } from 'react';

import { apiRequest } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/StateCards';
import type { Payment } from '../types/models';

const paymentStatusLabels: Record<string, string> = {
  pending: 'Ожидает подтверждения',
  waiting_for_capture: 'Ожидает подтверждения',
  succeeded: 'Успешно',
  canceled: 'Отменен',
  failed: 'Отклонен',
};

function paymentIcon(status: string) {
  if (status === 'succeeded') return <CircleCheckBig size={16} className="icon-success" />;
  if (status === 'pending' || status === 'waiting_for_capture') return <Clock3 size={16} className="icon-pending" />;
  return <CircleX size={16} className="icon-danger" />;
}

export function PaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<Payment[]>('/payments')
      .then(setPayments)
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось загрузить платежи'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="stack">
      <PageHeader title="История платежей" subtitle="Все операции по оплате подписок" />

      {loading && <LoadingState text="Загружаем историю платежей..." />}
      {error && <ErrorState text={error} />}
      {!loading && !error && payments.length === 0 && (
        <EmptyState title="История пуста" text="Здесь появятся завершенные и ожидающие платежи." />
      )}

      {!loading && !error && payments.map((payment) => (
        <article key={payment.id} className="glass-card">
          <div className="row-between">
            <p className="title-line">{payment.amount} {payment.currency}</p>
            <div className="row-inline">
              {paymentIcon(payment.status)}
              <span className="muted caps">{paymentStatusLabels[payment.status] ?? payment.status}</span>
            </div>
          </div>
          <p className="muted">Операция: {payment.operation}</p>
          <p className="muted row-inline"><CalendarClock size={14} /> {new Date(payment.created_at).toLocaleString()}</p>
        </article>
      ))}
    </section>
  );
}
