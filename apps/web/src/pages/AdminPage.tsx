import {
  BellRing, ChevronDown, ChevronUp, Gift, KeyRound, Link2, RefreshCcw, Search, Send, Settings2,
  Sparkles, Trash2, UserRound, Wallet, Wrench,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { apiRequest } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { ErrorState, SkeletonCards } from '../components/StateCards';
import { StatusBadge } from '../components/StatusBadge';
import { useAuth } from '../context/AuthContext';
import type { Payment, Plan, SystemStatus, VPNKey } from '../types/models';

type AdminStats = { total_payments: number; succeeded_payments: number; pending_payments: number; failed_payments: number; total_revenue: string; month_revenue: string };
type AdminUser = { id: string; referral_code: string; bonus_days_balance: number; created_at: string; telegram_username: string | null; telegram_user_id: number | null; total_keys_count: number };
type AdminReferral = { id: string; referrer_user_id: string; referred_user_id: string; status: string; created_at: string };
type AdminSubscription = { id: string; vpn_key_id: string; plan_id: string; starts_at: string; expires_at: string; status: string };
type AdminPaymentsList = { items: Payment[] };
type AdminPlansList = { items: Plan[] };
type ReferralSettings = { referral_bonus_days: number };
type UserLookup = { id: string; telegram_username: string | null };
type MessageResult = { ok: boolean; target_count: number; duplicate_blocked: boolean; audit_log_id: string | null };
type NotificationQueueStatus = { queue_key: string; pending_count: number };
type AdminLoadResult =
  | { name: string; ok: true; value: unknown }
  | { name: string; ok: false; reason: string };

const statusOptions: Array<{ value: SystemStatus['status']; label: string }> = [
  { value: 'online', label: 'Онлайн' },
  { value: 'degraded', label: 'Есть сбои' },
  { value: 'maintenance', label: 'Техработы' },
  { value: 'panel_unavailable', label: 'Панель недоступна' },
  { value: 'server_unavailable', label: 'Сервер недоступен' },
];

const userLabel = (user: AdminUser) => user.telegram_username ? `@${user.telegram_username}` : user.telegram_user_id ? `tg_${user.telegram_user_id}` : `user_${user.id.slice(0, 8)}`;

export function AdminPage() {
  const { refreshSystemStatus } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [keys, setKeys] = useState<VPNKey[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subscriptions, setSubscriptions] = useState<AdminSubscription[]>([]);
  const [referrals, setReferrals] = useState<AdminReferral[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [referralSettings, setReferralSettings] = useState<ReferralSettings>({ referral_bonus_days: 7 });
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [notificationQueue, setNotificationQueue] = useState<NotificationQueueStatus | null>(null);
  const [expandedUsers, setExpandedUsers] = useState<Record<string, boolean>>({});
  const [search, setSearch] = useState('');
  const [lookupUsername, setLookupUsername] = useState('');
  const [lookupResult, setLookupResult] = useState<UserLookup | null>(null);
  const [bonusTargetId, setBonusTargetId] = useState('');
  const [bonusDays, setBonusDays] = useState(7);
  const [bonusReason, setBonusReason] = useState('Ручное начисление');
  const [grantTargetId, setGrantTargetId] = useState('');
  const [grantPlanId, setGrantPlanId] = useState('');
  const [grantKeyName, setGrantKeyName] = useState('Подарочный ключ');
  const [bindUsername, setBindUsername] = useState('');
  const [bindDisplayName, setBindDisplayName] = useState('');
  const [bindClientUuid, setBindClientUuid] = useState('');
  const [bindInboundId, setBindInboundId] = useState('');
  const [sendText, setSendText] = useState('');
  const [sendUserId, setSendUserId] = useState('');
  const [sendToAll, setSendToAll] = useState(false);
  const [forceSend, setForceSend] = useState(false);
  const [statusValue, setStatusValue] = useState<SystemStatus['status']>('online');
  const [statusMessage, setStatusMessage] = useState('');
  const [maintenanceMode, setMaintenanceMode] = useState(false);
  const [statusShowToAll, setStatusShowToAll] = useState(true);
  const [statusNotifyAll, setStatusNotifyAll] = useState(false);
  const [statusScheduledFor, setStatusScheduledFor] = useState('');
  const [resetMode, setResetMode] = useState<'soft' | 'hard'>('soft');
  const [resetConfirm, setResetConfirm] = useState('');
  const [newPlan, setNewPlan] = useState({ name: '', duration_days: 30, price: '990', currency: 'RUB', is_active: true, sort_order: 0 });
  const [planDrafts, setPlanDrafts] = useState<Record<string, Plan>>({});

  const load = async () => {
    setLoading(true);
    setError(null);
    const requests: Array<{ name: string; run: () => Promise<unknown> }> = [
      { name: 'users', run: () => apiRequest<AdminUser[]>('/admin/users?limit=100') },
      { name: 'keys', run: () => apiRequest<VPNKey[]>('/admin/keys?limit=150') },
      { name: 'payments', run: () => apiRequest<AdminPaymentsList>('/admin/payments?limit=200') },
      { name: 'plans', run: () => apiRequest<AdminPlansList>('/admin/plans') },
      { name: 'subscriptions', run: () => apiRequest<AdminSubscription[]>('/admin/subscriptions?limit=150') },
      { name: 'referrals', run: () => apiRequest<AdminReferral[]>('/admin/referrals?limit=150') },
      { name: 'stats', run: () => apiRequest<AdminStats>('/admin/stats') },
      { name: 'referral_settings', run: () => apiRequest<ReferralSettings>('/admin/settings/referral') },
      { name: 'system_status', run: () => apiRequest<SystemStatus>('/admin/system/status') },
      { name: 'notification_queue', run: () => apiRequest<NotificationQueueStatus>('/admin/system/notification-queue') },
    ];

    try {
      const results = await Promise.all(
        requests.map(async ({ name, run }): Promise<AdminLoadResult> => {
          try {
            return { name, ok: true, value: await run() };
          } catch (err) {
            return {
              name,
              ok: false,
              reason: err instanceof Error ? err.message : 'unknown error',
            };
          }
        }),
      );

      const failed: string[] = [];

      for (const result of results) {
        if (!result.ok) {
          console.warn('[admin] section load failed', { section: result.name, reason: result.reason });
          failed.push(result.name);
          continue;
        }

        switch (result.name) {
          case 'users':
            setUsers(result.value as AdminUser[]);
            break;
          case 'keys':
            setKeys(result.value as VPNKey[]);
            break;
          case 'payments':
            setPayments((result.value as AdminPaymentsList).items);
            break;
          case 'plans': {
            const planItems = (result.value as AdminPlansList).items;
            setPlans(planItems);
            setPlanDrafts(Object.fromEntries(planItems.map((plan) => [plan.id, { ...plan, price: String(plan.price) }])) as Record<string, Plan>);
            break;
          }
          case 'subscriptions':
            setSubscriptions(result.value as AdminSubscription[]);
            break;
          case 'referrals':
            setReferrals(result.value as AdminReferral[]);
            break;
          case 'stats':
            setStats(result.value as AdminStats);
            break;
          case 'referral_settings':
            setReferralSettings(result.value as ReferralSettings);
            break;
          case 'system_status': {
            const sys = result.value as SystemStatus;
            setSystemStatus(sys);
            setStatusValue(sys.status);
            setStatusMessage(sys.message ?? '');
            setMaintenanceMode(sys.maintenance_mode);
            setStatusShowToAll(sys.show_to_all);
            setStatusScheduledFor(sys.scheduled_for ? sys.scheduled_for.slice(0, 16) : '');
            break;
          }
          case 'notification_queue':
            setNotificationQueue(result.value as NotificationQueueStatus);
            break;
          default:
            break;
        }
      }

      if (failed.length === requests.length) {
        setError('Не удалось загрузить админ-панель.');
      } else if (failed.length > 0) {
        setError(`Часть разделов не загрузилась: ${failed.join(', ')}`);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const keysByOwner = useMemo(() => keys.reduce<Record<string, VPNKey[]>>((acc, key) => {
    const ownerId = (key as VPNKey & { owner_id?: string }).owner_id;
    if (ownerId) acc[ownerId] = [...(acc[ownerId] ?? []), key];
    return acc;
  }, {}), [keys]);
  const paymentsByUser = useMemo(() => payments.reduce<Record<string, Payment[]>>((acc, payment) => {
    acc[payment.user_id] = [...(acc[payment.user_id] ?? []), payment];
    return acc;
  }, {}), [payments]);
  const referralsByReferrer = useMemo(() => referrals.reduce<Record<string, AdminReferral[]>>((acc, item) => {
    acc[item.referrer_user_id] = [...(acc[item.referrer_user_id] ?? []), item];
    return acc;
  }, {}), [referrals]);
  const subscriptionsByKey = useMemo(() => Object.fromEntries(subscriptions.map((item) => [item.vpn_key_id, item])), [subscriptions]);
  const filteredUsers = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return users;
    return users.filter((user) => [userLabel(user), user.id, user.referral_code].some((value) => value.toLowerCase().includes(q)));
  }, [search, users]);

  const afterAction = async (text: string) => { setMessage(text); await load(); await refreshSystemStatus(); };
  const updatePlanDraft = (id: string, field: keyof Plan, value: string | number | boolean) => setPlanDrafts((prev) => ({ ...prev, [id]: { ...prev[id], [field]: value } }));

  const lookupUser = async () => {
    try {
      const result = await apiRequest<UserLookup>(`/admin/users/lookup?username=${encodeURIComponent(lookupUsername)}`);
      setLookupResult(result); setBonusTargetId(result.id); setGrantTargetId(result.id); setMessage(`Пользователь ${result.telegram_username ? `@${result.telegram_username}` : result.id} найден.`);
    } catch (err) {
      setLookupResult(null); setError(err instanceof Error ? err.message : 'Пользователь не найден');
    }
  };

  const run = async (fn: () => Promise<void>) => {
    setError(null);
    try { await fn(); } catch (err) { setError(err instanceof Error ? err.message : 'Операция завершилась ошибкой'); }
  };

  if (loading) return <section className="stack"><PageHeader title="Админ-панель" subtitle="Загружаем данные управления" /><SkeletonCards count={5} /></section>;

  return (
    <section className="stack">
      <PageHeader title="Админ-панель" subtitle="Клиенты, статусы сервиса, тарифы и рассылки" />
      {error && <ErrorState text={error} />}

      <div className="stat-grid">
        <article className="glass-card stat-card"><span className="stat-icon"><Wallet size={16} /></span><p className="stat-label">Общая выручка</p><p className="stat-value">{stats?.total_revenue ?? '0'}</p></article>
        <article className="glass-card stat-card"><span className="stat-icon"><Sparkles size={16} /></span><p className="stat-label">Выручка за месяц</p><p className="stat-value">{stats?.month_revenue ?? '0'}</p></article>
        <article className="glass-card stat-card"><span className="stat-icon"><BellRing size={16} /></span><p className="stat-label">Ожидают оплаты</p><p className="stat-value">{stats?.pending_payments ?? 0}</p></article>
        <article className="glass-card stat-card"><span className="stat-icon"><KeyRound size={16} /></span><p className="stat-label">Клиентов</p><p className="stat-value">{users.length}</p></article>
      </div>

      <div className="admin-grid">
        <article className="glass-card admin-section">
          <p className="title-line row-inline"><Settings2 size={16} /> Статус системы</p>
          <div className="input-grid">
            <label className="field"><span className="field-label">Статус</span><select className="input" value={statusValue} onChange={(e) => setStatusValue(e.target.value as SystemStatus['status'])}>{statusOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
            <label className="field"><span className="field-label">Плановое время</span><input className="input" type="datetime-local" value={statusScheduledFor} onChange={(e) => setStatusScheduledFor(e.target.value)} /></label>
          </div>
          <label className="field"><span className="field-label">Сообщение</span><textarea className="input textarea" value={statusMessage} onChange={(e) => setStatusMessage(e.target.value)} /></label>
          <div className="toggle-list">
            <label className="toggle-row"><input type="checkbox" checked={maintenanceMode} onChange={(e) => setMaintenanceMode(e.target.checked)} /><span>Maintenance mode</span></label>
            <label className="toggle-row"><input type="checkbox" checked={statusShowToAll} onChange={(e) => setStatusShowToAll(e.target.checked)} /><span>Показывать всем</span></label>
            <label className="toggle-row"><input type="checkbox" checked={statusNotifyAll} onChange={(e) => setStatusNotifyAll(e.target.checked)} /><span>Отправить уведомление всем</span></label>
          </div>
          <button className="btn btn-primary" onClick={() => void run(async () => {
            await apiRequest<SystemStatus>('/admin/system/status', { method: 'PATCH', body: JSON.stringify({ status: statusValue, message: statusMessage || null, maintenance_mode: maintenanceMode, show_to_all: statusShowToAll, scheduled_for: statusScheduledFor ? new Date(statusScheduledFor).toISOString() : null, send_notification_to_all: statusNotifyAll }) });
            await afterAction('Системный статус обновлён.');
          })}><Wrench size={16} /> Сохранить статус</button>
        </article>

        <article className="glass-card admin-section">
          <p className="title-line row-inline"><Send size={16} /> Рассылка</p>
          <div className="admin-note">
            Очередь уведомлений: <strong>{notificationQueue?.pending_count ?? 0}</strong>
            {notificationQueue?.queue_key ? ` · ${notificationQueue.queue_key}` : ''}
          </div>
          <label className="field"><span className="field-label">Текст сообщения</span><textarea className="input textarea" value={sendText} onChange={(e) => setSendText(e.target.value)} /></label>
          <label className="field"><span className="field-label">ID пользователя</span><input className="input" value={sendUserId} onChange={(e) => setSendUserId(e.target.value)} disabled={sendToAll} placeholder="UUID пользователя" /></label>
          <div className="toggle-list">
            <label className="toggle-row"><input type="checkbox" checked={sendToAll} onChange={(e) => setSendToAll(e.target.checked)} /><span>Отправить всем</span></label>
            <label className="toggle-row"><input type="checkbox" checked={forceSend} onChange={(e) => setForceSend(e.target.checked)} /><span>Игнорировать защиту от дублей</span></label>
          </div>
          <div className="input-grid">
            <button className="btn btn-primary" onClick={() => void run(async () => {
              const result = await apiRequest<MessageResult>('/admin/messages/send', { method: 'POST', body: JSON.stringify({ message: sendText, user_id: sendToAll ? null : sendUserId || null, send_to_all: sendToAll, force: forceSend }) });
              await afterAction(result.duplicate_blocked ? 'Похожая рассылка уже отправлялась недавно.' : `Сообщение поставлено в очередь для ${result.target_count} получателей.`);
            })}><BellRing size={16} /> Отправить</button>
            <button className="btn btn-ghost" onClick={() => void run(async () => {
              const result = await apiRequest<{ ok: boolean; cleared_count: number }>('/admin/system/notification-queue/clear', { method: 'POST', body: JSON.stringify({}) });
              await afterAction(`Очередь очищена. Удалено сообщений: ${result.cleared_count}.`);
            })}><Trash2 size={16} /> Очистить очередь</button>
          </div>
        </article>

        <article className="glass-card admin-section">
          <p className="title-line row-inline"><Gift size={16} /> Рефералы и бонусы</p>
          <label className="field"><span className="field-label">Бонус за приглашение</span><input className="input" type="number" value={referralSettings.referral_bonus_days} onChange={(e) => setReferralSettings({ referral_bonus_days: Number(e.target.value || 0) })} /></label>
          <button className="btn btn-primary" onClick={() => void run(async () => {
            await apiRequest('/admin/settings/referral', { method: 'PATCH', body: JSON.stringify({ referral_bonus_days: referralSettings.referral_bonus_days }) });
            await afterAction('Реферальная награда обновлена.');
          })}><Gift size={16} /> Сохранить награду</button>
          <div className="divider" />
          <label className="field"><span className="field-label">UUID пользователя</span><input className="input" value={bonusTargetId} onChange={(e) => setBonusTargetId(e.target.value)} /></label>
          <div className="input-grid">
            <label className="field"><span className="field-label">Дней</span><input className="input" type="number" value={bonusDays} onChange={(e) => setBonusDays(Number(e.target.value || 0))} /></label>
            <label className="field"><span className="field-label">Причина</span><input className="input" value={bonusReason} onChange={(e) => setBonusReason(e.target.value)} /></label>
          </div>
          <button className="btn btn-ghost" onClick={() => void run(async () => {
            await apiRequest(`/admin/users/${bonusTargetId}/bonus-days`, { method: 'POST', body: JSON.stringify({ days: bonusDays, reason: bonusReason }) });
            await afterAction('Бонусные дни начислены.');
          })}><Sparkles size={16} /> Начислить бонус</button>
        </article>

        <article className="glass-card admin-section">
          <p className="title-line row-inline"><Search size={16} /> Поиск и привязка</p>
          <div className="input-grid">
            <label className="field"><span className="field-label">Поиск по @username</span><input className="input" value={lookupUsername} onChange={(e) => setLookupUsername(e.target.value)} placeholder="@username" /></label>
            <button className="btn btn-ghost" onClick={() => void run(lookupUser)}><Search size={16} /> Найти</button>
          </div>
          {lookupResult && <div className="admin-note">Найден пользователь: {lookupResult.telegram_username ? `@${lookupResult.telegram_username}` : lookupResult.id}</div>}
          <div className="divider" />
          <label className="field"><span className="field-label">@username</span><input className="input" value={bindUsername} onChange={(e) => setBindUsername(e.target.value)} placeholder="@username" /></label>
          <div className="input-grid">
            <label className="field"><span className="field-label">Название ключа</span><input className="input" value={bindDisplayName} onChange={(e) => setBindDisplayName(e.target.value)} placeholder="VPN ключ" /></label>
            <label className="field"><span className="field-label">UUID клиента</span><input className="input" value={bindClientUuid} onChange={(e) => setBindClientUuid(e.target.value)} placeholder="client uuid" /></label>
          </div>
          <label className="field"><span className="field-label">Inbound ID</span><input className="input" value={bindInboundId} onChange={(e) => setBindInboundId(e.target.value)} placeholder="1" /></label>
          <button className="btn btn-primary" onClick={() => void run(async () => {
            await apiRequest('/admin/keys/bind-by-username', { method: 'POST', body: JSON.stringify({ username: bindUsername, display_name: bindDisplayName || null, client_uuid: bindClientUuid || null, inbound_id: bindInboundId ? Number(bindInboundId) : null }) });
            await afterAction('Ключ из панели привязан к пользователю.');
          })}><Link2 size={16} /> Привязать ключ</button>
        </article>
      </div>

      <div className="admin-grid">
        <article className="glass-card admin-section">
          <p className="title-line row-inline"><KeyRound size={16} /> Ручная выдача подписки</p>
          <label className="field"><span className="field-label">UUID пользователя</span><input className="input" value={grantTargetId} onChange={(e) => setGrantTargetId(e.target.value)} /></label>
          <div className="input-grid">
            <label className="field"><span className="field-label">Тариф</span><select className="input" value={grantPlanId} onChange={(e) => setGrantPlanId(e.target.value)}><option value="">Выберите тариф</option>{plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.name} · {plan.price} {plan.currency}</option>)}</select></label>
            <label className="field"><span className="field-label">Название ключа</span><input className="input" value={grantKeyName} onChange={(e) => setGrantKeyName(e.target.value)} /></label>
          </div>
          <button className="btn btn-primary" onClick={() => void run(async () => {
            await apiRequest(`/admin/users/${grantTargetId}/grant-subscription`, { method: 'POST', body: JSON.stringify({ plan_id: grantPlanId, key_name: grantKeyName || null }) });
            await afterAction('Подписка выдана вручную.');
          })}><KeyRound size={16} /> Выдать подписку</button>
        </article>

        <article className="glass-card admin-section">
          <p className="title-line row-inline"><RefreshCcw size={16} /> Сервисные действия</p>
          <button className="btn btn-ghost" onClick={() => void run(async () => { await apiRequest('/admin/system/sync-panel', { method: 'POST', body: JSON.stringify({}) }); await afterAction('Синхронизация с 3x-ui завершена.'); })}><RefreshCcw size={16} /> Синхронизировать с панелью</button>
          <div className="divider" />
          <div className="toggle-list">
            <label className="toggle-row"><input type="radio" checked={resetMode === 'soft'} onChange={() => setResetMode('soft')} /><span>Мягкая зачистка</span></label>
            <label className="toggle-row"><input type="radio" checked={resetMode === 'hard'} onChange={() => setResetMode('hard')} /><span>Полная зачистка</span></label>
          </div>
          <label className="field"><span className="field-label">Подтверждение</span><input className="input" value={resetConfirm} onChange={(e) => setResetConfirm(e.target.value)} placeholder="RESET" /></label>
          <button className="btn btn-danger-soft" onClick={() => void run(async () => {
            await apiRequest('/admin/system/reset-keys-and-earnings', { method: 'POST', body: JSON.stringify({ confirm_text: resetConfirm, mode: resetMode }) });
            await afterAction('Операция сброса выполнена.');
            setResetConfirm('');
          })}><Trash2 size={16} /> Выполнить зачистку</button>
        </article>
      </div>

      <article className="glass-card admin-section">
        <p className="title-line row-inline"><Wallet size={16} /> Тарифы</p>
        <div className="input-grid">
          <input className="input" value={newPlan.name} onChange={(e) => setNewPlan((prev) => ({ ...prev, name: e.target.value }))} placeholder="Название" />
          <input className="input" type="number" value={newPlan.duration_days} onChange={(e) => setNewPlan((prev) => ({ ...prev, duration_days: Number(e.target.value || 0) }))} placeholder="Дней" />
          <input className="input" value={newPlan.price} onChange={(e) => setNewPlan((prev) => ({ ...prev, price: e.target.value }))} placeholder="Цена" />
          <input className="input" value={newPlan.currency} onChange={(e) => setNewPlan((prev) => ({ ...prev, currency: e.target.value }))} placeholder="Валюта" />
        </div>
        <button className="btn btn-primary" onClick={() => void run(async () => {
          await apiRequest('/admin/plans', { method: 'POST', body: JSON.stringify({ ...newPlan, price: Number(newPlan.price) }) });
          await afterAction('Тариф создан.');
          setNewPlan({ name: '', duration_days: 30, price: '990', currency: 'RUB', is_active: true, sort_order: 0 });
        })}><Wallet size={16} /> Создать тариф</button>
        <div className="admin-list">
          {plans.map((plan) => {
            const draft = planDrafts[plan.id] ?? plan;
            return (
              <article className="admin-item" key={plan.id}>
                <div className="input-grid">
                  <input className="input" value={draft.name} onChange={(e) => updatePlanDraft(plan.id, 'name', e.target.value)} />
                  <input className="input" type="number" value={draft.duration_days} onChange={(e) => updatePlanDraft(plan.id, 'duration_days', Number(e.target.value || 0))} />
                  <input className="input" value={String(draft.price)} onChange={(e) => updatePlanDraft(plan.id, 'price', e.target.value)} />
                  <input className="input" value={draft.currency} onChange={(e) => updatePlanDraft(plan.id, 'currency', e.target.value)} />
                </div>
                <div className="row-between">
                  <label className="toggle-row"><input type="checkbox" checked={draft.is_active} onChange={(e) => updatePlanDraft(plan.id, 'is_active', e.target.checked)} /><span>Активен</span></label>
                  <button className="btn btn-ghost" onClick={() => void run(async () => { await apiRequest(`/admin/plans/${plan.id}`, { method: 'PATCH', body: JSON.stringify({ ...draft, price: Number(draft.price) }) }); await afterAction('Тариф обновлён.'); })}>Сохранить</button>
                </div>
              </article>
            );
          })}
        </div>
      </article>

      <article className="glass-card admin-section">
        <p className="title-line row-inline"><UserRound size={16} /> Клиенты</p>
        <label className="field"><span className="field-label">Поиск</span><input className="input" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="@username, user_id, referral code" /></label>
        <div className="admin-list">
          {filteredUsers.map((user) => {
            const expanded = Boolean(expandedUsers[user.id]);
            const userKeys = keysByOwner[user.id] ?? [];
            const userPayments = paymentsByUser[user.id] ?? [];
            const userReferrals = referralsByReferrer[user.id] ?? [];
            return (
              <article className="admin-user-card" key={user.id}>
                <button className="admin-user-header" onClick={() => setExpandedUsers((prev) => ({ ...prev, [user.id]: !prev[user.id] }))}>
                  <div>
                    <p className="title-line">{userLabel(user)}</p>
                    <p className="muted">Ключей: {user.total_keys_count} · Бонус: {user.bonus_days_balance} · Рефералов: {userReferrals.length} · Платежей: {userPayments.length}</p>
                  </div>
                  {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                </button>
                {expanded && (
                  <div className="admin-user-body">
                    <div className="chip-row">
                      <span className="chip">UUID: {user.id.slice(0, 8)}...</span>
                      <span className="chip">Referral: {user.referral_code}</span>
                    </div>
                    {userKeys.map((key) => (
                      <div className="admin-subitem" key={key.id}>
                        <div className="row-between">
                          <div>
                            <p className="title-line">{key.display_name}</p>
                            <p className="muted">{subscriptionsByKey[key.id] ? `Истекает ${new Date(subscriptionsByKey[key.id].expires_at).toLocaleDateString()}` : 'Подписка не найдена'}</p>
                          </div>
                          <StatusBadge status={key.status} />
                        </div>
                        <div className="admin-actions">
                          <button className="btn btn-ghost" onClick={() => setSendUserId(user.id)}>Сообщение</button>
                          <button className="btn btn-ghost" onClick={() => void run(async () => { await apiRequest(`/admin/keys/${key.id}/revoke`, { method: 'POST', body: JSON.stringify({ reason: 'manual_revoke' }) }); await afterAction('Ключ отозван.'); })}>Отозвать</button>
                          <button className="btn btn-danger-soft" onClick={() => void run(async () => { await apiRequest(`/admin/keys/${key.id}`, { method: 'DELETE', body: JSON.stringify({ reason: 'admin_delete_from_history' }) }); await afterAction('Ключ удалён из истории.'); })}>Удалить</button>
                        </div>
                      </div>
                    ))}
                    {!userKeys.length && <p className="muted">У пользователя пока нет ключей.</p>}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      </article>

      <div className="admin-grid">
        <article className="glass-card admin-section">
          <p className="title-line row-inline"><Wallet size={16} /> Платежи</p>
          <div className="admin-list">
            {payments.slice(0, 20).map((payment) => (
              <article className="admin-item" key={payment.id}>
                <div className="row-between">
                  <div><p className="title-line">{payment.amount} {payment.currency}</p><p className="muted">Пользователь: {payment.user_id.slice(0, 8)}... · {payment.status}</p></div>
                  <div className="admin-actions">
                    {payment.status !== 'succeeded' && <button className="btn btn-ghost" onClick={() => void run(async () => { await apiRequest(`/admin/payments/${payment.id}/approve`, { method: 'POST', body: JSON.stringify({ reason: 'manual_approve' }) }); await afterAction('Платёж подтверждён.'); })}>Подтвердить</button>}
                    {payment.status !== 'failed' && payment.status !== 'canceled' && <button className="btn btn-danger-soft" onClick={() => void run(async () => { await apiRequest(`/admin/payments/${payment.id}/reject`, { method: 'POST', body: JSON.stringify({ reason: 'manual_reject' }) }); await afterAction('Платёж отклонён.'); })}>Отклонить</button>}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </article>

        <article className="glass-card admin-section">
          <p className="title-line row-inline"><KeyRound size={16} /> Последние ключи</p>
          <div className="admin-list">
            {keys.slice(0, 20).map((key) => (
              <article className="admin-item" key={key.id}>
                <div className="row-between">
                  <div><p className="title-line">{key.display_name}</p><p className="muted">{key.id.slice(0, 8)}...</p></div>
                  <StatusBadge status={key.status} />
                </div>
              </article>
            ))}
          </div>
        </article>
      </div>

      {message && <div className="toast-success">{message}</div>}
    </section>
  );
}
