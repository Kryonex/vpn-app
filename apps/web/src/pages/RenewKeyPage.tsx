import { CircleDollarSign, Copy, Sparkles } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

import { apiRequest, toJsonBody } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/StateCards';
import { SystemStatusBanner } from '../components/SystemStatusBanner';
import { useAuth } from '../context/AuthContext';
import type { PaymentIntent, Plan } from '../types/models';

export function RenewKeyPage() {
  const { systemStatus } = useAuth();
  const { keyId } = useParams<{ keyId: string }>();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [bonusDays, setBonusDays] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [transferPhone, setTransferPhone] = useState<string | null>(null);
  const [transferNote, setTransferNote] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<Plan[]>('/plans')
      .then(setPlans)
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось загрузить тарифы'))
      .finally(() => setLoading(false));
  }, []);

  const renew = async (planId: string) => {
    if (!keyId) return;
    try {
      const payment = await apiRequest<PaymentIntent>(
        `/keys/${keyId}/renew`,
        toJsonBody({ plan_id: planId, apply_bonus_days: bonusDays }),
      );
      setTransferPhone(payment.transfer_phone);
      setTransferNote(payment.transfer_note);
      setMessage('Заявка на продление создана. Выполните перевод и отправьте чек администратору.');
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать платеж на продление');
    }
  };

  return (
    <section className="stack">
      <PageHeader title="Продление ключа" subtitle="Продлите текущий ключ без перевыпуска" />
      <SystemStatusBanner status={systemStatus} compact />

      <article className="glass-card">
        <label className="muted" htmlFor="bonus-days">Бонусных дней применить</label>
        <div className="input-wrap">
          <Sparkles size={16} />
          <input
            id="bonus-days"
            className="input"
            type="number"
            value={bonusDays}
            min={0}
            onChange={(e) => setBonusDays(Number(e.target.value || 0))}
          />
        </div>
      </article>

      {loading && <LoadingState text="Загружаем тарифы..." />}
      {error && <ErrorState text={error} />}
      {!loading && !error && plans.length === 0 && <EmptyState title="Тарифов нет" text="Попробуйте позже." />}

      {transferPhone && (
        <article className="glass-card">
          <p className="title-line">Оплата переводом</p>
          <p className="muted">Номер для перевода: <strong>{transferPhone}</strong></p>
          <p className="muted">Комментарий к переводу:</p>
          <p className="mono-block">{transferNote || 'VPN продление'}</p>
          <button className="btn btn-ghost" onClick={() => navigator.clipboard.writeText(transferPhone)}>
            <Copy size={16} /> Скопировать номер
          </button>
        </article>
      )}

      {!loading && !error && plans.map((plan) => (
        <article key={plan.id} className="glass-card plan-card">
          <div className="row-between">
            <p className="title-line">{plan.name}</p>
            <p className="price-line">{plan.price} {plan.currency}</p>
          </div>
          <p className="muted">Длительность: {plan.duration_days} дней</p>
          <button
            className="btn btn-primary"
            onClick={() => renew(plan.id)}
            disabled={Boolean(systemStatus?.maintenance_mode)}
          >
            <CircleDollarSign size={16} /> Создать заявку на продление
          </button>
        </article>
      ))}

      {message && <div className="toast-success">{message}</div>}
    </section>
  );
}
