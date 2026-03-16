import {
  BellRing, ChevronDown, ChevronUp, Gift, KeyRound, Link2, RefreshCcw, Search, Send, Settings2,
  Sparkles, Trash2, UserRound, Wallet, Wrench,
} from 'lucide-react';
import { useEffect, useMemo, useState, type ChangeEvent, type ReactNode } from 'react';

import { apiRequest } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { ErrorState, SkeletonCards } from '../components/StateCards';
import { StatusBadge } from '../components/StatusBadge';
import { useAuth } from '../context/AuthContext';
import type { NewsItem, Payment, PaymentSettings, Plan, SystemStatus, TelegramProxyItem, VPNKey } from '../types/models';

type AdminStats = { total_payments: number; succeeded_payments: number; pending_payments: number; failed_payments: number; total_revenue: string; month_revenue: string };
type AdminUser = {
  id: string;
  referral_code: string;
  bonus_days_balance: number;
  created_at: string;
  telegram_username: string | null;
  telegram_user_id: number | null;
  total_keys_count: number;
  has_used_free_trial: boolean;
  has_active_free_trial: boolean;
};
type AdminReferral = { id: string; referrer_user_id: string; referred_user_id: string; status: string; created_at: string };
type AdminSubscription = { id: string; vpn_key_id: string; plan_id: string; starts_at: string; expires_at: string; status: string };
type AdminPaymentsList = { items: Payment[] };
type AdminPlansList = { items: Plan[] };
type ReferralSettings = { referral_bonus_days: number };
type UserLookup = { id: string; telegram_username: string | null };
type MessageResult = { ok: boolean; target_count: number; duplicate_blocked: boolean; audit_log_id: string | null };
type NotificationQueueStatus = { queue_key: string; pending_count: number };
type PaymentSettingsState = PaymentSettings;
type TelegramProxySettings = { proxy_url: string | null; button_text: string; enabled: boolean; proxies: TelegramProxyItem[] };
type AdminInbound = { id: number; remark: string | null; protocol: string | null; port: number | null };
type PurchaseInboundSettings = { inbound_ids: number[] };
type FreeTrialSettings = { enabled: boolean; days: number; inbound_ids: number[] };
type DeleteUserResult = {
  ok: boolean;
  user_id: string;
  deleted_keys_count: number;
  deleted_payments_count: number;
  deleted_referrals_count: number;
};
type AdminLoadResult =
  | { name: string; ok: true; value: unknown }
  | { name: string; ok: false; reason: string };

const statusOptions: Array<{ value: SystemStatus['status']; label: string }> = [
  { value: 'online', label: 'Онлайн' },
  { value: 'degraded', label: 'Есть сбои' },
  { value: 'maintenance', label: 'Технические работы' },
  { value: 'panel_unavailable', label: 'Сервис выдачи недоступен' },
  { value: 'server_unavailable', label: 'Сервер недоступен' },
];

const userLabel = (user: AdminUser) => user.telegram_username ? `@${user.telegram_username}` : user.telegram_user_id ? `tg_${user.telegram_user_id}` : `user_${user.id.slice(0, 8)}`;

