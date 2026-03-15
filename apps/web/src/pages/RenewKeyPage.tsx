import { CircleDollarSign, Copy, MessageCircleMore, Sparkles } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

import { apiRequest, toJsonBody } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/StateCards';
import { SystemStatusBanner } from '../components/SystemStatusBanner';
import { useAuth } from '../context/AuthContext';
import type { PaymentIntent, PaymentSettings, Plan, SupportContact } from '../types/models';

export function RenewKeyPage() {
  const { systemStatus } = useAuth();
  const { keyId } = useParams<{ keyId: string }>();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [paymentSettings, setPaymentSettings] = useState<PaymentSettings>({ enabled: true, mode: 'direct' });
  const [support, setSupport] = useState<SupportContact | null>(null);
  const [bonusDays, setBonusDays] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [transferPhone, setTransferPhone] = useState<string | null>(null);
  const [transferNote, setTransferNote] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      apiRequest<Plan[]>('/plans'),
      apiRequest<PaymentSettings>('/system/payments'),
      apiRequest<SupportContact>('/support'),
    ])
      .then(([planData, paymentConfig, supportData]) => {
        setPlans(planData);
        setPaymentSettings(paymentConfig);
        setSupport(supportData);
      })
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
      setMessage(
        paymentSettings.enabled
          ? 'Заявка на продление создана. Выполните перевод и отправьте подтверждение администратору.'
          : 'Заявка создана. Для оплаты продолжите общение с администратором.',
      );
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать заявку на продление');
    }
  };

  return (
    <section className="stack">
      <PageHeader title="Продление доступа" subtitle="Продлите текущий доступ без перевыпуска" />
      <SystemStatusBanner status={systemStatus} compact />

      <article className="glass-card liquid-panel">
        <label className="muted" htmlFor="bonus-days">Сколько бонусных дней использовать</label>
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
      {!loading && !error && plans.length === 0 && <EmptyState title="Тарифов пока нет" text="Попробуйте открыть раздел немного позже." />}

      {paymentSettings.enabled && transferPhone && (
        <article className="glass-card liquid-panel">
          <p className="title-line">Как оплатить продление</p>
          <p className="muted">Номер для перевода: <strong>{transferPhone}</strong></p>
          <p className="muted">Комментарий к переводу:</p>
          <p className="mono-block">{transferNote || 'ZERO продление'}</p>
          <button className="btn btn-ghost" onClick={() => transferPhone && navigator.clipboard.writeText(transferPhone)}>
            <Copy size={16} /> Скопировать номер
          </button>
        </article>
      )}

      {!paymentSettings.enabled && message && (
        <article className="glass-card liquid-panel">
          <p className="title-line">Продление через администратора</p>
          <p className="muted">ZERO не показывает прямые реквизиты в этом режиме. Администратор завершит оформление вручную.</p>
          {support?.telegram_link && (
            <a className="btn btn-primary" href={support.telegram_link} target="_blank" rel="noreferrer">
              <MessageCircleMore size={16} /> Написать администратору
            </a>
          )}
        </article>
      )}

      {!loading && !error && plans.map((plan) => (
        <article key={plan.id} className="glass-card plan-card liquid-panel">
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
