import { CircleDollarSign, ExternalLink } from 'lucide-react';
import { useEffect, useState } from 'react';

import { apiRequest, toJsonBody } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/StateCards';
import type { PaymentIntent, Plan } from '../types/models';

export function BuyPlanPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<Plan[]>('/plans')
      .then(setPlans)
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось загрузить тарифы'))
      .finally(() => setLoading(false));
  }, []);

  const buy = async (planId: string) => {
    try {
      const payment = await apiRequest<PaymentIntent>('/keys/purchase', toJsonBody({ plan_id: planId, apply_bonus_days: 0 }));
      if (payment.confirmation_url) {
        const tg = window.Telegram?.WebApp;
        if (tg?.openLink) {
          tg.openLink(payment.confirmation_url);
        } else {
          window.open(payment.confirmation_url, '_blank');
        }
      }
      setMessage('Сессия оплаты создана. Завершите оплату для активации ключа.');
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать платеж');
    }
  };

  return (
    <section className="stack">
      <PageHeader title="Покупка тарифа" subtitle="Выберите срок и перейдите к оплате" />

      {loading && <LoadingState text="Загружаем тарифы..." />}
      {error && <ErrorState text={error} />}
      {!loading && !error && plans.length === 0 && <EmptyState title="Тарифов нет" text="Попробуйте позже." />}

      {!loading && !error && plans.map((plan) => (
        <article key={plan.id} className="glass-card plan-card">
          <div className="row-between">
            <p className="title-line">{plan.name}</p>
            <p className="price-line">{plan.price} {plan.currency}</p>
          </div>
          <p className="muted">Длительность: {plan.duration_days} дней</p>
          <button className="btn btn-primary" onClick={() => buy(plan.id)}>
            <CircleDollarSign size={16} /> Оплатить <ExternalLink size={14} />
          </button>
        </article>
      ))}

      {message && <div className="toast-success">{message}</div>}
    </section>
  );
}
