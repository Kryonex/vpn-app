import { CheckCircle2, CircleSlash2, Gift, Plus, RefreshCw, Settings2, TrendingUp } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { apiRequest, toJsonBody } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/StateCards';
import type { Payment, Plan } from '../types/models';

type AdminPaymentsResponse = { items: Payment[] };
type AdminPlansResponse = { items: Plan[] };
type AdminStats = {
  total_payments: number;
  succeeded_payments: number;
  pending_payments: number;
  failed_payments: number;
  total_revenue: string;
  month_revenue: string;
};
type ReferralSettings = {
  referral_bonus_days: number;
};
type BindPanelKeyResponse = {
  key_id: string;
  version_id: string;
  owner_id: string;
  connection_uri: string | null;
};

type PlanForm = {
  name: string;
  duration_days: number;
  price: string;
  currency: string;
  is_active: boolean;
  sort_order: number;
};

const defaultPlanForm: PlanForm = {
  name: '',
  duration_days: 30,
  price: '299.00',
  currency: 'RUB',
  is_active: true,
  sort_order: 0,
};

export function AdminPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [referralBonusDays, setReferralBonusDays] = useState(7);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState<PlanForm>(defaultPlanForm);
  const [editing, setEditing] = useState<Record<string, PlanForm>>({});
  const [bindUsername, setBindUsername] = useState('');
  const [bindClientUuid, setBindClientUuid] = useState('');
  const [bindInboundId, setBindInboundId] = useState('');

  const pendingPayments = useMemo(
    () => payments.filter((payment) => payment.status === 'pending' || payment.status === 'waiting_for_capture'),
    [payments],
  );

  const loadData = async () => {
    try {
      setLoading(true);
      const [plansData, paymentsData, statsData, referralSettings] = await Promise.all([
        apiRequest<AdminPlansResponse>('/admin/plans'),
        apiRequest<AdminPaymentsResponse>('/admin/payments?limit=200'),
        apiRequest<AdminStats>('/admin/stats'),
        apiRequest<ReferralSettings>('/admin/settings/referral'),
      ]);
      setPlans(plansData.items);
      setPayments(paymentsData.items);
      setStats(statsData);
      setReferralBonusDays(referralSettings.referral_bonus_days);

      const editState: Record<string, PlanForm> = {};
      plansData.items.forEach((plan) => {
        editState[plan.id] = {
          name: plan.name,
          duration_days: plan.duration_days,
          price: String(plan.price),
          currency: plan.currency,
          is_active: plan.is_active,
          sort_order: plan.sort_order,
        };
      });
      setEditing(editState);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки админ-данных');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const approve = async (paymentId: string) => {
    try {
      await apiRequest(`/admin/payments/${paymentId}/approve`, toJsonBody({ reason: 'manual_approve' }));
      setMessage('Платеж подтвержден');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось подтвердить платеж');
    }
  };

  const reject = async (paymentId: string) => {
    try {
      await apiRequest(`/admin/payments/${paymentId}/reject`, toJsonBody({ reason: 'manual_reject' }));
      setMessage('Платеж отклонен');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось отклонить платеж');
    }
  };

  const createPlan = async () => {
    try {
      await apiRequest('/admin/plans', toJsonBody(createForm));
      setMessage('Тариф создан');
      setCreateForm(defaultPlanForm);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать тариф');
    }
  };

  const updatePlan = async (planId: string) => {
    const form = editing[planId];
    if (!form) return;
    try {
      await apiRequest(`/admin/plans/${planId}`, {
        method: 'PATCH',
        body: JSON.stringify(form),
      });
      setMessage('Тариф обновлен');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось обновить тариф');
    }
  };

  const saveReferralSettings = async () => {
    try {
      await apiRequest('/admin/settings/referral', {
        method: 'PATCH',
        body: JSON.stringify({ referral_bonus_days: referralBonusDays }),
      });
      setMessage('Настройка реферальной награды сохранена');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить настройку рефералки');
    }
  };

  const resetKeysAndEarnings = async () => {
    const confirmText = window.prompt('Это действие удалит все ключи и данные заработка. Введите RESET для подтверждения.');
    if (!confirmText) return;

    try {
      const result = await apiRequest<{
        ok: boolean;
        keys_revoked: number;
        payments_zeroed: number;
      }>('/admin/system/reset-keys-and-earnings', toJsonBody({ confirm_text: confirmText }));

      if (result.ok) {
        setMessage(`Сброс выполнен. Отозвано ключей: ${result.keys_revoked}, обнулено платежей: ${result.payments_zeroed}.`);
        await loadData();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось выполнить сброс данных');
    }
  };

  const bindPanelKey = async () => {
    try {
      const payload = {
        username: bindUsername,
        client_uuid: bindClientUuid || null,
        inbound_id: bindInboundId ? Number(bindInboundId) : null,
      };
      const result = await apiRequest<BindPanelKeyResponse>('/admin/keys/bind-by-username', toJsonBody(payload));
      setMessage(
        `Ключ привязан к @${bindUsername.replace('@', '')}. key_id=${result.key_id}${
          result.connection_uri ? `, uri=${result.connection_uri}` : ''
        }`,
      );
      setBindUsername('');
      setBindClientUuid('');
      setBindInboundId('');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось привязать ключ из панели');
    }
  };

  if (loading) {
    return <LoadingState text="Загружаем админ-панель..." />;
  }

  if (error && plans.length === 0 && payments.length === 0) {
    return <ErrorState text={error} />;
  }

  return (
    <section className="stack">
      <PageHeader title="Админ-панель" subtitle="Платежи, статистика, тарифы и рефералы" />

      {stats && (
        <div className="stat-grid">
          <article className="glass-card stat-card">
            <span className="stat-icon"><TrendingUp size={16} /></span>
            <p className="stat-label">Выручка всего</p>
            <p className="stat-value">{stats.total_revenue} ₽</p>
          </article>
          <article className="glass-card stat-card">
            <span className="stat-icon"><TrendingUp size={16} /></span>
            <p className="stat-label">Выручка за месяц</p>
            <p className="stat-value">{stats.month_revenue} ₽</p>
          </article>
          <article className="glass-card stat-card">
            <span className="stat-icon"><Settings2 size={16} /></span>
            <p className="stat-label">Успешных оплат</p>
            <p className="stat-value">{stats.succeeded_payments}</p>
          </article>
          <article className="glass-card stat-card">
            <span className="stat-icon"><Settings2 size={16} /></span>
            <p className="stat-label">Ожидают</p>
            <p className="stat-value">{stats.pending_payments}</p>
          </article>
        </div>
      )}

      <article className="glass-card">
        <p className="title-line row-inline"><Gift size={16} /> Реферальная награда</p>
        <p className="muted">Количество бонусных дней за первую успешную оплату приглашенного пользователя</p>
        <div className="admin-grid">
          <input
            className="input"
            type="number"
            min={0}
            max={3650}
            value={referralBonusDays}
            onChange={(e) => setReferralBonusDays(Number(e.target.value || 0))}
          />
        </div>
        <button className="btn btn-primary" onClick={() => void saveReferralSettings()}>
          Сохранить реферальную награду
        </button>
      </article>

      <article className="glass-card">
        <p className="title-line">Системный сброс</p>
        <p className="muted">Мягкий сброс: ключи/подписки/платежи переводятся в неактивное состояние, история пользователей и тарифы сохраняются.</p>
        <button className="btn btn-soft" onClick={() => void resetKeysAndEarnings()}>
          Мягко обнулить ключи и заработок
        </button>
      </article>

      <article className="glass-card">
        <p className="title-line">Привязка ключа из панели к @user</p>
        <p className="muted">Позволяет импортировать клиентский ключ из 3x-ui до первого входа пользователя в бота.</p>
        <div className="admin-grid">
          <input
            className="input"
            placeholder="@username"
            value={bindUsername}
            onChange={(e) => setBindUsername(e.target.value)}
          />
          <input
            className="input"
            placeholder="client_uuid (необязательно)"
            value={bindClientUuid}
            onChange={(e) => setBindClientUuid(e.target.value)}
          />
          <input
            className="input"
            type="number"
            placeholder="inbound_id (необязательно)"
            value={bindInboundId}
            onChange={(e) => setBindInboundId(e.target.value)}
          />
        </div>
        <button className="btn btn-primary" onClick={() => void bindPanelKey()}>
          Привязать ключ к пользователю
        </button>
      </article>

      <article className="glass-card">
        <div className="row-between">
          <p className="title-line row-inline"><Settings2 size={16} /> Новые заявки на оплату</p>
          <button className="btn btn-ghost" onClick={() => void loadData()}>
            <RefreshCw size={16} /> Обновить
          </button>
        </div>

        {pendingPayments.length === 0 ? (
          <EmptyState title="Нет ожидающих платежей" text="Все заявки уже обработаны." />
        ) : (
          <div className="stack">
            {pendingPayments.map((payment) => (
              <article key={payment.id} className="admin-item">
                <p className="title-line">{payment.amount} {payment.currency}</p>
                <p className="muted">ID: {payment.id}</p>
                <p className="muted">Операция: {payment.operation}</p>
                <p className="muted">Создан: {new Date(payment.created_at).toLocaleString()}</p>
                <div className="action-row">
                  <button className="btn btn-primary" onClick={() => void approve(payment.id)}>
                    <CheckCircle2 size={16} /> Подтвердить
                  </button>
                  <button className="btn btn-ghost" onClick={() => void reject(payment.id)}>
                    <CircleSlash2 size={16} /> Отклонить
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </article>

      <article className="glass-card">
        <p className="title-line row-inline"><Plus size={16} /> Создать тариф</p>
        <div className="admin-grid">
          <input className="input" placeholder="Название" value={createForm.name} onChange={(e) => setCreateForm((prev) => ({ ...prev, name: e.target.value }))} />
          <input className="input" placeholder="Дней" type="number" min={1} value={createForm.duration_days} onChange={(e) => setCreateForm((prev) => ({ ...prev, duration_days: Number(e.target.value || 1) }))} />
          <input className="input" placeholder="Цена" value={createForm.price} onChange={(e) => setCreateForm((prev) => ({ ...prev, price: e.target.value }))} />
          <input className="input" placeholder="Валюта" value={createForm.currency} onChange={(e) => setCreateForm((prev) => ({ ...prev, currency: e.target.value.toUpperCase() }))} />
          <input className="input" placeholder="Порядок" type="number" value={createForm.sort_order} onChange={(e) => setCreateForm((prev) => ({ ...prev, sort_order: Number(e.target.value || 0) }))} />
          <label className="toggle-row">
            <input type="checkbox" checked={createForm.is_active} onChange={(e) => setCreateForm((prev) => ({ ...prev, is_active: e.target.checked }))} />
            Активен
          </label>
        </div>
        <button className="btn btn-primary" onClick={() => void createPlan()}>
          <Plus size={16} /> Добавить тариф
        </button>
      </article>

      <article className="glass-card">
        <p className="title-line">Существующие тарифы</p>
        {plans.length === 0 ? (
          <EmptyState title="Тарифов нет" text="Создайте первый тариф." />
        ) : (
          <div className="stack">
            {plans.map((plan) => {
              const form = editing[plan.id];
              if (!form) return null;
              return (
                <article key={plan.id} className="admin-item">
                  <div className="admin-grid">
                    <input className="input" value={form.name} onChange={(e) => setEditing((prev) => ({ ...prev, [plan.id]: { ...form, name: e.target.value } }))} />
                    <input className="input" type="number" min={1} value={form.duration_days} onChange={(e) => setEditing((prev) => ({ ...prev, [plan.id]: { ...form, duration_days: Number(e.target.value || 1) } }))} />
                    <input className="input" value={form.price} onChange={(e) => setEditing((prev) => ({ ...prev, [plan.id]: { ...form, price: e.target.value } }))} />
                    <input className="input" value={form.currency} onChange={(e) => setEditing((prev) => ({ ...prev, [plan.id]: { ...form, currency: e.target.value.toUpperCase() } }))} />
                    <input className="input" type="number" value={form.sort_order} onChange={(e) => setEditing((prev) => ({ ...prev, [plan.id]: { ...form, sort_order: Number(e.target.value || 0) } }))} />
                    <label className="toggle-row">
                      <input type="checkbox" checked={form.is_active} onChange={(e) => setEditing((prev) => ({ ...prev, [plan.id]: { ...form, is_active: e.target.checked } }))} />
                      Активен
                    </label>
                  </div>
                  <button className="btn btn-primary" onClick={() => void updatePlan(plan.id)}>
                    Сохранить
                  </button>
                </article>
              );
            })}
          </div>
        )}
      </article>

      {error && <ErrorState text={error} />}
      {message && <div className="toast-success">{message}</div>}
    </section>
  );
}
