import {
  CheckCircle2,
  CircleSlash2,
  Gift,
  KeyRound,
  Plus,
  RefreshCw,
  Shield,
  Sparkles,
  TrendingUp,
  UserCog,
  Wallet,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { apiRequest, toJsonBody } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/StateCards';
import { StatusBadge } from '../components/StatusBadge';
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
type AdminUser = {
  id: string;
  referral_code: string;
  bonus_days_balance: number;
  created_at: string;
};
type AdminKey = {
  id: string;
  owner_id: string;
  display_name: string;
  status: 'active' | 'expired' | 'revoked' | 'pending_payment';
  current_subscription_id: string | null;
  created_at: string;
};
type AdminSubscription = {
  id: string;
  vpn_key_id: string;
  plan_id: string;
  starts_at: string;
  expires_at: string;
  status: string;
};
type AdminReferral = {
  id: string;
  referrer_user_id: string;
  referred_user_id: string;
  status: string;
  created_at: string;
};

type PlanForm = {
  name: string;
  duration_days: number;
  price: string;
  currency: string;
  is_active: boolean;
  sort_order: number;
};

type GrantForm = {
  user_id: string;
  plan_id: string;
  key_id: string;
  key_name: string;
};

type BonusForm = {
  user_id: string;
  days: number;
  reason: string;
};

const defaultPlanForm: PlanForm = {
  name: '',
  duration_days: 30,
  price: '299.00',
  currency: 'RUB',
  is_active: true,
  sort_order: 0,
};

const defaultGrantForm: GrantForm = {
  user_id: '',
  plan_id: '',
  key_id: '',
  key_name: '',
};

const defaultBonusForm: BonusForm = {
  user_id: '',
  days: 7,
  reason: 'admin_bonus',
};

export function AdminPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [keys, setKeys] = useState<AdminKey[]>([]);
  const [subscriptions, setSubscriptions] = useState<AdminSubscription[]>([]);
  const [referrals, setReferrals] = useState<AdminReferral[]>([]);
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
  const [grantForm, setGrantForm] = useState<GrantForm>(defaultGrantForm);
  const [bonusForm, setBonusForm] = useState<BonusForm>(defaultBonusForm);
  const [revokeReason, setRevokeReason] = useState<Record<string, string>>({});
  const [softResetLoading, setSoftResetLoading] = useState(false);

  const pendingPayments = useMemo(
    () => payments.filter((payment) => payment.status === 'pending' || payment.status === 'waiting_for_capture'),
    [payments],
  );

  const loadData = async () => {
    try {
      setLoading(true);
      const [plansData, paymentsData, statsData, referralSettings, usersData, keysData, subscriptionsData, referralsData] =
        await Promise.all([
          apiRequest<AdminPlansResponse>('/admin/plans'),
          apiRequest<AdminPaymentsResponse>('/admin/payments?limit=200'),
          apiRequest<AdminStats>('/admin/stats'),
          apiRequest<ReferralSettings>('/admin/settings/referral'),
          apiRequest<AdminUser[]>('/admin/users?limit=100'),
          apiRequest<AdminKey[]>('/admin/keys?limit=120'),
          apiRequest<AdminSubscription[]>('/admin/subscriptions?limit=120'),
          apiRequest<AdminReferral[]>('/admin/referrals?limit=120'),
        ]);

      setPlans(plansData.items);
      setPayments(paymentsData.items);
      setStats(statsData);
      setReferralBonusDays(referralSettings.referral_bonus_days);
      setUsers(usersData);
      setKeys(keysData);
      setSubscriptions(subscriptionsData);
      setReferrals(referralsData);

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

      setGrantForm((prev) => ({
        ...prev,
        plan_id: prev.plan_id || plansData.items.find((item) => item.is_active)?.id || plansData.items[0]?.id || '',
      }));

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

  const addBonusDays = async () => {
    if (!bonusForm.user_id) {
      setError('Укажите user_id');
      return;
    }

    try {
      await apiRequest(`/admin/users/${bonusForm.user_id}/bonus-days`, toJsonBody({
        days: bonusForm.days,
        reason: bonusForm.reason,
      }));
      setMessage('Бонусные дни начислены');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось начислить бонусные дни');
    }
  };

  const grantSubscription = async () => {
    if (!grantForm.user_id || !grantForm.plan_id) {
      setError('Укажите user_id и plan_id');
      return;
    }

    try {
      await apiRequest(`/admin/users/${grantForm.user_id}/grant-subscription`, toJsonBody({
        plan_id: grantForm.plan_id,
        key_id: grantForm.key_id || null,
        key_name: grantForm.key_name || null,
      }));
      setMessage('Подписка успешно выдана');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось выдать подписку');
    }
  };

  const revokeKey = async (keyId: string) => {
    const reason = revokeReason[keyId] || 'manual_revoke';
    try {
      await apiRequest(`/admin/keys/${keyId}/revoke`, toJsonBody({ reason }));
      setMessage(`Ключ ${keyId} отозван`);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось отозвать ключ');
    }
  };

  const resetKeysAndEarnings = async () => {
    const confirmText = window.prompt('Подтвердите мягкий сброс. Введите RESET для продолжения.');
    if (!confirmText) return;

    try {
      setSoftResetLoading(true);
      const result = await apiRequest<{
        ok: boolean;
        keys_revoked: number;
        payments_zeroed: number;
      }>('/admin/system/reset-keys-and-earnings', toJsonBody({ confirm_text: confirmText }));

      if (result.ok) {
        setMessage(`Сброс выполнен: ключей отозвано ${result.keys_revoked}, платежей обнулено ${result.payments_zeroed}.`);
        await loadData();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось выполнить сброс данных');
    } finally {
      setSoftResetLoading(false);
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

  const attachUser = (userId: string) => {
    setBonusForm((prev) => ({ ...prev, user_id: userId }));
    setGrantForm((prev) => ({ ...prev, user_id: userId }));
  };

  if (loading) {
    return <LoadingState text="Загружаем админ-панель..." />;
  }

  if (error && plans.length === 0 && payments.length === 0 && users.length === 0) {
    return <ErrorState text={error} />;
  }

  return (
    <section className="stack">
      <PageHeader title="Админ-панель" subtitle="Финансы, пользователи, ключи, подписки и системные операции" />

      {stats && (
        <div className="stat-grid">
          <article className="glass-card stat-card">
            <span className="stat-icon"><TrendingUp size={16} /></span>
            <p className="stat-label">Выручка всего</p>
            <p className="stat-value">{stats.total_revenue} ₽</p>
          </article>
          <article className="glass-card stat-card">
            <span className="stat-icon"><Wallet size={16} /></span>
            <p className="stat-label">Выручка за месяц</p>
            <p className="stat-value">{stats.month_revenue} ₽</p>
          </article>
          <article className="glass-card stat-card">
            <span className="stat-icon"><CheckCircle2 size={16} /></span>
            <p className="stat-label">Успешные оплаты</p>
            <p className="stat-value">{stats.succeeded_payments}</p>
          </article>
          <article className="glass-card stat-card">
            <span className="stat-icon"><RefreshCw size={16} /></span>
            <p className="stat-label">Ожидают решения</p>
            <p className="stat-value">{stats.pending_payments}</p>
          </article>
        </div>
      )}

      <article className="glass-card">
        <p className="title-line row-inline"><Gift size={16} /> Реферальная награда</p>
        <p className="muted">Бонусные дни за первую успешную оплату приглашенного пользователя.</p>
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
        <div className="admin-actions">
          <button className="btn btn-primary" onClick={() => void saveReferralSettings()}>
            Сохранить
          </button>
          <button className="btn btn-ghost" onClick={() => void loadData()}>
            <RefreshCw size={16} /> Обновить данные
          </button>
        </div>
      </article>

      <article className="glass-card">
        <p className="title-line row-inline"><Shield size={16} /> Ручные операции с пользователями</p>
        <p className="muted">Начисление бонусных дней и выдача подписки без оплаты.</p>
        <div className="admin-grid">
          <input
            className="input"
            placeholder="user_id"
            value={bonusForm.user_id}
            onChange={(e) => setBonusForm((prev) => ({ ...prev, user_id: e.target.value }))}
          />
          <input
            className="input"
            type="number"
            min={1}
            value={bonusForm.days}
            onChange={(e) => setBonusForm((prev) => ({ ...prev, days: Number(e.target.value || 1) }))}
          />
          <input
            className="input"
            placeholder="Причина (min 3 символа)"
            value={bonusForm.reason}
            onChange={(e) => setBonusForm((prev) => ({ ...prev, reason: e.target.value }))}
          />
        </div>
        <div className="admin-actions">
          <button className="btn btn-primary" onClick={() => void addBonusDays()}>
            <Sparkles size={16} /> Начислить бонусные дни
          </button>
        </div>

        <div className="admin-grid" style={{ marginTop: 12 }}>
          <input
            className="input"
            placeholder="user_id"
            value={grantForm.user_id}
            onChange={(e) => setGrantForm((prev) => ({ ...prev, user_id: e.target.value }))}
          />
          <select
            className="input"
            value={grantForm.plan_id}
            onChange={(e) => setGrantForm((prev) => ({ ...prev, plan_id: e.target.value }))}
          >
            <option value="">Выберите тариф</option>
            {plans.map((plan) => (
              <option key={plan.id} value={plan.id}>
                {plan.name} ({plan.duration_days} дн.)
              </option>
            ))}
          </select>
          <input
            className="input"
            placeholder="key_id (необязательно, если нужно продлить существующий)"
            value={grantForm.key_id}
            onChange={(e) => setGrantForm((prev) => ({ ...prev, key_id: e.target.value }))}
          />
          <input
            className="input"
            placeholder="Название нового ключа (если key_id пустой)"
            value={grantForm.key_name}
            onChange={(e) => setGrantForm((prev) => ({ ...prev, key_name: e.target.value }))}
          />
        </div>
        <div className="admin-actions">
          <button className="btn btn-primary" onClick={() => void grantSubscription()}>
            <Plus size={16} /> Выдать подписку
          </button>
        </div>
      </article>

      <article className="glass-card">
        <p className="title-line">Привязка ключа из панели к @user</p>
        <p className="muted">Импортирует существующий клиент 3x-ui пользователю, даже если он еще не запускал бота.</p>
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
          <KeyRound size={16} /> Привязать ключ
        </button>
      </article>

      <article className="glass-card">
        <div className="row-between">
          <p className="title-line row-inline"><Wallet size={16} /> Заявки на оплату</p>
          <button className="btn btn-ghost" onClick={() => void loadData()}>
            <RefreshCw size={16} /> Обновить
          </button>
        </div>

        {pendingPayments.length === 0 ? (
          <EmptyState title="Нет ожидающих платежей" text="Все заявки обработаны." />
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

      <article className="glass-card">
        <p className="title-line row-inline"><UserCog size={16} /> Пользователи</p>
        {users.length === 0 ? (
          <EmptyState title="Пользователей нет" text="Список пока пуст." />
        ) : (
          <div className="stack">
            {users.slice(0, 20).map((user) => (
              <article className="admin-item" key={user.id}>
                <p className="title-line">{user.id}</p>
                <p className="muted">Реф-код: {user.referral_code}</p>
                <p className="muted">Бонусные дни: {user.bonus_days_balance}</p>
                <p className="muted">Создан: {new Date(user.created_at).toLocaleString()}</p>
                <div className="action-row">
                  <button className="btn btn-ghost" onClick={() => attachUser(user.id)}>
                    Использовать в формах выше
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </article>

      <article className="glass-card">
        <p className="title-line row-inline"><KeyRound size={16} /> Ключи</p>
        {keys.length === 0 ? (
          <EmptyState title="Ключей нет" text="Список ключей пуст." />
        ) : (
          <div className="stack">
            {keys.slice(0, 40).map((key) => (
              <article className="admin-item" key={key.id}>
                <div className="row-between">
                  <p className="title-line">{key.display_name}</p>
                  <StatusBadge status={key.status} />
                </div>
                <p className="muted">key_id: {key.id}</p>
                <p className="muted">owner_id: {key.owner_id}</p>
                <p className="muted">Создан: {new Date(key.created_at).toLocaleString()}</p>
                <div className="admin-grid">
                  <input
                    className="input"
                    placeholder="reason (например manual_revoke)"
                    value={revokeReason[key.id] ?? ''}
                    onChange={(e) => setRevokeReason((prev) => ({ ...prev, [key.id]: e.target.value }))}
                  />
                </div>
                <div className="action-row">
                  <button className="btn btn-soft" onClick={() => void revokeKey(key.id)}>
                    Отозвать ключ
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </article>

      <article className="glass-card">
        <p className="title-line">Подписки</p>
        {subscriptions.length === 0 ? (
          <EmptyState title="Подписок нет" text="Список подписок пуст." />
        ) : (
          <div className="stack">
            {subscriptions.slice(0, 20).map((item) => (
              <article className="admin-item" key={item.id}>
                <p className="title-line">{item.id}</p>
                <p className="muted">vpn_key_id: {item.vpn_key_id}</p>
                <p className="muted">plan_id: {item.plan_id}</p>
                <p className="muted">Статус: {item.status}</p>
                <p className="muted">До: {new Date(item.expires_at).toLocaleString()}</p>
              </article>
            ))}
          </div>
        )}
      </article>

      <article className="glass-card">
        <p className="title-line">Реферальные связи</p>
        {referrals.length === 0 ? (
          <EmptyState title="Рефералов нет" text="Список пока пуст." />
        ) : (
          <div className="stack">
            {referrals.slice(0, 20).map((item) => (
              <article className="admin-item" key={item.id}>
                <p className="muted">referrer: {item.referrer_user_id}</p>
                <p className="muted">referred: {item.referred_user_id}</p>
                <p className="muted">status: {item.status}</p>
              </article>
            ))}
          </div>
        )}
      </article>

      <article className="glass-card">
        <p className="title-line">Системный сброс</p>
        <p className="muted">Мягкий сброс: ключи/подписки/платежи деактивируются, пользователи и тарифы сохраняются.</p>
        <button className="btn btn-danger-soft" onClick={() => void resetKeysAndEarnings()} disabled={softResetLoading}>
          {softResetLoading ? 'Выполняется...' : 'Мягко обнулить ключи и заработок'}
        </button>
      </article>

      {error && <ErrorState text={error} />}
      {message && <div className="toast-success">{message}</div>}
    </section>
  );
}
