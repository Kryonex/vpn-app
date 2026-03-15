import { CheckCircle2, CircleDollarSign, Copy, History, MessageCircleMore, ReceiptText } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';

import { apiRequest, toJsonBody } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState, SkeletonCards } from '../components/StateCards';
import { StatusBadge } from '../components/StatusBadge';
import { SystemStatusBanner } from '../components/SystemStatusBanner';
import { useAuth } from '../context/AuthContext';
import type { Payment, PaymentIntent, PaymentSettings, Plan, SupportContact } from '../types/models';

export function BuyPlanPage() {
  const { systemStatus } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [paymentSettings, setPaymentSettings] = useState<PaymentSettings>({ enabled: true, mode: 'direct' });
  const [support, setSupport] = useState<SupportContact | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [transferPhone, setTransferPhone] = useState<string | null>(null);
  const [transferNote, setTransferNote] = useState<string | null>(null);
  const [showPurchaseSuccess, setShowPurchaseSuccess] = useState(false);
  const successTimerRef = useRef<number | null>(null);

  useEffect(() => {
    Promise.all([
      apiRequest<Plan[]>('/plans'),
      apiRequest<Payment[]>('/payments'),
      apiRequest<PaymentSettings>('/system/payments'),
      apiRequest<SupportContact>('/support'),
    ])
      .then(([plansData, paymentsData, paymentConfig, supportData]) => {
        setPlans(plansData);
        setPayments(paymentsData);
        setPaymentSettings(paymentConfig);
        setSupport(supportData);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Не удалось загрузить данные для подключения'))
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
      setMessage(
        paymentSettings.enabled
          ? 'Заявка создана. Выполните перевод по инструкции ниже и отправьте подтверждение администратору.'
          : 'Заявка создана. Напишите администратору, и он лично отправит реквизиты для оплаты.',
      );
      setShowPurchaseSuccess(true);
      if (successTimerRef.current) {
        window.clearTimeout(successTimerRef.current);
      }
      successTimerRef.current = window.setTimeout(() => setShowPurchaseSuccess(false), 2600);
      await refreshPayments();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать заявку на подключение');
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
      <PageHeader title="Подключение ZERO" subtitle="Тарифы, заявки и история активаций в одном месте" />
      <SystemStatusBanner status={systemStatus} compact />

      {loading && <SkeletonCards count={3} />}
      {error && <ErrorState text={error} />}
      {!loading && !error && plans.length === 0 && <EmptyState title="Тарифы пока недоступны" text="Попробуйте открыть раздел немного позже." />}

      <article className="glass-card liquid-panel buy-mode-card">
        <div>
          <p className="title-line row-inline"><ReceiptText size={16} /> Режим оплаты</p>
          <p className="muted">
            {paymentSettings.enabled
              ? 'ZERO показывает номер для перевода и комментарий к платежу прямо в приложении.'
              : 'Прямые реквизиты скрыты. После создания заявки ZERO переводит вас к администратору для ручного оформления оплаты.'}
          </p>
        </div>
        {!paymentSettings.enabled && support?.telegram_link && (
          <a className="btn btn-primary" href={support.telegram_link} target="_blank" rel="noreferrer">
            <MessageCircleMore size={16} /> Написать администратору
          </a>
        )}
      </article>

      {showPurchaseSuccess && (
        <article className="glass-card purchase-success liquid-panel">
          <div className="purchase-check-wrap">
            <span className="purchase-check-ripple" />
            <CheckCircle2 size={28} className="purchase-check-icon" />
          </div>
          <p className="title-line">Заявка создана</p>
          <p className="muted">
            {paymentSettings.enabled
              ? 'Мы уже подготовили данные для перевода. После подтверждения оплаты доступ появится в разделе с подключениями.'
              : 'Теперь откройте чат с администратором. Он отправит реквизиты и проведёт вас дальше вручную.'}
          </p>
        </article>
      )}

      {paymentSettings.enabled && transferPhone && (
        <article className="glass-card buy-instructions-card liquid-panel">
          <p className="title-line row-inline"><ReceiptText size={16} /> Как оплатить заявку</p>
          <div className="stack compact-stack">
            <div className="hint-row"><span className="step-badge">1</span><span>Переведите оплату на номер <strong>{transferPhone}</strong>.</span></div>
            <div className="hint-row"><span className="step-badge">2</span><span>Укажите комментарий к переводу, чтобы администратор быстро нашёл заявку.</span></div>
            <div className="hint-row"><span className="step-badge">3</span><span>После перевода отправьте чек администратору. Он подтвердит оплату и активирует доступ.</span></div>
          </div>
          <p className="muted">Комментарий к переводу</p>
          <p className="mono-block">{transferNote || 'ZERO заявка'}</p>
          <div className="action-row">
            <button className="btn btn-primary" onClick={() => transferPhone && navigator.clipboard.writeText(transferPhone)}>
              <Copy size={16} /> Скопировать номер
            </button>
            <button className="btn btn-ghost" onClick={() => navigator.clipboard.writeText(transferNote || 'ZERO заявка')}>
              <Copy size={16} /> Скопировать комментарий
            </button>
          </div>
        </article>
      )}

      {!paymentSettings.enabled && activePayments.length > 0 && (
        <article className="glass-card liquid-panel support-inline-card">
          <p className="title-line">Открытые заявки переданы администратору</p>
          <p className="muted">Ваши заявки уже зафиксированы. Для оплаты просто продолжите общение с администратором.</p>
          {support?.telegram_link && (
            <a className="btn btn-primary" href={support.telegram_link} target="_blank" rel="noreferrer">
              <MessageCircleMore size={16} /> Открыть чат
            </a>
          )}
        </article>
      )}

      <article className="glass-card liquid-panel">
        <div className="section-head">
          <div>
            <p className="title-line row-inline"><CircleDollarSign size={16} /> Тарифы ZERO</p>
            <p className="muted">Выберите подходящий режим ускорения и создайте заявку на подключение.</p>
          </div>
        </div>
        <div className="stack compact-stack">
          {!loading && !error && plans.map((plan) => (
            <article key={plan.id} className="plan-card compact-plan-card liquid-panel">
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
        <article className="glass-card admin-section liquid-panel">
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
            {!activePayments.length && <p className="muted">Сейчас нет активных заявок.</p>}
          </div>
        </article>

        <article className="glass-card admin-section liquid-panel">
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
