import { CheckCircle2, CircleDollarSign, Copy, History, ReceiptText } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';

import { apiRequest, toJsonBody } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState, SkeletonCards } from '../components/StateCards';
import { StatusBadge } from '../components/StatusBadge';
import { SystemStatusBanner } from '../components/SystemStatusBanner';
import { useAuth } from '../context/AuthContext';
import type { Payment, PaymentIntent, Plan } from '../types/models';

export function BuyPlanPage() {
  const { systemStatus } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [transferPhone, setTransferPhone] = useState<string | null>(null);
  const [transferNote, setTransferNote] = useState<string | null>(null);
  const [showPurchaseSuccess, setShowPurchaseSuccess] = useState(false);
  const successTimerRef = useRef<number | null>(null);

  useEffect(() => {
    Promise.all([apiRequest<Plan[]>('/plans'), apiRequest<Payment[]>('/payments')])
      .then(([plansData, paymentsData]) => {
        setPlans(plansData);
        setPayments(paymentsData);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось загрузить данные для покупки'))
      .finally(() => setLoading(false));

    return () => {
      if (successTimerRef.current) {
        window.clearTimeout(successTimerRef.current);
      }
    };
  }, []);

  const refreshPayments = async () => {
    const nextPayments = await apiRequest<Payment[]>('/payments');
    setPayments(nextPayments);
  };

  const buy = async (planId: string) => {
    try {
      const payment = await apiRequest<PaymentIntent>(
        '/keys/purchase',
        toJsonBody({ plan_id: planId, apply_bonus_days: 0 }),
      );
      setTransferPhone(payment.transfer_phone);
      setTransferNote(payment.transfer_note);
      setMessage('Заявка создана. Переведите оплату по реквизитам ниже и отправьте чек администратору.');
      setShowPurchaseSuccess(true);
      if (successTimerRef.current) {
        window.clearTimeout(successTimerRef.current);
      }
      successTimerRef.current = window.setTimeout(() => setShowPurchaseSuccess(false), 2600);
      await refreshPayments();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать заявку на оплату');
    }
  };

  const activePayments = useMemo(
    () => payments.filter((payment) => payment.status === 'pending' || payment.status === 'waiting_for_capture'),
    [payments],
  );
  const historyPayments = useMemo(
    () => payments.filter((payment) => payment.status !== 'pending' && payment.status !== 'waiting_for_capture').slice(0, 6),
    [payments],
  );

  return (
    <section className="stack">
      <PageHeader title="Купить" subtitle="Тарифы, текущие заявки и история оплат в одном разделе" />
      <SystemStatusBanner status={systemStatus} compact />

      {loading && <SkeletonCards count={3} />}
      {error && <ErrorState text={error} />}
      {!loading && !error && plans.length === 0 && <EmptyState title="Тарифы пока недоступны" text="Попробуйте открыть раздел немного позже." />}

      {showPurchaseSuccess && (
        <article className="glass-card purchase-success">
          <div className="purchase-check-wrap">
            <span className="purchase-check-ripple" />
            <CheckCircle2 size={28} className="purchase-check-icon" />
          </div>
          <p className="title-line">Заявка создана</p>
          <p className="muted">Мы уже подготовили данные для перевода. Как только оплата будет подтверждена, ключ появится в разделе «Ключи».</p>
        </article>
      )}

      {transferPhone && (
        <article className="glass-card buy-instructions-card">
          <p className="title-line row-inline"><ReceiptText size={16} /> Как оплатить заявку</p>
          <div className="stack compact-stack">
            <div className="hint-row"><span className="step-badge">1</span><span>Переведите оплату на номер <strong>{transferPhone}</strong>.</span></div>
            <div className="hint-row"><span className="step-badge">2</span><span>Укажите комментарий к переводу, чтобы мы быстрее нашли ваш платёж.</span></div>
            <div className="hint-row"><span className="step-badge">3</span><span>После перевода отправьте чек администратору. Мы подтвердим оплату и активируем доступ.</span></div>
          </div>
          <p className="muted">Комментарий к переводу</p>
          <p className="mono-block">{transferNote || 'VPN заявка'}</p>
          <div className="action-row">
            <button className="btn btn-primary" onClick={() => navigator.clipboard.writeText(transferPhone)}>
              <Copy size={16} /> Скопировать номер
            </button>
            <button className="btn btn-ghost" onClick={() => navigator.clipboard.writeText(transferNote || 'VPN заявка')}>
              <Copy size={16} /> Скопировать комментарий
            </button>
          </div>
        </article>
      )}

      <article className="glass-card">
        <div className="section-head">
          <div>
            <p className="title-line row-inline"><CircleDollarSign size={16} /> Тарифы</p>
            <p className="muted">Выберите подходящий срок подписки. После создания заявки мы сразу покажем реквизиты для оплаты.</p>
          </div>
        </div>
        <div className="stack compact-stack">
          {!loading && !error && plans.map((plan) => (
            <article key={plan.id} className="plan-card compact-plan-card">
              <div className="row-between">
                <div>
                  <p className="title-line">{plan.name}</p>
                  <p className="muted">{plan.duration_days} дней доступа</p>
                </div>
                <p className="price-line">{plan.price} {plan.currency}</p>
              </div>
              <button className="btn btn-primary" onClick={() => void buy(plan.id)} disabled={Boolean(systemStatus?.maintenance_mode)}>
                <CircleDollarSign size={16} /> Создать заявку
              </button>
            </article>
          ))}
        </div>
      </article>

      <div className="admin-grid">
        <article className="glass-card admin-section">
          <p className="title-line row-inline"><ReceiptText size={16} /> Активные заявки</p>
          <div className="admin-list">
            {activePayments.map((payment) => (
              <article key={payment.id} className="admin-item">
                <div className="row-between">
                  <div>
                    <p className="title-line">{payment.amount} {payment.currency}</p>
                    <p className="muted">Создано: {new Date(payment.created_at).toLocaleString()}</p>
                  </div>
                  <StatusBadge status={payment.status} />
                </div>
              </article>
            ))}
            {!activePayments.length && <p className="muted">Сейчас нет активных заявок на оплату.</p>}
          </div>
        </article>

        <article className="glass-card admin-section">
          <p className="title-line row-inline"><History size={16} /> История оплат</p>
          <div className="admin-list">
            {historyPayments.map((payment) => (
              <article key={payment.id} className="admin-item">
                <div className="row-between">
                  <div>
                    <p className="title-line">{payment.amount} {payment.currency}</p>
                    <p className="muted">{new Date(payment.created_at).toLocaleString()}</p>
                  </div>
                  <StatusBadge status={payment.status} />
                </div>
              </article>
            ))}
            {!historyPayments.length && <p className="muted">Завершённых оплат пока нет.</p>}
          </div>
        </article>
      </div>

      {message && <div className="toast-success">{message}</div>}
    </section>
  );
}