function FoldableSection({
  title,
  subtitle,
  icon,
  defaultOpen = true,
  children,
}: {
  title: string;
  subtitle?: string;
  icon: ReactNode;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  return (
    <details className="glass-card admin-section foldable" open={defaultOpen}>
      <summary className="foldable-summary">
        <div>
          <p className="title-line row-inline">{icon} {title}</p>
          {subtitle && <p className="muted">{subtitle}</p>}
        </div>
        <ChevronDown size={18} className="foldable-arrow" />
      </summary>
      <div className="foldable-body">
        {children}
      </div>
    </details>
  );
}

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
  const [paymentSettings, setPaymentSettings] = useState<PaymentSettingsState>({ enabled: true, mode: 'direct' });
  const [telegramProxy, setTelegramProxy] = useState<TelegramProxySettings>({ proxy_url: null, button_text: 'Подключить прокси', enabled: false, proxies: [] });
  const [newsItems, setNewsItems] = useState<NewsItem[]>([]);
  const [availableInbounds, setAvailableInbounds] = useState<AdminInbound[]>([]);
  const [purchaseInboundIds, setPurchaseInboundIds] = useState<number[]>([]);
  const [freeTrialSettings, setFreeTrialSettings] = useState<FreeTrialSettings>({ enabled: false, days: 3, inbound_ids: [] });
  const [expandedUsers, setExpandedUsers] = useState<Record<string, boolean>>({});
  const [showCompletedPayments, setShowCompletedPayments] = useState(false);
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
  const [sendImageDataUrl, setSendImageDataUrl] = useState<string | null>(null);
  const [sendImageFilename, setSendImageFilename] = useState<string | null>(null);
  const [publishAsNews, setPublishAsNews] = useState(false);
  const [newsTitle, setNewsTitle] = useState('');
  const [statusValue, setStatusValue] = useState<SystemStatus['status']>('online');
  const [statusMessage, setStatusMessage] = useState('');
  const [maintenanceMode, setMaintenanceMode] = useState(false);
  const [statusShowToAll, setStatusShowToAll] = useState(true);
  const [statusNotifyAll, setStatusNotifyAll] = useState(false);
  const [statusScheduledFor, setStatusScheduledFor] = useState('');
  const [resetMode, setResetMode] = useState<'soft' | 'hard'>('soft');
  const [resetConfirm, setResetConfirm] = useState('');
  const [newPlan, setNewPlan] = useState({ name: '', duration_days: 30, price: '990', currency: 'RUB', is_active: true, sort_order: 0, inbound_ids: [] as number[] });
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
      { name: 'payment_settings', run: () => apiRequest<PaymentSettingsState>('/admin/system/payments') },
      { name: 'telegram_proxy', run: () => apiRequest<TelegramProxySettings>('/admin/system/telegram-proxy') },
      { name: 'system_news', run: () => apiRequest<{ items: NewsItem[] }>('/system/news') },
      { name: 'inbounds', run: () => apiRequest<AdminInbound[]>('/admin/system/inbounds') },
      { name: 'purchase_inbounds', run: () => apiRequest<PurchaseInboundSettings>('/admin/system/purchase-inbounds') },
      { name: 'free_trial', run: () => apiRequest<FreeTrialSettings>('/admin/system/free-trial') },
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
          case 'payment_settings':
            setPaymentSettings(result.value as PaymentSettingsState);
            break;
          case 'telegram_proxy':
            setTelegramProxy(result.value as TelegramProxySettings);
            break;
          case 'system_news':
            setNewsItems((result.value as { items: NewsItem[] }).items);
            break;
          case 'inbounds':
            setAvailableInbounds(result.value as AdminInbound[]);
            break;
          case 'purchase_inbounds':
            setPurchaseInboundIds((result.value as PurchaseInboundSettings).inbound_ids);
            break;
          case 'free_trial':
            setFreeTrialSettings(result.value as FreeTrialSettings);
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
  const pendingPayments = useMemo(
    () => payments.filter((payment) => payment.status === 'pending' || payment.status === 'waiting_for_capture'),
    [payments],
  );
  const completedPayments = useMemo(
    () => payments.filter((payment) => payment.status !== 'pending' && payment.status !== 'waiting_for_capture'),
    [payments],
  );
  const filteredUsers = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return users;
    return users.filter((user) => [userLabel(user), user.id, user.referral_code].some((value) => value.toLowerCase().includes(q)));
  }, [search, users]);
  const trialUsers = useMemo(() => filteredUsers.filter((user) => user.has_active_free_trial), [filteredUsers]);
  const regularUsers = useMemo(() => filteredUsers.filter((user) => !user.has_active_free_trial), [filteredUsers]);

  const afterAction = async (text: string) => { setMessage(text); await load(); await refreshSystemStatus(); };
  const updatePlanDraft = (id: string, field: keyof Plan, value: string | number | boolean | number[]) => setPlanDrafts((prev) => ({ ...prev, [id]: { ...prev[id], [field]: value } }));
  const getSelectedInboundIds = (event: ChangeEvent<HTMLSelectElement>) =>
    Array.from(event.target.selectedOptions).map((option) => Number(option.value)).filter((value) => Number.isFinite(value));
  const inboundLabel = (inbound: AdminInbound) => [inbound.remark || `Inbound ${inbound.id}`, inbound.protocol, inbound.port ? `:${inbound.port}` : null].filter(Boolean).join(' ');

  const addProxyDraft = () => setTelegramProxy((prev) => ({
    ...prev,
    proxies: [...prev.proxies, { id: crypto.randomUUID(), country: '', proxy_url: null, button_text: prev.button_text || 'Подключить прокси', enabled: false }],
  }));

  const updateProxyDraft = (id: string, field: keyof TelegramProxyItem, value: string) => setTelegramProxy((prev) => ({
    ...prev,
    proxies: prev.proxies.map((item) => item.id === id
      ? { ...item, [field]: value, enabled: field === 'proxy_url' ? Boolean(value.trim()) : item.enabled }
      : item),
  }));

  const removeProxyDraft = (id: string) => setTelegramProxy((prev) => ({
    ...prev,
    proxies: prev.proxies.filter((item) => item.id !== id),
  }));

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

  const deleteUser = async (user: AdminUser) => {
    const label = userLabel(user);
    const confirmation = window.prompt(`Удаление необратимо.\n\nБудут удалены пользователь, его ключи, платежи и связанные записи.\n\nЧтобы продолжить, введите УДАЛИТЬ`);
    if (confirmation?.trim().toUpperCase() !== 'УДАЛИТЬ') {
      return;
    }

    await run(async () => {
      const result = await apiRequest<DeleteUserResult>(`/admin/users/${user.id}`, {
        method: 'DELETE',
        body: JSON.stringify({ reason: `manual_delete_user:${label}` }),
      });
      await afterAction(
        `Пользователь удалён. Ключей: ${result.deleted_keys_count}, платежей: ${result.deleted_payments_count}, рефералов: ${result.deleted_referrals_count}.`,
      );
    });
  };

  const resetFreeTrial = async (user: AdminUser) => {
    await run(async () => {
      const result = await apiRequest<{ ok: boolean; deleted_logs_count: number }>(`/admin/users/${user.id}/reset-free-trial`, {
        method: 'POST',
      });
      await afterAction(`Счётчик пробного периода сброшен. Удалено записей: ${result.deleted_logs_count}.`);
    });
  };

  const renderUserCards = (list: AdminUser[]) => (
    <div className="admin-list">
      {list.map((user) => {
        const expanded = Boolean(expandedUsers[user.id]);
        const userKeys = keysByOwner[user.id] ?? [];
        const userPayments = paymentsByUser[user.id] ?? [];
        const userReferrals = referralsByReferrer[user.id] ?? [];
        return (
          <article className={`admin-user-card${user.has_active_free_trial ? ' admin-user-card--trial' : ''}`} key={user.id}>
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
                  {user.has_active_free_trial && <span className="chip chip-danger">Активный trial</span>}
                  {!user.has_active_free_trial && user.has_used_free_trial && <span className="chip chip-danger">Trial использован</span>}
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
                <p className="muted">Удаление пользователя стирает его аккаунт, ключи, платежи и связанные записи без возможности восстановления.</p>
                <div className="admin-actions">
                  <button className="btn btn-ghost" onClick={() => void resetFreeTrial(user)}>
                    Сбросить trial
                  </button>
                  <button className="btn btn-danger-soft" onClick={() => void deleteUser(user)}>
                    <Trash2 size={16} /> Удалить пользователя
                  </button>
                </div>
              </div>
            )}
          </article>
        );
      })}
    </div>
  );

  const handleMessageImageChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      setSendImageDataUrl(null);
      setSendImageFilename(null);
      return;
    }

    if (file.size > 4 * 1024 * 1024) {
      setError('Фотография слишком большая. Выберите изображение до 4 МБ.');
      event.target.value = '';
      return;
    }

    const reader = new FileReader();
    const result = await new Promise<string>((resolve, reject) => {
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(new Error('Не удалось прочитать изображение'));
      reader.readAsDataURL(file);
    });

    setSendImageDataUrl(result);
    setSendImageFilename(file.name);
    setMessage(`Фотография прикреплена: ${file.name}`);
  };

  if (loading) return <section className="stack"><PageHeader title="Управление ZERO" subtitle="Загружаем клиентов, тарифы и служебные настройки" /><SkeletonCards count={5} /></section>;

  return (
      <section className="stack">
      <PageHeader title="Управление ZERO" subtitle="Клиенты, тарифы, статусы сервиса и рассылки в одном экране" />
      {error && <ErrorState text={error} />}

      <div className="stat-grid">
        <article className="glass-card stat-card"><span className="stat-icon"><Wallet size={16} /></span><p className="stat-label">Общая выручка</p><p className="stat-value">{stats?.total_revenue ?? '0'}</p></article>
        <article className="glass-card stat-card"><span className="stat-icon"><Sparkles size={16} /></span><p className="stat-label">Выручка за месяц</p><p className="stat-value">{stats?.month_revenue ?? '0'}</p></article>
        <article className="glass-card stat-card"><span className="stat-icon"><BellRing size={16} /></span><p className="stat-label">Ожидают оплаты</p><p className="stat-value">{stats?.pending_payments ?? 0}</p></article>
        <article className="glass-card stat-card"><span className="stat-icon"><KeyRound size={16} /></span><p className="stat-label">Клиентов</p><p className="stat-value">{users.length}</p></article>
      </div>

      <div className="admin-grid">
        <FoldableSection title="Статус системы" subtitle="Публичный статус, ограничения и режим обслуживания" icon={<Settings2 size={16} />}>
          <div className="input-grid">
            <label className="field"><span className="field-label">Статус</span><select className="input" value={statusValue} onChange={(e) => setStatusValue(e.target.value as SystemStatus['status'])}>{statusOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
            <label className="field"><span className="field-label">Плановое время</span><input className="input" type="datetime-local" value={statusScheduledFor} onChange={(e) => setStatusScheduledFor(e.target.value)} /></label>
          </div>
          <label className="field"><span className="field-label">Сообщение</span><textarea className="input textarea" value={statusMessage} onChange={(e) => setStatusMessage(e.target.value)} /></label>
          <div className="toggle-list">
            <label className="toggle-row"><input type="checkbox" checked={maintenanceMode} onChange={(e) => setMaintenanceMode(e.target.checked)} /><span>Режим обслуживания</span></label>
            <label className="toggle-row"><input type="checkbox" checked={statusShowToAll} onChange={(e) => setStatusShowToAll(e.target.checked)} /><span>Показывать всем</span></label>
            <label className="toggle-row"><input type="checkbox" checked={statusNotifyAll} onChange={(e) => setStatusNotifyAll(e.target.checked)} /><span>Отправить уведомление всем</span></label>
          </div>
          <button className="btn btn-primary" onClick={() => void run(async () => {
            await apiRequest<SystemStatus>('/admin/system/status', { method: 'PATCH', body: JSON.stringify({ status: statusValue, message: statusMessage || null, maintenance_mode: maintenanceMode, show_to_all: statusShowToAll, scheduled_for: statusScheduledFor ? new Date(statusScheduledFor).toISOString() : null, send_notification_to_all: statusNotifyAll }) });
            await afterAction('Системный статус обновлён.');
          })}><Wrench size={16} /> Сохранить статус</button>
        </FoldableSection>

        <FoldableSection title="Платежи ZERO" subtitle="Управление выдачей реквизитов внутри мини-приложения" icon={<Wallet size={16} />} defaultOpen={false}>
          <div className="admin-note">
            Когда прямые платежи выключены, ZERO не показывает номер для перевода. Пользователь создаёт заявку и продолжает оплату через администратора.
          </div>
          <div className="toggle-list">
            <label className="toggle-row"><input type="checkbox" checked={paymentSettings.enabled} onChange={(e) => setPaymentSettings((prev) => ({ ...prev, enabled: e.target.checked }))} /><span>{paymentSettings.enabled ? 'Прямые платежи включены' : 'Оплата через администратора'}</span></label>
          </div>
          <button className="btn btn-primary" onClick={() => void run(async () => {
            const updated = await apiRequest<PaymentSettingsState>('/admin/system/payments', {
              method: 'PATCH',
              body: JSON.stringify({ enabled: paymentSettings.enabled }),
            });
            setPaymentSettings(updated);
            await afterAction(updated.enabled ? 'Прямые реквизиты снова доступны пользователям.' : 'Прямые платежи выключены. Теперь заявки ведут пользователей к администратору.');
          })}><Wallet size={16} /> Сохранить режим оплаты</button>
        </FoldableSection>

        <FoldableSection title="Рассылка" subtitle="Сообщения пользователям и очередь уведомлений" icon={<Send size={16} />}>
          <div className="admin-note">
            Очередь уведомлений: <strong>{notificationQueue?.pending_count ?? 0}</strong>
            {notificationQueue?.queue_key ? ` · ${notificationQueue.queue_key}` : ''}
          </div>
          <label className="field"><span className="field-label">Текст сообщения</span><textarea className="input textarea" value={sendText} onChange={(e) => setSendText(e.target.value)} /></label>
          <label className="field">
            <span className="field-label">Фотография</span>
            <input className="input" type="file" accept="image/*" onChange={(e) => void handleMessageImageChange(e)} />
          </label>
          {sendImageFilename && (
            <div className="admin-note">
              Прикреплено: <strong>{sendImageFilename}</strong>
            </div>
          )}
          <label className="field"><span className="field-label">ID пользователя</span><input className="input" value={sendUserId} onChange={(e) => setSendUserId(e.target.value)} disabled={sendToAll} placeholder="UUID пользователя" /></label>
          <div className="toggle-list">
            <label className="toggle-row"><input type="checkbox" checked={sendToAll} onChange={(e) => setSendToAll(e.target.checked)} /><span>Отправить всем</span></label>
            <label className="toggle-row"><input type="checkbox" checked={forceSend} onChange={(e) => setForceSend(e.target.checked)} /><span>Игнорировать защиту от дублей</span></label>
            <label className="toggle-row"><input type="checkbox" checked={publishAsNews} onChange={(e) => setPublishAsNews(e.target.checked)} /><span>Опубликовать как новость</span></label>
          </div>
          {publishAsNews && (
            <label className="field">
              <span className="field-label">Заголовок новости</span>
              <input className="input" value={newsTitle} onChange={(e) => setNewsTitle(e.target.value)} placeholder="Например: Новое обновление" />
            </label>
          )}
          <div className="input-grid">
            <button className="btn btn-primary" onClick={() => void run(async () => {
              const result = await apiRequest<MessageResult>('/admin/messages/send', {
                method: 'POST',
                body: JSON.stringify({
                  message: sendText,
                  user_id: sendToAll ? null : sendUserId || null,
                  send_to_all: sendToAll,
                  force: forceSend,
                  image_data_url: sendImageDataUrl,
                  image_filename: sendImageFilename,
                  publish_as_news: publishAsNews,
                  news_title: publishAsNews ? newsTitle || null : null,
                }),
              });
              setSendText('');
              setSendImageDataUrl(null);
              setSendImageFilename(null);
              setPublishAsNews(false);
              setNewsTitle('');
              const successText = publishAsNews
                ? result.target_count > 0
                  ? `Новость опубликована и поставлена в очередь для ${result.target_count} получателей.`
                  : 'Новость опубликована в личном кабинете.'
                : result.duplicate_blocked
                  ? 'Похожая рассылка уже отправлялась недавно.'
                  : `Сообщение поставлено в очередь для ${result.target_count} получателей.`;
              await afterAction(successText);
            })}><BellRing size={16} /> Отправить</button>
            <button className="btn btn-ghost" onClick={() => { setSendImageDataUrl(null); setSendImageFilename(null); }}>
              Убрать фото
            </button>
            <button className="btn btn-ghost" onClick={() => void run(async () => {
              const result = await apiRequest<{ ok: boolean; cleared_count: number }>('/admin/system/notification-queue/clear', { method: 'POST', body: JSON.stringify({}) });
              await afterAction(`Очередь очищена. Удалено сообщений: ${result.cleared_count}.`);
            })}><Trash2 size={16} /> Очистить очередь</button>
          </div>
        </FoldableSection>

        <FoldableSection title="Управление новостями" subtitle="Удаление опубликованных новостей из раздела пользователей" icon={<BellRing size={16} />} defaultOpen={false}>
          {!newsItems.length ? (
            <p className="muted">Опубликованных новостей пока нет.</p>
          ) : (
            <div className="admin-list">
              {newsItems.map((item) => (
                <article key={item.id} className="admin-item">
                  <div className="row-between">
                    <div>
                      <p className="title-line">{item.title}</p>
                      <p className="muted">{new Date(item.created_at).toLocaleString()}</p>
                    </div>
                    <button className="btn btn-danger-soft" onClick={() => void run(async () => {
                      await apiRequest(`/admin/system/news/${item.id}`, { method: "DELETE" });
                      await afterAction("Новость удалена.");
                    })}>
                      <Trash2 size={16} /> Удалить
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </FoldableSection>

        <FoldableSection title="Telegram-прокси" subtitle="Несколько прокси с выбором страны для пользователя" icon={<Link2 size={16} />} defaultOpen={false}>
          <div className="admin-note">
            Ссылки хранятся на сервере в настройках приложения и не зашиваются в код репозитория.
          </div>
          <div className="admin-list">
            {telegramProxy.proxies.map((proxy, index) => (
              <article key={proxy.id} className="admin-item">
                <div className="row-between">
                  <div>
                    <p className="title-line">Прокси {index + 1}</p>
                    <p className="muted">Пользователь увидит эту страну при выборе подключения.</p>
                  </div>
                  <button className="btn btn-danger-soft" onClick={() => removeProxyDraft(proxy.id)}>
                    <Trash2 size={16} /> Удалить
                  </button>
                </div>
                <div className="input-grid">
                  <label className="field">
                    <span className="field-label">Страна</span>
                    <input className="input" value={proxy.country} onChange={(e) => updateProxyDraft(proxy.id, "country", e.target.value)} placeholder="Например: Германия" />
                  </label>
                  <label className="field">
                    <span className="field-label">Текст кнопки</span>
                    <input className="input" value={proxy.button_text} onChange={(e) => updateProxyDraft(proxy.id, "button_text", e.target.value)} placeholder="Подключить прокси" />
                  </label>
                </div>
                <label className="field">
                  <span className="field-label">Ссылка прокси</span>
                  <input className="input" type="password" value={proxy.proxy_url ?? ""} onChange={(e) => updateProxyDraft(proxy.id, "proxy_url", e.target.value)} placeholder="tg://proxy?server=..." />
                </label>
              </article>
            ))}
          </div>
          <div className="input-grid">
            <button className="btn btn-ghost" onClick={addProxyDraft}>
              <Link2 size={16} /> Добавить прокси
            </button>
            <button className="btn btn-primary" onClick={() => void run(async () => {
              const prepared = telegramProxy.proxies
                .map((item) => ({
                  ...item,
                  country: item.country.trim(),
                  proxy_url: item.proxy_url?.trim() || null,
                  button_text: item.button_text.trim() || "Подключить прокси",
                }))
                .filter((item) => item.country && item.proxy_url);
              const updated = await apiRequest<TelegramProxySettings>("/admin/system/telegram-proxy", {
                method: "PATCH",
                body: JSON.stringify({
                  proxy_url: prepared[0]?.proxy_url ?? null,
                  button_text: prepared[0]?.button_text ?? "Подключить прокси",
                  proxies: prepared,
                }),
              });
              setTelegramProxy(updated);
              await afterAction("Настройки Telegram-прокси сохранены.");
            })}>
              <Link2 size={16} /> Сохранить прокси
            </button>
            <button className="btn btn-danger-soft" onClick={() => void run(async () => {
              const updated = await apiRequest<TelegramProxySettings>("/admin/system/telegram-proxy", {
                method: "PATCH",
                body: JSON.stringify({ proxy_url: null, button_text: "Подключить прокси", proxies: [] }),
              });
              setTelegramProxy(updated);
              await afterAction("Telegram-прокси отключены.");
            })}>
              <Trash2 size={16} /> Отключить все
            </button>
          </div>
        </FoldableSection>

        <FoldableSection title="Рефералы и бонусы" subtitle="Награда за приглашения и ручные начисления" icon={<Gift size={16} />} defaultOpen={false}>
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
        </FoldableSection>

        <FoldableSection title="Поиск и привязка" subtitle="Поиск по Telegram и привязка уже существующего ключа" icon={<Search size={16} />} defaultOpen={false}>
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
          <label className="field">
            <span className="field-label">Inbound</span>
            <select className="input" value={bindInboundId} onChange={(e) => setBindInboundId(e.target.value)}>
              <option value="">Автоматически определить</option>
              {availableInbounds.map((inbound) => (
                <option key={inbound.id} value={String(inbound.id)}>{inboundLabel(inbound)}</option>
              ))}
            </select>
          </label>
          <button className="btn btn-primary" onClick={() => void run(async () => {
            await apiRequest('/admin/keys/bind-by-username', { method: 'POST', body: JSON.stringify({ username: bindUsername, display_name: bindDisplayName || null, client_uuid: bindClientUuid || null, inbound_id: bindInboundId ? Number(bindInboundId) : null }) });
            await afterAction('Импортированный ключ привязан к пользователю.');
          })}><Link2 size={16} /> Привязать ключ</button>
        </FoldableSection>
      </div>

      <div className="admin-grid">
        <FoldableSection title="Ручная выдача подписки" subtitle="Выдача доступа без новой оплаты" icon={<KeyRound size={16} />} defaultOpen={false}>
          <label className="field"><span className="field-label">UUID пользователя</span><input className="input" value={grantTargetId} onChange={(e) => setGrantTargetId(e.target.value)} /></label>
          <div className="input-grid">
            <label className="field"><span className="field-label">Тариф</span><select className="input" value={grantPlanId} onChange={(e) => setGrantPlanId(e.target.value)}><option value="">Выберите тариф</option>{plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.name} · {plan.price} {plan.currency}</option>)}</select></label>
            <label className="field"><span className="field-label">Название ключа</span><input className="input" value={grantKeyName} onChange={(e) => setGrantKeyName(e.target.value)} /></label>
          </div>
          <button className="btn btn-primary" onClick={() => void run(async () => {
            await apiRequest(`/admin/users/${grantTargetId}/grant-subscription`, { method: 'POST', body: JSON.stringify({ plan_id: grantPlanId, key_name: grantKeyName || null }) });
            await afterAction('Подписка выдана вручную.');
          })}><KeyRound size={16} /> Выдать подписку</button>
        </FoldableSection>

        <FoldableSection title="Сервисные действия" subtitle="Синхронизация ключей, мягкая и полная зачистка" icon={<RefreshCcw size={16} />} defaultOpen={false}>
          <button className="btn btn-ghost" onClick={() => void run(async () => { await apiRequest('/admin/system/sync-panel', { method: 'POST', body: JSON.stringify({}) }); await afterAction('Синхронизация ключей завершена.'); })}><RefreshCcw size={16} /> Синхронизировать ключи</button>
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
        </FoldableSection>
      </div>

      <FoldableSection title="Тарифы" subtitle="Создание и редактирование доступных планов" icon={<Wallet size={16} />} defaultOpen={false}>
        <div className="input-grid">
          <input className="input" value={newPlan.name} onChange={(e) => setNewPlan((prev) => ({ ...prev, name: e.target.value }))} placeholder="Название" />
          <input className="input" type="number" value={newPlan.duration_days} onChange={(e) => setNewPlan((prev) => ({ ...prev, duration_days: Number(e.target.value || 0) }))} placeholder="Дней" />
          <input className="input" value={newPlan.price} onChange={(e) => setNewPlan((prev) => ({ ...prev, price: e.target.value }))} placeholder="Цена" />
          <input className="input" value={newPlan.currency} onChange={(e) => setNewPlan((prev) => ({ ...prev, currency: e.target.value }))} placeholder="Валюта" />
        </div>
        <label className="field">
          <span className="field-label">Inbound'ы тарифа</span>
          <select className="input" multiple value={newPlan.inbound_ids.map(String)} onChange={(e) => setNewPlan((prev) => ({ ...prev, inbound_ids: getSelectedInboundIds(e) }))}>
            {availableInbounds.map((inbound) => (
              <option key={inbound.id} value={inbound.id}>{inboundLabel(inbound)}</option>
            ))}
          </select>
        </label>
        <button className="btn btn-primary" onClick={() => void run(async () => {
          await apiRequest('/admin/plans', { method: 'POST', body: JSON.stringify({ ...newPlan, price: Number(newPlan.price) }) });
          await afterAction('Тариф создан. Новые подписки по нему будут сразу попадать в выбранные inbound’ы.');
          setNewPlan({ name: '', duration_days: 30, price: '990', currency: 'RUB', is_active: true, sort_order: 0, inbound_ids: [] });
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
                <label className="field">
                  <span className="field-label">Inbound'ы тарифа</span>
                  <select className="input" multiple value={(draft.inbound_ids ?? []).map(String)} onChange={(e) => updatePlanDraft(plan.id, 'inbound_ids', getSelectedInboundIds(e))}>
                    {availableInbounds.map((inbound) => (
                      <option key={inbound.id} value={inbound.id}>{inboundLabel(inbound)}</option>
                    ))}
                  </select>
                </label>
                <div className="row-between plan-actions-row">
                  <label className="toggle-row"><input type="checkbox" checked={draft.is_active} onChange={(e) => updatePlanDraft(plan.id, 'is_active', e.target.checked)} /><span>Активен</span></label>
                  <div className="admin-actions">
                    <button className="btn btn-ghost" onClick={() => void run(async () => { await apiRequest(`/admin/plans/${plan.id}`, { method: 'PATCH', body: JSON.stringify({ ...draft, price: Number(draft.price) }) }); await afterAction('Тариф обновлён. Активные клиенты этого тарифа автоматически досинхронизированы в новые inbound’ы.'); })}>Сохранить</button>
                    <button className="btn btn-danger-soft" onClick={() => void run(async () => {
                      const confirmed = window.confirm(`Удалить тариф «${draft.name}»? Это доступно только если по нему ещё не было оплат и подписок.`);
                      if (!confirmed) return;
                      await apiRequest<{ ok: boolean; plan_id: string }>(`/admin/plans/${plan.id}`, { method: 'DELETE' });
                      await afterAction('Тариф удалён.');
                    })}>Удалить</button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </FoldableSection>

      <FoldableSection title="Клиенты" subtitle="Раскрывающиеся карточки пользователей, ключей и быстрых действий" icon={<UserRound size={16} />}>
        <label className="field"><span className="field-label">Поиск</span><input className="input" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="@username, user_id, referral code" /></label>
        {trialUsers.length > 0 && (
          <>
            <div className="admin-note admin-note-danger">Пользователи с активным пробным доступом</div>
            {renderUserCards(trialUsers)}
            <div className="divider" />
          </>
        )}
        {renderUserCards(regularUsers)}
      </FoldableSection>

      <div className="admin-grid">
        <FoldableSection title="Платежи" subtitle="Активные запросы сверху, завершённые операции ниже" icon={<Wallet size={16} />}>
          <div className="row-between">
            <button className="btn btn-ghost" onClick={() => void run(async () => {
              const result = await apiRequest<{ ok: boolean; deleted_count: number }>('/admin/payments/clear-history', { method: 'POST', body: JSON.stringify({}) });
              await afterAction(`\u0418\u0441\u0442\u043e\u0440\u0438\u044f \u0437\u0430\u0432\u0435\u0440\u0448\u0451\u043d\u043d\u044b\u0445 \u043f\u043b\u0430\u0442\u0435\u0436\u0435\u0439 \u043e\u0447\u0438\u0449\u0435\u043d\u0430: ${result.deleted_count}.`);
            })}>{'\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c \u0438\u0441\u0442\u043e\u0440\u0438\u044e'}</button>
          </div>
          <div className="admin-note">{'\u0410\u043a\u0442\u0438\u0432\u043d\u044b\u0435 \u0437\u0430\u043f\u0440\u043e\u0441\u044b \u0432\u0441\u0435\u0433\u0434\u0430 \u0441\u0432\u0435\u0440\u0445\u0443. \u0417\u0430\u0432\u0435\u0440\u0448\u0451\u043d\u043d\u044b\u0435 \u043f\u043b\u0430\u0442\u0435\u0436\u0438 \u043c\u043e\u0436\u043d\u043e \u043e\u0442\u043a\u0440\u044b\u0442\u044c \u043d\u0438\u0436\u0435 \u0438\u043b\u0438 \u043e\u0447\u0438\u0441\u0442\u0438\u0442\u044c \u043e\u0434\u043d\u043e\u0439 \u043a\u043d\u043e\u043f\u043a\u043e\u0439.'}</div>
          <div className="admin-list">
            {pendingPayments.slice(0, 20).map((payment) => (
              <article className="admin-item" key={payment.id}>
                <div className="row-between">
                  <div><p className="title-line">{payment.amount} {payment.currency}</p><p className="muted">{'\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c:'} {payment.user_id.slice(0, 8)}... {'\u00b7'} {payment.status}</p></div>
                  <div className="admin-actions">
                    {payment.status !== 'succeeded' && <button className="btn btn-ghost" onClick={() => void run(async () => { await apiRequest(`/admin/payments/${payment.id}/approve`, { method: 'POST', body: JSON.stringify({ reason: 'manual_approve' }) }); await afterAction('\u041f\u043b\u0430\u0442\u0451\u0436 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0451\u043d.'); })}>{'\u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0434\u0438\u0442\u044c'}</button>}
                    {payment.status !== 'failed' && payment.status !== 'canceled' && <button className="btn btn-danger-soft" onClick={() => void run(async () => { await apiRequest(`/admin/payments/${payment.id}/reject`, { method: 'POST', body: JSON.stringify({ reason: 'manual_reject' }) }); await afterAction('\u041f\u043b\u0430\u0442\u0451\u0436 \u043e\u0442\u043a\u043b\u043e\u043d\u0451\u043d.'); })}>{'\u041e\u0442\u043a\u043b\u043e\u043d\u0438\u0442\u044c'}</button>}
                  </div>
                </div>
              </article>
            ))}
            {!pendingPayments.length && <p className="muted">{'\u0421\u0435\u0439\u0447\u0430\u0441 \u043d\u0435\u0442 \u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0445 \u0437\u0430\u043f\u0440\u043e\u0441\u043e\u0432 \u043d\u0430 \u043e\u043f\u043b\u0430\u0442\u0443.'}</p>}
          </div>
          <button className="btn btn-ghost" onClick={() => setShowCompletedPayments((prev) => !prev)}>
            {showCompletedPayments ? '\u0421\u043a\u0440\u044b\u0442\u044c \u0437\u0430\u0432\u0435\u0440\u0448\u0451\u043d\u043d\u044b\u0435 \u043f\u043b\u0430\u0442\u0435\u0436\u0438' : `\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u044c \u0437\u0430\u0432\u0435\u0440\u0448\u0451\u043d\u043d\u044b\u0435 \u043f\u043b\u0430\u0442\u0435\u0436\u0438 (${completedPayments.length})`}
          </button>
          {showCompletedPayments && (
            <div className="admin-list">
              {completedPayments.slice(0, 50).map((payment) => (
                <article className="admin-item" key={payment.id}>
                  <div className="row-between">
                    <div><p className="title-line">{payment.amount} {payment.currency}</p><p className="muted">{'\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c:'} {payment.user_id.slice(0, 8)}... {'\u00b7'} {payment.status}</p></div>
                    <StatusBadge status={payment.status} />
                  </div>
                </article>
              ))}
              {!completedPayments.length && <p className="muted">{'\u0417\u0430\u0432\u0435\u0440\u0448\u0451\u043d\u043d\u044b\u0445 \u043f\u043b\u0430\u0442\u0435\u0436\u0435\u0439 \u043f\u043e\u043a\u0430 \u043d\u0435\u0442.'}</p>}
            </div>
          )}
        </FoldableSection>

        <FoldableSection title="Последние ключи" subtitle="Быстрый обзор недавно созданных и обновлённых подключений" icon={<KeyRound size={16} />} defaultOpen={false}>
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
        </FoldableSection>
      </div>

      {message && <div className="toast-success">{message}</div>}
    </section>
  );
}


